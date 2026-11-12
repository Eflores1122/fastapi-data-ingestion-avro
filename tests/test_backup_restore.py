import json

from fastavro import writer

from app.avro_io import SCHEMAS, backup_table, restore_table
from app.database import get_connection, initialize_database
from app.repository import fetch_all, insert_records


def test_backup_and_restore_roundtrip_replaces_current_row(client):
    created = client.post("/ingest/departments", json=[{"id": 1, "department": "Sales"}])
    assert created.status_code == 200

    backup = client.post("/backup/departments")
    assert backup.status_code == 200
    body = backup.json()
    assert body["table"] == "departments"
    assert body["records"] == 1
    assert body["path"].endswith(".avro")

    changed = client.post("/ingest/departments", json=[{"id": 1, "department": "Changed"}])
    assert changed.status_code == 200

    restored = client.post("/restore/departments", json={"file_path": body["path"]})
    assert restored.status_code == 200
    assert restored.json() == {
        "table": "departments",
        "restored": 1,
        "path": body["path"],
    }
    with get_connection() as connection:
        assert fetch_all(connection, "departments") == [{"id": 1, "department": "Sales"}]


def test_restore_requires_a_file_path(client):
    missing = client.post("/restore/departments", json={})
    blank = client.post("/restore/departments", json={"file_path": ""})
    spaces = client.post("/restore/departments", json={"file_path": "   "})
    number = client.post("/restore/departments", json={"file_path": 12})
    assert missing.status_code == 422
    assert missing.json() == {"detail": "file_path is required"}
    assert blank.json() == {"detail": "file_path is required"}
    assert spaces.json() == {"detail": "file_path is required"}
    assert number.json() == {"detail": "file_path is required"}


def test_restore_unknown_table_and_missing_file(client, isolated_storage):
    unknown = client.post("/backup/locations")
    assert unknown.status_code == 404

    missing = isolated_storage["backup_dir"] / "missing.avro"
    response = client.post("/restore/jobs", json={"file_path": str(missing)})
    assert response.status_code == 422
    assert str(missing) in response.json()["detail"]

    corrupt = isolated_storage["backup_dir"] / "corrupt.avro"
    corrupt.write_bytes(b"not an avro file")
    broken = client.post("/restore/jobs", json={"file_path": str(corrupt)})
    assert broken.status_code == 422


def test_failed_restore_rolls_back_rows_and_keeps_the_log_line(client, isolated_storage):
    created = client.post("/ingest/departments", json=[{"id": 1, "department": "Sales"}])
    assert created.status_code == 200

    path = isolated_storage["backup_dir"] / "departments_bad.avro"
    with path.open("wb") as file:
        writer(
            file,
            SCHEMAS["departments"],
            [
                {"id": 2, "department": "Legal"},
                {"id": 3, "department": ""},
            ],
        )

    response = client.post("/restore/departments", json={"file_path": str(path)})
    assert response.status_code == 422
    assert response.json()["detail"] == "Restore rejected 1 records"

    with get_connection() as connection:
        assert fetch_all(connection, "departments") == [{"id": 1, "department": "Sales"}]
        invalid = connection.execute("SELECT COUNT(*) FROM invalid_records").fetchone()[0]
    assert invalid == 0
    logged = json.loads(isolated_storage["invalid_log"].read_text(encoding="utf-8"))
    assert logged["table"] == "departments"
    assert logged["errors"] == ["department is required"]


def test_restore_accepts_more_rows_than_the_ingest_endpoint(monkeypatch, tmp_path):
    records = [{"id": index, "department": f"Department {index}"} for index in range(1, 1002)]
    with get_connection() as connection:
        first = insert_records(connection, "departments", records[:1000])
        second = insert_records(connection, "departments", records[1000:])
        assert first["inserted"] == 1000
        assert second["inserted"] == 1
        backup = backup_table(connection, "departments")
    assert backup["records"] == 1001

    monkeypatch.setattr("app.database.DATABASE_PATH", tmp_path / "restored.db")
    initialize_database()
    with get_connection() as connection:
        result = restore_table(connection, "departments", backup["path"])
        assert result["restored"] == 1001
        assert fetch_all(connection, "departments") == records


def test_empty_backup_restores_zero_rows(client):
    backup = client.post("/backup/jobs")
    assert backup.status_code == 200
    assert backup.json()["records"] == 0

    restored = client.post("/restore/jobs", json={"file_path": backup.json()["path"]})
    assert restored.status_code == 200
    assert restored.json()["restored"] == 0
