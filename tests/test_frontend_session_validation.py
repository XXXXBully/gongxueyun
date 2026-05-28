import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FrontendSessionValidationTest(unittest.TestCase):
    def read_web_file(self, relative_path: str) -> str:
        return (ROOT / "web" / "src" / relative_path).read_text(encoding="utf-8")

    def test_admin_store_validates_cookie_session_against_backend(self):
        source = self.read_web_file("stores/auth.js")

        self.assertIn("validateSession", source)
        self.assertIn("fetch('/api/auth/me'", source)
        self.assertIn("permissions", source)
        self.assertNotIn("if (!this.authed)", source)
        self.assertIn("sessionChecked: false", source)
        self.assertNotIn("sessionChecked: meta.sessionChecked === true", source)
        self.assertNotIn("sessionChecked: this.sessionChecked", source)

    def test_user_store_validates_cookie_session_against_backend(self):
        source = self.read_web_file("stores/userAuth.js")

        self.assertIn("validateSession", source)
        self.assertIn("fetch('/api/app/me'", source)
        self.assertNotIn("if (!this.authed)", source)
        self.assertIn("sessionChecked: false", source)
        self.assertNotIn("sessionChecked: meta.sessionChecked === true", source)
        self.assertNotIn("sessionChecked: this.sessionChecked", source)

    def test_router_waits_for_session_validation_before_allowing_private_routes(self):
        source = self.read_web_file("router/index.js")

        self.assertIn("beforeEach(async", source)
        self.assertIn("await auth.validateSession()", source)
        self.assertIn("await userAuth.validateSession()", source)
        self.assertNotIn("auth.isAuthed && !auth.sessionChecked", source)
        self.assertNotIn("userAuth.isAuthed && !userAuth.sessionChecked", source)

    def test_router_uses_permission_points_for_admin_routes(self):
        source = self.read_web_file("router/index.js")

        self.assertIn("permissions: ['audit:read']", source)
        self.assertIn("permissions: ['users:read']", source)
        self.assertIn("auth.can(permission)", source)

    def test_api_clients_attach_csrf_token_for_unsafe_cookie_requests(self):
        admin_http = self.read_web_file("api/http.js")
        user_http = self.read_web_file("api/userHttp.js")

        for source in (admin_http, user_http):
            self.assertIn("csrf_token", source)
            self.assertIn("X-CSRF-Token", source)
            self.assertIn("interceptors.request.use", source)


if __name__ == "__main__":
    unittest.main()
