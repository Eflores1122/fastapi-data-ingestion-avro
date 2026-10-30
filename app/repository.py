from app.settings import MAX_BATCH_SIZE
from app.validation import log_invalid_record, validate_batch_size, validate_record

INSERT_SQL = {
    "departments": "INSERT OR REPLACE INTO departments (id, department) VALUES (:id, :department)",
    "jobs": "INSERT OR REPLACE INTO jobs (id, job) VALUES (:id, :job)",
    "hired_employees": """
        INSERT OR REPLACE INTO hired_employees (id, name, datetime, department_id, job_id)
        VALUES (:id, :name, :datetime, :department_id, :job_id)
    """,
}

FETCH_SQL = {
    "departments": "SELECT id, department FROM departments ORDER BY id",
    "jobs": "SELECT id, job FROM jobs ORDER BY id",
    "hired_employees": """
        SELECT id, name, datetime, department_id, job_id
        FROM hired_employees
        ORDER BY id
    """,
}


def insert_records(connection, table_name: str, records) -> dict:
    validate_batch_size(records)
    inserted = 0
    rejected = []
    for index, record in enumerate(records):
        clean, errors = validate_record(connection, table_name, record)
        if clean:
            connection.execute(INSERT_SQL[table_name], clean)
            inserted += 1
        else:
            log_invalid_record(connection, table_name, record, errors)
            rejected.append({"index": index, "errors": errors})
    return {
        "table": table_name,
        "received": len(records),
        "inserted": inserted,
        "rejected": len(rejected),
        "errors": rejected,
    }


def fetch_all(connection, table_name: str) -> list[dict]:
    rows = connection.execute(FETCH_SQL[table_name]).fetchall()
    return [dict(row) for row in rows]


def restore_records(connection, table_name: str, records: list) -> dict:
    """Upsert a backup using the same row rules as ingest.

    Ingest refuses a batch outside 1..1000 rows. A table backup can be larger,
    so restore validates and upserts in batches of ``MAX_BATCH_SIZE``. One
    rejected row fails the restore. The caller rolls the SQLite transaction
    back. Log lines already appended to ``invalid_records.jsonl`` stay on disk.
    """
    if not records:
        return {
            "table": table_name,
            "received": 0,
            "inserted": 0,
            "rejected": 0,
            "errors": [],
        }

    inserted = 0
    rejected = 0
    for start in range(0, len(records), MAX_BATCH_SIZE):
        batch = records[start : start + MAX_BATCH_SIZE]
        result = insert_records(connection, table_name, batch)
        inserted += result["inserted"]
        rejected += result["rejected"]
    if rejected:
        raise ValueError(f"Restore rejected {rejected} records")
    return {
        "table": table_name,
        "received": len(records),
        "inserted": inserted,
        "rejected": 0,
        "errors": [],
    }
