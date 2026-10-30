from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.analytics import departments_above_average, hires_by_quarter
from app.avro_io import backup_table, restore_table
from app.database import get_connection, initialize_database
from app.repository import insert_records
from app.validation import TABLE_COLUMNS


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="FastAPI Data Ingestion with AVRO Backup", version="1.0.0", lifespan=lifespan)


def check_table(table_name: str) -> None:
    if table_name not in TABLE_COLUMNS:
        raise HTTPException(status_code=404, detail="Unknown table")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ingest/{table_name}")
def ingest(table_name: str, records: list[dict]) -> dict:
    check_table(table_name)
    try:
        with get_connection() as connection:
            return insert_records(connection, table_name, records)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/backup/{table_name}")
def backup(table_name: str) -> dict:
    check_table(table_name)
    with get_connection() as connection:
        return backup_table(connection, table_name)


@app.post("/restore/{table_name}")
def restore(table_name: str, payload: dict) -> dict:
    check_table(table_name)
    file_path = payload.get("file_path")
    if not file_path:
        raise HTTPException(status_code=422, detail="file_path is required")
    try:
        with get_connection() as connection:
            return restore_table(connection, table_name, file_path)
    except Exception as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/analytics/hires-by-quarter")
def analytics_hires_by_quarter() -> list[dict]:
    with get_connection() as connection:
        return hires_by_quarter(connection)


@app.get("/analytics/departments-above-average")
def analytics_departments_above_average() -> list[dict]:
    with get_connection() as connection:
        return departments_above_average(connection)
