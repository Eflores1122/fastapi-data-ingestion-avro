import json

from app.database import get_connection
from app.repository import fetch_all
from scripts.load_historical import load_table


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_table_is_not_found(client):
    response = client.post("/ingest/locations", json=[{"id": 1}])
    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown table"}


def test_non_list_payload_is_rejected(client):
    response = client.post("/ingest/departments", json={"id": 1, "department": "Sales"})
    assert response.status_code == 422


def test_batch_size_boundaries(client):
    empty = client.post("/ingest/departments", json=[])
    assert empty.status_code == 422
    assert empty.json()["detail"] == "Batch size must be between 1 and 1000 rows"

    accepted = [{"id": index, "department": f"Department {index}"} for index in range(1, 1001)]
    response = client.post("/ingest/departments", json=accepted)
    assert response.status_code == 200
    assert response.json()["inserted"] == 1000

    too_many = accepted + [{"id": 1001, "department": "Extra"}]
    rejected = client.post("/ingest/departments", json=too_many)
    assert rejected.status_code == 422
    assert rejected.json()["detail"] == "Batch size must be between 1 and 1000 rows"

    with get_connection() as connection:
        assert len(fetch_all(connection, "departments")) == 1000


def test_partial_batch_keeps_valid_rows_and_logs_the_rest(client, isolated_storage):
    response = client.post(
        "/ingest/departments",
        json=[
            {"id": 1, "department": "  Sales  ", "extra": "ignored"},
            {"id": "nope", "department": "Bad"},
            {"id": 2, "department": ""},
        ],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["table"] == "departments"
    assert body["received"] == 3
    assert body["inserted"] == 1
    assert body["rejected"] == 2
    assert body["errors"] == [
        {"index": 1, "errors": ["must be an integer"]},
        {"index": 2, "errors": ["department is required"]},
    ]

    with get_connection() as connection:
        assert fetch_all(connection, "departments") == [{"id": 1, "department": "Sales"}]
        invalid = connection.execute("SELECT COUNT(*) FROM invalid_records").fetchone()[0]
    assert invalid == 2
    lines = isolated_storage["invalid_log"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["errors"] == ["must be an integer"]


def test_duplicate_id_replaces_the_existing_row(client):
    first = client.post("/ingest/jobs", json=[{"id": 1, "job": "Analyst"}])
    second = client.post(
        "/ingest/jobs",
        json=[{"id": 1, "job": "Manager"}, {"id": "1", "job": "Director"}],
    )
    assert first.status_code == 200
    assert second.json()["inserted"] == 2
    with get_connection() as connection:
        assert fetch_all(connection, "jobs") == [{"id": 1, "job": "Director"}]


def test_employee_ingest_checks_parents_and_accepts_a_valid_row(client):
    assert (
        client.post("/ingest/departments", json=[{"id": 1, "department": "Sales"}]).status_code
        == 200
    )
    assert client.post("/ingest/jobs", json=[{"id": 2, "job": "Analyst"}]).status_code == 200

    rejected = client.post(
        "/ingest/hired_employees",
        json=[
            {
                "id": 5,
                "name": "Ada Example",
                "datetime": "2021-01-15T00:00:00Z",
                "department_id": 9,
                "job_id": 8,
            }
        ],
    )
    assert rejected.json()["inserted"] == 0
    assert rejected.json()["errors"][0]["errors"] == [
        "department_id does not exist",
        "job_id does not exist",
    ]

    accepted = client.post(
        "/ingest/hired_employees",
        json=[
            {
                "id": "6",
                "name": " Ada Example ",
                "datetime": "2021-01-15T00:00:00Z",
                "department_id": "1",
                "job_id": 2,
            }
        ],
    )
    assert accepted.json()["inserted"] == 1
    with get_connection() as connection:
        assert fetch_all(connection, "hired_employees") == [
            {
                "id": 6,
                "name": "Ada Example",
                "datetime": "2021-01-15T00:00:00Z",
                "department_id": 1,
                "job_id": 2,
            }
        ]


def test_loader_chunks_headerless_csv_and_rejects_incomplete_rows(tmp_path):
    (tmp_path / "departments.csv").write_text("1,Engineering\n2,\n", encoding="utf-8")
    (tmp_path / "jobs.csv").write_text("1,Analyst\n", encoding="utf-8")
    (tmp_path / "hired_employees.csv").write_text(
        "1,Ada Example,2021-03-01T00:00:00Z,1,1\n2,Ada Example,2021-03-01T00:00:00Z,99,1\n",
        encoding="utf-8",
    )

    with get_connection() as connection:
        summaries = [
            load_table(connection, name, tmp_path)
            for name in ("departments", "jobs", "hired_employees")
        ]

    assert summaries == [
        {"table": "departments", "received": 2, "inserted": 1, "rejected": 1},
        {"table": "jobs", "received": 1, "inserted": 1, "rejected": 0},
        {"table": "hired_employees", "received": 2, "inserted": 1, "rejected": 1},
    ]
    with get_connection() as connection:
        rows = fetch_all(connection, "hired_employees")
    assert rows[0]["name"] == "Ada Example"
    assert rows[0]["department_id"] == 1
