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
            "speaker_name": "testbot",
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
            "speaker_name": "testbot",
        },
    )

    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": key,
            "message": "hi again",
            "author": "alice",
            "speaker_name": "testbot",
        },
    )

    second_call_style_guide = mock_generate_reply.call_args_list[1].args[1]
    assert "lives in Austin" in second_call_style_guide


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_reply_tells_model_its_speaker_name(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "hey"
    mock_extract_facts.return_value = []
    persona_id = _create_persona(client, api_headers)

    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": "discord:1",
            "message": "hi",
            "author": "alice",
            "speaker_name": "capsize",
        },
    )

    style_guide = mock_generate_reply.call_args.args[1]
    assert "You are capsize." in style_guide


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
            "speaker_name": "testbot",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "suppressed"
    assert mock_generate_reply.call_count == 3


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_reply_flags_facts_from_private_source(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "reply"
    mock_extract_facts.return_value = ["a private fact"]
    persona_id = _create_persona(client, api_headers)

    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": "discord:1",
            "message": "a secret",
            "author": "alice",
            "speaker_name": "testbot",
            "source_is_private": True,
        },
    )

    memory = client.get(
        f"{PERSONAS_URL}/{persona_id}/memory",
        headers=api_headers,
        params={"conversation_key": "discord:1"},
    ).json()
    assert memory[0]["is_sensitive"] is True


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_reply_defaults_facts_to_not_sensitive(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "reply"
    mock_extract_facts.return_value = ["a public fact"]
    persona_id = _create_persona(client, api_headers)

    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": "discord:1",
            "message": "hi",
            "author": "alice",
            "speaker_name": "testbot",
        },
    )

    memory = client.get(
        f"{PERSONAS_URL}/{persona_id}/memory",
        headers=api_headers,
        params={"conversation_key": "discord:1"},
    ).json()
    assert memory[0]["is_sensitive"] is False


def test_reply_404s_for_missing_persona(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{PERSONAS_URL}/999/reply",
        headers=api_headers,
        json={
            "conversation_key": "k",
            "message": "hi",
            "author": "alice",
            "speaker_name": "testbot",
        },
    )
    assert response.status_code == 404


def test_reply_requires_api_key(client: TestClient) -> None:
    response = client.post(
        f"{PERSONAS_URL}/1/reply",
        json={
            "conversation_key": "k",
            "message": "hi",
            "author": "alice",
            "speaker_name": "testbot",
        },
    )
    assert response.status_code == 401


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_reply_writes_turn_pair_after_sent_reply(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "hey there"
    mock_extract_facts.return_value = []
    persona_id = _create_persona(client, api_headers)

    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": "discord:1",
            "message": "hi",
            "author": "alice",
            "speaker_name": "testbot",
        },
    )

    rooms = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms", headers=api_headers
    ).json()
    assert len(rooms) == 1
    turns = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms/{rooms[0]['id']}/turns",
        headers=api_headers,
    ).json()
    assert [(t["speaker"], t["text"]) for t in turns] == [
        ("alice", "hi"),
        ("testbot", "hey there"),
    ]


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_reply_threads_recent_turns_into_next_call(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "reply"
    mock_extract_facts.return_value = []
    persona_id = _create_persona(client, api_headers)
    key = "discord:1"

    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": key,
            "message": "just moved to Austin",
            "author": "alice",
            "speaker_name": "testbot",
        },
    )
    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": key,
            "message": "summarize the conversation so far",
            "author": "alice",
            "speaker_name": "testbot",
        },
    )

    second_call_kwargs = mock_generate_reply.call_args_list[1].kwargs
    recent_turns = second_call_kwargs["recent_turns"]
    assert ("alice", "just moved to Austin") in recent_turns
    assert ("testbot", "reply") in recent_turns


@patch("capsize_persona.generation.generate_reply")
def test_reply_does_not_store_turns_when_suppressed(
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

    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": "discord:1",
            "message": "hi",
            "author": "alice",
            "speaker_name": "testbot",
        },
    )

    rooms = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms", headers=api_headers
    ).json()
    turns = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms/{rooms[0]['id']}/turns",
        headers=api_headers,
    ).json()
    assert turns == []


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_public_reply_excludes_sensitive_facts_and_turns(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    """Confirm leak prevention.

    A fact/turn learned somewhere private must never reach a reply
    headed somewhere public.
    """
    mock_generate_reply.return_value = "reply"
    mock_extract_facts.return_value = []
    persona_id = _create_persona(client, api_headers)
    key = "discord:1"

    # A private exchange: learns a sensitive fact and turn.
    mock_extract_facts.return_value = ["a private fact"]
    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": key,
            "message": "a secret",
            "author": "alice",
            "speaker_name": "testbot",
            "source_is_private": True,
        },
    )

    # A later, public exchange in the same conversation.
    mock_extract_facts.return_value = []
    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": key,
            "message": "hi again",
            "author": "alice",
            "speaker_name": "testbot",
            "source_is_private": False,
        },
    )

    public_call_kwargs = mock_generate_reply.call_args_list[1].kwargs
    assert public_call_kwargs["recent_turns"] == []
    public_call_style_guide = mock_generate_reply.call_args_list[1].args[1]
    assert "a private fact" not in public_call_style_guide


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_private_reply_still_sees_sensitive_context(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "reply"
    mock_extract_facts.return_value = []
    persona_id = _create_persona(client, api_headers)
    key = "discord:1"

    mock_extract_facts.return_value = ["a private fact"]
    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": key,
            "message": "a secret",
            "author": "alice",
            "speaker_name": "testbot",
            "source_is_private": True,
        },
    )
    mock_extract_facts.return_value = []
    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": key,
            "message": "still private",
            "author": "alice",
            "speaker_name": "testbot",
            "source_is_private": True,
        },
    )

    second_call_style_guide = mock_generate_reply.call_args_list[1].args[1]
    assert "a private fact" in second_call_style_guide


@patch("capsize_persona.generation.extract_facts")
@patch("capsize_persona.generation.generate_reply")
def test_reply_multi_speaker_shared_room(
    mock_generate_reply: MagicMock,
    mock_extract_facts: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_reply.return_value = "reply"
    mock_extract_facts.return_value = []
    persona_id = _create_persona(client, api_headers)
    room_body = {
        "platform": "discord",
        "room_type": "channel",
        "room_key": "guild:channel",
    }

    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": "unused",
            "message": "hey everyone",
            "author": "alice",
            "speaker_name": "testbot",
            "speaker_id": "u1",
            **room_body,
        },
    )
    client.post(
        f"{PERSONAS_URL}/{persona_id}/reply",
        headers=api_headers,
        json={
            "conversation_key": "unused",
            "message": "hi alice",
            "author": "bob",
            "speaker_name": "testbot",
            "speaker_id": "u2",
            **room_body,
        },
    )

    rooms = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms", headers=api_headers
    ).json()
    assert len(rooms) == 1
    turns = client.get(
        f"{PERSONAS_URL}/{persona_id}/rooms/{rooms[0]['id']}/turns",
        headers=api_headers,
    ).json()
    speakers = {t["speaker"] for t in turns}
    assert {"alice", "bob", "testbot"} <= speakers
