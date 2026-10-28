import hashlib
import re
import unicodedata

_TOKEN_RE = re.compile(r"[a-z0-9]+|[\uac00-\ud7a3]+")
_SUFFIXES = ("???", "???", "??", "??", "??", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?", "?")
_HANGUL_RE = re.compile(r"^[\uac00-\ud7a3]+$")


def _tokens(text):
    normalized = unicodedata.normalize("NFKC", text).casefold()
    result = []
    for token in _TOKEN_RE.findall(normalized):
        if _HANGUL_RE.fullmatch(token):
            for suffix in _SUFFIXES:
                if token.endswith(suffix) and len(token) - len(suffix) >= 2:
                    token = token[:-len(suffix)]
                    break
        result.append(token)
    return result


def solve(payload):
    query_tokens = set(_tokens(payload["query"]))
    if not query_tokens:
        return []

    alternatives = {}
    for raw_key, raw_values in payload.get("aliases", {}).items():
        keys = _tokens(raw_key)
        values = set()
        for value in raw_values:
            values.update(_tokens(value))
        for key in keys:
            alternatives.setdefault(key, set()).update(values)

    best_doc = None
    best_score = 0
    best_id = None
    for doc in payload["docs"]:
        body = doc["body"]
        document_tokens = set(_tokens(body))
        score = sum(
            1
            for token in query_tokens
            if token in document_tokens
            or bool(alternatives.get(token, set()) & document_tokens)
        )
        doc_id = doc["id"]
        if score > best_score or (score > 0 and score == best_score and (best_id is None or doc_id < best_id)):
            best_doc = doc
            best_score = score
            best_id = doc_id

    if best_doc is None or best_score <= 0:
        return []
    body = best_doc["body"]
    quote = body[:256]
    if not quote:
        return []
    return [{
        "id": best_doc["id"],
        "quote": quote,
        "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }]
