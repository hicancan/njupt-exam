import json
import os
from functools import lru_cache
from typing import Any


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SEARCH_CONTRACT_PATH = os.path.join(BASE_DIR, "config", "search_contract.json")


@lru_cache(maxsize=1)
def load_search_contract(path: str = SEARCH_CONTRACT_PATH) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"search contract must be a JSON object: {path}")
    return payload


def contract_tuple(field: str) -> tuple[str, ...]:
    payload = load_search_contract()
    values = payload.get(field)
    if not isinstance(values, list) or not all(isinstance(item, str) and item for item in values):
        raise ValueError(f"search contract field {field!r} must be a non-empty string list")
    return tuple(values)


SEARCH_DOCUMENT_KINDS = contract_tuple("document_kinds")
SEARCH_CATEGORIES = contract_tuple("categories")
SEARCH_DOMAINS = contract_tuple("domains")
SEARCH_INTENTS = contract_tuple("intents")
SEARCH_SOURCE_TYPES = contract_tuple("source_types")
SEARCH_LIFECYCLES = contract_tuple("lifecycles")
SEARCH_SEMANTIC_MODES = contract_tuple("semantic_modes")
TASK_FRAME_SOURCE_MODES = contract_tuple("task_frame_source_modes")
TASK_TYPES = contract_tuple("task_types")


def normalize_contract_value(value: Any, allowed: tuple[str, ...], fallback: str) -> str:
    text = str(value or "").strip()
    if text in allowed:
        return text
    if fallback not in allowed:
        raise ValueError(f"fallback {fallback!r} is not in contract values")
    return fallback


def ensure_contract_value(value: Any, allowed: tuple[str, ...], *, field: str) -> str:
    text = str(value or "").strip()
    if text not in allowed:
        raise ValueError(f"invalid {field}: {text!r}; allowed={', '.join(allowed)}")
    return text
