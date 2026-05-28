import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FrontendTenantLoginTest(unittest.TestCase):
    def read_web_file(self, relative_path: str) -> str:
        return (ROOT / "web" / "src" / relative_path).read_text(encoding="utf-8")

    def test_admin_login_submits_tenant_id(self):
        source = self.read_web_file("views/Login.vue")

        self.assertIn("tenant_id", source)
        self.assertIn("v-model=\"form.tenant_id\"", source)
        self.assertIn("tenant_id: form.tenant_id", source)

    def test_admin_login_submits_optional_mfa_code(self):
        source = self.read_web_file("views/Login.vue")

        self.assertIn("v-model=\"form.mfa_code\"", source)
        self.assertIn("autocomplete=\"one-time-code\"", source)
        self.assertIn("mfa_code: form.mfa_code || undefined", source)

    def test_admin_security_page_exposes_mfa_controls(self):
        router_source = self.read_web_file("router/index.js")
        app_source = self.read_web_file("App.vue")
        security_source = self.read_web_file("views/SecuritySettings.vue")

        self.assertIn("SecuritySettings.vue", router_source)
        self.assertIn("/security", router_source)
        self.assertIn("账号安全", app_source)
        self.assertIn("/auth/mfa/status", security_source)
        self.assertIn("/auth/mfa/setup", security_source)
        self.assertIn("password: setupForm.password", security_source)
        self.assertIn("/auth/mfa/enable", security_source)
        self.assertIn("/auth/mfa/disable", security_source)
        self.assertIn("useAuthStore", security_source)
        self.assertIn("router.replace('/login')", security_source)

    def test_user_login_and_register_submit_tenant_id(self):
        login_source = self.read_web_file("views/user/UserLogin.vue")
        register_source = self.read_web_file("views/user/UserRegister.vue")

        for source in (login_source, register_source):
            self.assertIn("tenant_id", source)
            self.assertIn("v-model=\"form.tenant_id\"", source)
            self.assertIn("tenant_id: form.tenant_id", source)

    def test_tenant_metadata_is_persisted_without_tokens(self):
        admin_store = self.read_web_file("stores/auth.js")
        user_store = self.read_web_file("stores/userAuth.js")

        self.assertIn("tenantId", admin_store)
        self.assertIn("tenantId", user_store)
        self.assertNotIn("token:", admin_store)
        self.assertNotIn("token:", user_store)

    def test_user_register_password_rule_matches_backend_minimum(self):
        source = self.read_web_file("views/user/UserRegister.vue")

        self.assertIn("form.password.length < 10", source)
        self.assertNotIn("form.password.length < 6", source)
        self.assertIn("密码至少 10 位", source)


if __name__ == "__main__":
    unittest.main()
