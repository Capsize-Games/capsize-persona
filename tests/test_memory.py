from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

PERSONAS_URL = "/api/personas"


def _create_persona(client: TestClient, api_headers: dict[str, str]) -> int:
    response = client.post(
        PERSONAS_URL,
        headers=api_headers,
        json={
            "name": "Test Persona",
            "style_guide": "Short sentences.",
            "exemplars": ["hey"],
            "safety_categories": [],
            "safety_threshold": 1.0,
        },
    )
    return int(response.json()["id"])


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_delete_fact_removes_it(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "reply"
    mock_extract_facts.return_value = ["bad fact"]
    persona_id = _create_persona(client, api_headers)
    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={"conversation_key": "k", "message": "hi", "author": "alice"},
    )
    fact_id = client.get(
        f"{PERSONAS_URL}/{persona_id}/memory",
        headers=api_headers,
        params={"conversation_key": "k"},
    ).json()[0]["id"]

    response = client.delete(
        f"{PERSONAS_URL}/{persona_id}/memory/{fact_id}", headers=api_headers
    )

    assert response.status_code == 204
    remaining = client.get(
        f"{PERSONAS_URL}/{persona_id}/memory",
        headers=api_headers,
        params={"conversation_key": "k"},
    ).json()
    assert remaining == []


def test_delete_missing_fact_404s(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    persona_id = _create_persona(client, api_headers)

    response = client.delete(
        f"{PERSONAS_URL}/{persona_id}/memory/999", headers=api_headers
    )

    assert response.status_code == 404


def test_list_memory_scoped_to_conversation_key(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    persona_id = _create_persona(client, api_headers)

    response = client.get(
        f"{PERSONAS_URL}/{persona_id}/memory",
        headers=api_headers,
        params={"conversation_key": "unused-key"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_create_fact_direct_write(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    persona_id = _create_persona(client, api_headers)

    response = client.post(
        f"{PERSONAS_URL}/{persona_id}/memory",
        headers=api_headers,
        json={"conversation_key": "k", "fact_text": "prefers tea"},
    )

    assert response.status_code == 201
    assert response.json()["fact_text"] == "prefers tea"
    assert response.json()["is_sensitive"] is False


def test_create_fact_direct_write_can_flag_sensitive(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    persona_id = _create_persona(client, api_headers)

    response = client.post(
        f"{PERSONAS_URL}/{persona_id}/memory",
        headers=api_headers,
        json={
            "conversation_key": "k",
            "fact_text": "a secret",
            "is_sensitive": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["is_sensitive"] is True


def test_create_fact_404s_for_missing_persona(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{PERSONAS_URL}/999/memory",
        headers=api_headers,
        json={"conversation_key": "k", "fact_text": "prefers tea"},
    )

    assert response.status_code == 404
