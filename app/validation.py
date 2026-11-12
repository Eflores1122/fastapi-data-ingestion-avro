import json
import re
import sqlite3
from datetime import datetime

from app.settings import INVALID_LOG_PATH, MAX_BATCH_SIZE

TABLE_COLUMNS = {
    "departments": ["id", "department"],
    "jobs": ["id", "job"],
    "hired_employees": ["id", "name", "datetime", "department_id", "job_id"],
}

EXISTS_SQL = {
    "departments": "SELECT 1 FROM departments WHERE id = ?",
    "jobs": "SELECT 1 FROM jobs WHERE id = ?",
}

ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def validate_batch_size(rows: object) -> None:
    if not isinstance(rows, list):
        raise ValueError("Payload must be a list of records")
    if len(rows) < 1 or len(rows) > MAX_BATCH_SIZE:
        raise ValueError("Batch size must be between 1 and 1000 rows")


def parse_int(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise ValueError("must be an integer")


def parse_text(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    raise ValueError("must be a non-empty string")


def parse_datetime(value: object) -> str:
    text = parse_text(value)
    if not ISO_PATTERN.match(text):
        raise ValueError("must be ISO 8601 format like 2021-07-27T16:02:08Z")
    datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    return text


def exists(connection: sqlite3.Connection, table_name: str, record_id: int) -> bool:
    row = connection.execute(EXISTS_SQL[table_name], (record_id,)).fetchone()
    return row is not None


def validate_record(
    connection: sqlite3.Connection, table_name: str, record: dict[str, object]
) -> tuple[dict | None, list[str]]:
    errors = []
    clean: dict = {}
    columns = TABLE_COLUMNS[table_name]
    for column in columns:
        if column not in record or record[column] in (None, ""):
            errors.append(f"{column} is required")
    # Type and foreign-key checks run only after every required field is present.
    if errors:
        return None, errors
    try:
        if table_name == "departments":
            clean["id"] = parse_int(record["id"])
            clean["department"] = parse_text(record["department"])
        elif table_name == "jobs":
            clean["id"] = parse_int(record["id"])
            clean["job"] = parse_text(record["job"])
        elif table_name == "hired_employees":
            clean["id"] = parse_int(record["id"])
            clean["name"] = parse_text(record["name"])
            clean["datetime"] = parse_datetime(record["datetime"])
            clean["department_id"] = parse_int(record["department_id"])
            clean["job_id"] = parse_int(record["job_id"])
            if not exists(connection, "departments", clean["department_id"]):
                errors.append("department_id does not exist")
            if not exists(connection, "jobs", clean["job_id"]):
                errors.append("job_id does not exist")
    except ValueError as error:
        errors.append(str(error))
    return (clean if not errors else None), errors


def log_invalid_record(
    connection: sqlite3.Connection,
    table_name: str,
    record: dict[str, object],
    errors: list[str],
) -> None:
    payload = json.dumps(record, ensure_ascii=False)
    error_text = json.dumps(errors, ensure_ascii=False)
    connection.execute(
        "INSERT INTO invalid_records (table_name, payload, errors) VALUES (?, ?, ?)",
        (table_name, payload, error_text),
    )
    with INVALID_LOG_PATH.open("a", encoding="utf-8") as file:
        line = json.dumps(
            {"table": table_name, "payload": record, "errors": errors},
            ensure_ascii=False,
        )
        file.write(line + "\n")
