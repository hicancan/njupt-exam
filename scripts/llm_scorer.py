import json
import time
import requests
from typing import Any, Dict, List, Optional
from indexer_config import GEMINI_API_KEYS, REQUEST_TIMEOUT

_last_call_time = 0.0
_MIN_INTERVAL = 1.5  # With 3 keys × 15 RPM = 45 RPM total, ~1.3s per call is safe

_api_keys: List[str] = [k.strip() for k in GEMINI_API_KEYS.split(",") if k.strip()] if GEMINI_API_KEYS else []
_current_key_index = 0


def _get_next_key() -> Optional[str]:
    """Round-robin key rotation."""
    global _current_key_index
    if not _api_keys:
        return None
    key = _api_keys[_current_key_index % len(_api_keys)]
    _current_key_index += 1
    return key


def analyze_document_with_llm(title: str, content: str, source_domain: str) -> Optional[Dict[str, Any]]:
    if not _api_keys:
        return None

    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    _last_call_time = time.time()

    prompt = f"""
你是一个南邮校园信息理解专家系统。
请根据以下给定网页标题、来源和正文片段，判断该信息是否对学生有用，并提取结构化字段。
要求：
1. 不要编造原文没有的信息。
2. 所有日期、截止时间、地点、对象必须严格来自原文。
3. 如果不确定，字段填 null。
4. 输出必须是合法的 JSON。

文档标题: {title}
来源域名: {source_domain}
正文片段: {content[:2000]}

请严格输出如下 JSON 格式：
{{
  "is_student_facing": true, // boolean, 若纯教职工文件（如党委巡视、招标）填 false
  "student_relevance": 0.95, // float 0-1, 对普通学生的价值
  "category": "只能选一个: 考试|选课|竞赛|奖助|就业|讲座|生活|研究生|学院|项目|资料|公告",
  "sub_category": "具体的二级分类，如 海外交流、慕课考试 等",
  "tags": ["标签1", "标签2"], // 提取 2-5 个相关关键词
  "importance_score": 0.85, // float 0-1, 紧急或必须处理的分数高
  "deadline": "2026-04-23T12:00:00+08:00", // ISO格式。如果没有明确截止日期，填 null
  "action_required": true, // boolean, 学生是否需要报名、填表、交费等动作
  "action_type": "报名", // string, 若无动作填 null
  "action_summary": "符合条件的学生需填写申请表，并在截止日前交至所在学院。", // 动作说明。若无填 null
  "student_summary": "一两句话概括核心信息，纯学生视角",
  "sensitive": false // boolean, 是否含有姓名、学号、手机号等个人隐私
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={key}"
        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            text_result = data["candidates"][0]["content"]["parts"][0]["text"]
            result = json.loads(text_result)

            if "category" not in result or "importance_score" not in result:
                return None

            return result
        except Exception as e:
            errors.append(f"key=...{key[-6:]}: {e}")
            continue  # Try next key

    print(f"LLM Scoring Error for '{title}': all keys failed: {errors}")
    return None
