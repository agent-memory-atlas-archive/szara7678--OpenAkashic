from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.research import get_store
from app.research_store import ResearchStore
from app.research_method_store import MethodStore
from app.research_methods import router
from app.research_method_graph import method_graph


def archive(tmp_path, monkeypatch):
    source = ResearchStore(tmp_path / "public.sqlite3")
    store = MethodStore(source)
    payload = dict(title="Small public experiment", situation="Uncertain demand", goal="Test an assumption",
                   constraints=[], steps=["Declare the metric before testing"], success_criteria=["Record observations"],
                   limitations=["Synthetic fixture"], tags=["제품·사업"], public_source_only=True, agent_name="fixture",
                   evidence_kind="documented_method", sources=[dict(url="https://example.org/method", title="Method source",
                   accessed_at="2026-10-28T00:00:00Z")])
    method = store.create_method(payload, "graph-fixture")
    outcome = store.add_outcome(method["id"], dict(method_version=1, status="unknown", situation="Public fixture",
        goal="Test", actions=["Prepared plan"], observed_result="No real execution", evidence=[],
        agent_name="fixture", public_source_only=True), "graph-outcome")
    store.add_opinion(method["id"], dict(method_version=1, kind="limitation", body="Unmeasured outcome",
        outcome_id=outcome["id"], agent_name="fixture", public_source_only=True), "graph-opinion")
    monkeypatch.setattr("app.research_methods.method_store", lambda: store)
    app = FastAPI(); app.include_router(router)
    return TestClient(app), store, method


def test_catalog_is_bounded_filterable_and_read_only(tmp_path, monkeypatch):
    client, store, method = archive(tmp_path, monkeypatch)
    before = open(store.db_path, "rb").read()
    result = client.get("/research/api/methods/catalog?domain=제품·사업&limit=1").json()
    assert result["items"][0]["id"] == method["id"]
    assert result["counts"] == dict(methods=1, documented_methods=1, outcomes=1, opinions=1)
    assert result["items"][0]["feedback_counts"] == dict(outcomes=1, opinions=1)
    assert client.get("/research/api/methods/catalog?domain=unknown").json()["items"] == []
    assert client.get("/research/api/methods/catalog?offset=1").json()["has_more"] is False
    for query in ("limit=25", "offset=-1", "offset=10001", "domain=closed://private"):
        assert client.get("/research/api/methods/catalog?" + query).status_code == 422
    assert open(store.db_path, "rb").read() == before


def test_graph_ids_edges_and_exact_version_links_are_stable(tmp_path, monkeypatch):
    client, store, method = archive(tmp_path, monkeypatch)
    path = "/research/api/methods/" + method["id"] + "/graph"
    one = client.get(path).json(); two = client.get(path).json()
    assert one == two
    assert one["graph_kind"] == "record_relationships"
    nodes = {n["id"]: n for n in one["nodes"]}
    assert len(nodes) == 6
    assert all(e["source"] in nodes and e["target"] in nodes for e in one["edges"])
    assert len({e["id"] for e in one["edges"]}) == len(one["edges"])
    assert {e["relation"] for e in one["edges"]} == {"applies_in", "pursues", "documented_by", "reported_application", "has_opinion", "comments_on"}
    assert all(n["method_version"] == 1 for n in nodes.values() if n["kind"] in ("outcome", "opinion"))
    assert client.get("/research/api/methods/missing/graph").status_code == 404


def test_graph_truncation_does_not_claim_all_feedback_is_present(tmp_path, monkeypatch):
    _, store, method = archive(tmp_path, monkeypatch)
    detail = store.get(method["id"])
    detail["feedback_counts"]["opinions"]["total"] = 1000
    detail["opinions"] = [dict(detail["opinions"][0], id="opinion_" + str(n)) for n in range(20)]
    graph = method_graph(detail)
    assert graph["truncated"]["opinions"] is True
    assert len([n for n in graph["nodes"] if n["kind"] == "opinion"]) == 12


def test_evaluation_reads_only_the_operator_reviewed_filename(tmp_path, monkeypatch):
    client, _, _ = archive(tmp_path, monkeypatch)
    assert client.get("/research/api/methods/evaluation/report").status_code == 404
    (tmp_path / "other-private-file.json").write_text('{"not_public":true}')
    (tmp_path / "method-kpi.json").write_text('{"schema":"reviewed-public-fixture"}')
    assert client.get("/research/api/methods/evaluation/report").json() == {"schema": "reviewed-public-fixture"}
    assert client.get("/research/api/methods/evaluation/report?path=other-private-file.json").json() == {"schema": "reviewed-public-fixture"}


def test_network_merges_only_exact_sources_and_stays_bounded(tmp_path, monkeypatch):
    client, store, method = archive(tmp_path, monkeypatch)
    payload = {k:v for k,v in method.items() if k in {"title","situation","goal","constraints","steps","success_criteria","limitations","tags","public_source_only","agent_name","evidence_kind","sources"}}
    payload["title"] = "Second public method"
    second = store.create_method(payload, "second-method")
    before = open(store.db_path,"rb").read()
    one = client.get("/research/api/methods/network?limit=80").json()
    assert one == client.get("/research/api/methods/network?limit=80").json()
    ids = {n["id"] for n in one["nodes"]}
    assert len([n for n in one["nodes"] if n["kind"] == "source"]) == 1
    assert len([e for e in one["edges"] if e["relation"] == "documented_by"]) == 2
    assert all(e["source"] in ids and e["target"] in ids for e in one["edges"])
    assert one["scope"]["methods_shown"] == 2 and not one["scope"]["truncated"]
    source = next(n for n in one["nodes"] if n["kind"] == "source")
    focused = client.get("/research/api/methods/network", params={"focus":source["id"],"depth":1}).json()
    assert {n.get("method_id") for n in focused["nodes"] if n["kind"] == "method"} == {method["id"],second["id"]}
    assert len(focused["edges"]) == 2 and not focused["scope"]["focus_missing"]
    assert client.get("/research/api/methods/network?focus=missing").json()["scope"]["focus_missing"]
    assert client.get("/research/api/methods/network?depth=3").status_code == 422
    short = client.get("/research/api/methods/network?limit=1").json()
    assert short["scope"]["truncated"] and short["scope"]["methods_shown"] == 1
    assert client.get("/research/api/methods/network?domain=unknown").json()["nodes"] == []
    for query in ("limit=101","limit=0","domain=closed://private"):
        assert client.get("/research/api/methods/network?"+query).status_code == 422
    assert open(store.db_path,"rb").read() == before
