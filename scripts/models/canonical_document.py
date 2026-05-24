import hashlib
import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from pydantic import BaseModel, Field, field_validator


class CanonicalAttachment(BaseModel):
    name: str = ""
    url: str = ""
    type: str | None = None
    role: str | None = None
    description: str | None = None
    sensitive: bool = False

    @field_validator("name", "url", "type", "role", "description", mode="before")
    @classmethod
    def _coerce_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = re.sub(r"\s+", " ", str(value)).strip()
        return text or None


class RawDocument(BaseModel):
    raw_id: str
    source_id: str
    channel_id: str
    url: str
    title: str
    raw_html: str | None = None
    raw_text: str | None = None
    fetched_at: str
    http_status: int | None = None
    published_at: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class CanonicalDocument(BaseModel):
    doc_id: str
    source_id: str
    channel_id: str
    title: str
    canonical_url: str
    published_at: str | None = None
    clean_text: str
    attachments: list[CanonicalAttachment] = Field(default_factory=list)
    content_hash: str
    dedupe_key: str
    language: str = "zh"
    status: str = "ok"
    fetched_at: str | None = None
    http_status: int | None = None


def normalize_canonical_url(url: str, base_url: str | None = None) -> str:
    absolute = urljoin(base_url or "", str(url or "").strip())
    parsed = urlparse(absolute)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(("utm_", "spm", "from"))
    ]
    query = urlencode(sorted(query_pairs), doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))


def normalize_clean_text(text: str) -> str:
    text = re.sub(r"\u00a0", " ", str(text or ""))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def stable_hash(*parts: Any) -> str:
    payload = jsonish(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def jsonish(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "[" + "|".join(jsonish(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + "|".join(f"{key}:{jsonish(value[key])}" for key in sorted(value)) + "}"
    return str(value)


def canonicalize_attachment(attachment: dict[str, Any], page_url: str) -> CanonicalAttachment:
    raw_url = str(attachment.get("url") or "")
    canonical_url = normalize_canonical_url(raw_url, page_url) if raw_url else ""
    parsed_path = urlparse(canonical_url).path
    inferred_type = (parsed_path.rsplit(".", 1)[-1].lower() if "." in parsed_path else None)
    return CanonicalAttachment(
        name=str(attachment.get("name") or parsed_path.rsplit("/", 1)[-1] or "附件"),
        url=canonical_url,
        type=str(attachment.get("type") or inferred_type or "").lstrip(".") or None,
        role=attachment.get("role"),
        description=attachment.get("description"),
        sensitive=bool(attachment.get("sensitive", False)),
    )


def canonicalize_raw_document(raw: RawDocument, *, base_url: str | None = None) -> CanonicalDocument:
    canonical_url = normalize_canonical_url(raw.url, base_url)
    clean_text = normalize_clean_text(raw.raw_text or raw.raw_html or raw.title)
    attachments = [canonicalize_attachment(item, canonical_url) for item in raw.attachments]
    content_hash = stable_hash(raw.title, clean_text, [item.model_dump() for item in attachments])
    title_key = re.sub(r"[，,。；;：:\s\"“”'‘’（）()《》<>·\-—_]+", "", raw.title).lower()
    dedupe_key = stable_hash(raw.source_id, title_key or canonical_url, content_hash)
    published_at = normalize_datetime(raw.published_at)
    return CanonicalDocument(
        doc_id=raw.raw_id,
        source_id=raw.source_id,
        channel_id=raw.channel_id,
        title=normalize_clean_text(raw.title),
        canonical_url=canonical_url,
        published_at=published_at,
        clean_text=clean_text,
        attachments=attachments,
        content_hash=content_hash,
        dedupe_key=dedupe_key,
        fetched_at=normalize_datetime(raw.fetched_at),
        http_status=raw.http_status,
    )


def normalize_datetime(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        return text
