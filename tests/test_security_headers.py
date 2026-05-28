import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from starlette.responses import Response


class SecurityHeadersTest(unittest.TestCase):
    def test_default_security_headers_include_csp(self):
        from server.security import apply_security_headers

        response = Response()

        apply_security_headers(response)

        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertIn("frame-src 'self' https://www.mapchaxun.cn", response.headers["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_hsts_can_be_enabled_for_https_deployments(self):
        from server.security import apply_security_headers

        response = Response()

        with patch.dict("os.environ", {"ENABLE_HSTS": "true"}, clear=False):
            apply_security_headers(response)

        self.assertIn("max-age=", response.headers["Strict-Transport-Security"])

    def test_hsts_is_enabled_by_default_in_production_and_can_be_disabled(self):
        from server.security import apply_security_headers

        production_response = Response()
        disabled_response = Response()

        with patch.dict("os.environ", {"APP_ENV": "production", "ENABLE_HSTS": ""}, clear=False):
            apply_security_headers(production_response)
        with patch.dict("os.environ", {"APP_ENV": "production", "ENABLE_HSTS": "false"}, clear=False):
            apply_security_headers(disabled_response)

        self.assertIn("max-age=", production_response.headers["Strict-Transport-Security"])
        self.assertNotIn("Strict-Transport-Security", disabled_response.headers)

    def test_metrics_requires_token_in_production(self):
        from server.security import require_metrics_access

        request = SimpleNamespace(headers={})

        with patch.dict("os.environ", {"APP_ENV": "production", "METRICS_AUTH_TOKEN": ""}, clear=False):
            with self.assertRaises(HTTPException) as ctx:
                require_metrics_access(request)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_metrics_accepts_configured_token(self):
        from server.security import require_metrics_access

        request = SimpleNamespace(headers={"x-metrics-token": "secret-token"})

        with patch.dict("os.environ", {"APP_ENV": "production", "METRICS_AUTH_TOKEN": "secret-token"}, clear=False):
            self.assertIsNone(require_metrics_access(request))

    def test_api_docs_are_disabled_by_default_in_production(self):
        from server.main import _should_expose_api_docs

        with patch.dict("os.environ", {"APP_ENV": "production"}, clear=False):
            self.assertFalse(_should_expose_api_docs())
        with patch.dict("os.environ", {"APP_ENV": "development"}, clear=False):
            self.assertTrue(_should_expose_api_docs())

    def test_wildcard_cors_is_rejected_in_production_by_default(self):
        from server.main import _resolve_cors_origins

        with patch.dict(
            "os.environ",
            {"APP_ENV": "production", "FRONTEND_ORIGINS": "*", "ALLOW_WILDCARD_CORS": ""},
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                _resolve_cors_origins()

        with patch.dict(
            "os.environ",
            {"APP_ENV": "production", "FRONTEND_ORIGINS": "*", "ALLOW_WILDCARD_CORS": "true"},
            clear=False,
        ):
            self.assertEqual(_resolve_cors_origins(), ["*"])


if __name__ == "__main__":
    unittest.main()
