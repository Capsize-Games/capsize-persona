"""Characterize the repository metadata and documented fleet boundary."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]


def _manifest() -> dict[str, object]:
    return json.loads((ROOT / "capsize.json").read_text())


def test_manifest_identifies_the_public_python_service() -> None:
    manifest = _manifest()

    assert manifest["name"] == "capsize-persona"
    assert manifest["type"] == "service"
    assert manifest["languages"] == ["python"]
    assert manifest["runtimes"] == {"python": ">=3.11"}
    assert manifest["owner"] == "Capsize-Games"
    assert manifest["license"] == "MIT"


def test_manifest_exposes_the_supported_task_contract() -> None:
    commands = _manifest()["commands"]

    assert commands == {
        "setup": "setup",
        "build": "build",
        "test": "test",
        "lint": "lint",
        "format": "format",
        "typecheck": "typecheck",
        "run": "run",
        "clean": None,
        "docs": None,
        "ci": "ci",
    }


def test_shared_and_domain_dependencies_have_distinct_authorities() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    dependencies = project["project"]["dependencies"]

    assert "capsize-commons[config,db,web]>=0.1.2" in dependencies
    assert "capsize-memory>=0.1.0" in dependencies
    assert "capsize-voice>=0.1.0" in dependencies


def test_fleet_document_records_retained_product_boundaries() -> None:
    document = (ROOT / "docs" / "FLEET_CONSOLIDATION.md").read_text()

    for phrase in (
        "Persona models, generation orchestration",
        "Alembic migrations and persistence schema",
        "Docker startup, port, healthcheck, and secret injection",
        '`/health` as `200 {"ok": true}`',
        '`/ready` as the unauthenticated `200 {"status":"ready"}`',
    ):
        assert phrase in document


def test_no_new_extraction_is_claimed_without_compatibility_evidence() -> None:
    document = (ROOT / "docs" / "FLEET_CONSOLIDATION.md").read_text()

    assert "This audit proposes no new extraction." in document
    assert (
        "No consumer, API shape, compatibility test, "
        "or rollback plan" in document
    )
