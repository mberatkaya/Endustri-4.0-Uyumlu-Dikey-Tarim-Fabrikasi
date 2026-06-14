from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from subscriber import mqtt_subscriber


def test_get_db_builds_postgres_connection(monkeypatch):
    connection = object()
    connect = Mock(return_value=connection)
    monkeypatch.setitem(sys.modules, "psycopg2", SimpleNamespace(connect=connect))

    assert mqtt_subscriber.get_db("POSTGRES") is connection
    connect.assert_called_once_with(
        host=mqtt_subscriber.DB_HOST,
        port=mqtt_subscriber.DB_PORT,
        dbname=mqtt_subscriber.DB_NAME,
        user=mqtt_subscriber.DB_USER,
        password=mqtt_subscriber.DB_PASS,
        sslmode="require",
    )


def test_get_db_uses_explicit_sqlserver_connection_string(monkeypatch):
    connection = object()
    connect = Mock(return_value=connection)
    monkeypatch.setitem(sys.modules, "mssql_python", SimpleNamespace(connect=connect))
    monkeypatch.setattr(
        mqtt_subscriber,
        "SQLSERVER_CONNECTION_STRING",
        "Server=test;Database=DikeyTarimDB",
    )

    assert mqtt_subscriber.get_db("SQLSERVER") is connection
    connect.assert_called_once_with("Server=test;Database=DikeyTarimDB")


def test_get_db_builds_sqlserver_connection_string_from_settings(monkeypatch):
    connect = Mock(return_value=object())
    monkeypatch.setitem(sys.modules, "mssql_python", SimpleNamespace(connect=connect))
    monkeypatch.setattr(mqtt_subscriber, "SQLSERVER_CONNECTION_STRING", "")

    mqtt_subscriber.get_db("sqlserver")

    connection_string = connect.call_args.args[0]
    assert f"Server={mqtt_subscriber.SQLSERVER_HOST},{mqtt_subscriber.SQLSERVER_PORT}" in (
        connection_string
    )
    assert f"Database={mqtt_subscriber.SQLSERVER_DATABASE}" in connection_string
    assert f"UID={mqtt_subscriber.SQLSERVER_USER}" in connection_string
    assert f"PWD={mqtt_subscriber.SQLSERVER_PASSWORD}" in connection_string


def test_get_db_rejects_unknown_engine():
    with pytest.raises(ValueError, match="DB_ENGINE"):
        mqtt_subscriber.get_db("sqlite")
