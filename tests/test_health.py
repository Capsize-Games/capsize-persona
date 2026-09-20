"""Health and readiness endpoint contracts."""

from fastapi.testclient import TestClient


def test_health_preserves_the_existing_body(client: TestClient) -> None:
    """The shared route keeps the service's liveness payload unchanged."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_ready_uses_the_shared_contract(client: TestClient) -> None:
    """The service exposes the shared unauthenticated readiness probe."""
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
