from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any
from urllib.parse import urlparse


def sha1_text(text: str, length: int = 20) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def sha256_text(text: str, length: int = 16) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"\s+", "", text)


def stable_slug(value: Any, *, fallback: str = "unknown", max_length: int = 48) -> str:
    text = normalize_text(value)
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff_-]+", "-", text).strip("-")
    if not text:
        text = fallback
    return text[:max_length]


def canonical_title(value: Any) -> str:
    text = clean_text(value)
    text = re.sub(r"^【[^】]{1,24}】", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -_")
    return text or clean_text(value)


def unique_strings(values: list[Any], *, limit: int | None = None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if limit is not None and len(result) >= limit:
            break
    return result


def sitegraph_tokens(value: Any, *, cjk_max_n: int = 3, cap: int | None = None) -> set[str]:
    text = normalize_text(value)
    tokens: set[str] = set()
    if not text:
        return tokens
    for match in re.finditer(r"[\u4e00-\u9fff]{2,}|[a-z0-9][a-z0-9._-]{1,}", text):
        part = match.group(0)
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            if len(part) <= 16:
                tokens.add(part)
            for size in range(2, cjk_max_n + 1):
                if len(part) < size:
                    continue
                for index in range(0, len(part) - size + 1):
                    tokens.add(part[index : index + size])
                    if cap is not None and len(tokens) >= cap:
                        return tokens
        else:
            tokens.add(part)
        if cap is not None and len(tokens) >= cap:
            return tokens
    return tokens


def summarize(content: str, title: str, limit: int = 180) -> str:
    text = clean_text(content)
    title_text = clean_text(title)
    if text.startswith(title_text):
        text = text[len(title_text):].strip()
    return text[:limit] if text else title_text


def doc_host(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc
