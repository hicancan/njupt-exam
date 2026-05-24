from typing import Any


def task_frame_prompt_contract() -> str:
    return """
【严格行动判定原则】
1. 只有学生需要“主动去办理”某事（如申请、报名、缴费、系统确认、提交纸质材料等），action_required 才是 true。
2. 公示类、新闻类、宣讲预告、阅读类默认 action_required=false，除非文中明确要求学生“如无异议请签字确认”、“如有异议请发邮件申诉”。
3. 如果原文没有要求学生做任何特定动作，或者主体不是学生（例如“请各学院于5月1日报送...”是学院任务，不是学生任务），则 action_required=false。

【TaskFrames 生成原则】
1. task_frames 只用来描述“可执行的学生任务”，如果 action_required=false 或者只是信息通知，则 task_frames 必须为 []。不是所有的文档都需要 task_frames。
2. 如果存在多个子任务（例如大一选课、大二选课分开），可以拆分成多个 task frame，否则返回一个。

【严格证据与字段抽取原则】
1. 不得用标题推断 deadline。deadline 必须来自正文（或附件名附近）的明确文本，如果只有“下周五”之类的模糊描述，将明确的模糊词提取至 missing_reason，并设 deadline=null。
2. evidence 必须是一字不改地摘取原文短句！不得进行语义改写。
3. field_evidence 必须将证据细分到各自的字段（如 domain/intent/deadline 等）。
4. 如果找不到明确材料清单，不要随便把普通附件当成 required_materials；仅展示名单或结果的文档，materials 为空。
5. 所有不确定的字段、没有明确原文证据的字段一律填 null 或 []，并填写对应的 missing_reason。
6. 不得编造任何地点、截止日期、行动事项和资料清单。

task_frames[i] schema:
{
  "task_id": "留空",
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
