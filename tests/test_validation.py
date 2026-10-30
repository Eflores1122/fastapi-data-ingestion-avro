import json

import pytest

from app.database import get_connection
from app.validation import (
    parse_datetime,
    parse_int,
    parse_text,
    validate_batch_size,
    validate_record,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, 1),
        (0, 0),
        (-3, -3),
        ("42", 42),
        (" 7 ", 7),
    ],
)
def test_parse_int_accepts_integers_and_digit_strings(value, expected):
    assert parse_int(value) == expected


@pytest.mark.parametrize("value", [True, False, 1.5, "1.5", "-2", "+2", "", "  ", None, "abc"])
def test_parse_int_rejects_bools_floats_and_non_digits(value):
    with pytest.raises(ValueError, match="must be an integer"):
        parse_int(value)


def test_parse_text_strips_and_rejects_blank_values():
    assert parse_text("  Sales  ") == "Sales"
    for value in ("", "   ", None, 12):
        with pytest.raises(ValueError, match="must be a non-empty string"):
            parse_text(value)


def test_parse_datetime_accepts_exact_utc_timestamp():
    raw = " 2021-07-27T16:02:08Z "
    assert parse_datetime(raw) == "2021-07-27T16:02:08Z"


@pytest.mark.parametrize(
    "value",
    [
        "2021-07-27 16:02:08Z",
        "2021-07-27T16:02:08+00:00",
        "2021-7-27T16:02:08Z",
        "2021-07-27T16:02:08.000Z",
    ],
)
def test_parse_datetime_rejects_other_shapes(value):
    with pytest.raises(ValueError, match="must be ISO 8601 format"):
        parse_datetime(value)


def test_parse_datetime_rejects_impossible_calendar_dates():
    with pytest.raises(ValueError, match="day is out of range for month"):
        parse_datetime("2021-02-31T00:00:00Z")


def test_batch_size_limits():
    validate_batch_size([{"id": 1}])
    validate_batch_size([{"id": index} for index in range(1000)])
    with pytest.raises(ValueError, match="Payload must be a list of records"):
        validate_batch_size({"id": 1})
    with pytest.raises(ValueError, match="Batch size must be between 1 and 1000 rows"):
        validate_batch_size([])
    with pytest.raises(ValueError, match="Batch size must be between 1 and 1000 rows"):
        validate_batch_size([{"id": index} for index in range(1001)])


def test_missing_required_field_skips_later_checks():
    record = {
        "id": "5",
        "name": "",
        "datetime": "not-a-date",
        "department_id": "99",
        "job_id": "nope",
    }
    with get_connection() as connection:
        clean, errors = validate_record(connection, "hired_employees", record)
    assert clean is None
    assert errors == ["name is required"]


def test_invalid_datetime_stops_before_foreign_key_checks():
    record = {
        "id": 5,
        "name": "Ada Example",
        "datetime": "2021-02-31T00:00:00Z",
        "department_id": 99,
        "job_id": 99,
    }
    with get_connection() as connection:
        clean, errors = validate_record(connection, "hired_employees", record)
    assert clean is None
    assert errors == ["day is out of range for month"]


def test_employee_reports_both_missing_parents():
    record = {
        "id": " 15 ",
        "name": " Ada Example ",
        "datetime": "2021-01-15T00:00:00Z",
        "department_id": "9",
        "job_id": 8,
    }
    with get_connection() as connection:
        clean, errors = validate_record(connection, "hired_employees", record)
    assert clean is None
    assert errors == ["department_id does not exist", "job_id does not exist"]


def test_valid_employee_is_trimmed_and_coerced():
    with get_connection() as connection:
        connection.execute("INSERT INTO departments (id, department) VALUES (2, 'Sales')")
        connection.execute("INSERT INTO jobs (id, job) VALUES (4, 'Analyst')")
        clean, errors = validate_record(
            connection,
            "hired_employees",
            {
                "id": " 3 ",
                "name": " Ada Example ",
                "datetime": "2021-03-01T08:30:00Z",
                "department_id": "2",
                "job_id": "4",
            },
        )
    assert errors == []
    assert clean == {
        "id": 3,
        "name": "Ada Example",
        "datetime": "2021-03-01T08:30:00Z",
        "department_id": 2,
        "job_id": 4,
    }


def test_whitespace_only_text_is_not_treated_as_missing():
    with get_connection() as connection:
        clean, errors = validate_record(
            connection,
            "departments",
            {"id": 1, "department": "   "},
        )
    assert clean is None
    assert errors == ["must be a non-empty string"]


def test_rejected_row_is_written_as_jsonl(isolated_storage):
    from app.repository import insert_records

    with get_connection() as connection:
        result = insert_records(
            connection,
            "jobs",
            [{"id": 1, "job": "Analyst"}, {"id": 2, "job": ""}],
        )
    assert result["inserted"] == 1
    assert result["rejected"] == 1
    lines = isolated_storage["invalid_log"].read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {
        "table": "jobs",
        "payload": {"id": 2, "job": ""},
        "errors": ["job is required"],
    }
