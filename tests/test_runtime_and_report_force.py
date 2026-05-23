import datetime
import unittest
from unittest.mock import Mock, patch

from sqlmodel import Session, SQLModel, create_engine

from server.batch_jobs import count_batch_job_items_by_status, get_batch_job_item_status_counts
from server.clockin_backfill import build_missing_clockin_day_options
from server.coreApi.MainLogicApi import ApiClient, _clear_ip_restriction_state
from server.models import BatchJobItem
from server import task_runner
from server.task_runner import _submit_report_common
from server.util.Config import ConfigManager
from server.user_runtime import runtime_login_valid


class RuntimeAndManualReportTest(unittest.TestCase):
    def test_runtime_login_valid_accepts_second_precision_expired_time(self):
        self.assertTrue(runtime_login_valid({"token": "abc", "expiredTime": "1893456000"}, now_ms=1760000000000))

    def test_force_report_ignores_disabled_report_switch(self):
        config = Mock()
        config.get_value.side_effect = lambda key: False if key == "config.reportSettings.daily.enabled" else 0
        api_client = Mock()
        api_client.get_job_info.return_value = {"jobId": "job-1"}
        api_client.get_from_info.return_value = []

        result = _submit_report_common(
            api_client=api_client,
            config=config,
            report_type="day",
            title_func=lambda count: f"day-{count}",
            check_time_func=lambda _: False,
            get_submitted_func=lambda: {"flag": 0, "data": []},
            paper_num_key="planInfo.planPaper.dayPaperNum",
            image_count_key="config.reportSettings.daily.imageCount",
            task_name="日报提交",
            form_type=7,
            force_report=True,
            target_period="2026-05-22",
        )

        self.assertNotEqual(result["status"], "skip")

    def test_missing_clockin_can_ignore_scheduled_weekdays_for_manual_makeup(self):
        options = build_missing_clockin_day_options(
            records=[],
            start_date="2026-05-18",
            end_date="2026-05-19",
            scheduled_weekdays=[1],
            respect_scheduled_weekdays=False,
        )

        self.assertEqual([item["value"] for item in options], ["2026-05-19", "2026-05-18"])


class BatchJobQueryTest(unittest.TestCase):
    def test_status_counts_are_grouped_by_database(self):
        engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            session.add_all(
                [
                    BatchJobItem(job_id=1, user_id=101, status="queued"),
                    BatchJobItem(job_id=1, user_id=102, status="queued"),
                    BatchJobItem(job_id=1, user_id=103, status="running"),
                    BatchJobItem(job_id=2, user_id=201, status="queued"),
                ]
            )
            session.commit()

            counts = get_batch_job_item_status_counts(session, 1, ["queued", "running"])
            running = count_batch_job_items_by_status(session, 1, "running")

        self.assertEqual(counts, {"queued": 2, "running": 1})
        self.assertEqual(running, 1)


class ModelDownloadConfigTest(unittest.TestCase):
    def test_default_model_urls_point_to_project_repo(self):
        from server.util import CaptchaUtils

        base_url = "https://raw.githubusercontent.com/27xk/gongxueyun/main/server/models_onnx"
        self.assertEqual(CaptchaUtils.MODEL_BASE_URL, base_url)
        self.assertEqual(CaptchaUtils.MODEL_URLS["ocr.onnx"], f"{base_url}/ocr.onnx")
        self.assertEqual(CaptchaUtils.MODEL_URLS["yolov5n.onnx"], f"{base_url}/yolov5n.onnx")


class FakeMogudingResponse:
    def __init__(self, payload, text="", status_code=200):
        self._payload = payload
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class ApiClientIPRestrictionTest(unittest.TestCase):
    def setUp(self):
        _clear_ip_restriction_state()

    def tearDown(self):
        _clear_ip_restriction_state()

    def test_ip_restricted_403_is_not_treated_as_token_expired(self):
        msg = "IP非法请求过多，已限制访问:111.23.44.229"

        self.assertFalse(ApiClient._is_token_expired_response(403, msg))

    def test_ip_restricted_response_blocks_later_unproxied_requests(self):
        msg = "IP非法请求过多，已限制访问:111.23.44.229"
        with patch("server.coreApi.MainLogicApi.load_global_proxy_settings", return_value={}):
            client = ApiClient(ConfigManager(config={}))
        client.session.post = Mock(return_value=FakeMogudingResponse({"code": 403, "msg": msg}))

        with self.assertRaises(ValueError) as ctx:
            client._post_request("test/path", {}, {})
        with self.assertRaises(ValueError):
            client._post_request("test/path", {}, {})

        self.assertIn("IP非法请求过多", str(ctx.exception))
        self.assertEqual(client.session.post.call_count, 1)

        with patch("server.coreApi.MainLogicApi.load_global_proxy_settings", return_value={}):
            second_client = ApiClient(ConfigManager(config={}))
        second_client.session.post = Mock()
        with self.assertRaises(ValueError):
            second_client._post_request("test/path", {}, {})
        second_client.session.post.assert_not_called()

    def test_ip_restricted_response_rotates_proxy_for_makeup_retry(self):
        msg = "IP非法请求过多，已限制访问:111.23.44.229"
        proxy_api = "http://proxy.example/get?accessName=u&accessPassword=p"
        with patch.dict("os.environ", {"MOGUDING_PROXY_API_URL": proxy_api}, clear=False):
            with patch(
                "server.coreApi.MainLogicApi.requests.get",
                side_effect=[
                    FakeMogudingResponse({}, text="1.2.3.4:5678\n"),
                    FakeMogudingResponse({}, text="5.6.7.8:9012\n"),
                ],
            ):
                client = ApiClient(ConfigManager(config={}))
                client.enable_proxy()
                client.max_retries = 2
                client.session.post = Mock(
                    side_effect=[
                        FakeMogudingResponse({"code": 403, "msg": msg}),
                        FakeMogudingResponse({"code": 200, "msg": "ok"}),
                    ]
                )
                with patch("server.coreApi.MainLogicApi.time.sleep"):
                    result = client._post_request("test/path", {}, {})

        self.assertEqual(result["code"], 200)
        calls = client.session.post.call_args_list
        self.assertEqual(calls[0].kwargs["proxies"]["https"], "http://u:p@1.2.3.4:5678")
        self.assertEqual(calls[1].kwargs["proxies"]["https"], "http://u:p@5.6.7.8:9012")


class TaskRunnerIPRestrictionTest(unittest.TestCase):
    def test_run_task_stops_remaining_moguding_tasks_after_ip_restriction(self):
        config_data = {
            "config": {
                "pushNotifications": [],
                "clockIn": {"schedule": {"startTime": "07:30", "endTime": "18:00"}},
                "reportSettings": {
                    "daily": {"enabled": True},
                    "weekly": {"enabled": True},
                    "monthly": {"enabled": True},
                },
            },
            "userInfo": {"token": "token", "expiredTime": "1893456000", "userType": "student", "nikeName": "tester"},
            "planInfo": {"planId": "plan-1"},
        }
        limited = {"status": "fail", "message": "打卡失败: IP非法请求过多，已限制访问:111.23.44.229", "task_type": "打卡"}

        with (
            patch.object(task_runner, "ApiClient"),
            patch.object(task_runner, "MessagePusher") as pusher_cls,
            patch.object(task_runner, "_load_global_smtp_settings", return_value={}),
            patch.object(task_runner, "perform_clock_in", return_value=limited) as clock_in,
            patch.object(task_runner, "submit_daily_report") as daily,
            patch.object(task_runner, "submit_weekly_report") as weekly,
            patch.object(task_runner, "submit_monthly_report") as monthly,
        ):
            pusher_cls.return_value.push = Mock()
            results = task_runner.run_task_by_config(config_data, forced_checkin_type="START")

        self.assertEqual(results, [limited])
        clock_in.assert_called_once()
        daily.assert_not_called()
        weekly.assert_not_called()
        monthly.assert_not_called()


if __name__ == "__main__":
    unittest.main()
