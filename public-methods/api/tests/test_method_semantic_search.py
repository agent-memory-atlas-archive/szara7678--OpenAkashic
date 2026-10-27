"""Deterministic semantic retrieval contracts; no model/network required."""
import json
import sqlite3

import pytest

from app.research_method_search import (
    SearchConfig, SearchUnavailable, build_index, search_methods, constraint_match,
)
from app.research_method_store import MethodStore
from app.research_store import ResearchStore, canonical


CONFIG = SearchConfig(model="fake-public", revision="immutable-revision", embedding_spec="unit-normalized-v1")


class FakeEmbeddings:
    def __init__(self):
        self.calls = []

    def embed(self, texts, input_type):
        self.calls.append((input_type, list(texts)))
        vectors = {
            "unstable builds": [1, 0, 0, 0], "compilations fail randomly": [1, 0, 0, 0],
            "repeatable release": [0, 1, 0, 0], "deterministic shipment": [0, 1, 0, 0],
            "sell more tickets": [0, 0, 1, 0], "make dinner": [0, 0, 0, 1],
            "stranded hikers": [0, 0, 0, 1],
        }
        return [vectors.get(t, [0, 0, 0, 1]) for t in texts]


@pytest.fixture
def archive(tmp_path):
    store = MethodStore(ResearchStore(tmp_path / "public.sqlite3"))
    base = {"title": "Reproducible build procedure", "situation": "unstable builds", "goal": "repeatable release",
            "constraints": ["manual review"], "steps": ["Pin tool versions"],
            "success_criteria": ["Compare outputs"], "limitations": ["Environment dependent"],
            "tags": [], "agent_name": "public-agent", "public_source_only": True,
            "evidence_kind": "documented_method", "sources": [{"url": "https://example.org/builds"}],
            "constraint_rules": {"requires": ["local-files"], "forbids": ["network-required"]}}
    method = store.create_method(base, "seed-1")
    other = store.create_method({**base, "title": "Ticket selling", "goal": "sell more tickets"}, "seed-2")
    return store, method, other


def setup_index(tmp_path, archive):
    store, method, other = archive
    embedder = FakeEmbeddings()
    index = tmp_path / "index.sqlite3"
    report = build_index(store, index, embedder, CONFIG)
    return store, method, other, embedder, index, report


def query(store, embedder, index, **kwargs):
    return search_methods(store, "compilations fail randomly", "deterministic shipment", embedder=embedder,
                          index_path=index, config=CONFIG, **kwargs)


def test_paraphrase_survives_no_lexical_overlap_and_other_goal_is_rejected(tmp_path, archive):
    store, method, other, embedder, index, report = setup_index(tmp_path, archive)
    result = query(store, embedder, index)
    assert [x["method"]["id"] for x in result["results"]] == [method["id"]]
    match = result["results"][0]["match"]
    assert match["situation"]["matched_terms"] == []
    assert match["goal"]["matched_terms"] == []
    assert match["ranks"]["lexical"] is None
    assert match["constraint_rules"]["status"] == "unknown"
    assert result["search"]["available"] is True
    assert other["id"] not in str(result["results"])


def test_hard_constraint_conflicts_exclude_and_explicit_capabilities_satisfy(tmp_path, archive):
    store, method, _, embedder, index, _ = setup_index(tmp_path, archive)
    assert query(store, embedder, index, forbids=["local-files"])["results"] == []
    assert query(store, embedder, index, requires=["network-required"])["results"] == []
    match = query(store, embedder, index, requires=["local-files"])["results"][0]["match"]
    assert match["constraint_rules"]["status"] == "satisfied"
    with pytest.raises(ValueError):
        query(store, embedder, index, requires=["local-files"], forbids=["local-files"])


def test_unrelated_and_changed_goal_abstain(tmp_path, archive):
    store, _, _, embedder, index, _ = setup_index(tmp_path, archive)
    result = search_methods(store, "stranded hikers", "make dinner", index_path=index, config=CONFIG, embedder=embedder)
    assert result["results"] == [] and result["search"]["available"] is True
    result = search_methods(store, "unstable builds", "make dinner", index_path=index, config=CONFIG, embedder=embedder)
    assert result["results"] == []


def test_incremental_reuses_all_fields_and_does_not_touch_source(tmp_path, archive):
    store, _, _, embedder, index, report = setup_index(tmp_path, archive)
    source_before = open(store.db_path, "rb").read()
    embedder.calls.clear()
    before_rebuild = index.read_bytes()
    again = build_index(store, index, embedder, CONFIG)
    assert report["embedded_fields"] == 4
    assert again["embedded_fields"] == 0 and again["reused_fields"] == 4
    assert embedder.calls == []
    assert index.read_bytes() == before_rebuild
    index_before = index.read_bytes()
    query(store, embedder, index)
    assert index.read_bytes() == index_before
    assert open(store.db_path, "rb").read() == source_before


@pytest.mark.parametrize("change", ["revision", "source_hash", "content_hash", "model", "version", "dimensions"])
def test_stale_or_mismatched_entry_excluded(tmp_path, archive, change):
    store, method, _, embedder, index, _ = setup_index(tmp_path, archive)
    value = 999 if change in {"version", "dimensions"} else "stale"
    with sqlite3.connect(index) as db:
        db.execute("UPDATE embeddings SET " + change + "=? WHERE method_id=?", (value, method["id"]))
    result = query(store, embedder, index)
    assert result["results"] == []
    assert result["search"]["stale_or_missing_methods"] == 1


def test_current_full_body_hash_includes_sources_and_rules(tmp_path, archive):
    store, method, _, embedder, index, _ = setup_index(tmp_path, archive)
    changed = {**method, "sources": [{"url": "https://example.org/new-source"}]}
    with store.archive._connect() as db:
        db.execute("UPDATE method_methods SET body=? WHERE id=?", (canonical(changed), method["id"]))
    assert query(store, embedder, index)["results"] == []
    embedder.calls.clear()
    result = build_index(store, index, embedder, CONFIG)
    assert result["embedded_fields"] == 0 and result["reused_fields"] == 4
    assert query(store, embedder, index)["results"]


def test_index_model_revision_pin_mismatch_and_missing_index_abstain(tmp_path, archive):
    store, _, _, embedder, index, _ = setup_index(tmp_path, archive)
    config = SearchConfig(model=CONFIG.model, revision="changed", embedding_spec=CONFIG.embedding_spec)
    result = search_methods(store, "unstable builds", "repeatable release", index_path=index, config=config, embedder=embedder)
    assert result["results"] == [] and result["search"]["available"] is False
    assert "mismatch" in result["search"]["reason"]
    assert query(store, embedder, tmp_path / "absent.sqlite3")["results"] == []


def test_exact_version_feedback_bounded_and_never_embedded(tmp_path, archive):
    store, method, _, embedder, index, _ = setup_index(tmp_path, archive)
    payload = {"public_source_only": True, "agent_name": "agent", "method_version": 1,
               "status": "success", "situation": "unstable builds", "goal": "repeatable release",
               "actions": ["pinned"], "observed_result": "reported " * 100, "evidence": []}
    report = store.add_outcome(method["id"], payload, "feedback-1")
    with store.archive._connect() as db:
        bad = {**report, "id": "wrong-version", "method_version": 2}
        db.execute("INSERT INTO method_outcomes VALUES(?,?,?,?,?)", (bad["id"], method["id"], 2, bad["created_at"], canonical(bad)))
    result = query(store, embedder, index)
    feedback = result["results"][0]["match"]["feedback"]
    assert len(feedback) == 1 and len(feedback[0]["excerpt"]) == 280
    assert feedback[0]["verification"] == "not_independently_verified"
    assert feedback[0]["truncated"] is True
    embedder.calls.clear()
    assert build_index(store, index, embedder, CONFIG)["embedded_fields"] == 0
    assert embedder.calls == []


def test_atomic_rebuild_failure_retains_old_index(tmp_path, archive):
    store, _, _, embedder, index, _ = setup_index(tmp_path, archive)
    prior = index.read_bytes()
    class Broken:
        def embed(self, texts, input_type):
            raise SearchUnavailable("service down")
    changed = SearchConfig(model=CONFIG.model, revision="next", embedding_spec=CONFIG.embedding_spec)
    with pytest.raises(SearchUnavailable):
        build_index(store, index, Broken(), changed)
    assert index.read_bytes() == prior


def test_lexical_default_shape_remains_unchanged(tmp_path, archive):
    store, _, _ = archive
    expected = store.search("unstable builds", "repeatable release")
    assert search_methods(store, "unstable builds", "repeatable release", mode="lexical") == expected



def test_http_service_protocol_pins_and_network_guard(monkeypatch):
    import io
    from app.research_method_search import HTTPEmbedder
    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "http://127.0.0.1:18083/embed"
            assert json.loads(request.data) == {"texts": ["public query"], "input_type": "query"}
            return io.BytesIO(json.dumps({"model": CONFIG.model, "revision": CONFIG.revision,
                "embedding_spec": CONFIG.embedding_spec, "dimensions": 2, "normalized": True,
                "embeddings": [[3, 4]]}).encode())
    client = HTTPEmbedder(CONFIG, "http://127.0.0.1:18083/embed")
    client.opener = Opener()
    assert client.embed(["public query"], "query") == [[0.6, 0.8]]
    for endpoint in ("https://example.org/embed", "http://192.168.1.1/embed", "http://127.0.0.1:18083/embed?url=private"):
        with pytest.raises(SearchUnavailable):
            HTTPEmbedder(CONFIG, endpoint)
    monkeypatch.setenv("OPENAKASHIC_EMBEDDING_BRIDGE_HOST", "172.20.0.1")
    assert HTTPEmbedder(CONFIG, "http://172.20.0.1:18083/embed")
    monkeypatch.setenv("OPENAKASHIC_EMBEDDING_BRIDGE_HOST", "169.254.169.254")
    with pytest.raises(SearchUnavailable):
        HTTPEmbedder(CONFIG, "http://169.254.169.254/embed")


@pytest.mark.parametrize("errors, succeeds, expected_calls", [
    ([429, 429], True, 3), ([429] * 5, False, 5), ([503], False, 1),
])
def test_embedding_contention_recovers_but_retries_are_bounded(monkeypatch, errors, succeeds, expected_calls):
    import io
    from urllib.error import HTTPError
    from app import research_method_search as module

    client = module.HTTPEmbedder(CONFIG, "http://127.0.0.1:18083/embed")
    seen = []
    clock = [0.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(module.time, "sleep", lambda delay: clock.__setitem__(0, clock[0] + delay))
    body = {**CONFIG.provenance(), "normalized": True, "dimensions": 2, "embeddings": [[1, 0]]}
    def open_request(request, timeout):
        seen.append((request.data, timeout))
        if len(seen) <= len(errors):
            raise HTTPError(request.full_url, errors[len(seen) - 1], "controlled test", {}, None)
        return io.BytesIO(json.dumps(body).encode())
    monkeypatch.setattr(client.opener, "open", open_request)
    if succeeds:
        assert client.embed(["unchanged query"], "query") == [[1.0, 0.0]]
    else:
        with pytest.raises(SearchUnavailable):
            client.embed(["unchanged query"], "query")
    assert len(seen) == expected_calls
    assert len({entry[0] for entry in seen}) == 1
    assert all(0 < timeout <= client.timeout for _, timeout in seen)
    assert clock[0] < client.timeout


def test_changed_axis_reembeds_only_changed_field(tmp_path, archive):
    store, method, _, embedder, index, _ = setup_index(tmp_path, archive)
    changed = {**method, "situation": "compilations fail randomly"}
    with store.archive._connect() as db:
        db.execute("UPDATE method_methods SET body=? WHERE id=?", (canonical(changed), method["id"]))
    embedder.calls.clear()
    report = build_index(store, index, embedder, CONFIG)
    assert report["embedded_fields"] == 1 and report["reused_fields"] == 3
    assert embedder.calls == [("document", ["compilations fail randomly"])]
    assert query(store, embedder, index)["results"]


def test_private_locator_rejected_before_index_creation(tmp_path, archive):
    store, method, _ = archive
    with store.archive._connect() as db:
        changed = {**method, "situation": "/home/private/personal_vault/raw_notes"}
        db.execute("UPDATE method_methods SET body=? WHERE id=?", (canonical(changed), method["id"]))
    index = tmp_path / "not-created.sqlite3"
    embedder = FakeEmbeddings()
    with pytest.raises(ValueError):
        build_index(store, index, embedder, CONFIG)
    assert not index.exists() and not embedder.calls


def test_source_change_during_embedding_rolls_back(tmp_path, archive):
    store, method, _, embedder, index, _ = setup_index(tmp_path, archive)
    before = index.read_bytes()
    class Mutating(FakeEmbeddings):
        def embed(self, texts, input_type):
            with store.archive._connect() as db:
                changed = {**method, "title": "Concurrent source edit"}
                db.execute("UPDATE method_methods SET body=? WHERE id=?", (canonical(changed), method["id"]))
            return super().embed(texts, input_type)
    config = SearchConfig(model=CONFIG.model, revision="fresh", embedding_spec=CONFIG.embedding_spec)
    with pytest.raises(SearchUnavailable, match="source changed"):
        build_index(store, index, Mutating(), config)
    assert index.read_bytes() == before


def test_weak_goal_abstains_even_when_mean_similarity_is_high(tmp_path, archive):
    store, _, _, embedder, index, _ = setup_index(tmp_path, archive)
    class WeakGoal(FakeEmbeddings):
        def embed(self, texts, input_type):
            return [[1, 0, 0, 0], [0, 0.61, 0, (1-0.61**2)**0.5]]
    result = query(store, WeakGoal(), index)
    assert result["results"] == []
    assert result["search"]["relevance_status"] == "unknown"
    assert result["search"]["weak_axis_methods"] == 2

def test_undeclared_query_tags_remain_unknown():
    for rules in ({}, {"requires": [], "forbids": []}):
        result = constraint_match({"constraint_rules": rules}, forbids=["network-required"])
        assert result["status"] == "unknown" and result["unknown"] == ["network-required"]
        assert result["basis"] == "declared_tags_not_environment_verification"
    result = constraint_match({"constraint_rules": {"requires": [], "forbids": ["network-required"]}}, forbids=["network-required"])
    assert result["status"] == "satisfied" and result["interpretation"] == "compatible_declared"
