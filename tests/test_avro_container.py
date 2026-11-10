import importlib.util
import io
import shutil
import subprocess
import sys
from pathlib import Path

from fastavro import reader as fastavro_reader
from fastavro import writer as fastavro_writer

from app.avro_io import SCHEMAS

ROOT = Path(__file__).resolve().parents[1]
CONTAINER_PATH = ROOT / "web" / "avro_container.py"


def load_container():
    spec = importlib.util.spec_from_file_location("avro_container", CONTAINER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_container_bytes_roundtrip_through_fastavro_and_back():
    container = load_container()
    samples = {
        "departments": [
            {"id": 1, "department": "Support"},
            {"id": -3, "department": "Año"},
            {"id": 0, "department": ""},
        ],
        "jobs": [{"id": 183, "job": "Analyst"}],
        "hired_employees": [
            {
                "id": 6,
                "name": "Ada Example",
                "datetime": "2021-01-15T00:00:00Z",
                "department_id": 1,
                "job_id": 2,
            }
        ],
    }
    for table_name, records in samples.items():
        schema = SCHEMAS[table_name]
        marker = b"sync-marker-16b!"
        ours = io.BytesIO()
        container.writer(ours, schema, records, sync_marker=marker)
        official = io.BytesIO()
        fastavro_writer(official, schema, records, sync_marker=marker)
        assert ours.getvalue() == official.getvalue()
        assert list(fastavro_reader(io.BytesIO(ours.getvalue()))) == records
        assert list(container.reader(io.BytesIO(official.getvalue()))) == records


def test_empty_container_matches_fastavro():
    container = load_container()
    schema = SCHEMAS["departments"]
    marker = bytes(range(16))
    ours = io.BytesIO()
    container.writer(ours, schema, [], sync_marker=marker)
    official = io.BytesIO()
    fastavro_writer(official, schema, [], sync_marker=marker)
    assert ours.getvalue() == official.getvalue()
    assert list(fastavro_reader(io.BytesIO(ours.getvalue()))) == []


def test_single_block_larger_than_fastavro_sync_interval_is_readable():
    container = load_container()
    schema = SCHEMAS["departments"]
    records = [{"id": index, "department": f"Department {index}"} for index in range(1, 1501)]
    buffer = io.BytesIO()
    container.writer(buffer, schema, records, sync_marker=b"0123456789abcdef")
    assert list(fastavro_reader(io.BytesIO(buffer.getvalue()))) == records


def test_reader_accepts_fastavro_blocks_split_on_the_default_interval():
    container = load_container()
    schema = SCHEMAS["jobs"]
    records = [{"id": index, "job": f"Role {index} with a longer title"} for index in range(800)]
    official = io.BytesIO()
    fastavro_writer(official, schema, records)
    assert list(container.reader(io.BytesIO(official.getvalue()))) == records


def test_shim_imports_as_fastavro_before_the_installed_package(tmp_path):
    package = tmp_path / "fastavro"
    package.mkdir()
    shutil.copy(CONTAINER_PATH, package / "__init__.py")
    script = """
import io, sys
sys.path.insert(0, sys.argv[1])
from fastavro import writer
buffer = io.BytesIO()
schema = {
    "type": "record",
    "name": "Department",
    "fields": [
        {"name": "id", "type": "int"},
        {"name": "department", "type": "string"},
    ],
}
writer(buffer, schema, [{"id": 8, "department": "Support"}])
sys.stdout.buffer.write(buffer.getvalue())
"""
    completed = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path)],
        check=True,
        capture_output=True,
    )
    rows = list(fastavro_reader(io.BytesIO(completed.stdout)))
    assert rows == [{"id": 8, "department": "Support"}]
