import json
import time
import requests
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError, field_validator
from indexer_config import GEMINI_API_KEYS, REQUEST_TIMEOUT
from semantic_model import SEARCH_DOMAINS, SEARCH_INTENTS, normalize_domain, normalize_intent

_last_call_time = 0.0
_MIN_INTERVAL = 1.5  # With 3 keys × 15 RPM = 45 RPM total, ~1.3s per call is safe
LLM_MODEL_NAME = "gemini-3.1-flash-lite"
LLM_SCHEMA_VERSION = "llm-v4"

SearchCategory = Literal["考试", "选课", "竞赛", "奖助", "就业", "讲座", "生活", "研究生", "学院", "项目", "资料", "公告"]
SearchDomain = Literal[
    "academic", "exam", "course", "degree", "scholarship", "employment", "competition",
    "project", "international", "life", "library", "security", "logistics", "lecture",
    "research", "resource", "news", "policy"
]
SearchIntent = Literal[
    "apply", "register", "submit", "attend", "check_result", "publicity", "download",
    "read", "schedule", "alert"
]


class AttachmentRole(BaseModel):
    name: str = ""
    role: str | None = None
    description: str | None = None
    sensitive: bool = False


class LLMResult(BaseModel):
    is_student_facing: bool = True
    student_relevance: float = Field(default=0.5, ge=0, le=1)
    audience: list[str] = Field(default_factory=list)
    category: SearchCategory = "公告"
    domain: SearchDomain = "news"
    intent: SearchIntent = "read"
    sub_category: str | None = None
    tags: list[str] = Field(default_factory=list)
    importance_score: float = Field(default=0.5, ge=0, le=1)
    deadline: str | None = None
    action_required: bool = False
    action_type: str | None = None
    action_summary: str | None = None
    required_materials: list[str] = Field(default_factory=list)
    student_summary: str
    sensitive: bool = False
    sensitive_types: list[str] = Field(default_factory=list)
    attachment_roles: list[AttachmentRole] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0, le=1)
    review_required: bool = False

    @field_validator("tags", "audience", "required_materials", "sensitive_types", "risk_flags", "evidence", mode="before")
    @classmethod
    def _coerce_string_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @field_validator("sub_category", "deadline", "action_type", "action_summary", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("domain", mode="before")
    @classmethod
    def _coerce_domain(cls, value: Any) -> str:
        return normalize_domain(value)

    @field_validator("intent", mode="before")
    @classmethod
    def _coerce_intent(cls, value: Any) -> str:
        return normalize_intent(value)

_api_keys: List[str] = [k.strip() for k in GEMINI_API_KEYS.split(",") if k.strip()] if GEMINI_API_KEYS else []
_current_key_index = 0


def llm_enabled() -> bool:
    return bool(_api_keys)


def _get_next_key() -> Optional[str]:
    """Round-robin key rotation."""
    global _current_key_index
    if not _api_keys:
        return None
    key = _api_keys[_current_key_index % len(_api_keys)]
    _current_key_index += 1
    return key


def analyze_document_with_llm(
    title: str,
    content: str,
    source_domain: str,
    *,
    enabled: bool = True,
    schema_version: str = LLM_SCHEMA_VERSION,
) -> Optional[Dict[str, Any]]:
    if not enabled or not _api_keys:
        return None

    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    _last_call_time = time.time()

    prompt = f"""
你是南京邮电大学学生信息清洗助手。你的任务是把公开网页转成可验证的学生事务结构化数据。

硬性要求：
1. 不要编造原文没有的信息；标题暗示但正文没有证据时，降低 confidence 并设置 review_required=true。
2. 日期、截止时间、地点、对象、材料必须来自原文；不确定填 null 或空数组。
3. 若正文显示“仅校内地址访问 / 请登录 / 无权访问 / 当前 IP 非校内地址”，不得推断行动事项，设置 review_required=true。
4. 分类只能使用给定枚举。竞赛只用于真实比赛/赛事/获奖/校赛；海外访学、创业基金、科研训练、交流项目优先归“项目”；奖助只用于奖学金、助学金、资助、评优，不要因为普通“公示”就归奖助；新闻回顾没有学生动作时通常归“公告”或对应生活/讲座。
5. 若含姓名、学号、手机号、身份证、名单、考生名单、获奖名单、参赛队员等个人信息风险，sensitive=true 并说明 sensitive_types。
6. domain 和 intent 必须从给定英文枚举中选择；evidence 必须摘自原文，不得编造。
7. 输出必须是合法 JSON，不要包含 Markdown。

文档标题: {title}
来源域名: {source_domain}
Schema 版本: {schema_version}
正文片段: {content[:2000]}

请严格输出如下 JSON 格式：
{{
  "is_student_facing": true, // boolean, 若纯教职工文件（如党委巡视、招标）填 false
  "student_relevance": 0.95, // float 0-1, 对普通学生的价值
  "audience": ["本科生", "研究生"], // 原文明确或可由来源推断的对象，不确定为空数组
  "category": "只能选一个: 考试|选课|竞赛|奖助|就业|讲座|生活|研究生|学院|项目|资料|公告",
  "domain": "只能选一个: {'|'.join(SEARCH_DOMAINS)}",
  "intent": "只能选一个: {'|'.join(SEARCH_INTENTS)}",
  "sub_category": "具体的二级分类，如 海外交流、慕课考试 等",
  "tags": ["标签1", "标签2"], // 提取 2-5 个相关关键词
  "importance_score": 0.85, // float 0-1, 紧急或必须处理的分数高
  "deadline": "2026-04-23T12:00:00+08:00", // ISO格式。如果没有明确截止日期，填 null
  "action_required": true, // boolean, 学生是否需要报名、填表、交费等动作
  "action_type": "报名", // string, 若无动作填 null
  "action_summary": "符合条件的学生需填写申请表，并在截止日前交至所在学院。", // 动作说明。若无填 null
  "required_materials": ["申请表", "英语成绩证明"], // 若无填 []
  "student_summary": "一两句话概括核心信息，纯学生视角",
  "sensitive": false, // boolean, 是否含有姓名、学号、手机号等个人隐私
  "sensitive_types": ["名单", "学号"],
  "attachment_roles": [
    {{"name": "附件名", "role": "申请表", "description": "学生报名需要填写", "sensitive": false}}
  ],
  "risk_flags": [],
  "evidence": ["原文中支撑分类、截止时间或行动事项的短句"],
  "confidence": 0.86,
  "review_required": false
}}
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    # Try all keys with round-robin, fallback on failure
    errors = []
    for _ in range(len(_api_keys)):
        key = _get_next_key()
        if not key:
            break
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL_NAME}:generateContent?key={key}"
        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            text_result = data["candidates"][0]["content"]["parts"][0]["text"]
            raw_result = json.loads(text_result)
            result = LLMResult.model_validate(raw_result).model_dump()

            return result
        except (ValidationError, json.JSONDecodeError, KeyError, IndexError, requests.RequestException) as e:
            errors.append(f"key=...{key[-6:]}: {e}")
            continue  # Try next key

    print(f"LLM Scoring Error for '{title}': all keys failed: {errors}")
    return None
