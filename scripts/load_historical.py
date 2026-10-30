"""Load the sample CSVs into SQLite in batches of at most 1000 rows."""

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import get_connection, initialize_database  # noqa: E402
from app.repository import insert_records  # noqa: E402
from app.settings import DATA_DIR, MAX_BATCH_SIZE  # noqa: E402

TABLE_FILES = {
    "departments": ("departments.csv", ["id", "department"]),
    "jobs": ("jobs.csv", ["id", "job"]),
    "hired_employees": (
        "hired_employees.csv",
        ["id", "name", "datetime", "department_id", "job_id"],
    ),
}


def read_csv(path: Path, columns: list[str]) -> list[dict]:
    records = []
    with path.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.reader(file):
            records.append(
                {
                    column: row[index] if index < len(row) else None
                    for index, column in enumerate(columns)
                }
            )
    return records


def chunks(records: list, size: int):
    for index in range(0, len(records), size):
        yield records[index : index + size]


def load_table(connection, table_name: str, data_dir: Path) -> dict:
    filename, columns = TABLE_FILES[table_name]
    records = read_csv(data_dir / filename, columns)
    summary = {"table": table_name, "received": len(records), "inserted": 0, "rejected": 0}
    for batch in chunks(records, MAX_BATCH_SIZE):
        result = insert_records(connection, table_name, batch)
        summary["inserted"] += result["inserted"]
        summary["rejected"] += result["rejected"]
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Load sample CSVs into the local SQLite database.")
    parser.add_argument("--data-dir", default=str(DATA_DIR))
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    initialize_database()
    with get_connection() as connection:
        summaries = [load_table(connection, table_name, data_dir) for table_name in TABLE_FILES]
    for summary in summaries:
        print(summary)


if __name__ == "__main__":
    main()
