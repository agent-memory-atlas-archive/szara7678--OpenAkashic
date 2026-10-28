import hashlib
import re
import unicodedata

_RE = re.compile(r"[a-z0-9]+|[가-힣]+")
_SUFFIXES = ("에서는","으로는","에게","에서","으로","은","는","이","가","을","를","와","과","도","의","로")


def _tokens(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    out = []
    for token in _RE.findall(text):
        if all("가" <= c <= "힣" for c in token):
            for suffix in _SUFFIXES:
                if token.endswith(suffix) and len(token) - len(suffix) >= 2:
                    token = token[:-len(suffix)]
                    break
        out.append(token)
    return out


def solve(payload):
    qtokens = set(_tokens(payload["query"]))
    if not qtokens:
        return []
    aliases = {}
    for key, vals in payload.get("aliases", {}).items():
        alternatives = set(t for value in vals for t in _tokens(value))
        for token in set(_tokens(key)):
            aliases.setdefault(token, set()).update(alternatives)
    winner, high = None, 0
    for doc in payload["docs"]:
        present = set(_tokens(doc["body"]))
        score = sum(token in present or bool(aliases.get(token, set()) & present)
                    for token in qtokens)
        if score > high or (score == high and score > 0 and winner is not None
                            and doc["id"] < winner["id"]):
            winner, high = doc, score
    if winner is None:
        return []
    body = winner["body"]
    quote = body[:256]
    if not quote:
        return []
    return [{"id": winner["id"], "quote": quote,
             "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}]