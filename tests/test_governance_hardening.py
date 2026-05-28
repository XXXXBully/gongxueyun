import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlmodel import Session, SQLModel, create_engine, select

from server import api
from server.models import AuditLog, User


class GovernanceHardeningTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(self.engine)

    def test_audit_log_purge_is_disabled_by_default(self):
        with Session(self.engine) as session:
            session.add(AuditLog(actor="admin", action="probe", target_user_id=None, detail={}))
            session.commit()

            with patch.dict("os.environ", {"ALLOW_AUDIT_LOG_PURGE": ""}, clear=False):
                with self.assertRaises(HTTPException) as ctx:
                    api.clear_audit_logs(session=session, admin={"sub": "admin"})

            self.assertEqual(ctx.exception.status_code, 403)
            self.assertEqual(len(session.exec(select(AuditLog)).all()), 1)

    def test_delete_user_soft_deletes_and_keeps_audit_trail(self):
        with Session(self.engine) as session:
            user = User(phone="13800000000", password="encrypted-password")
            session.add(user)
            session.commit()
            session.refresh(user)

            result = api.delete_user(session=session, user_id=user.id, admin={"sub": "admin"})

            deleted = session.get(User, user.id)
            self.assertEqual(result["ok"], True)
            self.assertIsNotNone(deleted)
            self.assertIsNotNone(deleted.deleted_at)
            self.assertFalse(deleted.app_enabled)
            self.assertFalse(deleted.enable_clockin)
            logs = session.exec(select(AuditLog).where(AuditLog.action == "user.soft_delete")).all()
            self.assertEqual(len(logs), 1)

    def test_user_detail_is_tenant_scoped(self):
        with Session(self.engine) as session:
            user = User(phone="13800000000", password="encrypted-password", tenant_id="default")
            session.add(user)
            session.commit()
            session.refresh(user)

            with self.assertRaises(HTTPException) as ctx:
                api.read_user(
                    session=session,
                    user_id=user.id,
                    viewer={"sub": "operator", "role": "operator", "tenant_id": "acme"},
                )

            self.assertEqual(ctx.exception.status_code, 404)

    def test_user_update_is_tenant_scoped(self):
        with Session(self.engine) as session:
            user = User(phone="13800000001", password="encrypted-password", tenant_id="default")
            session.add(user)
            session.commit()
            session.refresh(user)

            with self.assertRaises(HTTPException) as ctx:
                api.update_user(
                    session=session,
                    user_id=user.id,
                    user_update=api.UserUpdate(remark="cross-tenant-write"),
                    operator={"sub": "operator", "role": "operator", "tenant_id": "acme"},
                )

            self.assertEqual(ctx.exception.status_code, 404)
            self.assertNotEqual(session.get(User, user.id).remark, "cross-tenant-write")

    def test_app_registration_can_be_disabled_by_policy(self):
        from server import api

        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
        response = SimpleNamespace(headers={}, set_cookie=lambda *args, **kwargs: None)
        req = api.AppRegisterRequest(phone="13800000000", password="strong-pass", tenant_id="default")

        with patch.dict("os.environ", {"APP_REGISTRATION_ENABLED": "false"}, clear=False):
            with self.assertRaises(HTTPException) as ctx:
                api.app_register(request=request, response=response, req=req)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_short_app_password_is_rejected(self):
        from server import api

        request = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
        response = SimpleNamespace(headers={}, set_cookie=lambda *args, **kwargs: None)
        req = api.AppRegisterRequest(phone="13800000001", password="short", tenant_id="default")

        with patch.dict("os.environ", {"APP_REGISTRATION_ENABLED": "true"}, clear=False):
            with self.assertRaises(HTTPException) as ctx:
                api.app_register(request=request, response=response, req=req)

        self.assertEqual(ctx.exception.status_code, 400)

    def test_batch_run_rejects_duplicate_and_oversized_requests(self):
        from server import api

        with Session(self.engine) as session:
            session.add(User(tenant_id="default", phone="13800000010", password="encrypted"))
            session.add(User(tenant_id="default", phone="13800000011", password="encrypted"))
            session.commit()

            with patch.dict("os.environ", {"BATCH_JOB_MAX_USERS": "1"}, clear=False):
                with patch("server.api.engine", self.engine):
                    with self.assertRaises(HTTPException) as ctx:
                        api.run_users_batch(
                            request=SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1")),
                            req=api.BatchRunRequest(ids=[1, 1], concurrency=1),
                            operator={"sub": "operator", "role": "operator", "tenant_id": "default"},
                        )

        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
