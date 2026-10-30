def _seed(client):
    departments = [
        {"id": 1, "department": "Alpha"},
        {"id": 2, "department": "Beta"},
        {"id": 3, "department": "Compliance"},
    ]
    jobs = [
        {"id": 10, "job": "Analyst"},
        {"id": 20, "job": "Manager"},
    ]
    employees = [
        _employee(1, 1, 10, "2021-01-01T00:00:00Z"),
        _employee(2, 1, 10, "2021-03-31T23:59:59Z"),
        _employee(3, 1, 20, "2021-04-01T00:00:00Z"),
        _employee(4, 1, 20, "2021-06-30T12:00:00Z"),
        _employee(5, 1, 10, "2021-07-01T00:00:00Z"),
        _employee(6, 2, 20, "2021-09-30T00:00:00Z"),
        _employee(7, 2, 10, "2021-10-01T00:00:00Z"),
        _employee(8, 2, 20, "2021-12-31T23:59:59Z"),
        _employee(9, 1, 10, "2022-02-02T00:00:00Z"),
        _employee(10, 2, 10, "2020-12-31T00:00:00Z"),
    ]
    assert client.post("/ingest/departments", json=departments).json()["inserted"] == 3
    assert client.post("/ingest/jobs", json=jobs).json()["inserted"] == 2
    assert client.post("/ingest/hired_employees", json=employees).json()["inserted"] == 10


def _employee(record_id, department_id, job_id, timestamp):
    return {
        "id": record_id,
        "name": f"Person {record_id}",
        "datetime": timestamp,
        "department_id": department_id,
        "job_id": job_id,
    }


def test_analytics_are_empty_before_any_rows(client):
    assert client.get("/analytics/hires-by-quarter").json() == []
    assert client.get("/analytics/departments-above-average").json() == []


def test_hires_by_quarter_counts_2021_months_only(client):
    _seed(client)
    response = client.get("/analytics/hires-by-quarter")
    assert response.status_code == 200
    assert response.json() == [
        {"department": "Alpha", "job": "Analyst", "Q1": 2, "Q2": 0, "Q3": 1, "Q4": 0},
        {"department": "Alpha", "job": "Manager", "Q1": 0, "Q2": 2, "Q3": 0, "Q4": 0},
        {"department": "Beta", "job": "Analyst", "Q1": 0, "Q2": 0, "Q3": 0, "Q4": 1},
        {"department": "Beta", "job": "Manager", "Q1": 0, "Q2": 0, "Q3": 1, "Q4": 1},
    ]


def test_departments_above_average_include_zero_hire_departments_in_the_mean(client):
    _seed(client)
    # 2021 hires are Alpha 5, Beta 3, Compliance 0. Mean is 8/3.
    # Beta stays in the result because 3 > 8/3. Dropping the zero-hire
    # department would raise the mean to 4 and remove Beta.
    response = client.get("/analytics/departments-above-average")
    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "department": "Alpha", "hired": 5},
        {"id": 2, "department": "Beta", "hired": 3},
    ]
