import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


class MigrationsContractTest(unittest.TestCase):
    def test_alembic_files_exist(self):
        root = Path(__file__).resolve().parents[1]

        self.assertTrue((root / "alembic.ini").exists())
        self.assertTrue((root / "server" / "migrations" / "env.py").exists())
        versions = list((root / "server" / "migrations" / "versions").glob("*.py"))
        self.assertTrue(versions)

    def test_baseline_revision_imports(self):
        root = Path(__file__).resolve().parents[1]
        versions = list((root / "server" / "migrations" / "versions").glob("*.py"))
        spec = importlib.util.spec_from_file_location("baseline_migration", versions[0])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertTrue(callable(module.upgrade))
        self.assertTrue(callable(module.downgrade))

    def test_upgrade_existing_legacy_user_table_adds_runtime_columns(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "legacy.db"
            engine = create_engine(f"sqlite:///{db_path}")
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "CREATE TABLE user ("
                        "id INTEGER PRIMARY KEY, "
                        "phone VARCHAR(255) NOT NULL, "
                        "password TEXT NOT NULL"
                        ")"
                    )
                )
            engine.dispose()

            env = dict(os.environ)
            env["DATABASE_URL"] = f"sqlite:///{db_path}"
            subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=root,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )

            columns = {item["name"] for item in inspect(engine).get_columns("user")}
            tables = set(inspect(engine).get_table_names())
            engine.dispose()
            self.assertIn("tenant", tables)
            self.assertIn("userInfo", columns)
            self.assertIn("planInfo", columns)
            self.assertIn("tenant_id", columns)
            self.assertIn("deleted_at", columns)
            self.assertIn("deleted_by", columns)
            self.assertIn("delete_reason", columns)


if __name__ == "__main__":
    unittest.main()
