from datetime import UTC, datetime

from fastavro import reader, writer

from app.repository import fetch_all, restore_records
from app.settings import BACKUP_DIR

SCHEMAS = {
    "departments": {
        "type": "record",
        "name": "Department",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "department", "type": "string"},
        ],
    },
    "jobs": {
        "type": "record",
        "name": "Job",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "job", "type": "string"},
        ],
    },
    "hired_employees": {
        "type": "record",
        "name": "HiredEmployee",
        "fields": [
            {"name": "id", "type": "int"},
            {"name": "name", "type": "string"},
            {"name": "datetime", "type": "string"},
            {"name": "department_id", "type": "int"},
            {"name": "job_id", "type": "int"},
        ],
    },
}


def backup_table(connection, table_name: str) -> dict:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    path = BACKUP_DIR / f"{table_name}_{timestamp}.avro"
    records = fetch_all(connection, table_name)
    with path.open("wb") as file:
        writer(file, SCHEMAS[table_name], records)
    return {"table": table_name, "records": len(records), "path": str(path)}


def restore_table(connection, table_name: str, file_path: str) -> dict:
    with open(file_path, "rb") as file:
        records = [dict(record) for record in reader(file)]
    result = restore_records(connection, table_name, records)
    return {"table": table_name, "restored": result["inserted"], "path": file_path}
