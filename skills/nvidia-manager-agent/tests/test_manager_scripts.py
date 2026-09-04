#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for nvidia-manager-agent bundled scripts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
CATALOG = SKILL_ROOT / "references" / "workflow-catalog.json"


def run_script(name: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class InitManagerStateTests(unittest.TestCase):
    def test_writes_state_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            first = run_script(
                "init_manager_state.py",
                [
                    "--workspace",
                    str(workspace),
                    "--goal",
                    "iterate until evals pass",
                    "--mode",
                    "loop",
                    "--max-iterations",
                    "3",
                    "--success-criterion",
                    "all evals pass",
                ],
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            state_file = Path(first.stdout.strip())
            self.assertTrue(state_file.is_file())
            state = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(state["mode"], "loop")
            self.assertEqual(state["max_iterations"], 3)
            self.assertEqual(state["success_criteria"], ["all evals pass"])
            self.assertEqual(state["status"], "ready")
            self.assertIsNone(state["chosen_workflow"])

            second = run_script(
                "init_manager_state.py",
                [
                    "--workspace",
                    str(workspace),
                    "--goal",
                    "other",
                    "--mode",
                    "suggest",
                    "--max-iterations",
                    "1",
                ],
            )
            self.assertEqual(second.returncode, 1)
            self.assertIn("already exists", second.stderr)

            forced = run_script(
                "init_manager_state.py",
                [
                    "--workspace",
                    str(workspace),
                    "--goal",
                    "other",
                    "--mode",
                    "suggest",
                    "--max-iterations",
                    "1",
                    "--force",
                ],
            )
            self.assertEqual(forced.returncode, 0, forced.stderr)
            state = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(state["mode"], "suggest")
            self.assertEqual(state["goal"], "other")

    def test_rejects_nonpositive_iterations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_script(
                "init_manager_state.py",
                [
                    "--workspace",
                    tmp,
                    "--goal",
                    "x",
                    "--mode",
                    "loop",
                    "--max-iterations",
                    "0",
                ],
            )
            self.assertEqual(result.returncode, 2)


class SuggestWorkflowsTests(unittest.TestCase):
    def test_ranks_deft_loop_for_far_goal(self) -> None:
        result = run_script(
            "suggest_workflows.py",
            [
                "--goal",
                "Run a DEFT loop until ChangeNet FAR is low enough",
                "--catalog",
                str(CATALOG),
                "--limit",
                "3",
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["live_catalog_checked"])
        ids = [row["id"] for row in payload["suggestions"]]
        self.assertIn("tao-run-deft-aoi", ids)
        self.assertEqual(payload["suggestions"][0]["kind"], "loop")

    def test_ranks_train_kind_for_playbook_goal(self) -> None:
        result = run_script(
            "suggest_workflows.py",
            [
                "--goal",
                "Train an agent playbook specialist for OpenUSD review",
                "--catalog",
                str(CATALOG),
                "--limit",
                "5",
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        ids = [row["id"] for row in payload["suggestions"]]
        self.assertIn("playbook-specialist", ids)

    def test_live_catalog_merges_and_bundled_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            live = Path(tmp) / "live.json"
            live.write_text(
                json.dumps(
                    {
                        "groupings": [
                            {
                                "title": "Agentic AI",
                                "skills": ["tao-run-deft-aoi", "changenet-live-helper"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = run_script(
                "suggest_workflows.py",
                [
                    "--goal",
                    "DEFT AOI ChangeNet FAR loop",
                    "--catalog",
                    str(CATALOG),
                    "--live-catalog",
                    str(live),
                    "--limit",
                    "8",
                ],
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["live_catalog_checked"])
            by_id = {row["id"]: row for row in payload["suggestions"]}
            self.assertEqual(by_id["tao-run-deft-aoi"]["kind"], "loop")
            self.assertIn("changenet-live-helper", by_id)


class LogLoopEventTests(unittest.TestCase):
    def test_monotonic_seq_and_skips_bad_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "loop_log.jsonl"
            first = run_script(
                "log_loop_event.py",
                [
                    "--log-path",
                    str(log_path),
                    "--iteration",
                    "1",
                    "--stage",
                    "plan",
                    "--status",
                    "ok",
                    "--summary",
                    "first",
                ],
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(first.stdout)["seq"], 1)

            with log_path.open("a", encoding="utf-8") as handle:
                handle.write("not-json\n")

            second = run_script(
                "log_loop_event.py",
                [
                    "--log-path",
                    str(log_path),
                    "--iteration",
                    "1",
                    "--stage",
                    "execute",
                    "--status",
                    "ok",
                    "--summary",
                    "second",
                ],
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            event = json.loads(second.stdout)
            self.assertEqual(event["seq"], 2)
            self.assertEqual(event["stage"], "execute")
            lines = [
                json.loads(line)
                for line in log_path.read_text(encoding="utf-8").splitlines()
                if line.startswith("{")
            ]
            self.assertEqual([row["seq"] for row in lines], [1, 2])


class TrainAgentTests(unittest.TestCase):
    def test_init_revise_and_record_eval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            init = run_script(
                "train_agent.py",
                [
                    "--workspace",
                    str(workspace),
                    "--agent-name",
                    "usd-optimizer",
                    "--goal",
                    "Optimize OpenUSD scenes",
                    "--action",
                    "init",
                ],
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            payload = json.loads(init.stdout)
            playbook = Path(payload["playbook"])
            self.assertTrue(playbook.is_file())
            body = playbook.read_text(encoding="utf-8")
            self.assertIn("name: usd-optimizer", body)
            self.assertIn("## Training history", body)

            again = run_script(
                "train_agent.py",
                [
                    "--workspace",
                    str(workspace),
                    "--agent-name",
                    "usd-optimizer",
                    "--goal",
                    "Optimize OpenUSD scenes",
                    "--action",
                    "init",
                ],
            )
            self.assertEqual(again.returncode, 1)

            revise = run_script(
                "train_agent.py",
                [
                    "--workspace",
                    str(workspace),
                    "--agent-name",
                    "usd-optimizer",
                    "--goal",
                    "Optimize OpenUSD scenes",
                    "--action",
                    "revise",
                    "--notes",
                    "eval pos-002 failed: skipped approval gate",
                ],
            )
            self.assertEqual(revise.returncode, 0, revise.stderr)
            self.assertIn("eval pos-002", playbook.read_text(encoding="utf-8"))

            evals = workspace / "evals.json"
            evals.write_text(
                json.dumps(
                    [
                        {
                            "id": "pos-001",
                            "question": "optimize this usd stage",
                            "expected_skill": "usd-optimizer",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            recorded = run_script(
                "train_agent.py",
                [
                    "--workspace",
                    str(workspace),
                    "--agent-name",
                    "usd-optimizer",
                    "--goal",
                    "Optimize OpenUSD scenes",
                    "--action",
                    "record-eval",
                    "--eval-json",
                    str(evals),
                ],
            )
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            log_path = Path(json.loads(recorded.stdout)["training_log"])
            actions = [
                json.loads(line)["action"]
                for line in log_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(actions, ["init", "revise", "record-eval"])

    def test_rejects_unsafe_agent_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_script(
                "train_agent.py",
                [
                    "--workspace",
                    tmp,
                    "--agent-name",
                    "../evil",
                    "--goal",
                    "x",
                    "--action",
                    "init",
                ],
            )
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
