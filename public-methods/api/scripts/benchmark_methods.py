"""Reproducible retrieval/record-contract checks, not an answer-quality eval."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import time
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler

from app.research_method_context import pack_context, counted


def run(endpoint, queries, mapping):
    opener = build_opener(ProxyHandler({}))
    origin = endpoint.rstrip("/")
    def get(path):
        started = time.perf_counter()
        with opener.open(Request(origin + "/research/api/methods" + path,
                headers={"Accept": "application/json", "User-Agent": "OpenAkashic-Method-Benchmark/0.1"}), timeout=40) as r:
            body = json.load(r)
        return body, time.perf_counter() - started

    records = []
    for case in queries["cases"]:
        for mode in ("lexical", "hybrid"):
            body, elapsed = get("/search?" + urlencode({"situation": case["situation"], "goal": case["goal"], "mode": mode, "limit": 5,
                "requires": ",".join(case.get("requires", [])), "forbids": ",".join(case.get("forbids", []))}))
            ids = [x["method"]["id"] for x in body["results"]]
            wanted = [mapping[k] for k in case["expected_keys"]]
            record = {"case": case.get("key", case.get("id")), "type": case.get("type", "answerable" if wanted else "no_material"),
                      "mode": mode, "expected_ids": wanted, "ids": ids,
                      "excluded_absent": all(mapping[k] not in ids for k in case.get("excluded_keys", [])),
                      "available": body.get("search", {}).get("available", True), "elapsed_seconds": round(elapsed, 4),
                      "top1": bool(wanted and ids and ids[0] in wanted),
                      "top5": bool(wanted and any(i in wanted for i in ids)), "abstained": not ids,
                      "raw": body}
            if mode == "hybrid" and wanted and ids:
                contexts = [pack_context(body, cap) for cap in (256, 1024, 2048)]
                selected = next((x["method"] for x in body["results"] if x["method"]["id"] in wanted), None)
                fetched, _ = get("/" + selected["id"]) if selected else (None, 0)
                chosen_context = contexts[1]
                record["context"] = {"budgets": [{"cap": c["max_tokens"], "actual_tokens": counted(c),
                    "counter_matches": c["tokens"] == counted(c), "within_cap": counted(c) <= c["max_tokens"],
                    "expected_reference_retained": any(i["id"] in wanted for i in c["items"])} for c in contexts],
                    "full_top5_method_tokens": counted([x["method"] for x in body["results"]]),
                    "compact_1024_tokens": counted(chosen_context),
                    "compact_plus_exact_fetch_tokens": counted(chosen_context) + counted(fetched) if fetched else None,
                    "selected_fetch_id": fetched["id"] if fetched else None,
                    "limits": "o200k JSON material counts, not billed usage. Expected method ID selects the exact fetch (oracle assumption), not an independent agent. Reference retention is not answer sufficiency."}
            records.append(record)
            print(record["case"], mode, flush=True)
    catalog, _ = get("/catalog?limit=24")
    items = list(catalog["items"])
    offset = len(items)
    while catalog["has_more"]:
        catalog, _ = get("/catalog?limit=24&offset=" + str(offset))
        items.extend(catalog["items"]); offset += len(catalog["items"])
    audits = []
    for item in items:
        method, _ = get("/" + item["id"])
        graph, elapsed = get("/" + item["id"] + "/graph")
        again, _ = get("/" + item["id"] + "/graph")
        nodes = {n["id"]: n for n in graph["nodes"]}
        source_urls = {n["url"] for n in graph["nodes"] if n["kind"] == "source"}
        audits.append({"id": item["id"], "version": item["version"], "stable_graph": graph == again,
            "no_dangling_edges": all(e["source"] in nodes and e["target"] in nodes for e in graph["edges"]),
            "source_links_match_record": source_urls == {s["url"] for s in method.get("sources", [])[:8]},
            "exact_feedback_versions": all(n["method_version"] == method["version"] for n in graph["nodes"] if n["kind"] in ("outcome", "opinion")),
            "source_nodes_checked": sum(n["kind"] == "source" for n in graph["nodes"]),
            "feedback_nodes_checked": sum(n["kind"] in ("outcome", "opinion") for n in graph["nodes"]),
            "graph_seconds": round(elapsed, 4), "node_count": len(nodes), "edge_count": len(graph["edges"]),
            "graph_kind": graph["graph_kind"]})
    summary = {}
    for mode in ("lexical", "hybrid"):
        rows = [r for r in records if r["mode"] == mode]
        positive = [r for r in rows if r["expected_ids"]]; negative = [r for r in rows if r["type"] == "no_material"]
        conflict = [r for r in rows if r["type"] == "constraint_conflict"]
        times = sorted(r["elapsed_seconds"] for r in rows)
        summary[mode] = {"positive_n": len(positive), "top1": sum(r["top1"] for r in positive), "top5": sum(r["top5"] for r in positive),
            "negative_n": len(negative), "valid_abstentions": sum(r["available"] and r["abstained"] for r in negative),
            "conflict_n": len(conflict), "excluded_absent": sum(r["excluded_absent"] for r in conflict),
            "service_errors": sum(not r["available"] for r in rows), "median_seconds": statistics.median(times),
            "p95_seconds": times[max(0, int(len(times) * .95 + .999999) - 1)],
            "failed_cases": [r["case"] for r in positive if not r["top5"]]}
    contexts = [r["context"] for r in records if "context" in r]
    summary["context"] = {"cases": len(contexts), "budget_checks": sum(len(c["budgets"]) for c in contexts),
        "all_within_cap": all(b["within_cap"] and b["counter_matches"] for c in contexts for b in c["budgets"]),
        "reference_retained_checks": sum(b["expected_reference_retained"] for c in contexts for b in c["budgets"]),
        "full_top5_tokens": sum(c["full_top5_method_tokens"] for c in contexts),
        "compact_reference_tokens": sum(c["compact_1024_tokens"] for c in contexts),
        "compact_plus_fetch_tokens": sum(c["compact_plus_exact_fetch_tokens"] or 0 for c in contexts),
        "same_answer_quality": "unmeasured", "actual_billed_usage": None}
    summary["graph"] = {"methods": len(audits), **{field: sum(a[field] for a in audits) for field in ("stable_graph", "no_dangling_edges")},
        "source_methods": sum(a["source_nodes_checked"] > 0 for a in audits),
        "source_links_match_record": sum(a["source_links_match_record"] for a in audits if a["source_nodes_checked"]),
        "feedback_methods": sum(a["feedback_nodes_checked"] > 0 for a in audits),
        "exact_feedback_versions": sum(a["exact_feedback_versions"] for a in audits if a["feedback_nodes_checked"])}
    return {"schema": "method-kpi-v1", "measured_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_kind": "author_created_development_regression_not_independent_holdout",
        "summary": summary, "records": records, "graph_audits": audits,
        "unmeasured": ["human_preference", "revision_time", "causal_answer_quality_gain", "business_value", "independent_OSS_reproduction"],
        "limits": "Retrieval of expected methods and record integrity are measured. Source truth, expert identity, execution success, and answer quality are not inferred."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--queries", required=True)
    parser.add_argument("--mapping", required=True, help="JSON receipts with key and id")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error("refusing to overwrite observed results")
    queries = json.loads(Path(args.queries).read_text())
    mapping = {r["key"]: r["id"] for r in json.loads(Path(args.mapping).read_text())["receipts"]}
    report = run(args.endpoint, queries, mapping)
    report["input_hashes"] = {k: hashlib.sha256(Path(p).read_bytes()).hexdigest() for k,p in (("queries",args.queries),("mapping",args.mapping))}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
