#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Initialize or revise a specialist agent playbook and append training_log.jsonl.

This is playbook training, not GPU weight training.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_ACTIONS = ("init", "revise", "record-eval")
NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

PLAYBOOK_TEMPLATE = """---
name: {name}
description: {goal}
---

# {title}

## Purpose

Specialist playbook trained by nvidia-manager-agent for: {goal}

## When to invoke

- The manager loop (or a user) needs this specialist for the goal above.

## When not to invoke

- The request is a different specialty.
- The work belongs to a product NVIDIA skill; hand off instead of reimplementing it.
- The user asked for GPU/RL weight training; do not treat this playbook as a trainer job.

## Instructions

1. Read this playbook completely.
2. Re-read the manager goal and current `{workspace_hint}` artifacts from disk.
3. Do the smallest next action that advances the goal.
4. Write results to disk; return paths, not large payloads.

## Success criteria

- Observable checks from the manager success criteria and any eval ids recorded below.

## Training history

- {ts} — {action}: playbook {action_verb} by nvidia-manager-agent.
"""


def playbook_path(workspace: Path, agent_name: str) -> Path:
    return workspace / "agents" / f"{agent_name}.md"


def training_log_path(workspace: Path) -> Path:
    return workspace / ".nvidia-manager" / "training_log.jsonl"


def title_from_name(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def append_history(text: str, bullet: str) -> str:
    marker = "## Training history\n"
    if marker not in text:
        return text.rstrip() + "\n\n" + marker + "\n" + bullet + "\n"
    prefix, rest = text.split(marker, 1)
    return prefix + marker + bullet + "\n" + rest.lstrip("\n")


def append_log(workspace: Path, payload: dict) -> Path:
    path = training_log_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--action", required=True, choices=VALID_ACTIONS)
    parser.add_argument("--notes", default=None)
    parser.add_argument("--eval-json", type=Path, default=None)
    args = parser.parse_args(argv)

    name = args.agent_name.strip()
    if not NAME_RE.match(name):
        print(
            "error: --agent-name must be lowercase kebab-case "
            "(e.g. usd-optimizer)",
            file=sys.stderr,
        )
        return 2

    workspace = args.workspace.expanduser().resolve()
    dest = playbook_path(workspace, name)
    ts = datetime.now(timezone.utc).isoformat()
    eval_path = (
        str(args.eval_json.expanduser().resolve()) if args.eval_json else None
    )

    if args.action == "init":
        if dest.exists():
            print(
                f"error: {dest} already exists; use --action revise",
                file=sys.stderr,
            )
            return 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            PLAYBOOK_TEMPLATE.format(
                name=name,
                goal=args.goal.strip(),
                title=title_from_name(name),
                workspace_hint=".nvidia-manager/",
                ts=ts,
                action="init",
                action_verb="created",
            ),
            encoding="utf-8",
        )
    elif args.action == "revise":
        if not dest.is_file():
            print(f"error: playbook not found: {dest}", file=sys.stderr)
            return 1
        note = args.notes or "revision without notes"
        text = dest.read_text(encoding="utf-8")
        dest.write_text(
            append_history(text, f"- {ts} — revise: {note}"),
            encoding="utf-8",
        )
    else:  # record-eval
        if args.eval_json is None:
            print("error: --eval-json is required for record-eval", file=sys.stderr)
            return 2
        eval_file = args.eval_json.expanduser().resolve()
        if not eval_file.is_file():
            print(f"error: eval file not found: {eval_file}", file=sys.stderr)
            return 1
        try:
            data = json.loads(eval_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"error: invalid eval JSON: {exc}", file=sys.stderr)
            return 1
        n_tasks = len(data) if isinstance(data, list) else 1
        if dest.is_file():
            text = dest.read_text(encoding="utf-8")
            dest.write_text(
                append_history(
                    text,
                    f"- {ts} — record-eval: {n_tasks} task(s) from {eval_file}",
                ),
                encoding="utf-8",
            )

    log_path = append_log(
        workspace,
        {
            "ts": ts,
            "action": args.action,
            "agent_name": name,
            "playbook": str(dest),
            "goal": args.goal.strip(),
            "notes": args.notes,
            "eval_json": eval_path,
        },
    )
    print(json.dumps({"playbook": str(dest), "training_log": str(log_path)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
