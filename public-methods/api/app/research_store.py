import hashlib
import ipaddress
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunsplit


def require_tables(db, names):
    """Validate an initialized public archive using SELECT statements only."""
    existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = set(names) - existing
    if missing:
        raise RuntimeError("read-only research schema is incomplete: " + ", ".join(sorted(missing)))


def connect_archive(path, read_only=False):
    if read_only:
        if not Path(path).is_file():
            raise RuntimeError("read-only research requires an existing initialized database")
        db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    else:
        db = sqlite3.connect(str(path))
    db.row_factory = sqlite3.Row
    return db


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def public_payload(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in {"private", "private_note", "private_notes", "raw_note", "raw_notes", "personal_vault", "owner", "owner_id", "credentials", "access_token", "api_key", "secret"}:
                raise ValueError("private payload is not accepted")
            public_payload(item)
    elif isinstance(value, list):
        for item in value:
            public_payload(item)


def public_uri(uri):
    parsed = urlparse(uri)
    host = (parsed.hostname or "").rstrip(".").lower()
    if any(ord(c) < 32 or c.isspace() for c in uri) or "\\" in uri:
        raise ValueError("invalid evidence URI")
    try:
        parsed.port
    except ValueError:
        raise ValueError("invalid evidence URI port") from None
    if parsed.scheme not in {"http", "https"} or not host or parsed.username or parsed.password:
        raise ValueError("public HTTP(S) evidence URI required")
    if host.lower() in {"localhost", "closed-akashic", "closed.openakashic.com"} or host.lower().endswith((".localhost", ".local", ".internal")) or "closed-akashic" in host.lower():
        raise ValueError("private evidence URI rejected")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host or all(c.isdigit() or c == "." for c in host):
            raise ValueError("public hostname required")
        return
    if not address.is_global:
        raise ValueError("private evidence URI rejected")


def canonical_agent_uri(uri):
    """Stable document identity, without fetching or resolving a submitted URL."""
    public_uri(uri)
    parsed = urlparse(uri)
    if parsed.scheme != "https":
        raise ValueError("agent evidence requires HTTPS")
    host = parsed.hostname.rstrip(".").lower().encode("idna").decode("ascii")
    authority = "[" + host + "]" if ":" in host else host
    if parsed.port and parsed.port != 443:
        authority += ":" + str(parsed.port)
    return urlunsplit(("https", authority, parsed.path or "/", parsed.query, ""))


class ResearchStore:
    """Public investigation snapshots. Caller must supply an external data path."""
    def __init__(self, db_path, read_only=False):
        self.db_path = str(db_path)
        self.read_only = read_only
        if self.read_only:
            with self._connect() as db:
                require_tables(db, ["research_subjects", "research_evidence", "research_investigations", "research_current", "research_latest"])
            return
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS research_subjects (id TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS research_evidence (id TEXT PRIMARY KEY, source TEXT NOT NULL, external_id TEXT NOT NULL, hash TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(source, external_id, hash));
                CREATE TABLE IF NOT EXISTS research_investigations (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, subject_id TEXT NOT NULL, body TEXT NOT NULL, idem_key TEXT UNIQUE, fingerprint TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS research_current (subject_id TEXT NOT NULL, source TEXT NOT NULL, scope TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(subject_id, source, scope));
                CREATE TABLE IF NOT EXISTS research_latest (subject_id TEXT NOT NULL, source TEXT NOT NULL, scope TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(subject_id, source, scope));
            ''')

    def _connect(self):
        return connect_archive(self.db_path, self.read_only)

    def save_investigation(self, question, subject, source_results, idempotency_key=None, request_fingerprint=None):
        public_payload(subject)
        public_payload(source_results)
        if not isinstance(question, str) or not question.strip() or not subject.get("id"):
            raise ValueError("question and subject id required")
        fingerprint = request_fingerprint or digest({"question": question, "subject": subject, "source_results": source_results})
        now = datetime.now(timezone.utc).isoformat()
        result = {"id": str(uuid.uuid4()), "question": question, "subject_id": subject["id"], "subject": subject, "created_at": now, "source_results": [], "facts": [], "evidence": [], "changes": [], "reused_evidence_count": 0}
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if idempotency_key:
                prior = db.execute("SELECT body,fingerprint FROM research_investigations WHERE idem_key=?", (idempotency_key,)).fetchone()
                if prior:
                    if prior["fingerprint"] != fingerprint:
                        raise ValueError("idempotency key request conflict")
                    return json.loads(prior["body"])
            seen_scopes = set()
            for source in source_results:
                source_id, scope = source["source_id"], source["scope_key"]
                agent_source = isinstance(source_id, str) and source_id.startswith("agent_web:")
                if (source_id not in {"wikidata", "github", "opendart", "naver_news", "openakashic_core"} and not agent_source) or not isinstance(scope, str) or not scope.strip():
                    raise ValueError("supported public source and stable scope required")
                if (source_id, scope) in seen_scopes:
                    raise ValueError("duplicate source scope")
                seen_scopes.add((source_id, scope))
                status = source["status"]
                if status not in {"ok", "needs_credentials", "unavailable", "not_found"}:
                    raise ValueError("invalid source status")
                saved = {k: source[k] for k in ("source_id", "scope_key", "reason", "coverage") if k in source}
                saved["status"] = status
                saved["evidence_ids"] = []
                if status != "ok":
                    result["source_results"].append(saved)
                    continue
                if not source.get("evidence"):
                    raise ValueError("successful source requires evidence, including explicit empty-result evidence")
                lookup, snapshot = {}, {}
                current_facts, current_evidence = [], []
                for item in source.get("evidence", []):
                    public_uri(item["source_uri"])
                    if agent_source:
                        uri = canonical_agent_uri(item["source_uri"])
                        if source_id != "agent_web:" + urlparse(uri).hostname or scope != "agent-source:" + digest(uri):
                            raise ValueError("agent source identity must match public URI")
                    external_id = str(item["external_id"])
                    if external_id in lookup:
                        raise ValueError("duplicate evidence external id")
                    if not isinstance(item["excerpt"], str) or not isinstance(item["content"], dict):
                        raise ValueError("evidence text and content required")
                    content_hash = digest({k: item.get(k) for k in ("source_uri", "excerpt", "content", "source_time", "coverage")})
                    prior = db.execute("SELECT body FROM research_evidence WHERE source=? AND external_id=? AND hash=?", (source_id, external_id, content_hash)).fetchone()
                    if prior:
                        evidence = json.loads(prior["body"])
                        result["reused_evidence_count"] += 1
                    else:
                        evidence = dict(item, id=str(uuid.uuid4()), source_id=source_id, content_hash=content_hash, normalized_content_hash=digest(item["content"]), collected_at=now, observed_at=now)
                        db.execute("INSERT INTO research_evidence VALUES (?,?,?,?,?)", (evidence["id"], source_id, external_id, content_hash, canonical(evidence)))
                    evidence = dict(evidence, observed_at=now)
                    if agent_source:
                        evidence = dict(evidence, source_observed_at=item.get("source_observed_at"), agent_name=item.get("agent_name"))
                    current_evidence.append(evidence)
                    lookup[external_id] = evidence["id"]
                    snapshot[external_id] = {"evidence_id": evidence["id"], "content": item["content"]}
                    saved["evidence_ids"].append(evidence["id"])
                    if not any(e["id"] == evidence["id"] for e in result["evidence"]):
                        result["evidence"].append(evidence)
                for fact in source.get("facts", []):
                    ref = str(fact["evidence_external_id"])
                    if ref not in lookup or fact.get("epistemic_state") != "source_observation":
                        raise ValueError("invalid fact evidence or epistemic state")
                    fact_result = dict(fact, id=digest({"subject_id": subject["id"], "source_id": source_id, "scope_key": scope, "predicate": fact["predicate"], "value": fact["value"], "evidence_id": lookup[ref]}), source_id=source_id, scope_key=scope, evidence_id=lookup[ref], observed_at=now, source_time=next(e.get("source_time") for e in current_evidence if e["id"] == lookup[ref]))
                    current_facts.append(fact_result)
                    result["facts"].append(fact_result)
                previous = db.execute("SELECT body FROM research_latest WHERE subject_id=? AND source=? AND scope=?", (subject["id"], source_id, scope)).fetchone()
                old = json.loads(previous["body"]) if previous else {}
                for external_id in sorted(set(old) | set(snapshot)):
                    before, after = old.get(external_id), snapshot.get(external_id)
                    if before and not any(e["id"] == before["evidence_id"] for e in result["evidence"]):
                        historical = db.execute("SELECT body FROM research_evidence WHERE id=?", (before["evidence_id"],)).fetchone()
                        result["evidence"].append(json.loads(historical["body"]))
                    before_content = before["content"] if before else {}
                    after_content = after["content"] if after else {}
                    for field in sorted(set(before_content) | set(after_content)):
                        if field in before_content and field in after_content and canonical(before_content[field]) == canonical(after_content[field]):
                            continue
                        kind = ("initial_observation" if not previous else "added") if field not in before_content else "no_longer_observed" if field not in after_content else "changed"
                        result["changes"].append({"source_id": source_id, "scope_key": scope, "external_id": external_id, "field": field, "predicate": field, "kind": kind, "observed_at": now, "previous_evidence_id": before["evidence_id"] if before else None, "evidence_id": after["evidence_id"] if after else None, "previous": before_content.get(field), "current": after_content.get(field), "old_evidence_id": before["evidence_id"] if before else None, "new_evidence_id": after["evidence_id"] if after else None, "epistemic_state": "source_observation"})
                saved["status"] = "unchanged" if previous and canonical(old) == canonical(snapshot) else "saved"
                db.execute("INSERT OR REPLACE INTO research_latest VALUES (?,?,?,?)", (subject["id"], source_id, scope, canonical(snapshot)))
                db.execute("INSERT OR REPLACE INTO research_current VALUES (?,?,?,?)", (subject["id"], source_id, scope, canonical({"facts": current_facts, "evidence": current_evidence})))
                result["source_results"].append(saved)
            successes = sum(s["status"] in {"saved", "unchanged"} for s in result["source_results"])
            if successes:
                db.execute("INSERT OR REPLACE INTO research_subjects VALUES (?,?)", (subject["id"], canonical(subject)))
            else:
                db.execute("INSERT OR IGNORE INTO research_subjects VALUES (?,?)", (subject["id"], canonical(subject)))
            result["status"] = "complete" if successes and successes == len(source_results) else "partial" if successes else "failed"
            db.execute("INSERT INTO research_investigations VALUES (?,?,?,?,?,?)", (result["id"], now, subject["id"], canonical(result), idempotency_key, fingerprint))
        return result

    def list_subjects(self):
        with self._connect() as db:
            rows = db.execute("SELECT s.body, MAX(i.created_at) AS updated_at, COUNT(i.id) AS investigation_count FROM research_subjects s LEFT JOIN research_investigations i ON i.subject_id=s.id GROUP BY s.id ORDER BY updated_at DESC LIMIT 100").fetchall()
            return {"subjects": [dict(json.loads(r["body"]), updated_at=r["updated_at"], investigation_count=r["investigation_count"]) for r in rows]}

    def list_investigations(self):
        with self._connect() as db:
            return {"investigations": [json.loads(r[0]) for r in db.execute("SELECT body FROM research_investigations ORDER BY created_at DESC LIMIT 100")]}

    def get_investigation(self, investigation_id):
        with self._connect() as db:
            row = db.execute("SELECT body FROM research_investigations WHERE id=?", (investigation_id,)).fetchone()
            return json.loads(row[0]) if row else None

    def get_subject(self, subject_id):
        with self._connect() as db:
            row = db.execute("SELECT body FROM research_subjects WHERE id=?", (subject_id,)).fetchone()
            if not row:
                return None
            investigations = [json.loads(r[0]) for r in db.execute("SELECT body FROM research_investigations WHERE subject_id=? ORDER BY created_at DESC LIMIT 100", (subject_id,))]
            metadata = db.execute("SELECT MAX(created_at) AS updated_at, COUNT(*) AS investigation_count FROM research_investigations WHERE subject_id=?", (subject_id,)).fetchone()
            current = [json.loads(r[0]) for r in db.execute("SELECT body FROM research_current WHERE subject_id=? LIMIT 100", (subject_id,))]
        evidence = {e["id"]: e for item in current for e in item["evidence"]}
        return {"subject": dict(json.loads(row[0]), updated_at=metadata["updated_at"], investigation_count=metadata["investigation_count"]), "investigations": investigations, "facts": [f for i in current for f in i["facts"]], "evidence": list(evidence.values()), "changes": [c for i in investigations for c in i["changes"]]}

    def export(self, investigation_id):
        investigation = self.get_investigation(investigation_id)
        if investigation is None:
            return None
        subject = investigation.get("subject")
        if subject is None:
            # Old rows cannot reconstruct metadata at collection time; do not substitute current metadata.
            subject = {"id": investigation["subject_id"], "metadata_unavailable": True}
        return {"schema_version": "1.0", "provenance": {"kind": "public_source_investigation", "exported_at": datetime.now(timezone.utc).isoformat()}, "subject": subject, "investigation": investigation}
