import hashlib
import re
import unicodedata

_TOKEN_RE = re.compile(r"[a-z0-9]+|[가-힣]+")
_SUFFIXES = (
    "에서는", "으로는", "에게", "에서", "으로", "은", "는", "이", "가",
    "을", "를", "와", "과", "도", "의", "로",
)


def _tokens(text):
    normalized = unicodedata.normalize("NFKC", text).casefold()
    result = []
    for token in _TOKEN_RE.findall(normalized):
        if token and all("가" <= char <= "힣" for char in token):
            for suffix in sorted(_SUFFIXES, key=len, reverse=True):
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
    for key, values in payload.get("aliases", {}).items():
        key_tokens = _tokens(key)
        value_tokens = set()
        for value in values:
            value_tokens.update(_tokens(value))
        for token in key_tokens:
            alternatives.setdefault(token, set()).update(value_tokens)

    best_doc = None
    best_score = 0
    best_id = None
    for doc in payload["docs"]:
        body = doc["body"]
        document_tokens = set(_tokens(body))
        matched = {
            token for token in query_tokens
            if token in document_tokens or alternatives.get(token, set()) & document_tokens
        }
        score = len(matched)
        doc_id = doc["id"]
        if score > best_score or (score == best_score and score > 0 and doc_id < best_id):
            best_doc = doc
            best_score = score
            best_id = doc_id

    if best_doc is None:
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