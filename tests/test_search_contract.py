import json
from pathlib import Path

import pytest

from scripts.models.search_contract import (
    SEARCH_CATEGORIES,
    SEARCH_DOCUMENT_KINDS,
    SEARCH_DOMAINS,
    SEARCH_INTENTS,
    SEARCH_LIFECYCLES,
    SEARCH_SEMANTIC_MODES,
    SEARCH_SOURCE_TYPES,
    TASK_FRAME_SOURCE_MODES,
    TASK_TYPES,
)
from scripts.utils.validate_search_index import validate_contract_value


ROOT_DIR = Path(__file__).resolve().parents[1]


def test_search_contract_json_matches_python_constants():
    payload = json.loads((ROOT_DIR / "config" / "search_contract.json").read_text(encoding="utf-8"))

    assert tuple(payload["document_kinds"]) == SEARCH_DOCUMENT_KINDS
    assert tuple(payload["categories"]) == SEARCH_CATEGORIES
    assert tuple(payload["domains"]) == SEARCH_DOMAINS
    assert tuple(payload["intents"]) == SEARCH_INTENTS
    assert tuple(payload["source_types"]) == SEARCH_SOURCE_TYPES
    assert tuple(payload["lifecycles"]) == SEARCH_LIFECYCLES
    assert tuple(payload["semantic_modes"]) == SEARCH_SEMANTIC_MODES
    assert tuple(payload["task_frame_source_modes"]) == TASK_FRAME_SOURCE_MODES
    assert tuple(payload["task_types"]) == TASK_TYPES


def test_build_time_validator_rejects_invalid_enum_value():
    with pytest.raises(SystemExit):
        validate_contract_value("fixture/documents.json", "doc-1", "domain", "campus_life", SEARCH_DOMAINS)
