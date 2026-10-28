import hashlib, os, sqlite3
from collections import Counter
from urllib.parse import quote

def _ro(path):
    uri = "file:" + quote(os.path.abspath(os.fspath(path)), safe="/:\\") + "?mode=ro"
    return sqlite3.connect(uri, uri=True)

def _schema(c):
    return c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name,tbl_name,sql").fetchall()

def _tables(c):
    return [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]

def _rows(c):
    out = {}
    for t in _tables(c):
        q = '"' + t.replace('"', '""') + '"'
        out[t] = Counter(tuple(r) for r in c.execute("SELECT * FROM " + q))
    return out

def _hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1048576), b""): h.update(b)
    return h.digest()

def solve(payload):
    source, dest = os.fspath(payload["source_path"]), os.fspath(payload["destination_path"])
    try: fd = os.open(dest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
    except FileExistsError:
        return dict(status="destination_exists", byte_clone=None, schema_equal=None, rows_equal=None, integrity_ok=None, foreign_key_violations=None, clone_success=False, data_valid=None)
    os.close(fd)
    src = dst = None
    try:
        src = _ro(source)
        dst = sqlite3.connect(dest)
        src.backup(dst)
        dst.close(); dst = None
        src.close(); src = None
        src, dst = _ro(source), _ro(dest)
        byte_clone = _hash(source) == _hash(dest)
        schema_equal, rows_equal = _schema(src) == _schema(dst), _rows(src) == _rows(dst)
        checks = [r[0] for r in dst.execute("PRAGMA integrity_check")]
        integrity_ok = bool(checks) and all(x == "ok" for x in checks)
        violations = sum(1 for _ in dst.execute("PRAGMA foreign_key_check"))
        return dict(status="created", byte_clone=byte_clone, schema_equal=schema_equal, rows_equal=rows_equal, integrity_ok=integrity_ok, foreign_key_violations=violations, clone_success=schema_equal and rows_equal and integrity_ok, data_valid=integrity_ok and violations == 0)
    finally:
        if dst is not None: dst.close()
        if src is not None: src.close()
