import hashlib
import re
import unicodedata


_TOKEN_RE = re.compile(r"[a-z0-9]+|[가-힣]+")
_SUFFIXES = (
    "에서는", "으로는", "에게", "에서", "으로", "은", "는",
    "이", "가", "을", "를", "와", "과", "도", "의", "로",
)


def _tokens(text):
    normalized = unicodedata.normalize("NFKC", text).casefold()
    result = []
    for token in _TOKEN_RE.findall(normalized):
        if token and all("가" <= char <= "힣" for char in token):
            for suffix in _SUFFIXES:
                if token.endswith(suffix):
                    stem = token[:-len(suffix)]
                    if len(stem) >= 2:
                        token = stem
                    break
        result.append(token)
    return result


def solve(payload):
    query_tokens = set(_tokens(payload["query"]))
    aliases = {}
    for key, values in payload.get("aliases", {}).items():
        processed_keys = _tokens(key)
        processed_values = set(_tokens(" ".join(values)))
        for token in processed_keys:
            aliases.setdefault(token, set()).update(processed_values)

    alternatives = {
        token: {token} | aliases.get(token, set())
        for token in query_tokens
    }
    best_id = None
    best_doc = None
    best_score = 0

    for doc in payload["docs"]:
        body_tokens = set(_tokens(doc["body"]))
        score = sum(
            1 for token in query_tokens
            if alternatives[token] & body_tokens
        )
        if score > best_score or (
            score == best_score and score > 0 and
            (best_id is None or doc["id"] < best_id)
        ):
            best_id = doc["id"]
            best_doc = doc
            best_score = score

    if best_doc is None:
        return []
    body = best_doc["body"]
    # The prefix is a contiguous original substring and is within the limit.
    quote = body[:256]
    if not quote:
        return []
    return [{
        "id": best_doc["id"],
        "quote": quote,
        "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }]