import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("SCAN_API_KEY", "live-scan-key-123456789")
    monkeypatch.setenv("ADMIN_API_KEY", "live-admin-key-123456789")
    monkeypatch.setenv("JWT_SECRET_KEY", "live-jwt-secret-key-123456789")
    monkeypatch.setenv("EXPORT_DIR", str(tmp_path / "exports"))

    from core.config import reset_settings
    from core.database import SessionLocal, create_schema_for_testing, init_database, reset_database_state
    from core.bootstrap import bootstrap_defaults

    reset_settings()
    reset_database_state()
    init_database()
    create_schema_for_testing()
    bootstrap_defaults()
    with SessionLocal() as session:
        yield session
