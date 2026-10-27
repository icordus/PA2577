import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_deployment_http import validate_base_url, validate_responses


class DeploymentHTTPValidationTests(unittest.TestCase):
    def test_accepts_private_nodeport_url(self):
        self.assertEqual(validate_base_url("http://192.168.0.71:30081"), "http://192.168.0.71:30081")
        self.assertEqual(validate_base_url("http://127.0.0.1:30081/"), "http://127.0.0.1:30081")

    def test_rejects_non_private_or_non_nodeport_urls(self):
        invalid_urls = (
            "https://192.168.0.71:30081",
            "http://example.com:30081",
            "http://8.8.8.8:30081",
            "http://192.168.0.71:5000",
            "http://user:pass@192.168.0.71:30081",
            "http://192.168.0.71:30081/api/tasks",
            "http://192.168.0.71:30081/?target=elsewhere",
        )
        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_base_url(url)

    def test_accepts_matching_health_and_statistics(self):
        tasks = [
            {"id": 1, "title": "one", "completed": True},
            {"id": 2, "title": "two", "completed": False},
        ]
        statistics = {"total": 2, "completed": 1, "pending": 1}
        self.assertEqual(
            validate_responses({"status": "ok"}, {"status": "ok"}, tasks, statistics),
            statistics,
        )

    def test_rejects_mismatched_counters_and_boolean_counter_values(self):
        tasks = [{"completed": True}, {"completed": False}]
        for statistics in (
            {"total": 2, "completed": 0, "pending": 2},
            {"total": True, "completed": 1, "pending": 1},
            {"total": 2, "completed": 1, "pending": 1, "extra": 0},
        ):
            with self.subTest(statistics=statistics), self.assertRaises(ValueError):
                validate_responses({"status": "ok"}, {"status": "ok"}, tasks, statistics)

    def test_rejects_invalid_tasks_and_unhealthy_responses(self):
        invalid_cases = (
            ({"status": "bad"}, {"status": "ok"}, [], {"total": 0, "completed": 0, "pending": 0}),
            ({"status": "ok"}, {"status": "bad"}, [], {"total": 0, "completed": 0, "pending": 0}),
            ({"status": "ok"}, {"status": "ok"}, [{"completed": 1}], {"total": 1, "completed": 0, "pending": 1}),
        )
        for case in invalid_cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                validate_responses(*case)


if __name__ == "__main__":
    unittest.main(verbosity=2)
