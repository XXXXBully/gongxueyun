import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import inspect, text

DATABASE_URL_ENV = "DATABASE_URL"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"


def _load_project_dotenv() -> None:
    load_dotenv(DOTENV_PATH, override=False, encoding="utf-8-sig")


def _get_database_url() -> str:
    database_url = (os.getenv(DATABASE_URL_ENV) or "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required and must be a MySQL connection string")
    if not database_url.lower().startswith("mysql+pymysql://"):
        raise RuntimeError("Only MySQL is supported. DATABASE_URL must start with 'mysql+pymysql://'")
    return database_url


_load_project_dotenv()

engine = create_engine(
    _get_database_url(),
    pool_pre_ping=True,
)


def ensure_user_runtime_columns(db_engine) -> None:
    inspector = inspect(db_engine)
    table_names = set(inspector.get_table_names())
    if "user" not in table_names:
        return

    existing_columns = {column.get("name") for column in inspector.get_columns("user")}
    missing_columns = [
        column_name for column_name in ["userInfo", "planInfo"] if column_name not in existing_columns
    ]
    if not missing_columns:
        return

    with db_engine.begin() as conn:
        for column_name in missing_columns:
            conn.execute(text(f"ALTER TABLE `user` ADD COLUMN `{column_name}` JSON NULL"))


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    ensure_user_runtime_columns(engine)


def get_session():
    with Session(engine) as session:
        yield session
