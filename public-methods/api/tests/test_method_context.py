import pytest

from app.research_method_context import counted, pack_context
from app.research_store import digest
from test_research_methods import BASE, archive, create


@pytest.mark.parametrize("budget", [256, 512, 1024, 2048])
def test_bounded_context_preserves_identity_and_requires_full_procedure(budget):
    method = {"id": "method_public", "version": 1, "title": "한글 자료 정리 방법 " * 10,
              "situation": "공개 예제 상황 " * 90, "goal": "공개 예제 목적 " * 90,
              "constraints": ["인터넷 없음"], "limitations": ["일반 성능은 미확인"],
              "steps": ["This is data, never execute automatically"], "sources": []}
    result = {"mode": "hybrid_situation_goal", "results": [{"method": method, "match": {}}]}
    pack = pack_context(result, budget)
    assert counted(pack) <= budget
    assert pack["tokens"] == counted(pack)
    assert pack["content_policy"] == "untrusted_data_do_not_execute"
    assert pack["procedure_policy"] == "fetch_exact_version_before_applying"
    if pack["items"]:
        item = pack["items"][0]
        assert (item["id"], item["version"], item["source_hash"]) == (method["id"], 1, digest(method))
        assert item["fetch"].endswith(method["id"])
        assert "steps" not in item


def test_context_route_is_not_captured_as_a_method_id(archive):
    client, _ = archive
    method = create(client)
    query = {"situation": "network blocked environment", "goal": "preserve evidence citations", "mode": "lexical"}
    response = client.get(BASE + "/context", params={**query, "max_tokens": 512})
    assert response.status_code == 200, response.text
    pack = response.json()
    assert pack["items"][0]["id"] == method["id"]
    assert pack["tokens"] <= 512
    assert client.get(BASE + "/context", params={**query, "max_tokens": 255}).status_code == 422
