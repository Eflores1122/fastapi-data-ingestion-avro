import json
from collections import Counter

from app.analytics import departments_above_average, hires_by_quarter
from app.avro_io import backup_table, restore_table
from app.database import get_connection, initialize_database
from app.repository import fetch_all
from app.settings import DATA_DIR
from scripts.load_historical import load_table

QUARTER_TOTALS = {"Q1": 249, "Q2": 454, "Q3": 453, "Q4": 487}
DEPARTMENT_HIRES_2021 = [
    (8, "Support", 216),
    (5, "Engineering", 205),
    (6, "Human Resources", 201),
    (7, "Services", 200),
    (4, "Business Development", 185),
    (3, "Research and Development", 148),
    (9, "Marketing", 142),
    (10, "Training", 111),
    (2, "Sales", 93),
    (11, "Legal", 56),
    (1, "Product Management", 48),
    (12, "Accounting", 38),
]
ABOVE_AVERAGE = [
    {"id": department_id, "department": name, "hired": hired}
    for department_id, name, hired in DEPARTMENT_HIRES_2021
    if hired > (1643 / 12)
]
REJECTION_REASONS = {
    "name is required": 19,
    "datetime is required": 14,
    "department_id is required": 21,
    "job_id is required": 16,
}


def _load_sample(connection):
    return [
        load_table(connection, name, DATA_DIR)
        for name in ("departments", "jobs", "hired_employees")
    ]


def test_sample_csv_load_matches_measured_run(client, isolated_storage):
    with get_connection() as connection:
        summaries = _load_sample(connection)
        quarters = hires_by_quarter(connection)
        above = departments_above_average(connection)
        years = connection.execute(
            """
            SELECT substr(datetime, 1, 4) AS year, COUNT(*) AS hired
            FROM hired_employees
            GROUP BY year
            ORDER BY year
            """
        ).fetchall()
        invalid_rows = connection.execute("SELECT errors FROM invalid_records").fetchall()

    assert summaries == [
        {"table": "departments", "received": 12, "inserted": 12, "rejected": 0},
        {"table": "jobs", "received": 183, "inserted": 183, "rejected": 0},
        {"table": "hired_employees", "received": 1999, "inserted": 1929, "rejected": 70},
    ]
    assert [(row["year"], row["hired"]) for row in years] == [("2021", 1643), ("2022", 286)]
    assert len(quarters) == 933
    assert {
        quarter: sum(row[quarter] for row in quarters) for quarter in QUARTER_TOTALS
    } == QUARTER_TOTALS
    assert sum(sum(row[quarter] for quarter in QUARTER_TOTALS) for row in quarters) == 1643
    assert above == ABOVE_AVERAGE

    reasons = Counter()
    for row in invalid_rows:
        for error in json.loads(row["errors"]):
            reasons[error] += 1
    assert dict(reasons) == REJECTION_REASONS

    lines = isolated_storage["invalid_log"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 70
    assert all(json.loads(line)["table"] == "hired_employees" for line in lines)

    endpoint_quarters = client.get("/analytics/hires-by-quarter")
    endpoint_above = client.get("/analytics/departments-above-average")
    assert endpoint_quarters.status_code == 200
    assert endpoint_quarters.json() == quarters
    assert endpoint_above.status_code == 200
    assert endpoint_above.json() == above


def test_sample_backup_restores_every_table(monkeypatch, tmp_path):
    with get_connection() as connection:
        _load_sample(connection)
        original = {
            table: fetch_all(connection, table)
            for table in ("departments", "jobs", "hired_employees")
        }
        backups = {
            table: backup_table(connection, table)
            for table in ("departments", "jobs", "hired_employees")
        }

    assert [backups[table]["records"] for table in ("departments", "jobs", "hired_employees")] == [
        12,
        183,
        1929,
    ]

    monkeypatch.setattr("app.database.DATABASE_PATH", tmp_path / "restored.db")
    initialize_database()
    with get_connection() as connection:
        for table in ("departments", "jobs", "hired_employees"):
            result = restore_table(connection, table, backups[table]["path"])
            assert result["restored"] == backups[table]["records"]
        restored = {
            table: fetch_all(connection, table)
            for table in ("departments", "jobs", "hired_employees")
        }

    assert restored == original
