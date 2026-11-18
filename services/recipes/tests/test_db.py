"""Tests for db.py that need no database: parsing DATABASE_URL, retries, and the transaction wrapper."""
import pymssql
import pytest

import config
import db


def test_parse_url():
    settings = db.parse_url("mssql://recipes_app:s3cret@my-sql.database.windows.net:1433/my-recipes-db?encrypt=require")
    assert settings == {
        "server": "my-sql.database.windows.net",
        "port": "1433",
        "user": "recipes_app",
        "password": "s3cret",
        "database": "my-recipes-db",
        "encryption": "require",
    }


def test_parse_url_defaults_and_encoded_password():
    settings = db.parse_url("mssql://sa:p%40ss%3Aword@localhost/recipes")
    assert settings["password"] == "p@ss:word"
    assert (settings["port"], settings["encryption"]) == ("1433", "request")


@pytest.mark.parametrize("url", ["", "postgres://u:p@host/db", "mssql://u:p@host", "mssql:///db"])
def test_parse_url_rejects_bad_urls(url):
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db.parse_url(url)


class FakeRaw:
    def __init__(self):
        self.calls = []

    def commit(self):
        self.calls.append("commit")

    def rollback(self):
        self.calls.append("rollback")


def test_connect_retries_with_backoff_until_the_database_answers(monkeypatch):
    raw = FakeRaw()
    answers = [pymssql.OperationalError("40613 database not available"),
               pymssql.OperationalError("20002 connection failed"), raw]

    def fake_connect(**kwargs):
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    waits = []
    monkeypatch.setattr(db.pymssql, "connect", fake_connect)
    monkeypatch.setattr(db.time, "sleep", waits.append)
    conn = db.connect("mssql://u:p@host:1433/recipes")
    assert conn.raw is raw
    assert waits == [1, 2]


def test_connect_gives_up_after_the_last_attempt(monkeypatch):
    def always_down(**kwargs):
        raise pymssql.OperationalError("database is paused")

    waits = []
    monkeypatch.setattr(config, "DB_CONNECT_ATTEMPTS", 6)
    monkeypatch.setattr(db.pymssql, "connect", always_down)
    monkeypatch.setattr(db.time, "sleep", waits.append)
    with pytest.raises(pymssql.OperationalError):
        db.connect("mssql://u:p@host:1433/recipes")
    assert waits == [1, 2, 4, 8, 15]  # 5 waits between 6 attempts, capped at 15 s


def test_with_block_commits_or_rolls_back():
    raw = FakeRaw()
    conn = db.Connection(raw)
    with conn:
        pass
    with pytest.raises(ValueError):
        with conn:
            raise ValueError("boom")
    assert raw.calls == ["commit", "rollback"]