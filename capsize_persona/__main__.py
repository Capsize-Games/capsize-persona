"""Entry point: `python -m capsize_persona` or the `capsize-persona` script."""

import logging
import os

import uvicorn


def main() -> None:
    """Run the API with uvicorn, reading host/port from the environment."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s"
    )
    port = int(os.environ.get("PERSONA_PORT", "8879"))
    uvicorn.run("capsize_persona.app:app", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
