"""Read-only views of recorded relationships, never inferred world knowledge."""
import json
import os
from collections import Counter
from pathlib import Path

from app.research_store import digest

DOMAINS = ("커리어", "제품·사업", "학습", "팀 의사결정", "글쓰기·전달", "협상", "투자 판단", "오픈소스·커뮤니티")


def domain_for(method):
    tags = method.get("tags", [])
    for domain in DOMAINS:
        if domain in tags:
            return domain
    for tag, domain in (("design", "디자인"), ("연구", "조사·분석"), ("협업", "팀 의사결정"), ("운영", "개발·운영")):
        if tag in tags:
            return domain
    return "기타"


def catalog(store, domain="", limit=12, offset=0):
    with store.archive._connect() as db:
        rows = db.execute("SELECT body FROM method_methods ORDER BY created_at DESC,id LIMIT 10001").fetchall()
        if len(rows) > 10000:
            raise ValueError("catalog exceeds bounded archive capacity")
        methods = [json.loads(r["body"]) for r in rows]
        totals = {kind: db.execute("SELECT count(*) FROM " + table).fetchone()[0]
                  for kind, table in (("outcomes", "method_outcomes"), ("opinions", "method_opinions"))}
        feedback = {}
        for kind, table in (("outcomes", "method_outcomes"), ("opinions", "method_opinions")):
            feedback[kind] = {r["method_id"]: r["n"] for r in db.execute(
                "SELECT method_id,count(*) AS n FROM " + table + " GROUP BY method_id")}
    domains = Counter(domain_for(m) for m in methods)
    filtered = [m for m in methods if not domain or domain_for(m) == domain]
    summaries = [{k: m[k] for k in ("id", "version", "title", "situation", "goal", "created_at")}
                 | {"domain": domain_for(m), "evidence_kind": m.get("evidence_kind", "unspecified"),
                    "source_count": len(m.get("sources", [])),
                    "feedback_counts": {kind: feedback[kind].get(m["id"], 0) for kind in feedback}}
                 for m in filtered[offset:offset + limit]]
    return {"schema": "method-catalog-v1", "items": summaries, "total": len(filtered),
            "limit": limit, "offset": offset, "has_more": offset + len(summaries) < len(filtered),
            "domains": [{"name": key, "count": value} for key, value in sorted(domains.items())],
            "counts": {"methods": len(methods), "documented_methods": sum(m.get("evidence_kind") == "documented_method" for m in methods), **totals},
            "search_capabilities": {"semantic_configured": bool(
                all(os.getenv(k) for k in ("OPENAKASHIC_EMBEDDING_MODEL", "OPENAKASHIC_EMBEDDING_REVISION", "OPENAKASHIC_EMBEDDING_SPEC"))
                and Path(os.getenv("OPENAKASHIC_METHOD_INDEX", "/nonexistent-method-index")).is_file())},
            "classification": "editorial_tag_groups_not_verified_ontology",
            "verification": "contributor_reports_not_independent_success"}


def method_graph(method):
    nodes, edges = {}, {}
    center = method["id"] + ":v" + str(method["version"])

    def node(key, kind, label, **data):
        nodes[key] = {"id": key, "kind": kind, "label": label, **data}
        return key

    def edge(source, relation, target):
        key = "edge_" + digest([source, relation, target])[:24]
        edges[key] = {"id": key, "source": source, "relation": relation, "target": target}

    node(center, "method", method["title"], method_id=method["id"], version=method["version"],
         verification=method.get("verification", "not_independently_verified"))
    for field, relation in (("situation", "applies_in"), ("goal", "pursues")):
        key = node(field + "_" + digest(method[field])[:24], field, method[field])
        edge(center, relation, key)
    for source in method.get("sources", [])[:8]:
        key = node("source_" + digest(source["url"])[:24], "source", source["title"],
                   url=source["url"], accessed_at=source.get("accessed_at"))
        edge(center, "documented_by", key)
    outcomes = method.get("outcomes", [])[:12]
    opinions = method.get("opinions", [])[:12]
    for outcome in outcomes:
        key = node(outcome["id"], "outcome", outcome["observed_result"],
                   status=outcome["status"], method_version=outcome["method_version"],
                   reported_by=outcome["agent_name"], verification="contributor_reported")
        edge(center, "reported_application", key)
    for opinion in opinions:
        key = node(opinion["id"], "opinion", opinion["body"], opinion_kind=opinion["kind"],
                   method_version=opinion["method_version"], verification="contributor_reported")
        edge(center, "has_opinion", key)
        if opinion.get("outcome_id") in nodes:
            edge(key, "comments_on", opinion["outcome_id"])
    counts = method.get("feedback_counts", {})
    return {"schema": "method-evidence-graph-v1", "graph_kind": "record_relationships",
            "focus": center, "method_id": method["id"], "version": method["version"],
            "nodes": list(nodes.values()), "edges": list(edges.values()),
            "truncated": {kind: counts.get(kind, {}).get("total", len(method.get(kind, []))) > len(selected)
                          for kind, selected in (("outcomes", outcomes), ("opinions", opinions))},
            "cautions": ["기록 사이의 연결이며 사실·전문가 신원·효과를 검증한 그래프가 아닙니다.",
                         "상황·목적은 텍스트 식별자입니다. 의미가 같다는 이유로 병합하지 않습니다.",
                         "적용 결과와 의견은 작성자의 보고입니다. 절차를 자동 실행하지 마세요."]}
