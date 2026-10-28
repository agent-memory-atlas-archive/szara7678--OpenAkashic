import hashlib
import os
import sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import quote


def _uri(path, mode):
    raw = os.fspath(path)
    return "file:" + quote(raw, safe="/:") + "?mode=" + mode


def _ident(name):
    return '"' + name.replace('"', '""') + '"'


def _schema(conn):
    return sorted(
        (row[0], row[1], row[2], row[3])
        for row in conn.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%'"
        )
    )


def _rows(conn):
    result = {}
    for (table,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'"
    ):
        result[table] = Counter(
            tuple(row) for row in conn.execute("SELECT * FROM " + _ident(table))
        )
    return result


def _digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.digest()


def solve(payload):
    source = os.fspath(payload["source_path"])
    destination = os.fspath(payload["destination_path"])
    if os.path.exists(destination):
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

    # Reserve the new path atomically so an existing destination is never opened.
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(destination, flags, 0o666)
    os.close(fd)
    source_conn = target_conn = check_conn = None
    try:
        source_conn = sqlite3.connect(_uri(source, "ro"), uri=True)
        target_conn = sqlite3.connect(destination)
        source_conn.backup(target_conn)
        target_conn.close()
        target_conn = None

        check_conn = sqlite3.connect(_uri(destination, "ro"), uri=True)
        integrity_rows = [row[0] for row in check_conn.execute("PRAGMA integrity_check")]
        integrity_ok = bool(integrity_rows) and all(row == "ok" for row in integrity_rows)
        violations = sum(1 for _ in check_conn.execute("PRAGMA foreign_key_check"))
        source_schema = _schema(source_conn)
        target_schema = _schema(check_conn)
        source_rows = _rows(source_conn)
        target_rows = _rows(check_conn)
        schema_equal = source_schema == target_schema
        rows_equal = source_rows == target_rows
        byte_clone = _digest(source) == _digest(destination)
        clone_success = schema_equal and rows_equal and integrity_ok
        return {
            "status": "created",
            "byte_clone": byte_clone,
            "schema_equal": schema_equal,
            "rows_equal": rows_equal,
            "integrity_ok": integrity_ok,
            "foreign_key_violations": violations,
            "clone_success": clone_success,
            "data_valid": integrity_ok and violations == 0,
        }
    finally:
        if target_conn is not None:
            target_conn.close()
        if check_conn is not None:
            check_conn.close()
        if source_conn is not None:
            source_conn.close()