import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import run_state


class RunStateTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            "task_id": "t-1", "goal": "ship", "constraints": ["stdlib"],
            "done_when": ["tests pass", "evidence recorded"], "base_revision": "abc123",
            "status": "running", "attempts": 0, "max_attempts": 3,
            "verification": [], "pending_actions": []
        }

    def valid(self):
        value = json.loads(json.dumps(self.state))
        run_state.validate_state(value)
        return value

    def test_valid_state_continues(self):
        self.assertEqual(run_state.advisory(self.valid())["next_step"], "continue")

    def test_missing_and_extra_schema_keys_fail(self):
        value = self.valid(); del value["goal"]
        with self.assertRaises(ValueError): run_state.validate_state(value)
        value = self.valid(); value["extra"] = 1
        with self.assertRaises(ValueError): run_state.validate_state(value)

    def test_malformed_json_and_wrong_nested_types(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{not json", encoding="utf-8")
            result = subprocess.run([sys.executable, "run_state.py", "--state", str(path)],
                                    cwd=Path(__file__).parent, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(json.loads(result.stdout)["valid"])
        value = self.valid(); value["verification"] = [{"criterion": "tests pass"}]
        with self.assertRaises(ValueError): run_state.validate_state(value)

    def test_bool_is_not_integer(self):
        for key in ("attempts", "max_attempts"):
            value = self.valid(); value[key] = True
            with self.assertRaises(ValueError): run_state.validate_state(value)

    def test_enum_types_fail_closed(self):
        for malformed in ([], {}, None, True, 1):
            value = self.valid(); value["status"] = malformed
            with self.assertRaises(ValueError): run_state.validate_state(value)
            value = self.valid()
            value["pending_actions"] = [{"action_id": "a", "outcome": malformed}]
            with self.assertRaises(ValueError): run_state.validate_state(value)

    def test_advisory_validates_direct_call(self):
        value = self.valid(); value["attempts"] = -1
        with self.assertRaises(ValueError): run_state.advisory(value)

    def test_bounds_and_attempt_order(self):
        for number in (0, 11, -1):
            value = self.valid(); value["max_attempts"] = number
            with self.assertRaises(ValueError): run_state.validate_state(value)
        value = self.valid(); value["attempts"] = 4
        with self.assertRaises(ValueError): run_state.validate_state(value)

    def test_completed_requires_all_passed_evidence(self):
        value = self.valid(); value["status"] = "completed"
        with self.assertRaises(ValueError): run_state.validate_state(value)
        value["verification"] = [
            {"criterion": "tests pass", "passed": True, "evidence": "ok"},
            {"criterion": "evidence recorded", "passed": False, "evidence": "no"},
        ]
        with self.assertRaises(ValueError): run_state.validate_state(value)

    def test_completed_stops(self):
        value = self.valid(); value["status"] = "completed"
        value["verification"] = [
            {"criterion": c, "passed": True, "evidence": "observed"}
            for c in value["done_when"]
        ]
        run_state.validate_state(value)
        self.assertEqual(run_state.advisory(value)["next_step"], "stop")

    def test_unknown_action_inspection_forbids_replay(self):
        value = self.valid(); value["pending_actions"] = [{"action_id": "a1", "outcome": "unknown"}]
        self.assertEqual(run_state.advisory(value)["next_step"], "verify_existing_outcome")
        self.assertIn("do not replay", run_state.advisory(value)["reason"])

    def test_pending_has_priority_over_blocked_and_budget(self):
        value = self.valid(); value["status"] = "blocked"; value["attempts"] = 3
        value["pending_actions"] = [{"action_id": "a1", "outcome": "pending"}]
        self.assertEqual(run_state.advisory(value)["next_step"], "verify_existing_outcome")

    def test_exhausted_budget_stops(self):
        value = self.valid(); value["attempts"] = value["max_attempts"]
        self.assertEqual(run_state.advisory(value)["next_step"], "stop")

    def test_duplicate_ids_and_criteria_fail(self):
        value = self.valid(); value["pending_actions"] = [
            {"action_id": "a", "outcome": "succeeded"},
            {"action_id": "a", "outcome": "failed"}]
        with self.assertRaises(ValueError): run_state.validate_state(value)
        value = self.valid(); value["verification"] = [
            {"criterion": "tests pass", "passed": True, "evidence": "x"},
            {"criterion": "tests pass", "passed": True, "evidence": "y"}]
        with self.assertRaises(ValueError): run_state.validate_state(value)

    def test_cli_unicode_path_and_utf8(self):
        value = self.valid(); value["goal"] = "réussir"
        with tempfile.TemporaryDirectory(prefix="state space ") as directory:
            path = Path(directory) / "état résumé.json"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, "run_state.py", "--state", str(path)],
                                    cwd=Path(__file__).parent, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["next_step"], "continue")


if __name__ == "__main__":
    unittest.main()
