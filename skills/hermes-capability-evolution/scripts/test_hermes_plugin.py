"""Contract tests; no installed Hermes runtime is required or simulated as live."""
import importlib.util
import json
from pathlib import Path
import unittest


class PluginTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "__init__.py"
        spec = importlib.util.spec_from_file_location("capability_plugin_test", path)
        self.plugin = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.plugin)
        class Context:
            def __init__(self): self.tools = {}
            def register_tool(self, **kwargs): self.tools[kwargs["name"]] = kwargs
        self.ctx = Context()
        self.plugin.register(self.ctx)
        self.record = {"id": "sample", "name": "sample", "description": "search repository",
                       "kind": "tool", "source": "fixture", "available": True,
                       "authorized": True, "effect": "read", "path": "fixture"}

    def call(self, name, args):
        return json.loads(self.ctx.tools[name]["handler"](args, future_kwarg=True))

    def test_three_registered_tools(self):
        self.assertEqual(len(self.ctx.tools), 3)
        for name, entry in self.ctx.tools.items():
            self.assertEqual(name, entry["schema"]["name"])
            self.assertFalse(entry["schema"]["parameters"]["additionalProperties"])

    def test_search_handler(self):
        result = self.call("capability_search", {"records": [self.record], "query": "repository"})
        self.assertEqual(result[0]["id"], "sample")
        self.assertEqual(result[0]["match_mode"], "lexical-only")

    def test_write_requires_host_approval(self):
        self.record["effect"] = "write"
        self.record["approved"] = True
        result = self.call("capability_preflight", {"record": self.record})
        self.assertFalse(result["allowed"])
        self.assertEqual(result["reason"], "approval_required")

    def test_browser_policy(self):
        self.record["browser"] = "browser"
        self.assertFalse(self.call("capability_preflight", {"record": self.record,
                         "browser": "chrome", "profile": "Home"})["allowed"])
        self.assertTrue(self.call("capability_preflight", {"record": self.record,
                        "browser": "helium", "profile": "Home"})["allowed"])

    def test_report_reference_validation(self):
        report = {"task": "test", "status": "completed", "summary": "Observed a fixture",
                  "evidence": [{"call_id": "one", "claim": "Observed fixture"}],
                  "skills_used": [], "limitations": ["Mock-context wiring only"]}
        args = {"report": report, "calls": [{"call_id": "one", "success": True,
                "effect": "read"}], "installed": []}
        self.assertTrue(self.call("capability_report_check", args)["valid"])
        args["calls"] = []
        self.assertFalse(self.call("capability_report_check", args)["valid"])

    def test_errors_return_json_without_echoing_input(self):
        result = self.call("capability_search", {"unexpected": "sensitive-content"})
        self.assertEqual(result["error"], "invalid_input")
        self.assertNotIn("sensitive-content", json.dumps(result))


if __name__ == "__main__": unittest.main()
