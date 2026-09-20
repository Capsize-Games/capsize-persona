set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

setup:
    uv sync --extra dev

build:
    uv build

test:
    uv run pytest -q

lint:
    uv run ruff check capsize_persona tests migrations

format:
    uv run ruff format capsize_persona tests migrations

typecheck:
    uv run mypy capsize_persona

run:
    uv run python -m capsize_persona

ci: lint typecheck test build
