from __future__ import annotations

from fastapi.testclient import TestClient

from sociomemory.dashboard.api import create_app


class FakeDashboardService:
    connected = 0
    closed = 0

    async def connect(self) -> None:
        type(self).connected += 1

    async def close(self) -> None:
        type(self).closed += 1

    async def list_children(self, limit: int = 100):
        return {"children": [f"child-{limit}"]}

    async def summary(self, child_id: str):
        return {"summary": {"child_id": child_id, "nodes": 1, "edges": 0}}

    async def graph_export(
        self,
        child_id: str,
        start_id: str | None = None,
        max_depth: int = 3,
        min_confidence: float = 0.0,
        limit: int = 200,
    ):
        return {
            "child_id": child_id,
            "nodes": [],
            "edges": [],
            "mode": "traverse" if start_id else "all",
            "max_depth": max_depth,
            "min_confidence": min_confidence,
            "limit": limit,
        }

    async def node_detail(self, child_id: str, node_id: str):
        return {"node": {"id": node_id, "child_id": child_id}}

    async def stale_nodes(self, child_id: str):
        return {"nodes": []}

    async def profile(self, child_id: str):
        return {"profile": {"child_id": child_id}}

    async def context(self, child_id: str):
        return {"context": {"child_id": child_id}}

    async def coaching(self, child_id: str):
        return {"implications": []}

    async def privacy_export(self, child_id: str):
        return {"export": {"child_id": child_id}}

    async def privacy_erase(self, child_id: str):
        return {"status": "erased", "child_id": child_id}

    async def ingest(self, child_id: str, text: str, source: str = "conversation"):
        if not text.strip():
            raise ValueError("text is required")
        return {"result": {"child_id": child_id, "text": text, "source": source}}

    async def ingest_person(
        self,
        child_id: str,
        name: str | None = None,
        area: str | None = None,
        school: str | None = None,
        places: list[str] | None = None,
        notes: str | None = None,
    ):
        return {
            "result": {
                "child_id": child_id,
                "name": name,
                "area": area,
                "school": school,
                "places": places,
                "notes": notes,
            }
        }

    async def segment_episodes(self, child_id: str):
        return {"result": {"child_id": child_id, "episodes": 1}}

    async def acquire_location(
        self,
        child_id: str,
        lat: float,
        lng: float,
        accuracy_m: float | None = None,
    ):
        return {"result": {"child_id": child_id, "lat": lat, "lng": lng, "accuracy_m": accuracy_m}}


def client() -> TestClient:
    FakeDashboardService.connected = 0
    FakeDashboardService.closed = 0
    return TestClient(create_app(service_factory=FakeDashboardService))


def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def test_health_is_public_without_dashboard_token(monkeypatch):
    monkeypatch.delenv("SOCIOMEMORY_DASHBOARD_TOKEN", raising=False)
    monkeypatch.delenv("SOCIOMEMORY_LLM_BACKEND", raising=False)
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    response = client().get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["llm_configured"] is False
    assert "LLM is not configured" in payload["warnings"][0]


def test_health_reports_openai_llm_when_configured(monkeypatch):
    monkeypatch.delenv("SOCIOMEMORY_DASHBOARD_TOKEN", raising=False)
    monkeypatch.setenv("SOCIOMEMORY_LLM_BACKEND", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    response = client().get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["llm_backend"] == "openai"
    assert payload["llm_configured"] is True
    assert payload["warnings"] == []


def test_protected_routes_require_configured_token(monkeypatch):
    monkeypatch.delenv("SOCIOMEMORY_DASHBOARD_TOKEN", raising=False)

    response = client().get("/api/children")

    assert response.status_code == 503
    assert response.json()["detail"] == "SOCIOMEMORY_DASHBOARD_TOKEN is not configured"


def test_protected_routes_reject_missing_or_invalid_token(monkeypatch):
    monkeypatch.setenv("SOCIOMEMORY_DASHBOARD_TOKEN", "test-token")
    app_client = client()

    missing = app_client.get("/api/children")
    invalid = app_client.get("/api/children", headers={"Authorization": "Bearer wrong"})

    assert missing.status_code == 401
    assert missing.json()["detail"] == "invalid or missing dashboard token"
    assert invalid.status_code == 401
    assert invalid.json()["detail"] == "invalid or missing dashboard token"


def test_children_route_accepts_valid_token_and_closes_service(monkeypatch):
    monkeypatch.setenv("SOCIOMEMORY_DASHBOARD_TOKEN", "test-token")

    response = client().get("/api/children?limit=7", headers=auth_headers())

    assert response.status_code == 200
    assert response.json() == {"children": ["child-7"]}
    assert FakeDashboardService.connected == 1
    assert FakeDashboardService.closed == 1


def test_graph_export_matches_dashboard_payload_shape(monkeypatch):
    monkeypatch.setenv("SOCIOMEMORY_DASHBOARD_TOKEN", "test-token")

    response = client().get(
        "/api/children/child_001/graph?start_id=node-1&max_depth=2&min_confidence=0.5&limit=20",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "child_id": "child_001",
        "nodes": [],
        "edges": [],
        "mode": "traverse",
        "max_depth": 2,
        "min_confidence": 0.5,
        "limit": 20,
    }


def test_ingest_maps_service_value_error_to_bad_request(monkeypatch):
    monkeypatch.setenv("SOCIOMEMORY_DASHBOARD_TOKEN", "test-token")

    response = client().post(
        "/api/children/child_001/ingest",
        headers=auth_headers(),
        json={"text": ""},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "text is required"}


def test_person_route_normalizes_comma_separated_places(monkeypatch):
    monkeypatch.setenv("SOCIOMEMORY_DASHBOARD_TOKEN", "test-token")

    response = client().post(
        "/api/children/child_001/person",
        headers=auth_headers(),
        json={"places": "park, school, ", "name": "Aarav"},
    )

    assert response.status_code == 200
    assert response.json()["result"]["places"] == ["park", "school"]
    assert response.json()["result"]["name"] == "Aarav"
