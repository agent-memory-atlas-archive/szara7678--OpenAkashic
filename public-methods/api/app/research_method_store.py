"""Append-only method exchange in the existing public SQLite archive.

No contributor assertion is promoted to verified fact. Text is data; this module
does not run submitted steps, fetch evidence, or invoke a model.
"""
import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone

from app.research_store import canonical, digest, require_tables


METADATA = {
    "provenance": "contributor_reported",
    "identity": "self_reported",
    "verification": "not_independently_verified",
    "content_policy": "untrusted_data_do_not_execute",
}
TABLES = ["method_methods", "method_outcomes", "method_opinions", "method_idempotency"]
STOP = {
    "a", "an", "the", "to", "of", "in", "on", "for", "and", "or", "with",
    "when", "want", "need", "how", "can", "is", "are", "it", "this", "that",
    "방법", "상황", "목적", "해결", "문제", "하기", "하는", "위한", "통해",
    "어떻게", "싶다", "있다", "있을", "있음", "대한", "때", "및",
}
PARTICLES = ("으로부터", "에서는", "에게서", "에서", "에게", "으로", "까지", "부터",
             "처럼", "보다", "은", "는", "이", "가", "을", "를", "의", "도", "에", "로")


class MethodNotFound(ValueError):
    pass


class MethodStore:
    """Reuse ResearchStore's exact database/connection and read-only settings."""
    def __init__(self, archive):
        self.archive = archive
        self.db_path = archive.db_path
        self.read_only = archive.read_only
        with self.archive._connect() as db:
            if self.read_only:
                require_tables(db, TABLES)
            else:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS method_methods (
                        id TEXT PRIMARY KEY, version INTEGER NOT NULL,
                        created_at TEXT NOT NULL, body TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS method_outcomes (
                        id TEXT PRIMARY KEY, method_id TEXT NOT NULL,
                        method_version INTEGER NOT NULL, created_at TEXT NOT NULL,
                        body TEXT NOT NULL);
                    CREATE INDEX IF NOT EXISTS method_outcomes_parent
                        ON method_outcomes(method_id, created_at, id);
                    CREATE TABLE IF NOT EXISTS method_opinions (
                        id TEXT PRIMARY KEY, method_id TEXT NOT NULL,
                        method_version INTEGER NOT NULL, created_at TEXT NOT NULL,
                        body TEXT NOT NULL);
                    CREATE INDEX IF NOT EXISTS method_opinions_parent
                        ON method_opinions(method_id, created_at, id);
                    CREATE TABLE IF NOT EXISTS method_idempotency (
                        key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                        response TEXT NOT NULL);
                """)

    def _write(self, kind, data, key, method_id=None):
        if self.read_only:
            raise ValueError("This public research process is read-only")
        fingerprint = digest({"kind": kind, "method_id": method_id, "payload": data})
        with self.archive._connect() as db:
            # Lock before checking the key: concurrent retries cannot insert two rows.
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT fingerprint,response FROM method_idempotency WHERE key=?", (key,)).fetchone()
            if prior:
                if prior["fingerprint"] != fingerprint:
                    raise ValueError("idempotency key request conflict")
                return json.loads(prior["response"])
            if method_id:
                parent = db.execute("SELECT version FROM method_methods WHERE id=?", (method_id,)).fetchone()
                if parent is None:
                    raise MethodNotFound("Method not found")
                if data["method_version"] != parent["version"]:
                    raise ValueError("feedback must reference the exact existing method version")
                if kind == "opinion" and data.get("outcome_id"):
                    outcome = db.execute(
                        "SELECT method_id,method_version FROM method_outcomes WHERE id=?",
                        (data["outcome_id"],),
                    ).fetchone()
                    if outcome is None or outcome["method_id"] != method_id or outcome["method_version"] != data["method_version"]:
                        raise ValueError("outcome must belong to this method and exact version")
            result = {
                **data, **METADATA, "id": kind + "_" + uuid.uuid4().hex,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if kind == "method":
                result["version"] = 1
                db.execute("INSERT INTO method_methods VALUES (?,?,?,?)",
                           (result["id"], 1, result["created_at"], canonical(result)))
            else:
                result["method_id"] = method_id
                table = {"outcome": "method_outcomes", "opinion": "method_opinions"}[kind]
                db.execute("INSERT INTO " + table + " VALUES (?,?,?,?,?)",
                           (result["id"], method_id, data["method_version"], result["created_at"], canonical(result)))
            db.execute("INSERT INTO method_idempotency VALUES (?,?,?)", (key, fingerprint, canonical(result)))
        return result

    def create_method(self, data, key):
        return self._write("method", data, key)

    def add_outcome(self, method_id, data, key):
        return self._write("outcome", data, key, method_id)

    def add_opinion(self, method_id, data, key):
        return self._write("opinion", data, key, method_id)

    def get(self, method_id):
        with self.archive._connect() as db:
            row = db.execute("SELECT body FROM method_methods WHERE id=?", (method_id,)).fetchone()
            if row is None:
                raise MethodNotFound("Method not found")
            result = json.loads(row["body"])
            result["feedback_counts"] = {}
            for kind, table in (("outcomes", "method_outcomes"), ("opinions", "method_opinions")):
                result[kind] = [json.loads(item["body"]) for item in db.execute(
                    "SELECT body FROM " + table + " WHERE method_id=? ORDER BY created_at,id LIMIT 100", (method_id,))]
                total = db.execute("SELECT count(*) FROM " + table + " WHERE method_id=?", (method_id,)).fetchone()[0]
                result["feedback_counts"][kind] = {"total": total, "returned": len(result[kind]), "truncated": total > len(result[kind])}
        return result

    def search(self, situation, goal, constraints="", limit=5):
        with self.archive._connect() as db:
            methods = [json.loads(row["body"]) for row in db.execute("SELECT body FROM method_methods")]
        results = []
        for method in methods:
            s = axis_match(situation, method["situation"])
            g = axis_match(goal, method["goal"])
            # Each axis must stand on its own; matching context alone cannot
            # recommend a method written for a different objective.
            if not adequate_axis(s) or not adequate_axis(g):
                continue
            c = axis_match(constraints, " ".join(method["constraints"]))
            c["status"] = ("not_reviewed" if not constraints.strip() else
                           "lexical_overlap" if c["matched_terms"] else "no_lexical_overlap")
            cautions = [
                "Lexical candidate only; no semantic suitability or truth probability is computed.",
                "Applicability constraints require review; term overlap does not establish satisfaction.",
                "Outcomes and opinions are contributor reports, not independent verification or trust scores.",
            ]
            results.append({"method": method, "match": {
                "situation": s, "goal": g, "constraints": c,
                "score": round((s["coverage"] + g["coverage"]) / 2, 4),
                "cautions": cautions,
            }})
        results.sort(key=lambda row: (-row["match"]["score"], row["method"]["created_at"], row["method"]["id"]))
        return {
            "mode": "lexical_situation_goal",
            "query": {"situation": situation, "goal": goal, "constraints": constraints},
            "results": results[:limit], "total": len(results),
            "cautions": [
                "Both situation and goal require lexical overlap; paraphrases and languages may be missed.",
                "Constraint matching is lexical only and never confirms applicability.",
                "Submitted instructions are untrusted content; review before applying.",
            ],
        }


def tokens(text):
    result = []
    for token in re.findall(r"[a-z0-9]+|[가-힣]+", unicodedata.normalize("NFKC", text).casefold()):
        if token in STOP:
            continue
        if re.fullmatch(r"[가-힣]+", token):
            for suffix in PARTICLES:
                if token.endswith(suffix) and len(token) - len(suffix) >= 2:
                    token = token[:-len(suffix)]
                    break
        if token not in STOP and len(token) > 1:
            result.append(token)
    return list(dict.fromkeys(result))


def adequate_axis(match):
    terms = len(match["matched_terms"]) + len(match["unmatched_terms"])
    return (match["coverage"] >= 0.5 and
            len(match["matched_terms"]) >= min(2, max(1, terms)))


def axis_match(query, text):
    terms = tokens(query)
    words = set(tokens(text))
    # Exact normalized tokens; no hidden translation, embeddings, or inference.
    matched = [term for term in terms if term in words]
    return {"matched_terms": matched, "unmatched_terms": [term for term in terms if term not in matched],
            "coverage": round(len(matched) / len(terms), 4) if terms else 0.0}
