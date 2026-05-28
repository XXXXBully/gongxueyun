import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from sqlmodel import Session, SQLModel, create_engine, select

from server import api
from server.auth import hash_password, totp_code
from server.models import AdminUser, AuditLog


class AdminMfaTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        SQLModel.metadata.create_all(self.engine)
        self.payload = {"sub": "admin", "role": "admin", "tenant_id": "default"}
        self.request = SimpleNamespace(headers={}, client=SimpleNamespace(host="203.0.113.10"))
        self.response = SimpleNamespace(headers={}, set_cookie=lambda *args, **kwargs: None)

    def test_admin_can_setup_enable_and_login_with_totp(self):
        with Session(self.engine) as session:
            session.add(AdminUser(username="admin", password_hash=hash_password("correct-password-123"), role="admin"))
            session.commit()

            setup = api.admin_mfa_setup(
                session=session,
                payload=self.payload,
                req=api.MfaSetupRequest(password="correct-password-123"),
            )
            self.assertIn("otpauth://totp/", setup["otpauth_uri"])
            self.assertNotIn("apikey", str(setup).lower())
            self.assertFalse(api.admin_mfa_status(session=session, payload=self.payload)["mfa_enabled"])

            code = totp_code(setup["secret"])
            enabled = api.admin_mfa_enable(session=session, payload=self.payload, req=api.MfaCodeRequest(code=code))
            self.assertTrue(enabled["mfa_enabled"])
            self.assertTrue(api.admin_mfa_status(session=session, payload=self.payload)["mfa_enabled"])

        with (
            patch("server.api.engine", self.engine),
            patch("server.api._rate_limit", lambda *args, **kwargs: None),
            patch.dict("os.environ", {"APP_SECRET": "test-secret-value-with-more-than-thirty-two-chars"}, clear=False),
        ):
            with self.assertRaises(HTTPException) as missing_ctx:
                api.admin_login(
                    request=self.request,
                    response=self.response,
                    req=api.LoginRequest(username="admin", password="correct-password-123", tenant_id="default"),
                )
            result = api.admin_login(
                request=self.request,
                response=self.response,
                req=api.LoginRequest(
                    username="admin",
                    password="correct-password-123",
                    tenant_id="default",
                    mfa_code=code,
                ),
            )

        self.assertEqual(missing_ctx.exception.status_code, 401)
        self.assertEqual(result["role"], "admin")

    def test_invalid_mfa_code_is_audited_and_does_not_login(self):
        with Session(self.engine) as session:
            session.add(AdminUser(username="admin", password_hash=hash_password("correct-password-123"), role="admin"))
            session.commit()
            setup = api.admin_mfa_setup(
                session=session,
                payload=self.payload,
                req=api.MfaSetupRequest(password="correct-password-123"),
            )
            api.admin_mfa_enable(session=session, payload=self.payload, req=api.MfaCodeRequest(code=totp_code(setup["secret"])))

        with (
            patch("server.api.engine", self.engine),
            patch("server.api._rate_limit", lambda *args, **kwargs: None),
            patch.dict("os.environ", {"APP_SECRET": "test-secret-value-with-more-than-thirty-two-chars"}, clear=False),
        ):
            with self.assertRaises(HTTPException):
                api.admin_login(
                    request=self.request,
                    response=self.response,
                    req=api.LoginRequest(
                        username="admin",
                        password="correct-password-123",
                        tenant_id="default",
                        mfa_code="000000",
                    ),
                )

        with Session(self.engine) as session:
            logs = session.exec(select(AuditLog).where(AuditLog.action == "auth.mfa.failed")).all()

        self.assertEqual(len(logs), 1)
        self.assertNotIn("correct-password-123", str(logs[0].detail))

    def test_mfa_setup_requires_admin_permission_and_current_password(self):
        with Session(self.engine) as session:
            session.add(AdminUser(username="admin", password_hash=hash_password("correct-password-123"), role="admin"))
            session.commit()

            with self.assertRaises(HTTPException) as wrong_password:
                api.admin_mfa_setup(
                    session=session,
                    payload=self.payload,
                    req=api.MfaSetupRequest(password="bad-password"),
                )

            with self.assertRaises(HTTPException) as viewer_payload:
                api.admin_mfa_setup(
                    session=session,
                    payload={"sub": "admin", "role": "viewer", "tenant_id": "default"},
                    req=api.MfaSetupRequest(password="correct-password-123"),
                )

        self.assertEqual(wrong_password.exception.status_code, 401)
        self.assertEqual(viewer_payload.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
