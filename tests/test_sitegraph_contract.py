import json
from pathlib import Path

from sitegraph_search import recall_documents


ROOT_DIR = Path(__file__).resolve().parents[1]
PUBLIC_INDEX_DIR = ROOT_DIR / "public" / "index"
BANNED_KEYS = {"llm", "llm_provider", "llm_schema_version", "semantic_mode", "task_frames"}
REQUIRED_QUERIES = [
    "校历",
    "慕课考试",
    "期末考试",
    "转专业",
    "规章制度",
    "办事流程",
    "学生相关文件及表格",
    "教务管理系统",
    "大创",
    "推免",
    "成绩",
    "附件1",
    "xlsx",
]


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def walk_keys(payload):
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield key
            yield from walk_keys(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from walk_keys(item)


def test_public_index_is_pure_sitegraph_contract():
    manifest = read_json(PUBLIC_INDEX_DIR / "manifest.json")
    assert manifest["strategy"] == "pure-sitegraph-code-search-v1"
    assert manifest["exam_vertical_preserved"] is True
    assert manifest["core_search"]["llm_in_core_path"] is False
    assert manifest["core_search"]["source_channel_production_enabled"] is False
    assert manifest["core_search"]["github_resource_production_enabled"] is False
    assert manifest["core_search"]["light_first_screen"] is True
    assert manifest["core_search"]["full_text_loading"] == "on_demand_by_shard"

    for stale in ("documents.json", "task_frames.json", "ontology.json"):
        assert not (PUBLIC_INDEX_DIR / stale).exists()

    assert not (BANNED_KEYS & set(walk_keys(manifest)))


def test_jwc_truth_counts_are_preserved():
    manifest = read_json(PUBLIC_INDEX_DIR / "manifest.json")
    truth_counts = manifest["sitegraph"]["truth_counts"]
    assert truth_counts["detail_pages"] == 6884
    assert truth_counts["attachments"] == 7905
    assert truth_counts["external_links"] == 426
    assert truth_counts["edges"] == 16311
    assert manifest["sitegraph"]["detail_page_records"] == truth_counts["detail_pages"]
    assert manifest["sitegraph"]["attachment_metadata_records"] == truth_counts["attachments"]
    assert manifest["sitegraph"]["external_link_records"] == truth_counts["external_links"]
    assert manifest["sitegraph"]["quality"]["errors"] == 0
    assert manifest["sitegraph"]["quality"]["all_discovered_urls_have_outcomes"] is True
    assert manifest["sitegraph"]["quality"]["attachment_policy"] == "metadata_only"
    assert manifest["sitegraph"]["quality"]["external_link_policy"] == "record_only"


def test_light_index_and_shards_have_no_legacy_fields():
    manifest = read_json(PUBLIC_INDEX_DIR / "manifest.json")
    doc_meta = read_json(PUBLIC_INDEX_DIR / "doc_meta.json")
    assert not (BANNED_KEYS & set(walk_keys(doc_meta)))
    assert all("content" not in item for item in doc_meta)

    for shard in manifest["sitegraph"]["full_shards"]:
        documents = read_json(ROOT_DIR / "public" / shard["path"])
        assert len(documents) == shard["count"]
        assert not (BANNED_KEYS & set(walk_keys(documents)))


def test_required_queries_return_results():
    failures = {}
    for query in REQUIRED_QUERIES:
        results = recall_documents(query, limit=5)
        if not results:
            failures[query] = []
        elif query == "教务管理系统" and not any("教务管理系统" in str(item.get("title", "")) for item in results):
            failures[query] = [item.get("title") for item in results]
    assert failures == {}
