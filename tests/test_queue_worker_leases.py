import datetime
import unittest
from unittest.mock import patch

from sqlmodel import Session, SQLModel, create_engine

from server.models import BatchJob, BatchJobItem, Tenant, User


class QueueWorkerLeaseTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(self.engine)

    def test_claim_batch_job_items_records_lease_token(self):
        from server.batch_jobs import claim_batch_job_items

        now = datetime.datetime(2026, 5, 28, 12, 0, 0)
        with Session(self.engine) as session:
            job = BatchJob(created_by="test", total=1, concurrency=1, user_ids=[1])
            session.add(job)
            session.commit()
            session.refresh(job)
            item = BatchJobItem(job_id=job.id, user_id=1, status="queued")
            session.add(item)
            session.commit()

            claims = claim_batch_job_items(
                session,
                job.id,
                capacity=1,
                now=now,
                owner="worker-a",
                lease_seconds=30,
                return_claims=True,
            )
            session.refresh(item)

        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["item_id"], item.id)
        self.assertEqual(item.locked_by, "worker-a")
        self.assertEqual(item.lock_token, claims[0]["lock_token"])
        self.assertEqual(item.heartbeat_at, now)
        self.assertEqual(item.lease_until, now + datetime.timedelta(seconds=30))

    def test_finalize_item_ignores_stale_lease_token(self):
        from server.queue_worker import _finalize_item

        with Session(self.engine) as session:
            job = BatchJob(created_by="test", status="running", total=1, concurrency=1, user_ids=[1])
            session.add(job)
            session.commit()
            session.refresh(job)
            item = BatchJobItem(job_id=job.id, user_id=1, status="running", lock_token="new-token")
            session.add(item)
            session.commit()
            session.refresh(job)
            session.refresh(item)
            job_id = job.id
            item_id = item.id

        with patch("server.queue_worker.engine", self.engine):
            _finalize_item(job_id, item_id, ok=True, error=None, lock_token="old-token")

        with Session(self.engine) as session:
            job = session.get(BatchJob, job_id)
            item = session.get(BatchJobItem, item_id)

        self.assertEqual(item.status, "running")
        self.assertEqual(item.lock_token, "new-token")
        self.assertEqual(job.completed, 0)

    def test_touch_item_lease_extends_only_matching_token(self):
        from server.queue_worker import _touch_item_lease

        first_seen = datetime.datetime(2026, 5, 28, 12, 0, 0)
        next_seen = datetime.datetime(2026, 5, 28, 12, 1, 0)
        with Session(self.engine) as session:
            job = BatchJob(created_by="test", status="running", total=1, concurrency=1, user_ids=[1])
            session.add(job)
            session.commit()
            session.refresh(job)
            item = BatchJobItem(
                job_id=job.id,
                user_id=1,
                status="running",
                lock_token="live-token",
                heartbeat_at=first_seen,
                lease_until=first_seen + datetime.timedelta(seconds=30),
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            item_id = item.id

        stale_ok = _touch_item_lease(
            item_id,
            "stale-token",
            db_engine=self.engine,
            now=next_seen,
            timeout_seconds=90,
        )
        live_ok = _touch_item_lease(
            item_id,
            "live-token",
            db_engine=self.engine,
            now=next_seen,
            timeout_seconds=90,
        )

        with Session(self.engine) as session:
            item = session.get(BatchJobItem, item_id)

        self.assertFalse(stale_ok)
        self.assertTrue(live_ok)
        self.assertEqual(item.heartbeat_at, next_seen)
        self.assertEqual(item.lease_until, next_seen + datetime.timedelta(seconds=90))

    def test_run_item_rejects_cross_tenant_user_reference(self):
        from server.queue_worker import _run_item

        with Session(self.engine) as session:
            user = User(tenant_id="default", phone="17700000000", password="encrypted")
            session.add(user)
            session.commit()
            session.refresh(user)
            job = BatchJob(tenant_id="acme", created_by="operator", status="running", total=1, concurrency=1, user_ids=[user.id])
            session.add(job)
            session.commit()
            session.refresh(job)
            item = BatchJobItem(
                tenant_id="acme",
                job_id=job.id,
                user_id=user.id,
                status="running",
                lock_token="live-token",
                max_attempts=1,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            job_id = job.id
            item_id = item.id

        with patch("server.queue_worker.engine", self.engine):
            with patch("server.queue_worker.run_task_by_config", return_value=[]) as runner:
                _run_item(job_id, item_id, lock_token="live-token")

        with Session(self.engine) as session:
            item = session.get(BatchJobItem, item_id)

        runner.assert_not_called()
        self.assertEqual(item.status, "fail")
        self.assertIn("tenant", item.error)

    def test_run_item_rejects_cross_tenant_job_item_reference(self):
        from server.queue_worker import _run_item

        with Session(self.engine) as session:
            user = User(tenant_id="acme", phone="18800000000", password="encrypted")
            session.add(user)
            session.commit()
            session.refresh(user)
            job = BatchJob(tenant_id="default", created_by="operator", status="running", total=1, concurrency=1, user_ids=[user.id])
            session.add(job)
            session.commit()
            session.refresh(job)
            item = BatchJobItem(
                tenant_id="acme",
                job_id=job.id,
                user_id=user.id,
                status="running",
                lock_token="live-token",
                max_attempts=1,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            job_id = job.id
            item_id = item.id

        with patch("server.queue_worker.engine", self.engine):
            with patch("server.queue_worker.run_task_by_config", return_value=[]) as runner:
                _run_item(job_id, item_id, lock_token="live-token")

        with Session(self.engine) as session:
            item = session.get(BatchJobItem, item_id)

        runner.assert_not_called()
        self.assertEqual(item.status, "fail")
        self.assertIn("tenant", item.error)

    def test_run_item_rejects_disabled_tenant(self):
        from server.queue_worker import _run_item

        with Session(self.engine) as session:
            session.add(Tenant(id="acme", name="Acme", status="disabled"))
            user = User(tenant_id="acme", phone="19900000000", password="encrypted")
            session.add(user)
            session.commit()
            session.refresh(user)
            job = BatchJob(tenant_id="acme", created_by="operator", status="running", total=1, concurrency=1, user_ids=[user.id])
            session.add(job)
            session.commit()
            session.refresh(job)
            item = BatchJobItem(
                tenant_id="acme",
                job_id=job.id,
                user_id=user.id,
                status="running",
                lock_token="live-token",
                max_attempts=1,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            job_id = job.id
            item_id = item.id

        with patch("server.queue_worker.engine", self.engine):
            with patch("server.queue_worker.run_task_by_config", return_value=[]) as runner:
                _run_item(job_id, item_id, lock_token="live-token")

        with Session(self.engine) as session:
            item = session.get(BatchJobItem, item_id)

        runner.assert_not_called()
        self.assertEqual(item.status, "fail")
        self.assertIn("disabled", item.error)


if __name__ == "__main__":
    unittest.main()
