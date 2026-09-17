from capsize_persona.generation import _extra_body


def test_extra_body_returns_none_for_empty_order() -> None:
    assert _extra_body([]) is None


def test_extra_body_uses_only_not_allow_fallbacks() -> None:
    """`only` restricts-but-still-retries; `allow_fallbacks` doesn't.

    `allow_fallbacks: False` alone silently drops everything but the
    first provider in `order` and fails outright on its error.
    """
    body = _extra_body(["deepinfra", "fireworks"])

    assert body == {
        "provider": {
            "order": ["deepinfra", "fireworks"],
            "only": ["deepinfra", "fireworks"],
        }
    }
