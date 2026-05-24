import json
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PaginationConfig(BaseModel):
    type: str = "none"
    pattern: str | None = None


class SelectorConfig(BaseModel):
    list_item: str | None = None
    title: str | None = None
    date: str | None = None
    link: str | None = None
    content: str | None = None
    attachments: str | None = None


class ChannelNode(BaseModel):
    id: str
    source_id: str
    name: str
    list_urls: list[str] = Field(default_factory=list)
    student_value: float = Field(default=0.7, ge=0, le=1)
    expected_domains: list[str] = Field(default_factory=list)
    expected_intents: list[str] = Field(default_factory=list)
    priority: float = Field(default=0.7, ge=0, le=1)
    crawl_depth: int = Field(default=1, ge=1, le=5)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    selectors: SelectorConfig = Field(default_factory=SelectorConfig)
    sensitive_risks: list[str] = Field(default_factory=list)
    positive_keywords: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    audit_status: str = "manual_seeded"
    production_enabled: bool = True
    notes: str = ""

    @field_validator(
        "expected_domains",
        "expected_intents",
        "sensitive_risks",
        "positive_keywords",
        "negative_keywords",
        mode="before",
    )
    @classmethod
    def _coerce_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []


class SourceNode(BaseModel):
    id: str
    name: str
    base_url: str
    source_type: str = "central_admin"
    authority: float = Field(default=0.7, ge=0, le=1)
    default_audience: list[str] = Field(default_factory=list)
    access_level: str = "public"
    audit_status: str = "manual_seeded"
    enabled: bool = True
    adapter_kind: str = "njupt_wp"
    include_patterns: list[str] = Field(default_factory=list)
    exclude_patterns: list[str] = Field(default_factory=list)
    notes: str = ""
    channels: list[ChannelNode] = Field(default_factory=list)

    @field_validator("default_audience", "include_patterns", "exclude_patterns", mode="before")
    @classmethod
    def _coerce_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []


class SourceChannelGraph(BaseModel):
    version: int = 1
    sources: list[SourceNode] = Field(default_factory=list)

    def channel_count(self) -> int:
        return sum(len(source.channels) for source in self.sources)

    def audited_channel_count(self) -> int:
        return sum(
            1
            for source in self.sources
            for channel in source.channels
            if channel.audit_status not in {"", "unknown"}
        )

    def production_channel_count(self) -> int:
        return sum(1 for source in self.sources for channel in source.channels if channel.production_enabled)

    def failed_channel_count(self) -> int:
        return sum(1 for source in self.sources for channel in source.channels if channel.audit_status == "failed")


def load_source_channel_graph(path: str) -> SourceChannelGraph:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return SourceChannelGraph.model_validate(payload)
