import unittest
from datetime import datetime

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
            "category": "讲座",
            "domain": "campus_life",
            "intent": "attend",
            "confidence": 0.9,
            "action_required": True,
            "deadline": "2026-05-30T00:00:00"
        }
        result = route_semantic_pipeline(self.base_entry, llm_result, guard, run_config, self.mock_now)
        self.assertEqual(result.semantic_mode, "llm")
        self.assertEqual(result.category, "讲座")
        self.assertEqual(result.intent, "attend")
        self.assertEqual(result.field_sources["category"], "llm")
        self.assertEqual(result.field_sources["deadline"], "llm")

if __name__ == '__main__':
    unittest.main()
