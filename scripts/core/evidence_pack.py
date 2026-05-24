import re
from typing import Any, Dict, List

# Define keywords for candidate extraction
DEADLINE_KEYWORDS = ["截止", "于", "前", "之前", "报名时间", "提交时间", "申报时间", "截至"]
ACTION_KEYWORDS = ["申请", "报名", "提交", "下载", "填写", "报送", "参加", "缴费", "确认", "联系"]
MATERIAL_KEYWORDS = ["附件", "申请表", "汇总表", "证明", "成绩单", "证书", "材料", "扫描件"]
AUDIENCE_KEYWORDS = ["本科生", "研究生", "级", "学院", "专业", "班级", "全体学生"]
LOCATION_KEYWORDS = ["地点", "会议室", "教室", "线上", "邮箱", "系统", "平台", "办公室", "网址", "链接"]
CONTACT_KEYWORDS = ["联系人", "电话", "邮箱", "QQ", "群", "教务办", "学工办", "辅导员"]

def extract_candidates(sentences: List[str], keywords: List[str], max_count: int) -> List[str]:
    candidates = []
    pattern = re.compile("|".join(re.escape(k) for k in keywords))
    for s in sentences:
        if pattern.search(s):
            candidates.append(s.strip())
            if len(candidates) >= max_count:
                break
    return candidates

def build_evidence_pack(document: Dict[str, Any]) -> Dict[str, Any]:
    content = str(document.get("content", ""))
    
    # Split content into sentences roughly
    sentences = [s.strip() for s in re.split(r'([。！？\n])', content) if s.strip()]
    # Recombine delimiters with sentences
    combined_sentences = []
    for i in range(0, len(sentences)-1, 2):
        combined_sentences.append(sentences[i] + sentences[i+1])
    if len(sentences) % 2 != 0:
        combined_sentences.append(sentences[-1])
        
    lead_text = content[:800]
    tail_text = content[-500:] if len(content) > 1300 else ""
    
    deadline_c = extract_candidates(combined_sentences, DEADLINE_KEYWORDS, 10)
    action_c = extract_candidates(combined_sentences, ACTION_KEYWORDS, 10)
    material_c = extract_candidates(combined_sentences, MATERIAL_KEYWORDS, 10)
    audience_c = extract_candidates(combined_sentences, AUDIENCE_KEYWORDS, 10)
    location_c = extract_candidates(combined_sentences, LOCATION_KEYWORDS, 8)
    contact_c = extract_candidates(combined_sentences, CONTACT_KEYWORDS, 8)
    
    attachments = document.get("attachments", [])
    attachment_names = [str(a.get("name", "")) for a in attachments if isinstance(a, dict)]
    attachment_context = []
    if attachment_names:
        attachment_context.append("附件列表: " + ", ".join(attachment_names))
        # Look for sentences mentioning the attachments
        for s in combined_sentences:
            if "附件" in s or any(name in s for name in attachment_names):
                if s not in attachment_context:
                    attachment_context.append(s)
                    if len(attachment_context) > 10:
                        break

    rule_guard = document.get("rule_guard", {})
    if not isinstance(rule_guard, dict):
        rule_guard = {}

    return {
        "title": str(document.get("title", "")),
        "source": str(document.get("source_domain", "")),
        "channel": str(document.get("channel", "")),
        "published_at": str(document.get("published_at") or ""),
        "url": str(document.get("url", "")),
        "rule_guard": rule_guard,
        "content_slices": {
            "lead": lead_text,
            "deadline_candidates": deadline_c,
            "action_candidates": action_c,
            "material_candidates": material_c,
            "audience_candidates": audience_c,
            "location_candidates": location_c,
            "contact_candidates": contact_c,
            "attachment_context": attachment_context,
            "tail": tail_text
        },
        "attachments": attachments,
        "tables": [],
        "negative_signals": [],
        "source_expectations": {
            "expected_domains": [],
            "expected_intents": [],
            "student_value": 1.0
        }
    }
