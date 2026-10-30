import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, monkeypatch):
    database_path = tmp_path / "test.db"
    backup_dir = tmp_path / "backups"
    invalid_log = tmp_path / "invalid_records.jsonl"
    backup_dir.mkdir()
    monkeypatch.setattr("app.database.DATABASE_PATH", database_path)
    monkeypatch.setattr("app.settings.DATABASE_PATH", database_path)
    monkeypatch.setattr("app.settings.BACKUP_DIR", backup_dir)
    monkeypatch.setattr("app.avro_io.BACKUP_DIR", backup_dir)
    monkeypatch.setattr("app.settings.INVALID_LOG_PATH", invalid_log)
    monkeypatch.setattr("app.validation.INVALID_LOG_PATH", invalid_log)

    from app.database import initialize_database

    initialize_database()
    return {
        "database": database_path,
        "backup_dir": backup_dir,
        "invalid_log": invalid_log,
    }


@pytest.fixture
def client(isolated_storage):
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
