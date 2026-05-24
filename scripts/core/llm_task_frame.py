from typing import Any


def task_frame_prompt_contract() -> str:
    return """
新增 task_frames 字段，表示 Student Task Frames。每条文档可以输出 0 个、1 个或多个 task frame。
访问受限、敏感或低证据页面不得生成具体行动任务；不确定字段填 null 或空数组，不得编造 deadline、location、action。

task_frames[i] schema:
{
  "task_id": "留空或稳定 id",
  "doc_id": "输入文档 id",
  "task_type": "application|schedule|result_check|download|opportunity|read",
  "who": {"audience": [], "college": [], "grade": [], "major": [], "class_name": []},
  "what": "学生事务任务名称",
  "action": {"required": true, "verb": "提交", "object": "材料", "summary": "证据支持的一句话"},
  "time": {"published_at": null, "deadline": null, "lifecycle": "active|upcoming|expired|evergreen|unknown", "urgency_days": null},
  "materials": [{"name": "附件名", "role": "申请表", "required": true, "sensitive": false}],
  "location": {"place": null, "online": null, "contact": null},
  "source": {"source_id": "源 id", "channel_id": "栏目 id", "authority": 0.9, "official": true},
  "evidence": [{"field": "deadline", "text": "原文证据短句"}],
  "risk": {"sensitive": false, "restricted": false, "low_evidence": false, "review_required": false},
  "confidence": 0.88
}
"""


def public_task_frames(result: dict[str, Any]) -> list[dict[str, Any]]:
    frames = result.get("task_frames", [])
    return frames if isinstance(frames, list) else []
