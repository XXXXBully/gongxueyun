import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = ROOT / "docs" / "api" / "openapi-contract.json"


class OpenAPIContractTest(unittest.TestCase):
    def test_openapi_contract_snapshot_is_current(self):
        from scripts.openapi_contract import build_openapi_contract
        from server.main import app

        self.assertTrue(SNAPSHOT_PATH.exists(), "OpenAPI contract snapshot is missing")
        expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        actual = build_openapi_contract(app.openapi())

        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
