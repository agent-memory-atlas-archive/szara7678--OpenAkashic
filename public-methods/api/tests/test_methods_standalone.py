from fastapi.testclient import TestClient
from app.methods_main import app


def test_portable_reader_serves_graph_assets_and_no_legacy_ingestion():
    client = TestClient(app)
    for path in ("/research/", "/research/methods-graph.js", "/research/methods.css", "/research/methods-kpi.html", "/research/methods-kpi.js"):
        r = client.get(path)
        assert r.status_code == 200
        assert "no-transform" in r.headers["cache-control"]
        assert "unsafe-inline" not in r.headers["content-security-policy"]
    assert client.post("/research/api/investigations", json={}).status_code == 404
    assert client.get("/research/.env").status_code in (404, 422)
