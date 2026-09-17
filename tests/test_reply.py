from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

PERSONAS_URL = "/api/personas"


def _create_persona(
    client: TestClient, api_headers: dict[str, str], **overrides: object
) -> int:
    body: dict[str, object] = {
        "name": "Test Persona",
        "style_guide": "Short sentences.",
        "exemplars": ["hey", "sounds good"],
        "safety_categories": [],
        "safety_threshold": 1.0,
    }
    body.update(overrides)
    response = client.post(PERSONAS_URL, headers=api_headers, json=body)
    return int(response.json()["id"])


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_reply_returns_text_and_remembers_facts(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "hey, good to hear"
    mock_extract_facts.return_value = ["lives in Austin"]
    persona_id = _create_persona(client, api_headers)

    response = client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": "discord:1",
            "message": "just moved to Austin",
            "author": "alice",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply_text"] == "hey, good to hear"
    assert body["status"] == "sent"

    memory = client.get(
        f"{PERSONAS_URL}/{persona_id}/memory",
        headers=api_headers,
        params={"conversation_key": "discord:1"},
    ).json()
    assert memory[0]["fact_text"] == "lives in Austin"


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_reply_folds_prior_facts_into_next_call(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "reply"
    mock_extract_facts.return_value = []
    persona_id = _create_persona(client, api_headers)
    key = "discord:1"
    mock_extract_facts.return_value = ["lives in Austin"]
    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": key,
            "message": "just moved to Austin",
            "author": "alice",
        },
    )

    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": key,
            "message": "hi again",
            "author": "alice",
        },
    )

    second_call_style_guide = mock_generate_reply.call_args_list[1].args[1]
    assert "lives in Austin" in second_call_style_guide


@patch("capsize_persona.generation.generate_reply")
def test_reply_suppresses_when_repeatedly_flagged(
    mock_generate_reply: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "banned word here"
    persona_id = _create_persona(
        client,
        api_headers,
        safety_categories=[
            {
                "id": "banned",
                "label": "Banned",
                "weight": 5.0,
                "terms": ["banned word"],
            }
        ],
    )

    response = client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": "discord:1",
            "message": "hi",
            "author": "alice",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "suppressed"
    assert mock_generate_reply.call_count == 3


def test_reply_404s_for_missing_persona(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{PERSONAS_URL}/999/reply",
        headers=api_headers,
        json={"conversation_key": "k", "message": "hi", "author": "alice"},
    )
    assert response.status_code == 404


def test_reply_requires_api_key(client: TestClient) -> None:
    response = client.post(
        f"{PERSONAS_URL}/1/reply",
        json={"conversation_key": "k", "message": "hi", "author": "alice"},
    )
    assert response.status_code == 401
