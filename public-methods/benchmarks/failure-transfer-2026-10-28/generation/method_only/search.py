import hashlib, re, unicodedata

_TOKEN = re.compile(r"[a-z0-9]+|[\\uac00-\\ud7a3]+")
_SUFFIXES = ("\\uc5d0\\uc11c\\ub294", "\\uc73c\\ub85c\\ub294", "\\uc5d0\\uac8c", "\\uc5d0\\uc11c", "\\uc73c\\ub85c", "\\uc740", "\\ub294", "\\uc774", "\\uac00", "\\uc744", "\\ub97c", "\\uc640", "\\uacfc", "\\ub3c4", "\\uc758", "\\ub85c")

def _tokens(text):
    out = []
    for token in _TOKEN.findall(unicodedata.normalize("NFKC", text).casefold()):
        if all("\\uac00" <= ch <= "\\ud7a3" for ch in token):
            for suffix in _SUFFIXES:
                if token.endswith(suffix) and len(token)-len(suffix) >= 2:
                    token = token[:-len(suffix)]
                    break
        out.append(token)
    return out

def solve(payload):
    q = set(_tokens(payload["query"]))
    if not q: return []
    aliases = {}
    for key, vals in payload.get("aliases", {}).items():
        alts = set(t for v in vals for t in _tokens(v))
        for token in _tokens(key): aliases.setdefault(token, set()).update(alts)
    best, bestscore, bestid = None, 0, None
    for doc in payload["docs"]:
        terms = set(_tokens(doc["body"]))
        score = sum(1 for t in q if t in terms or bool(aliases.get(t, set()) & terms))
        did = doc["id"]
        if score > bestscore or (score and score == bestscore and did < bestid):
            best, bestscore, bestid = doc, score, did
    if best is None: return []
    body = best["body"]
    if not body: return []
    return [dict(id=best["id"], quote=body[:256], sha256=hashlib.sha256(body.encode("utf-8")).hexdigest())]
