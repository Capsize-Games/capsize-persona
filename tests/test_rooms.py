from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

PERSONAS_URL = "/api/personas"


def _create_persona(
    client: TestClient, api_headers: dict[str, str], name: str = "Test Persona"
) -> int:
    response = client.post(
        PERSONAS_URL,
        headers=api_headers,
        json={
            "name": name,
            "style_guide": "Short sentences.",
            "exemplars": ["hey"],
            "safety_categories": [],
            "safety_threshold": 1.0,
        },
    )
    return int(response.json()["id"])


def test_list_rooms_empty_for_new_persona(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    persona_id = _create_persona(client, api_headers)

    response = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms", headers=api_headers
    )

    assert response.status_code == 200
    assert response.json() == []


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_repeated_reply_reuses_same_room(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "hi"
    mock_extract_facts.return_value = []
    persona_id = _create_persona(client, api_headers)
    body = {
        "conversation_key": "discord:1",
        "message": "hi",
        "author": "alice",
        "speaker_name": "testbot",
    }

    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply", headers=api_headers, json=body
    )
    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply", headers=api_headers, json=body
    )

    rooms = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms", headers=api_headers
    ).json()
    assert len(rooms) == 1


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_different_personas_get_isolated_rooms(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "hi"
    mock_extract_facts.return_value = []
    persona_a = _create_persona(client, api_headers, name="Persona A")
    persona_b = _create_persona(client, api_headers, name="Persona B")
    body = {
        "conversation_key": "shared-key",
        "message": "hi",
        "author": "alice",
        "speaker_name": "testbot",
    }

    client.post(
        f"{PERSONAS_URL}/{persona_a}/reply", headers=api_headers, json=body
    )
    client.post(
        f"{PERSONAS_URL}/{persona_b}/reply", headers=api_headers, json=body
    )

    rooms_a = client.get(
        f"{PERSONAS_URL}/{persona_a}/rooms", headers=api_headers
    ).json()
    rooms_b = client.get(
        f"{PERSONAS_URL}/{persona_b}/rooms", headers=api_headers
    ).json()
    assert len(rooms_a) == 1
    assert len(rooms_b) == 1
    assert rooms_a[0]["id"] != rooms_b[0]["id"]


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_clear_turns_empties_room_but_keeps_it_listed(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "hi"
    mock_extract_facts.return_value = []
    persona_id = _create_persona(client, api_headers)
    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": "k",
            "message": "hi",
            "author": "alice",
            "speaker_name": "testbot",
        },
    )
    room_id = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms", headers=api_headers
    ).json()[0]["id"]

    response = client.delete(
        f"{PERSONAS_URL}/{persona_id}/rooms/{room_id}/turns",
        headers=api_headers,
    )

    assert response.status_code == 204
    turns = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms/{room_id}/turns",
        headers=api_headers,
    ).json()
    assert turns == []


def test_delete_turn_missing_404s(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    persona_id = _create_persona(client, api_headers)

    response = client.delete(
        f"{PERSONAS_URL}/{persona_id}/turns/999", headers=api_headers
    )

    assert response.status_code == 404


def test_rooms_requires_api_key(client: TestClient) -> None:
    response = client.get(f"{PERSONAS_URL}/1/rooms")
    assert response.status_code == 401


def test_create_turn_direct_write(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    persona_id = _create_persona(client, api_headers)

    response = client.post(
        f"{PERSONAS_URL}/{persona_id}/turns",
        headers=api_headers,
        json={
            "conversation_key": "bluesky:joecurlee.com",
            "platform": "bluesky",
            "room_type": "account",
            "room_key": "joecurlee.com",
            "speaker": "Joe",
            "text": "just shipped a new feature",
        },
    )

    assert response.status_code == 201
    assert response.json()["speaker"] == "Joe"
    assert response.json()["text"] == "just shipped a new feature"

    rooms = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms", headers=api_headers
    ).json()
    assert len(rooms) == 1
    assert rooms[0]["platform"] == "bluesky"


def test_create_turn_404s_for_missing_persona(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{PERSONAS_URL}/999/turns",
        headers=api_headers,
        json={
            "conversation_key": "k",
            "speaker": "Joe",
            "text": "hi",
        },
    )
    assert response.status_code == 404


def test_create_turn_reuses_room_across_posts(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    persona_id = _create_persona(client, api_headers)
    body = {
        "conversation_key": "k",
        "platform": "bluesky",
        "room_type": "account",
        "room_key": "joecurlee.com",
        "speaker": "Joe",
        "text": "post one",
    }

    client.post(
        f"{PERSONAS_URL}/{persona_id}/turns", headers=api_headers, json=body
    )
    client.post(
        f"{PERSONAS_URL}/{persona_id}/turns",
        headers=api_headers,
        json={**body, "text": "post two"},
    )

    rooms = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms", headers=api_headers
    ).json()
    assert len(rooms) == 1
    turns = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms/{rooms[0]['id']}/turns",
        headers=api_headers,
    ).json()
    assert [t["text"] for t in turns] == ["post one", "post two"]
