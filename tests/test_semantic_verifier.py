from scripts.core.semantic_verifier import verify_search_document


def base_document(**overrides):
    payload = {
        "id": "doc-1",
        "title": "关于学生报名竞赛的通知",
        "content": "请学生于2026年5月30日前提交申请表，联系人：025-12345678。",
        "evidence": ["请学生于2026年5月30日前提交申请表。"],
        "deadline": "2026-05-30T23:59:00+08:00",
        "action_required": True,
        "required_materials": ["申请表"],
        "attachments": [{"name": "申请表.docx", "url": "https://example.edu/a.docx"}],
        "risk_flags": [],
        "review_required": False,
        "rule_guard": {
            "restricted": False,
            "sensitive": False,
            "low_evidence": False,
            "allow_llm": True,
        },
        "task_frames": [{
            "task_id": "task-1",
            "doc_id": "doc-1",
            "source_mode": "generated_from_llm_fields",
            "task_type": "application",
            "what": "竞赛报名",
            "action": {"required": True, "verb": "报名", "object": "竞赛", "summary": "学生提交申请表。"},
            "time": {"published_at": None, "deadline": "2026-05-30T23:59:00+08:00", "lifecycle": "active", "urgency_days": 5},
            "materials": [{"name": "申请表", "required": True, "sensitive": False}],
            "location": {"place": None, "online": None, "contact": "025-12345678"},
            "evidence": [{"field": "action", "text": "请学生于2026年5月30日前提交申请表。"}],
            "risk": {"sensitive": False, "restricted": False, "low_evidence": False, "review_required": False},
        }],
    }
    payload.update(overrides)
    return payload


def test_verifier_keeps_grounded_deadline_action_and_materials():
    document = verify_search_document(base_document())

    assert document["deadline"] == "2026-05-30T23:59:00+08:00"
    assert document["task_frames"][0]["time"]["deadline"] == "2026-05-30T23:59:00+08:00"
    assert document["task_frames"][0]["materials"][0]["name"] == "申请表"
    assert "semantic_verifier" not in document


def test_verifier_removes_ungrounded_deadline_and_materials():
    document = verify_search_document(base_document(
        content="这是一条普通新闻，没有学生事项。",
        evidence=["普通新闻。"],
        attachments=[],
        required_materials=["申请表"],
    ))

    assert document["deadline"] is None
    assert document["task_frames"][0]["time"]["deadline"] is None
    assert document["task_frames"][0]["materials"] == []
    assert "semantic_verifier_modified" in document["risk_flags"]


def test_verifier_clears_task_frames_for_guarded_documents():
    document = verify_search_document(base_document(
        rule_guard={"restricted": True, "sensitive": False, "low_evidence": False, "allow_llm": False}
    ))

    assert document["task_frames"] == []
    assert document["semantic_verifier"]["removals"]["task_frames"] == 1
