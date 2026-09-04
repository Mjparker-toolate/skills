#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Create manager_state.json for an nvidia-manager-agent run.

Refuses to overwrite an existing state file unless --force is passed.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_MODES = ("suggest", "loop", "train")
STATE_VERSION = 1


def manager_dir(workspace: Path) -> Path:
    return workspace / ".nvidia-manager"


def state_path(workspace: Path) -> Path:
    return manager_dir(workspace) / "manager_state.json"


def build_state(
    workspace: Path,
    goal: str,
    mode: str,
    max_iterations: int,
    success_criteria: list[str],
) -> dict:
    return {
        "version": STATE_VERSION,
        "goal": goal,
        "mode": mode,
        "max_iterations": max_iterations,
        "iteration": 0,
        "status": "ready",
        "workspace": str(workspace.resolve()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "success_criteria": list(success_criteria),
        "chosen_workflow": None,
        "trained_agents": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--mode", required=True, choices=VALID_MODES)
    parser.add_argument("--max-iterations", required=True, type=int)
    parser.add_argument(
        "--success-criterion",
        action="append",
        default=[],
        dest="success_criteria",
        help="Repeatable. Observable stop condition.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing manager_state.json.",
    )
    args = parser.parse_args(argv)

    if args.max_iterations < 1:
        print("error: --max-iterations must be >= 1", file=sys.stderr)
        return 2

    workspace = args.workspace.expanduser().resolve()
    dest = state_path(workspace)
    if dest.exists() and not args.force:
        print(
            f"error: {dest} already exists; pass --force to replace it",
            file=sys.stderr,
        )
        return 1

    dest.parent.mkdir(parents=True, exist_ok=True)
    state = build_state(
        workspace,
        args.goal.strip(),
        args.mode,
        args.max_iterations,
        args.success_criteria,
    )
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    tmp.replace(dest)
    print(str(dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
