import unittest

from sqlmodel import Session, select
from sqlmodel import SQLModel, create_engine


class ObservabilityTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        from server.models import TaskExecutionEvent, TaskExecutionLock

        SQLModel.metadata.create_all(self.engine)

    def test_records_task_event_and_returns_metrics(self):
        from server.observability import record_task_event, runtime_metrics

        record_task_event(
            source="scheduler",
            event="finish",
            task_key="scheduler:user:1:clock_in:START",
            user_id=1,
            status="success",
            duration_ms=12,
            db_engine=self.engine,
        )

        metrics = runtime_metrics(db_engine=self.engine)

        self.assertEqual(metrics["task_events"]["by_status"]["success"], 1)
        self.assertIn("generated_at", metrics)

    def test_prometheus_metrics_text_is_exposed(self):
        from server.observability import prometheus_metrics_text, record_task_event

        record_task_event(
            source="scheduler",
            event="finish",
            task_key="scheduler:user:1:clock_in:START",
            user_id=1,
            status="success",
            duration_ms=12,
            db_engine=self.engine,
        )

        text = prometheus_metrics_text(db_engine=self.engine)

        self.assertIn('automoguding_task_events_total{status="success"} 1', text)
        self.assertIn("automoguding_locks_active", text)

    def test_static_and_health_paths_do_not_write_http_request_metrics(self):
        from server.models import HttpRequestMetric
        from server.observability import record_http_request

        record_http_request(method="GET", path="/assets/index.js", status_code=200, duration_ms=1, db_engine=self.engine)
        record_http_request(method="GET", path="/healthz", status_code=200, duration_ms=1, db_engine=self.engine)
        record_http_request(method="GET", path="/api/users", status_code=200, duration_ms=3, db_engine=self.engine)

        with Session(self.engine) as session:
            rows = session.exec(select(HttpRequestMetric)).all()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].path, "/api/users")


if __name__ == "__main__":
    unittest.main()
