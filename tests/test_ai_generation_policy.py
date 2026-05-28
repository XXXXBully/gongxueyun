import socket
import unittest
from unittest.mock import patch

from server.coreApi.AiServiceClient import _ai_endpoint_detail, _validate_ai_endpoint_policy, generate_article


class FakeAIResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": "这是一段符合要求的实习日报内容。"}}]}


class FakeConfig:
    def get_value(self, key):
        values = {
            "config.ai.apikey": "test-key",
            "config.ai.apiUrl": "https://api.example.com",
            "config.ai.model": "test-model",
            "userInfo.orgJson.majorName": "软件工程",
        }
        return values.get(key)


class AIGenerationPolicyTest(unittest.TestCase):
    def test_private_url_is_rejected_by_default(self):
        with patch.dict("os.environ", {"AI_ALLOWED_HOSTS": "", "ALLOW_PRIVATE_AI_ENDPOINTS": ""}, clear=False):
            with self.assertRaises(ValueError):
                _validate_ai_endpoint_policy("http://127.0.0.1:8080/v1/chat/completions")

    def test_private_url_requires_explicit_opt_in_and_allowlist(self):
        with patch.dict(
            "os.environ",
            {
                "ALLOW_PRIVATE_AI_ENDPOINTS": "true",
                "AI_ALLOWED_HOSTS": "127.0.0.1,ai.internal",
            },
            clear=False,
        ):
            detail = _validate_ai_endpoint_policy("http://127.0.0.1:8080/v1/chat/completions")

        self.assertEqual(detail["host"], "127.0.0.1")

    def test_allowlist_blocks_unlisted_host_without_special_casing_private_ips(self):
        with patch.dict("os.environ", {"ALLOW_PRIVATE_AI_ENDPOINTS": "true", "AI_ALLOWED_HOSTS": "127.0.0.1,ai.internal"}, clear=False):
            with self.assertRaises(ValueError):
                _validate_ai_endpoint_policy("http://192.168.1.20:8080/v1/chat/completions")

    def test_endpoint_detail_never_contains_api_key(self):
        detail = _ai_endpoint_detail("http://user:secret@127.0.0.1:8080/v1/chat/completions")

        self.assertEqual(detail["host"], "127.0.0.1")
        self.assertNotIn("secret", str(detail))

    def test_generate_article_pins_validated_dns_and_uses_short_timeout(self):
        resolve_calls = []

        def fake_getaddrinfo(host, port, *args, **kwargs):
            resolve_calls.append((host, port))
            if len(resolve_calls) == 1:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", int(port)))]
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", int(port)))]

        def fake_post(url, **kwargs):
            self.assertLessEqual(kwargs["timeout"], 60)
            resolved = socket.getaddrinfo("api.example.com", 443, type=socket.SOCK_STREAM)
            self.assertEqual(resolved[0][4][0], "93.184.216.34")
            return FakeAIResponse()

        with (
            patch.dict("os.environ", {"AI_ALLOWED_HOSTS": "", "ALLOW_PRIVATE_AI_ENDPOINTS": ""}, clear=False),
            patch("server.coreApi.AiServiceClient.socket.getaddrinfo", side_effect=fake_getaddrinfo),
            patch("server.coreApi.AiServiceClient.requests.post", side_effect=fake_post),
        ):
            content = generate_article(FakeConfig(), "日报", {"practiceCompanyEntity": {}}, count=50)

        self.assertIn("实习日报", content)


if __name__ == "__main__":
    unittest.main()
