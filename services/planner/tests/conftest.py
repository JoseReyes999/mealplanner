"""Shared fixture for the tests that need a database.

They run against a real SQL Server test database (TEST_DATABASE_URL), the same engine as
Azure SQL. Before every test the database is emptied, so each test starts from the
migrations applied to a blank database and ids start again at 1.
"""
import os

import pytest

import db

# Drop every foreign key, then every table (including schema_migrations).
EMPTY_DATABASE = """
DECLARE @sql NVARCHAR(MAX) = N'';
SELECT @sql += N'ALTER TABLE ' + QUOTENAME(OBJECT_SCHEMA_NAME(parent_object_id)) + N'.'
    + QUOTENAME(OBJECT_NAME(parent_object_id)) + N' DROP CONSTRAINT ' + QUOTENAME(name) + N';'
FROM sys.foreign_keys;
SELECT @sql += N'DROP TABLE ' + QUOTENAME(SCHEMA_NAME(schema_id)) + N'.' + QUOTENAME(name) + N';'
FROM sys.tables;
EXEC sp_executesql @sql;
"""


@pytest.fixture
def database_url():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("Set TEST_DATABASE_URL, e.g. mssql://sa:<password>@localhost:1433/planner_test")
    if not db.parse_url(url)["database"].endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must point at a *_test database: the tests delete everything in it")
    conn = db.connect(url)
    try:
        with conn:
            conn.execute(EMPTY_DATABASE)
    finally:
        conn.close()
    return url