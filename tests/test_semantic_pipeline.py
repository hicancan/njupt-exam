import unittest
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
for path in (ROOT_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.core.semantic_pipeline import route_semantic_pipeline
from scripts.models.semantic_result import SemanticMode

class TestSemanticPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_now = datetime(2026, 5, 24, 12, 0, 0)
        self.base_entry = {
            "title": "测试公告",
            "content": "这是一个测试内容",
            "default_category": "公告",
            "source_weight": 1.0,
            "source_type": "department",
            "attachments": [],
            "published_at": "2026-05-24T10:00:00"
        }

    def test_route_semantic_pipeline_guarded(self):
        guard = {"restricted": True, "allow_llm": False}
        result = route_semantic_pipeline(self.base_entry, None, guard, {}, self.mock_now)
        self.assertEqual(result.semantic_mode, "guarded_metadata")

    def test_route_semantic_pipeline_heuristic_no_llm(self):
        guard = {"allow_llm": True}
        run_config = {"no_llm": True}
        result = route_semantic_pipeline(self.base_entry, None, guard, run_config, self.mock_now)
        self.assertEqual(result.semantic_mode, "heuristic")
        self.assertIn("heuristic_semantic", result.risk_flags)

    def test_route_semantic_pipeline_heuristic_degraded(self):
        guard = {"allow_llm": True}
        run_config = {"no_llm": False}
        result = route_semantic_pipeline(self.base_entry, None, guard, run_config, self.mock_now)
        self.assertEqual(result.semantic_mode, "heuristic_degraded")
        self.assertIn("llm_failed_heuristic_fallback", result.risk_flags)

    def test_route_semantic_pipeline_llm(self):
        guard = {"allow_llm": True}
        run_config = {"no_llm": False}
        llm_result = {
            "validated": {
                "category": "讲座",
                "domain": "lecture",
                "intent": "attend",
                "confidence": 0.9,
                "action_required": True,
                "deadline": "2026-05-30T00:00:00"
            },
            "raw_field_presence": {
                "category": True,
                "domain": True,
                "intent": True,
                "confidence": True,
                "action_required": True,
                "deadline": True
            },
        }
        result = route_semantic_pipeline(self.base_entry, llm_result, guard, run_config, self.mock_now)
        self.assertEqual(result.semantic_mode, "llm")
        self.assertEqual(result.category, "讲座")
        self.assertEqual(result.intent, "attend")
        self.assertEqual(result.field_sources["category"], "llm")
        self.assertEqual(result.field_sources["deadline"], "llm")

    def test_route_semantic_pipeline_llm_missing(self):
        guard = {"allow_llm": True}
        run_config = {"no_llm": False}
        llm_result = {
            "validated": {
                "confidence": 0.9,
                "action_required": False
            },
            "raw_field_presence": {
                "confidence": True,
                "action_required": True
            },
        }
        result = route_semantic_pipeline(self.base_entry, llm_result, guard, run_config, self.mock_now)
        self.assertEqual(result.semantic_mode, "llm")
        self.assertEqual(result.field_sources["category"], "display_mapping")
        self.assertEqual(result.field_sources["deadline"], "llm_missing")
        self.assertEqual(result.field_sources["domain"], "system_default")
        self.assertEqual(result.domain, "unknown")
        self.assertEqual(result.category, "公告")

if __name__ == '__main__':
    unittest.main()
