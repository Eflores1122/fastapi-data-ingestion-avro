import sqlite3


def hires_by_quarter(connection: sqlite3.Connection) -> list[dict]:
    query = """
        SELECT
            d.department AS department,
            j.job AS job,
            SUM(
                CASE
                    WHEN CAST(strftime('%m', he.datetime) AS INTEGER) BETWEEN 1 AND 3 THEN 1
                    ELSE 0
                END
            ) AS Q1,
            SUM(
                CASE
                    WHEN CAST(strftime('%m', he.datetime) AS INTEGER) BETWEEN 4 AND 6 THEN 1
                    ELSE 0
                END
            ) AS Q2,
            SUM(
                CASE
                    WHEN CAST(strftime('%m', he.datetime) AS INTEGER) BETWEEN 7 AND 9 THEN 1
                    ELSE 0
                END
            ) AS Q3,
            SUM(
                CASE
                    WHEN CAST(strftime('%m', he.datetime) AS INTEGER) BETWEEN 10 AND 12 THEN 1
                    ELSE 0
                END
            ) AS Q4
        FROM hired_employees he
        JOIN departments d ON d.id = he.department_id
        JOIN jobs j ON j.id = he.job_id
        WHERE substr(he.datetime, 1, 4) = '2021'
        GROUP BY d.department, j.job
        ORDER BY d.department ASC, j.job ASC
    """
    return [dict(row) for row in connection.execute(query).fetchall()]


def departments_above_average(connection: sqlite3.Connection) -> list[dict]:
    # The mean includes every department, including those with zero hires in 2021.
    query = """
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
        ),
        average_hires AS (
            SELECT AVG(hired) AS average_hired FROM department_hires
        )
        SELECT id, department, hired
        FROM department_hires
        WHERE hired > (SELECT average_hired FROM average_hires)
        ORDER BY hired DESC
    """
    return [dict(row) for row in connection.execute(query).fetchall()]
