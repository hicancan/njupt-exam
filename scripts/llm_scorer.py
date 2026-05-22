import json
import time
import requests
from typing import Any, Dict, Optional
from indexer_config import GEMINI_API_KEY, REQUEST_TIMEOUT

_last_call_time = 0.0
_MIN_INTERVAL = 4.1  # Limit to ~14.6 RPM (Free tier is 15 RPM)

def analyze_document_with_llm(title: str, content: str, source_domain: str) -> Optional[Dict[str, Any]]:
    if not GEMINI_API_KEY:
        return None

    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    
    _last_call_time = time.time()

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
你是一个南邮校园助手系统的数据处理 AI。
请阅读以下校园通知/文档，提取关键信息并按照严格的 JSON 格式返回结果。

文档标题: {title}
来源域名: {source_domain}
正文片段: {content[:1500]}

请输出纯 JSON 格式：
{{
  "category": "只能从以下选项中选择一个: 考试|选课|竞赛|奖助|就业|讲座|生活|研究生|学院|项目|资料|公告",
  "tags": ["核心标签1", "核心标签2"], // 提取 2-5 个高度相关的简短关键词
  "importance_score": 0.85, // 0.0 到 1.0 之间的浮点数。与学生日常学习生活（停水停电、放假、选课、考试）越相关紧急，分数越高(0.8-1.0)；小众学术会议、不相关的教职工通知分数越低(0.1-0.4)。
  "summary": "...", // 用一句不超过 35 个字的大白话概括核心信息，对学生有用
  "is_student_facing": true // boolean, 如果是纯教职工文件（如党委巡视、工会发福利、采购招标），填 false；其他有用的填 true
}}
"""
    
    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        text_result = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text_result)
        
        if "category" not in result or "importance_score" not in result:
            return None
            
        return result
    except Exception as e:
        print(f"LLM Scoring Error for '{title}': {e}")
        return None
