from fastapi.testclient import TestClient

PERSONAS_URL = "/api/personas"


def _body(**overrides: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "name": "Test Persona",
        "style_guide": "Short sentences. No adjectives.",
        "exemplars": ["hey", "sounds good", "not really"],
        "safety_categories": [],
        "safety_threshold": 1.0,
    }
    defaults.update(overrides)
    return defaults


def test_create_and_list_persona(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    response = client.post(
        PERSONAS_URL, headers=api_headers, json=_body()
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Persona"

    listed = client.get(PERSONAS_URL, headers=api_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_create_persona_requires_api_key(client: TestClient) -> None:
    response = client.post(PERSONAS_URL, json=_body())
    assert response.status_code == 401


def test_get_persona(client: TestClient, api_headers: dict[str, str]) -> None:
    created = client.post(
        PERSONAS_URL, headers=api_headers, json=_body()
    ).json()

    response = client.get(
        f"{PERSONAS_URL}/{created['id']}", headers=api_headers
    )

    assert response.status_code == 200
    assert response.json()["exemplars"] == ["hey", "sounds good", "not really"]


def test_get_missing_persona_404s(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    response = client.get(f"{PERSONAS_URL}/999", headers=api_headers)
    assert response.status_code == 404


def test_update_persona(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    created = client.post(
        PERSONAS_URL, headers=api_headers, json=_body()
    ).json()

    response = client.patch(
        f"{PERSONAS_URL}/{created['id']}",
        headers=api_headers,
        json={"safety_threshold": 2.0},
    )

    assert response.status_code == 200
    assert response.json()["safety_threshold"] == 2.0
    assert response.json()["style_guide"] == "Short sentences. No adjectives."


def test_delete_persona(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    created = client.post(
        PERSONAS_URL, headers=api_headers, json=_body()
    ).json()

    response = client.delete(
        f"{PERSONAS_URL}/{created['id']}", headers=api_headers
    )

    assert response.status_code == 204
    assert (
        client.get(f"{PERSONAS_URL}/{created['id']}", headers=api_headers)
        .status_code
        == 404
    )
