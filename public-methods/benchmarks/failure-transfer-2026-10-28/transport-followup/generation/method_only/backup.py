import hashlib
import os
import sqlite3
from pathlib import Path
from collections import Counter


def _ro(path):
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)


def _schema(conn):
    return conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name,tbl_name,sql"
    ).fetchall()


def _tables(conn):
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]


def _rows_equal(a, b):
    ta, tb = _tables(a), _tables(b)
    if ta != tb:
        return False
    for table in ta:
        q = '"' + table.replace('"', '""') + '"'
        if Counter(a.execute("SELECT * FROM " + q).fetchall()) != Counter(
            b.execute("SELECT * FROM " + q).fetchall()
        ):
            return False
    return True


def solve(payload):
    source, destination = map(os.fspath, (payload["source_path"], payload["destination_path"]))
    result = {"status": "created", "byte_clone": None, "schema_equal": None,
              "rows_equal": None, "integrity_ok": None, "foreign_key_violations": None,
              "clone_success": False, "data_valid": None}
    try:
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
    except FileExistsError:
        result.update(status="destination_exists")
        return {k: (None if k in ("byte_clone","schema_equal","rows_equal","integrity_ok","foreign_key_violations","data_valid") else v)
                for k,v in result.items()}
    os.close(fd)
    try:
        with _ro(source) as src, sqlite3.connect(destination) as dst:
            src.backup(dst)
        result["byte_clone"] = hashlib.sha256(Path(source).read_bytes()).digest() == hashlib.sha256(Path(destination).read_bytes()).digest()
        with _ro(source) as src, _ro(destination) as dst:
            result["schema_equal"] = _schema(src) == _schema(dst)
            result["rows_equal"] = _rows_equal(src, dst)
            checks = dst.execute("PRAGMA integrity_check").fetchall()
            result["integrity_ok"] = all(row == ("ok",) for row in checks)
            result["foreign_key_violations"] = len(dst.execute("PRAGMA foreign_key_check").fetchall())
        result["clone_success"] = result["schema_equal"] and result["rows_equal"] and result["integrity_ok"]
        result["data_valid"] = result["integrity_ok"] and result["foreign_key_violations"] == 0
    except Exception:
        pass
    return result