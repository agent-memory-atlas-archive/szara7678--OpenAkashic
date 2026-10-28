import hashlib, os, sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import quote

def _ro(path):
    return sqlite3.connect("file:" + quote(str(Path(path).resolve()), safe="/") + "?mode=ro", uri=True)

def _schema(db):
    return sorted(tuple(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'"))

def _tables(db):
    return [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]

def _rows(db, table):
    name = '"' + table.replace('"', '""') + '"'
    return Counter(tuple(r) for r in db.execute("SELECT * FROM " + name))

def _hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.digest()

def solve(payload):
    src, dst = os.fspath(payload["source_path"]), os.fspath(payload["destination_path"])
    result = {"status":"destination_exists","byte_clone":None,"schema_equal":None,"rows_equal":None,"integrity_ok":None,"foreign_key_violations":None,"clone_success":False,"data_valid":None}
    try:
        fd = os.open(dst, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
    except FileExistsError:
        return result
    os.close(fd)
    result["status"] = "created"
    original = _ro(src)
    target = sqlite3.connect(dst)
    try:
        original.backup(target)
    finally:
        target.close()
        original.close()
    original, clone = _ro(src), _ro(dst)
    try:
        schema_equal = _schema(original) == _schema(clone)
        source_tables, clone_tables = _tables(original), _tables(clone)
        rows_equal = source_tables == clone_tables and all(_rows(original,t) == _rows(clone,t) for t in source_tables)
        integrity = [r[0] for r in clone.execute("PRAGMA integrity_check")]
        integrity_ok = all(v == "ok" for v in integrity)
        violations = sum(1 for _ in clone.execute("PRAGMA foreign_key_check"))
    finally:
        clone.close()
        original.close()
    byte_clone = _hash(src) == _hash(dst)
    result.update(byte_clone=byte_clone,schema_equal=schema_equal,rows_equal=rows_equal,integrity_ok=integrity_ok,foreign_key_violations=violations,clone_success=bool(schema_equal and rows_equal and integrity_ok),data_valid=bool(integrity_ok and violations == 0))
    return result
