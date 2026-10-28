import hashlib, re, unicodedata

_TOKEN_RE = re.compile(r"[a-z0-9]+|[\uac00-\ud7a3]+")
_SUFFIXES = tuple(sorted(("\uc5d0\uc11c\ub294","\uc73c\ub85c\ub294","\uc5d0\uac8c","\uc5d0\uc11c","\uc73c\ub85c","\uc740","\ub294","\uc774","\uac00","\uc744","\ub97c","\uc640","\uacfc","\ub3c4","\uc758","\ub85c"), key=len, reverse=True))

def _tokens(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    out = []
    for token in _TOKEN_RE.findall(text):
        if token[0] >= "\uac00" and token[0] <= "\ud7a3" and all("\uac00" <= c <= "\ud7a3" for c in token):
            for suffix in _SUFFIXES:
                if token.endswith(suffix):
                    stem = token[:-len(suffix)]
                    if len(stem) >= 2: token = stem
                    break
        out.append(token)
    return out

def solve(payload):
    qtokens = set(_tokens(payload["query"]))
    if not qtokens: return []
    aliases = {}
    for key, values in payload.get("aliases", {}).items():
        alts = set(t for value in values for t in _tokens(value))
        for token in _tokens(key): aliases.setdefault(token,set()).update(alts)
    best, best_score, best_id = None, 0, None
    for doc in payload["docs"]:
        body_tokens = set(_tokens(doc["body"]))
        score = sum(bool(({t} | aliases.get(t,set())) & body_tokens) for t in qtokens)
        if score > best_score or (score == best_score and score > 0 and doc["id"] < best_id):
            best, best_score, best_id = doc, score, doc["id"]
    if best is None: return []
    body = best["body"]
    return [{"id":best["id"],"quote":body[:256],"sha256":hashlib.sha256(body.encode("utf-8")).hexdigest()}]
