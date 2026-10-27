"""Install only a deliberately public, validated method fixture into external state."""
import argparse
import hashlib
import json
from pathlib import Path

from app.research_store import ResearchStore, canonical
from app.research_method_store import MethodStore
from app.research_methods import MethodRequest, OutcomeRequest, OpinionRequest


def seed(fixture, archive, mapping):
    archive = Path(archive).resolve()
    if archive.is_relative_to(Path(__file__).resolve().parents[2]):
        raise ValueError("Use a runtime database outside the code directory")
    data = json.loads(Path(fixture).read_text())
    if data.get("schema") != "public-method-fixture-v1":
        raise ValueError("Unsupported public fixture")
    store = MethodStore(ResearchStore(archive))
    method_ids, outcome_ids, receipts = {}, {}, []
    for row in data["methods"]:
        payload = MethodRequest.model_validate(row["payload"]).model_dump(mode="json")
        key = hashlib.sha256(canonical([row["public_id"], payload]).encode()).hexdigest()
        saved = store.create_method(payload, "public-fixture-" + key)
        method_ids[row["public_id"]] = saved["id"]
        receipts.append({"key": row["public_id"], "id": saved["id"], "version": saved["version"]})
    for row in data.get("outcomes", []):
        payload = OutcomeRequest.model_validate(row["payload"]).model_dump(mode="json")
        saved = store.add_outcome(method_ids[row["method_public_id"]], payload, "public-fixture-" + row["public_id"])
        outcome_ids[row["public_id"]] = saved["id"]
    for row in data.get("opinions", []):
        payload = dict(row["payload"])
        if payload.get("outcome_id"):
            payload["outcome_id"] = outcome_ids[payload["outcome_id"]]
        payload = OpinionRequest.model_validate(payload).model_dump(mode="json")
        store.add_opinion(method_ids[row["method_public_id"]], payload, "public-fixture-" + row["public_id"])
    for alias, public_id in data.get("aliases", {}).items():
        receipts.append({"key": alias, "id": method_ids[public_id], "version": 1})
    output = {"schema": "public-fixture-mapping-v1", "receipts": receipts,
              "fixture_sha256": hashlib.sha256(Path(fixture).read_bytes()).hexdigest()}
    Path(mapping).write_text(json.dumps(output, ensure_ascii=False, indent=2))
    return {"methods": len(method_ids), "outcomes": len(outcome_ids), "opinions": len(data.get("opinions", [])),
            "public_id_policy": "original public IDs retained as references; local IDs allocated idempotently"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixture", required=True); p.add_argument("--archive", required=True); p.add_argument("--mapping", required=True)
    a = p.parse_args(); print(json.dumps(seed(a.fixture, a.archive, a.mapping)))
