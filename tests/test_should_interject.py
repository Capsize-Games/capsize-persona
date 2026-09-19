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


@patch("capsize_persona.generation._voice_should_interject")
def test_should_interject_true(
    mock_voice_should_interject: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_voice_should_interject.return_value = True
    persona_id = _create_persona(client, api_headers)

    response = client.post(
        f"{PERSONAS_URL}/{persona_id}/should-interject",
        headers=api_headers,
        json={
            "conversation_key": "discord:1",
            "message": "what does everyone think?",
            "author": "alice",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"interject": True}


@patch("capsize_persona.generation._voice_should_interject")
def test_should_interject_false(
    mock_voice_should_interject: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_voice_should_interject.return_value = False
    persona_id = _create_persona(client, api_headers)

    response = client.post(
        f"{PERSONAS_URL}/{persona_id}/should-interject",
        headers=api_headers,
        json={
            "conversation_key": "discord:1",
            "message": "lol same",
            "author": "bob",
        },
    )

    assert response.json() == {"interject": False}


@patch("capsize_persona.generation._voice_should_interject")
def test_should_interject_passes_recent_turns(
    mock_voice_should_interject: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_voice_should_interject.return_value = False
    persona_id = _create_persona(client, api_headers)
    key = "discord:1"
    # Seed a turn via a direct-write-equivalent: two should-interject
    # calls don't write turns themselves (only /reply does), so seed
    # via /reply first with generation mocked out.
    with patch(
        "capsize_persona.generation.generate_reply", return_value="hi"
    ), patch("capsize_persona.generation.extract_facts", return_value=[]):
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
        f"{PERSONAS_URL}/{persona_id}/should-interject",
        headers=api_headers,
        json={"conversation_key": key, "message": "cool", "author": "bob"},
    )

    recent_turns = mock_voice_should_interject.call_args.args[3]
    assert ("alice", "just moved to Austin") in recent_turns


@patch("capsize_persona.generation._voice_should_interject")
def test_should_interject_never_sees_sensitive_turns(
    mock_voice_should_interject: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    """Confirm leak prevention.

    should-interject only ever runs on ambient channel messages -
    inherently public - so it must never see a turn learned somewhere
    private, regardless of that room's own history.
    """
    mock_voice_should_interject.return_value = False
    persona_id = _create_persona(client, api_headers)
    key = "discord:1"
    with patch(
        "capsize_persona.generation.generate_reply", return_value="hi"
    ), patch("capsize_persona.generation.extract_facts", return_value=[]):
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

    client.post(
        f"{PERSONAS_URL}/{persona_id}/should-interject",
        headers=api_headers,
        json={"conversation_key": key, "message": "cool", "author": "bob"},
    )

    recent_turns = mock_voice_should_interject.call_args.args[3]
    assert recent_turns == []


def test_should_interject_404s_for_missing_persona(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{PERSONAS_URL}/999/should-interject",
        headers=api_headers,
        json={"conversation_key": "k", "message": "hi", "author": "alice"},
    )
    assert response.status_code == 404


def test_should_interject_requires_api_key(client: TestClient) -> None:
    response = client.post(
        f"{PERSONAS_URL}/1/should-interject",
        json={"conversation_key": "k", "message": "hi", "author": "alice"},
    )
    assert response.status_code == 401
