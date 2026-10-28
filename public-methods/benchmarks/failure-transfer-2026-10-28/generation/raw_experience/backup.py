from collections import Counter
import hashlib
import os
import sqlite3
from urllib.parse import quote


def _readonly_uri(path):
    return "file:" + quote(os.path.abspath(os.fspath(path)), safe="/:") + "?mode=ro"


def _schema(conn):
    return Counter(
        (row[0], row[1], row[2], row[3])
        for row in conn.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master"
        )
        if not str(row[1]).startswith("sqlite_")
    )


def _user_tables(conn):
    return [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        if not str(row[0]).startswith("sqlite_")
    ]


def _rows(conn, table):
    identifier = '"' + table.replace('"', '""') + '"'
    return Counter(tuple(row) for row in conn.execute("SELECT * FROM " + identifier))


def _digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.digest()


def solve(payload):
    source = os.fspath(payload["source_path"])
    destination = os.fspath(payload["destination_path"])
    try:
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
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
    os.close(fd)

    source_conn = sqlite3.connect(_readonly_uri(source), uri=True)
    destination_conn = sqlite3.connect(destination)
    try:
        source_conn.backup(destination_conn)
    finally:
        destination_conn.close()
        source_conn.close()

    original = sqlite3.connect(_readonly_uri(source), uri=True)
    clone = sqlite3.connect(_readonly_uri(destination), uri=True)
    try:
        schema_equal = _schema(original) == _schema(clone)
        original_tables = _user_tables(original)
        clone_tables = _user_tables(clone)
        rows_equal = set(original_tables) == set(clone_tables)
        if rows_equal:
            rows_equal = all(_rows(original, name) == _rows(clone, name) for name in original_tables)
        integrity_rows = [row[0] for row in clone.execute("PRAGMA integrity_check")]
        integrity_ok = bool(integrity_rows) and all(row == "ok" for row in integrity_rows)
        violations = sum(1 for _ in clone.execute("PRAGMA foreign_key_check"))
    finally:
        clone.close()
        original.close()

    byte_clone = _digest(source) == _digest(destination)
    clone_success = bool(schema_equal and rows_equal and integrity_ok)
    return {
        "status": "created",
        "byte_clone": byte_clone,
        "schema_equal": schema_equal,
        "rows_equal": rows_equal,
        "integrity_ok": integrity_ok,
        "foreign_key_violations": violations,
        "clone_success": clone_success,
        "data_valid": bool(integrity_ok and violations == 0),
    }
