from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"
DATABASE_PATH = BASE_DIR / "ingestion.db"
INVALID_LOG_PATH = BASE_DIR / "invalid_records.jsonl"
MAX_BATCH_SIZE = 1000
