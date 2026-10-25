#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""The bootstrap hash must match the skills CLI, and --check must catch breaks.

`skills-lock.json` is consumed by `npx skills` (vercel-labs/skills). If our
hash disagrees with the CLI's, every freshly bootstrapped skill looks locally
modified and `skills update` starts treating clean installs as dirty. The CLI
sorts paths with JavaScript `localeCompare` (ICU root collation), which is not
byte order, so the ordering tests below pin the cases where the two disagree:

  * `_` sorts before `-` before `.`  -> `ext_pb2_reference.py` before `ext.proto`
  * letters compare case-insensitively at the primary level
    -> `references/...` before `SKILL.md`

The golden hash was produced by running the CLI's own `computeSkillFolderHash`
against the same fixture under Node, so it is an independent oracle rather
than a value this implementation generated for itself.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bootstrap_skills as bs  # noqa: E402

# Derived from the module under test so this stays correct if the test moves.
REPO_ROOT = Path(bs.__file__).resolve().parents[2]

# Fixture whose filenames exercise every collation rule that differs from
# byte order. Values are the file contents.
FIXTURE = {
    "SKILL.md": "---\nname: demo\n---\nbody\n",
    "skill-card.md": "card\n",
    "skill_manifest.yaml": "manifest\n",
    "references/ext.proto": "proto\n",
    "references/ext_pb2_reference.py": "py\n",
    "references/Makefile_custom": "make\n",
}

# Order and digest produced by the skills CLI's computeSkillFolderHash under
# Node for the fixture above.
EXPECTED_ORDER = [
    "references/ext_pb2_reference.py",
    "references/ext.proto",
    "references/Makefile_custom",
    "skill_manifest.yaml",
    "skill-card.md",
    "SKILL.md",
]
GOLDEN_HASH = "9d51fc097d9e8ef69014804ef0c606119525c74f9e559139a806971c751668e6"

# Bootstrapped by this change; their content is pristine, so the recorded
# hash must still match what is on disk.
NEWLY_BOOTSTRAPPED = ("apify-ultimate-scraper", "amplify-workflow")


def write_fixture(root: Path, files: dict[str, str]) -> Path:
    for relative_path, content in files.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return root


class CollationTests(unittest.TestCase):
    """Path ordering must reproduce ICU root collation, not byte order."""

    def test_fixture_order_matches_the_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = write_fixture(Path(tmp) / "demo", FIXTURE)
            self.assertEqual(bs.collect_files(skill), EXPECTED_ORDER)

    def test_order_differs_from_byte_order(self):
        # Guards against someone "simplifying" collect_files to sorted().
        self.assertNotEqual(EXPECTED_ORDER, sorted(EXPECTED_ORDER))

    def test_underscore_sorts_before_hyphen_before_dot(self):
        key = bs._collation_key
        self.assertLess(key("a_b"), key("a-b"))
        self.assertLess(key("a-b"), key("a.b"))

    def test_letters_outrank_punctuation_and_digits(self):
        key = bs._collation_key
        self.assertLess(key("."), key("0"))
        self.assertLess(key("0"), key("a"))

    def test_case_is_a_tertiary_difference(self):
        key = bs._collation_key
        # 'B' outranks 'a' on the primary level despite a lower code point.
        self.assertLess(key("a"), key("B"))
        # Same letters: lowercase first.
        self.assertLess(key("a"), key("A"))

    def test_unmodelled_characters_are_reported(self):
        self.assertEqual(bs.collation_warnings(["a.md", "b.md"]), [])
        self.assertEqual(bs.collation_warnings(["café.md"]), ["café.md"])


class FolderHashTests(unittest.TestCase):
    def test_matches_golden_hash_from_the_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = write_fixture(Path(tmp) / "demo", FIXTURE)
            self.assertEqual(bs.compute_skill_folder_hash(skill), GOLDEN_HASH)

    def test_hash_covers_path_names_not_just_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = write_fixture(Path(tmp) / "a", FIXTURE)
            renamed = dict(FIXTURE)
            renamed["references/ext2.proto"] = renamed.pop("references/ext.proto")
            b = write_fixture(Path(tmp) / "b", renamed)
            self.assertNotEqual(
                bs.compute_skill_folder_hash(a), bs.compute_skill_folder_hash(b)
            )

    def test_excluded_directories_do_not_affect_the_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = write_fixture(Path(tmp) / "demo", FIXTURE)
            before = bs.compute_skill_folder_hash(skill)
            for excluded in bs.HASH_EXCLUDED_DIRS:
                (skill / excluded).mkdir()
                (skill / excluded / "junk").write_text("junk\n", encoding="utf-8")
            self.assertEqual(bs.compute_skill_folder_hash(skill), before)

    def test_symlinks_are_skipped_like_node_dirents(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = write_fixture(Path(tmp) / "demo", FIXTURE)
            before = bs.compute_skill_folder_hash(skill)
            (skill / "alias.md").symlink_to(skill / "SKILL.md")
            self.assertEqual(bs.compute_skill_folder_hash(skill), before)


class AddTests(unittest.TestCase):
    """`--add` must write all three artifacts so `--check` passes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / bs.AGENTS_SKILLS_DIR).mkdir(parents=True)
        (self.root / ".claude/skills").mkdir(parents=True)
        bs.write_lock(self.root, {"version": 1, "skills": {}})
        self.src = write_fixture(self.root / "src" / "demo", FIXTURE)
        self.addCleanup(self.tmp.cleanup)

    def bootstrap(self, name="demo"):
        return bs.add(
            self.root, name, self.src, "acme/plugins", "skills/demo/SKILL.md"
        )

    def test_add_writes_content_lock_entry_and_symlink(self):
        self.assertEqual(self.bootstrap(), [])

        entry = bs.load_lock(self.root)["skills"]["demo"]
        self.assertEqual(entry["source"], "acme/plugins")
        self.assertEqual(entry["sourceType"], "github")
        self.assertEqual(entry["skillPath"], "skills/demo/SKILL.md")
        self.assertEqual(entry["computedHash"], GOLDEN_HASH)

        link = self.root / ".claude/skills/demo"
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), "../../.agents/skills/demo")
        self.assertTrue((link / "SKILL.md").is_file())

        self.assertEqual(bs.check(self.root), ([], []))

    def test_add_refuses_to_clobber_without_force(self):
        self.bootstrap()
        errors = self.bootstrap()
        self.assertTrue(errors)
        self.assertIn("--force", errors[0])

    def test_add_rejects_a_folder_without_skill_md(self):
        empty = self.root / "src" / "empty"
        empty.mkdir(parents=True)
        errors = bs.add(
            self.root, "empty", empty, "acme/plugins", "skills/empty/SKILL.md"
        )
        self.assertTrue(errors)
        self.assertIn("no SKILL.md", errors[0])
        self.assertNotIn("empty", bs.load_lock(self.root)["skills"])

    def test_only_existing_agent_dirs_are_mirrored(self):
        self.bootstrap()
        self.assertFalse((self.root / ".cline/skills").exists())


class CheckTests(unittest.TestCase):
    """Each way the three artifacts can desynchronise must be an error."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / bs.AGENTS_SKILLS_DIR).mkdir(parents=True)
        (self.root / ".claude/skills").mkdir(parents=True)
        bs.write_lock(self.root, {"version": 1, "skills": {}})
        src = write_fixture(self.root / "src" / "demo", FIXTURE)
        bs.add(self.root, "demo", src, "acme/plugins", "skills/demo/SKILL.md")
        self.addCleanup(self.tmp.cleanup)

    def errors(self):
        return bs.check(self.root)[0]

    def warnings(self):
        return bs.check(self.root)[1]

    def test_clean_workspace_has_no_findings(self):
        self.assertEqual(bs.check(self.root), ([], []))

    def test_missing_symlink_is_an_error(self):
        (self.root / ".claude/skills/demo").unlink()
        self.assertTrue(
            any("no .claude/skills/demo symlink" in e for e in self.errors())
        )

    def test_missing_vendored_content_is_an_error(self):
        shutil.rmtree(self.root / bs.AGENTS_SKILLS_DIR / "demo")
        self.assertTrue(any("not vendored" in e for e in self.errors()))

    def test_vendored_without_lock_entry_is_an_error(self):
        lock = bs.load_lock(self.root)
        del lock["skills"]["demo"]
        bs.write_lock(self.root, lock)
        self.assertTrue(
            any("missing from skills-lock.json" in e for e in self.errors())
        )

    def test_symlink_pointing_at_a_regular_directory_is_an_error(self):
        link = self.root / ".claude/skills/demo"
        link.unlink()
        link.mkdir()
        self.assertTrue(any("is not a symlink" in e for e in self.errors()))

    def test_incomplete_lock_entry_is_an_error(self):
        lock = bs.load_lock(self.root)
        lock["skills"]["demo"]["source"] = ""
        bs.write_lock(self.root, lock)
        self.assertTrue(any("missing 'source'" in e for e in self.errors()))

    def test_edited_content_is_a_warning_not_an_error(self):
        skill_md = self.root / bs.AGENTS_SKILLS_DIR / "demo" / "SKILL.md"
        skill_md.write_text("locally patched\n", encoding="utf-8")
        self.assertEqual(self.errors(), [])
        self.assertTrue(any("content differs" in w for w in self.warnings()))


class RepositoryTests(unittest.TestCase):
    """The catalog checked into this repo must stay bootstrappable."""

    def test_repository_bootstrap_has_no_structural_breaks(self):
        errors, _ = bs.check(REPO_ROOT)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_newly_bootstrapped_skills_match_their_recorded_hash(self):
        locked = bs.load_lock(REPO_ROOT)["skills"]
        for name in NEWLY_BOOTSTRAPPED:
            with self.subTest(skill=name):
                self.assertIn(name, locked)
                skill_dir = REPO_ROOT / bs.AGENTS_SKILLS_DIR / name
                self.assertEqual(
                    bs.compute_skill_folder_hash(skill_dir),
                    locked[name]["computedHash"],
                )

    def test_lock_stays_sorted_and_round_trips(self):
        raw = (REPO_ROOT / bs.LOCK_PATH).read_text(encoding="utf-8")
        names = list(json.loads(raw)["skills"])
        self.assertEqual(names, sorted(names))

        with tempfile.TemporaryDirectory() as tmp:
            bs.write_lock(Path(tmp), json.loads(raw))
            self.assertEqual(
                (Path(tmp) / bs.LOCK_PATH).read_text(encoding="utf-8"), raw
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
