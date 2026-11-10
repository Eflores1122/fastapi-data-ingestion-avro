"""Browser entry points for the static page.

The functions call the repository modules and return JSON text. ``ingest_text``
matches the HTTP status and body of ``POST /ingest/{table}`` on FastAPI
0.115.6: Pydantic rejects a body that is not a list of objects before the view
runs, and the view then returns 404 or the ``insert_records`` result.
"""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
ROOT = _HERE if (_HERE / "app" / "validation.py").is_file() else _HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import avro_io, database, validation  # noqa: E402
from app.analytics import departments_above_average, hires_by_quarter  # noqa: E402
from app.avro_io import backup_table  # noqa: E402
from app.database import get_connection, initialize_database  # noqa: E402
from app.repository import insert_records  # noqa: E402
from app.validation import TABLE_COLUMNS  # noqa: E402

_LOADER = None

DEPARTMENT_HIRES_SQL = """
WITH department_hires AS (
    SELECT
        d.id,
        d.department,
        COUNT(he.id) AS hired
    FROM departments d
    LEFT JOIN hired_employees he
        ON he.department_id = d.id
        AND substr(he.datetime, 1, 4) = '2021'
    GROUP BY d.id, d.department
)
SELECT
    id,
    department,
    hired,
    (SELECT AVG(hired) FROM department_hires) AS average_hired
FROM department_hires
ORDER BY hired DESC, id ASC
"""

YEAR_SQL = """
SELECT substr(datetime, 1, 4) AS year, COUNT(*) AS hired
FROM hired_employees
GROUP BY year
ORDER BY year
"""

COUNT_SQL = {
    "departments": "SELECT COUNT(*) FROM departments",
    "jobs": "SELECT COUNT(*) FROM jobs",
    "hired_employees": "SELECT COUNT(*) FROM hired_employees",
}


def _loader():
    global _LOADER
    if _LOADER is None:
        path = ROOT / "scripts" / "load_historical.py"
        spec = importlib.util.spec_from_file_location("browser_load_historical", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _LOADER = module
    return _LOADER


def _dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _body_text(body: object) -> str:
    return json.dumps(body, indent=2, ensure_ascii=False)


def _pack(status: int, body: object, **extra) -> str:
    payload = {"status": status, "body": body, "body_text": _body_text(body), **extra}
    return _dump(payload)


def ensure_db() -> None:
    avro_io.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    initialize_database()


def _log_lines() -> list[str]:
    path = Path(validation.INVALID_LOG_PATH)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    if not text:
        return []
    return text.splitlines()


def _field_required() -> dict:
    return {
        "detail": [
            {
                "type": "missing",
                "loc": ["body"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }


def _json_invalid(exc: json.JSONDecodeError) -> dict:
    return {
        "detail": [
            {
                "type": "json_invalid",
                "loc": ["body", exc.pos],
                "msg": "JSON decode error",
                "input": {},
                "ctx": {"error": exc.msg},
            }
        ]
    }


def _list_type(value: object) -> dict:
    return {
        "detail": [
            {
                "type": "list_type",
                "loc": ["body"],
                "msg": "Input should be a valid list",
                "input": value,
            }
        ]
    }


def _dict_type_errors(records: list) -> dict | None:
    errors = []
    for index, item in enumerate(records):
        if isinstance(item, dict):
            continue
        errors.append(
            {
                "type": "dict_type",
                "loc": ["body", index],
                "msg": "Input should be a valid dictionary",
                "input": item,
            }
        )
    if not errors:
        return None
    return {"detail": errors}


def _parse_body(raw: str) -> tuple[int | None, object]:
    """Return ``(status, body)`` when the body never reaches ``insert_records``."""
    if raw == "":
        return 422, _field_required()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return 422, _json_invalid(exc)
    if payload is None:
        return 422, _field_required()
    if not isinstance(payload, list):
        return 422, _list_type(payload)
    dict_errors = _dict_type_errors(payload)
    if dict_errors is not None:
        return 422, dict_errors
    return None, payload


def ingest_text(table_name: str, raw: str) -> str:
    ensure_db()
    before = len(_log_lines())
    status, parsed = _parse_body(raw)
    if status is not None:
        return _pack(status, parsed, jsonl=[])
    if table_name not in TABLE_COLUMNS:
        return _pack(404, {"detail": "Unknown table"}, jsonl=[])
    try:
        with get_connection() as connection:
            body = insert_records(connection, table_name, parsed)
    except ValueError as error:
        return _pack(422, {"detail": str(error)}, jsonl=[])
    return _pack(200, body, jsonl=_log_lines()[before:])


def ingest_csv_text(table_name: str, raw: str) -> str:
    """Parse a headerless CSV the way ``scripts/load_historical.py`` does.

    Each chunk of at most 1000 rows is one ``insert_records`` call. The page
    shows those bodies separately from the summary the script prints.
    """
    ensure_db()
    if table_name not in TABLE_COLUMNS:
        return _pack(404, {"detail": "Unknown table"}, mode="api", batches=[], jsonl=[])
    loader = _loader()
    columns = loader.TABLE_FILES[table_name][1]
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".csv", delete=False) as handle:
        handle.write(raw)
        upload = Path(handle.name)
    try:
        records = loader.read_csv(upload, columns)
    finally:
        upload.unlink(missing_ok=True)
    before = len(_log_lines())
    batches = []
    inserted = 0
    rejected = 0
    for start in range(0, len(records), loader.MAX_BATCH_SIZE):
        chunk = records[start : start + loader.MAX_BATCH_SIZE]
        with get_connection() as connection:
            body = insert_records(connection, table_name, chunk)
        inserted += body["inserted"]
        rejected += body["rejected"]
        batches.append(
            {
                "status": 200,
                "body": body,
                "body_text": _body_text(body),
                "row_offset": start,
            }
        )
    summary = {
        "table": table_name,
        "received": len(records),
        "inserted": inserted,
        "rejected": rejected,
    }
    return _dump(
        {
            "status": 200,
            "mode": "loader",
            "summary": summary,
            "summary_text": _body_text(summary),
            "batches": batches,
            "jsonl": _log_lines()[before:],
        }
    )


def backup(table_name: str) -> str:
    ensure_db()
    if table_name not in TABLE_COLUMNS:
        return _pack(404, {"detail": "Unknown table"})
    with get_connection() as connection:
        body = backup_table(connection, table_name)
    data = Path(body["path"]).read_bytes()
    return _pack(
        200,
        body,
        filename=Path(body["path"]).name,
        size=len(data),
        avro_b64=base64.b64encode(data).decode("ascii"),
    )


def session_counts() -> str:
    ensure_db()
    with get_connection() as connection:
        counts = {
            name: int(connection.execute(COUNT_SQL[name]).fetchone()[0]) for name in COUNT_SQL
        }
    return _dump(counts)


def reset_session() -> str:
    database_path = Path(database.DATABASE_PATH)
    if database_path.exists():
        database_path.unlink()
    log_path = Path(validation.INVALID_LOG_PATH)
    if log_path.exists():
        log_path.unlink()
    backup_dir = Path(avro_io.BACKUP_DIR)
    if backup_dir.exists():
        for path in backup_dir.glob("*.avro"):
            path.unlink()
    ensure_db()
    return _dump({"status": "ok"})


def _measure(connection) -> dict:
    quarters = [
        {
            "department": row["department"],
            "job": row["job"],
            "Q1": int(row["Q1"]),
            "Q2": int(row["Q2"]),
            "Q3": int(row["Q3"]),
            "Q4": int(row["Q4"]),
        }
        for row in hires_by_quarter(connection)
    ]
    above = [
        {"id": int(row["id"]), "department": row["department"], "hired": int(row["hired"])}
        for row in departments_above_average(connection)
    ]
    years = [
        {"year": row["year"], "hired": int(row["hired"])}
        for row in connection.execute(YEAR_SQL).fetchall()
    ]
    reasons: dict[str, int] = {}
    for row in connection.execute("SELECT errors FROM invalid_records"):
        for error in json.loads(row["errors"]):
            reasons[error] = reasons.get(error, 0) + 1
    totals = {
        quarter: sum(row[quarter] for row in quarters) for quarter in ("Q1", "Q2", "Q3", "Q4")
    }
    department_rows = connection.execute(DEPARTMENT_HIRES_SQL).fetchall()
    department_hires = [
        {"id": int(row["id"]), "department": row["department"], "hired": int(row["hired"])}
        for row in department_rows
    ]
    average = department_rows[0]["average_hired"] if department_rows else None
    mean = float(average) if average is not None else None
    return {
        "quarters": quarters,
        "quarter_totals": totals,
        "quarter_groups": len(quarters),
        "above": above,
        "above_text": _body_text(above),
        "years": years,
        "rejection_reasons": reasons,
        "department_count": len(department_hires),
        "hired_2021": sum(totals.values()),
        "mean_2021": mean,
        "department_hires": department_hires,
    }


def load_sample() -> str:
    """Replace the session database with ``data/*.csv`` and measure the reports."""
    reset_session()
    loader = _loader()
    data_dir = ROOT / "data"
    summaries = []
    with get_connection() as connection:
        for table_name in ("departments", "jobs", "hired_employees"):
            summaries.append(loader.load_table(connection, table_name, data_dir))
        measurement = _measure(connection)
    return _dump(
        {
            "summaries": summaries,
            "summaries_text": _body_text(summaries),
            "measurement": measurement,
        }
    )
