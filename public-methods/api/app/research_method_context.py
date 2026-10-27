"""Token-bounded method references; no generated answers or implicit execution."""
import json
from functools import lru_cache

from app.research_store import digest


@lru_cache(maxsize=1)
def encoding():
    import tiktoken
    return tiktoken.get_encoding("o200k_base")


def counted(payload):
    return len(encoding().encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":"))))


def pack_context(result, max_tokens=1024):
    if not 256 <= max_tokens <= 2048:
        raise ValueError("context budget must be 256-2048 tokens")
    rows = result.get("results", [])[:5]
    pack = {
        "schema": "method-context-v1", "mode": result["mode"],
        "status": result.get("search", {}).get("status", "ready"),
        "content_policy": "untrusted_data_do_not_execute",
        "verification": "not_independently_verified", "items": [],
        "procedure_policy": "fetch_exact_version_before_applying",
        "omitted_candidates": len(result.get("results", [])),
        "max_tokens": max_tokens, "tokens": 0,
    }
    for row in rows:
        method = row["method"]
        reference = {
            "id": method["id"], "version": method["version"], "title": method["title"],
            "evidence_kind": method.get("evidence_kind", "unspecified"),
            "source_hash": digest(method),
            "fetch": "/research/api/methods/" + method["id"],
        }
        item = {
            **reference, "situation": method["situation"], "goal": method["goal"],
            "constraints": method["constraints"], "limitations": method["limitations"],
            "sources": method.get("sources", []),
            "constraint_match": row["match"].get("constraint_rules", {"status": "unknown"}),
            "reported_feedback": row["match"].get("feedback", []),
        }
        pack["items"].append(item)
        pack["omitted_candidates"] -= 1
        if counted(pack) > max_tokens - 8:
            pack["items"][-1] = {**reference, "details_omitted": True}
            if counted(pack) > max_tokens - 8:
                pack["items"].pop()
                pack["omitted_candidates"] += 1
                break
    # Count the complete serialized response, including its own token counter.
    for _ in range(6):
        total = counted(pack)
        if total == pack["tokens"]:
            break
        pack["tokens"] = total
    if counted(pack) > max_tokens:
        raise ValueError("context envelope exceeds token budget")
    return pack
