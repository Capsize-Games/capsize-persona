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


@patch("capsize_persona.generation.generate_candidates")
def test_generate_returns_candidates(
    mock_generate_candidates: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_candidates.return_value = ["candidate one", "candidate two"]
    persona_id = _create_persona(client, api_headers)

    response = client.post(
        f"{PERSONAS_URL}/{persona_id}/generate",
        headers=api_headers,
        json={
            "context": "shipped a new feature",
            "count": 2,
            "speaker_name": "testbot",
        },
    )

    assert response.status_code == 200
    assert response.json()["candidates"] == [
        "candidate one",
        "candidate two",
    ]


@patch("capsize_persona.generation.generate_candidates")
def test_generate_tells_model_its_speaker_name(
    mock_generate_candidates: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    mock_generate_candidates.return_value = ["hey"]
    persona_id = _create_persona(client, api_headers)

    client.post(
        f"{PERSONAS_URL}/{persona_id}/generate",
        headers=api_headers,
        json={
            "context": "a context",
            "count": 1,
            "speaker_name": "capsize",
        },
    )

    style_guide = mock_generate_candidates.call_args.args[1]
    assert "You are capsize." in style_guide


@patch("capsize_persona.generation.generate_candidates")
def test_generate_does_not_fold_memory(
    mock_generate_candidates: MagicMock,
    client: TestClient,
    api_headers: dict[str, str],
) -> None:
    """Original posts aren't replies - no conversation facts apply."""
    mock_generate_candidates.return_value = ["hey"]
    persona_id = _create_persona(client, api_headers)

    client.post(
        f"{PERSONAS_URL}/{persona_id}/generate",
        headers=api_headers,
        json={
            "context": "a context",
            "count": 1,
            "speaker_name": "testbot",
        },
    )

    style_guide = mock_generate_candidates.call_args.args[1]
    assert "Known context about this conversation" not in style_guide


def test_generate_404s_for_missing_persona(
    client: TestClient, api_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{PERSONAS_URL}/999/generate",
        headers=api_headers,
        json={"context": "x", "count": 1, "speaker_name": "testbot"},
    )
    assert response.status_code == 404


def test_generate_requires_api_key(client: TestClient) -> None:
    response = client.post(
        f"{PERSONAS_URL}/1/generate",
        json={"context": "x", "count": 1, "speaker_name": "testbot"},
    )
    assert response.status_code == 401
