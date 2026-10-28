import hashlib
import os
import sqlite3
from collections import Counter
from pathlib import Path


def _readonly_uri(path):
    return Path(path).resolve().as_uri() + "?mode=ro"


def _schema(conn):
    rows = conn.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_master "
        "WHERE substr(name, 1, 7) != 'sqlite_'"
    ).fetchall()
    return Counter(tuple(row) for row in rows)


def _user_tables(conn):
    return [row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]


def _quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def _rows_equal(source, clone):
    source_tables = _user_tables(source)
    clone_tables = _user_tables(clone)
    if source_tables != clone_tables:
        return False
    for table in source_tables:
        query = "SELECT * FROM " + _quote_identifier(table)
        if Counter(tuple(row) for row in source.execute(query)) != Counter(
            tuple(row) for row in clone.execute(query)
        ):
            return False
    return True


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def solve(payload):
    source_path = payload["source_path"]
    destination_path = payload["destination_path"]
    try:
        descriptor = os.open(destination_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
    except FileExistsError:
        return {
            "status": "destination_exists",
            "byte_clone": None,
            "schema_equal": None,
            "rows_equal": None,
            "integrity_ok": None,
            "foreign_key_violations": None,
            "clone_success": False,
            "data_valid": None,
        }
    os.close(descriptor)

    byte_clone = schema_equal = rows_equal = integrity_ok = None
    foreign_key_violations = data_valid = None
    try:
        with sqlite3.connect(_readonly_uri(source_path), uri=True) as source:
            with sqlite3.connect(destination_path) as destination:
                source.backup(destination)
        byte_clone = _sha256(source_path) == _sha256(destination_path)

        with sqlite3.connect(_readonly_uri(source_path), uri=True) as source:
            with sqlite3.connect(_readonly_uri(destination_path), uri=True) as clone:
                schema_equal = _schema(source) == _schema(clone)
                rows_equal = _rows_equal(source, clone)
                integrity_rows = clone.execute("PRAGMA integrity_check").fetchall()
                integrity_ok = all(row[0] == "ok" for row in integrity_rows)
                foreign_key_violations = sum(
                    1 for _ in clone.execute("PRAGMA foreign_key_check")
                )
                data_valid = integrity_ok and foreign_key_violations == 0
    except (OSError, sqlite3.Error, ValueError):
        pass

    clone_success = bool(schema_equal and rows_equal and integrity_ok)
    return {
        "status": "created",
        "byte_clone": byte_clone,
        "schema_equal": schema_equal,
        "rows_equal": rows_equal,
        "integrity_ok": integrity_ok,
        "foreign_key_violations": foreign_key_violations,
        "clone_success": clone_success,
        "data_valid": data_valid,
    }