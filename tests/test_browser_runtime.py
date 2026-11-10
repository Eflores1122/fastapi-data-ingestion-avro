import importlib.util
import io
import json
from pathlib import Path

from fastavro import reader as fastavro_reader

from app.avro_io import backup_table
from app.database import get_connection
from tests.test_sample_data import ABOVE_AVERAGE, QUARTER_TOTALS, REJECTION_REASONS

ROOT = Path(__file__).resolve().parents[1]


def load_runtime():
    spec = importlib.util.spec_from_file_location("browser_runtime", ROOT / "web" / "runtime.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _api(client, table_name: str, raw: str):
    response = client.post(
        f"/ingest/{table_name}",
        content=raw.encode("utf-8"),
        headers={"content-type": "application/json"},
    )
    return response.status_code, response.json()


def _browser(runtime, table_name: str, raw: str):
    payload = json.loads(runtime.ingest_text(table_name, raw))
    return payload["status"], payload["body"], payload


def test_ingest_text_matches_the_api(client):
    runtime = load_runtime()
    raw_cases = [
        ("departments", ""),
        ("departments", "null"),
        ("departments", "   "),
        ("departments", "{"),
        ("departments", "[1, 2,]"),
        ("departments", "{}"),
        ("departments", '"hello"'),
        ("departments", "[]"),
        ("departments", "[1]"),
        ("departments", '["x", {"id": 1}]'),
        ("nope", "[]"),
        ("nope", "{}"),
        ("locations", json.dumps([{"id": 1, "department": "A"}])),
        (
            "departments",
            json.dumps(
                [
                    {"id": 1, "department": "  Sales  ", "extra": "ignored"},
                    {"id": "nope", "department": "Bad"},
                    {"id": 2, "department": ""},
                ]
            ),
        ),
        (
            "departments",
            json.dumps(
                [{"id": index, "department": f"Department {index}"} for index in range(1001)]
            ),
        ),
        (
            "jobs",
            json.dumps([{"id": 1, "job": "Analyst"}, {"id": 2, "job": ""}]),
        ),
    ]
    for table_name, raw in raw_cases:
        assert _browser(runtime, table_name, raw)[:2] == _api(client, table_name, raw)


def test_hired_employee_responses_match_the_api(client):
    runtime = load_runtime()
    department = json.dumps([{"id": 1, "department": "Sales"}])
    job = json.dumps([{"id": 2, "job": "Analyst"}])
    rejected = json.dumps(
        [
            {
                "id": 5,
                "name": "Ada Example",
                "datetime": "2021-01-15T00:00:00Z",
                "department_id": 9,
                "job_id": 8,
            }
        ]
    )
    accepted = json.dumps(
        [
            {
                "id": "6",
                "name": " Ada Example ",
                "datetime": "2021-01-15T00:00:00Z",
                "department_id": "1",
                "job_id": 2,
            }
        ]
    )

    def run(caller):
        caller("departments", department)
        caller("jobs", job)
        bad = caller("hired_employees", rejected)
        good = caller("hired_employees", accepted)
        return bad, good

    runtime.reset_session()
    browser_rows = run(lambda table, raw: _browser(runtime, table, raw)[:2])
    runtime.reset_session()
    api_rows = run(lambda table, raw: _api(client, table, raw))
    assert browser_rows == api_rows


def test_rejected_row_is_appended_to_the_jsonl_returned_with_the_body(client):
    runtime = load_runtime()
    runtime.reset_session()
    payload = json.loads(
        runtime.ingest_text("jobs", json.dumps([{"id": 1, "job": "Analyst"}, {"id": 2, "job": ""}]))
    )
    assert payload["status"] == 200
    assert json.loads(payload["jsonl"][0]) == {
        "table": "jobs",
        "payload": {"id": 2, "job": ""},
        "errors": ["job is required"],
    }


def test_csv_batch_matches_one_ingest_response(client):
    runtime = load_runtime()
    runtime.reset_session()
    raw = "1,Support\n2,\n"
    payload = json.loads(runtime.ingest_csv_text("departments", raw))
    assert payload["mode"] == "loader"
    assert payload["summary"] == {
        "table": "departments",
        "received": 2,
        "inserted": 1,
        "rejected": 1,
    }
    assert payload["batches"][0]["body"] == {
        "table": "departments",
        "received": 2,
        "inserted": 1,
        "rejected": 1,
        "errors": [{"index": 1, "errors": ["department is required"]}],
    }
    api_status, api_body = _api(
        client,
        "departments",
        json.dumps([{"id": "1", "department": "Support"}, {"id": "2", "department": ""}]),
    )
    assert api_status == 200
    assert api_body == payload["batches"][0]["body"]


def test_headerless_hires_without_parents_are_all_rejected():
    runtime = load_runtime()
    runtime.reset_session()
    raw = (ROOT / "data" / "hired_employees.csv").read_text(encoding="utf-8")
    payload = json.loads(runtime.ingest_csv_text("hired_employees", raw))
    assert payload["summary"] == {
        "table": "hired_employees",
        "received": 1999,
        "inserted": 0,
        "rejected": 1999,
    }
    assert len(payload["batches"]) == 2


def test_sample_load_matches_the_measured_run():
    runtime = load_runtime()
    payload = json.loads(runtime.load_sample())
    measurement = payload["measurement"]
    assert payload["summaries"] == [
        {"table": "departments", "received": 12, "inserted": 12, "rejected": 0},
        {"table": "jobs", "received": 183, "inserted": 183, "rejected": 0},
        {"table": "hired_employees", "received": 1999, "inserted": 1929, "rejected": 70},
    ]
    assert measurement["quarter_groups"] == 933
    assert measurement["quarter_totals"] == QUARTER_TOTALS
    assert measurement["hired_2021"] == 1643
    assert measurement["department_count"] == 12
    assert measurement["mean_2021"] == 1643 / 12
    assert measurement["years"] == [{"year": "2021", "hired": 1643}, {"year": "2022", "hired": 286}]
    assert measurement["above"] == ABOVE_AVERAGE
    assert measurement["rejection_reasons"] == REJECTION_REASONS
    assert json.loads(runtime.session_counts()) == {
        "departments": 12,
        "jobs": 183,
        "hired_employees": 1929,
    }


def test_backup_file_is_the_table_and_reads_with_fastavro():
    runtime = load_runtime()
    runtime.reset_session()
    runtime.ingest_text(
        "departments",
        json.dumps([{"id": 8, "department": "Support"}, {"id": 5, "department": "Engineering"}]),
    )
    payload = json.loads(runtime.backup("departments"))
    assert payload["status"] == 200
    assert payload["body"]["table"] == "departments"
    assert payload["body"]["records"] == 2
    assert payload["filename"].startswith("departments_")
    assert payload["filename"].endswith(".avro")
    assert payload["size"] > 0
    rows = list(fastavro_reader(io.BytesIO(Path(payload["body"]["path"]).read_bytes())))
    assert rows == [
        {"id": 5, "department": "Engineering"},
        {"id": 8, "department": "Support"},
    ]


def test_backup_table_accepts_the_pure_python_writer(monkeypatch):
    container_spec = importlib.util.spec_from_file_location(
        "avro_container_for_backup", ROOT / "web" / "avro_container.py"
    )
    container = importlib.util.module_from_spec(container_spec)
    container_spec.loader.exec_module(container)
    monkeypatch.setattr("app.avro_io.writer", container.writer)

    with get_connection() as connection:
        connection.execute("INSERT INTO departments (id, department) VALUES (12, 'Accounting')")
        body = backup_table(connection, "departments")
    rows = list(fastavro_reader(Path(body["path"]).open("rb")))
    assert rows == [{"id": 12, "department": "Accounting"}]


def test_assemble_copies_the_modules_the_page_imports(tmp_path):
    import subprocess

    subprocess.run(["sh", str(ROOT / "web" / "assemble.sh"), str(tmp_path / "site")], check=True)
    site = tmp_path / "site"
    validation = (site / "app" / "validation.py").read_text(encoding="utf-8")
    shim = (site / "fastavro" / "__init__.py").read_text(encoding="utf-8")
    assert "def validate_record" in validation
    assert "def writer" in shim
    assert (site / "data" / "hired_employees.csv").is_file()
    assert (site / "scripts" / "load_historical.py").is_file()
    assert (site / "runtime.py").is_file()
    assert (site / ".nojekyll").is_file()
