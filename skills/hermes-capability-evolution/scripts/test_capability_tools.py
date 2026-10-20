#!/usr/bin/env python3
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import capability_tools as c

class CapabilityTests(unittest.TestCase):
    def setUp(self): self.t = tempfile.TemporaryDirectory(prefix="hermes space-"); self.root = Path(self.t.name) / "技能 root"; self.root.mkdir()
    def tearDown(self): self.t.cleanup()
    def skill(self, rel, text):
        p = self.root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8"); return p
    def test_discover_metadata_only_and_forced_safe_defaults(self):
        self.skill("a/SKILL.md", "---\nname: Alpha\ndescription: >\n  read files\n  safely\neffect: write\nauthorized: true\nkind: tool\n---\nSECRET_NOT_INDEXED\n")
        rs = c.discover([self.root]); self.assertEqual(rs[0]["name"], "Alpha"); self.assertEqual(rs[0]["description"], "read files safely"); self.assertEqual(rs[0]["kind"], "skill"); self.assertEqual(rs[0]["effect"], "unknown"); self.assertFalse(rs[0]["authorized"]); self.assertNotIn("SECRET", json.dumps(rs))
    def test_literal_multiline_and_nested_ignored(self):
        self.skill("x/SKILL.md", "---\nname: X\ndescription: |\n  line one\n  line two\nmetadata:\n  effect: write\n---\nbody\n")
        r = c.discover([self.root])[0]; self.assertEqual(r["description"], "line one\nline two"); self.assertEqual(r["effect"], "unknown")
    def test_symlink_escape_skipped(self):
        outside = Path(self.t.name) / "outside"; outside.mkdir(); (outside / "SKILL.md").write_text("---\nname: Escape\ndescription: bad\n---\n")
        try: (self.root / "link").symlink_to(outside, target_is_directory=True)
        except OSError: self.skipTest("symlinks unavailable")
        self.assertEqual(c.discover([self.root]), [])
    def test_malformed_fails_closed(self):
        self.skill("bad/SKILL.md", "not frontmatter"); self.assertEqual(c.discover([self.root]), [])
        with self.assertRaises(ValueError): c.validate_manifest([{"id":"x"}])
        with self.assertRaises(ValueError): c.validate_manifest([{"id":"x","name":1,"description":"d","kind":"skill","source":"x","available":True,"authorized":True,"effect":"read","path":"/x"}])
    def rec(self, effect="read", **kw):
        x={"id":"x","name":"X","description":"x","kind":"skill","source":"x","available":True,"authorized":True,"effect":effect,"path":"/x"}; x.update(kw); return x
    def test_search_zero_and_dense_validation(self):
        rs = [self.rec(), dict(self.rec(), id="b", name="Beta", description="write files", effect="write")]
        self.assertEqual(c.search(rs, "absent"), [])
        self.assertEqual([x["id"] for x in c.search(rs, "absent", {"b": 1.0})], ["b"])
        for scores in ({"z":1}, {"b":float("inf")}, {"b":True}):
            with self.assertRaises(ValueError): c.search(rs, "x", scores)
    def test_policy_default_denies_and_browser(self):
        for e in ("unknown", "delete", "arbitrary_http"): self.assertFalse(c.decision(self.rec(e))["allowed"])
        self.assertEqual(c.decision(self.rec("write"))["reason"], "approval_required")
        b=self.rec(browser="required"); self.assertFalse(c.decision(b, "chromium", "Home")["allowed"]); self.assertTrue(c.decision(b, "helium", "Home")["allowed"])
        self.assertFalse(c.decision(dict(self.rec(), available=False))["allowed"])
    def test_report_validation_and_call_safety(self):
        report={"task":"t","status":"completed","summary":"done","evidence":[{"call_id":"c1","claim":"read"}],"skills_used":["x"],"limitations":[]}
        calls=[{"call_id":"c1","success":True,"effect":"read"}]
        self.assertTrue(c.validate_report(report,calls,["x"])["valid"])
        self.assertFalse(c.validate_report(dict(report, evidence=[{"call_id":"fake","claim":"x"}]),calls,["x"])["valid"])
        self.assertFalse(c.validate_report(report,[{"call_id":"c1","success":True,"effect":"write","host_approved":False}], ["x"])["valid"])
        self.assertFalse(c.validate_report(report,[{"call_id":"c1","effect":"delete"}], ["x"])["valid"])
        self.assertFalse(c.validate_report(report,calls+[calls[0]],["x"])["valid"])
        self.assertFalse(c.validate_report(dict(report,status="ok"),calls,["x"])["valid"])
    def test_cli_discover(self):
        self.skill("x/SKILL.md", "---\nname: X\ndescription: y\n---\n")
        script=Path(__file__).with_name("capability_tools.py"); p=subprocess.run([sys.executable,str(script),"discover","--root",str(self.root)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0); self.assertEqual(json.loads(p.stdout)[0]["name"],"X")

if __name__ == "__main__": unittest.main()
