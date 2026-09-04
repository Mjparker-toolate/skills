#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Rank bundled (and optional live) workflows against a user goal.

Prints Manager Plan rows (`--format plan`, default) or a JSON object with a
`suggestions` array (`--format json`). Does not install skills.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_TOKENS = frozenset({"the", "and", "for", "with", "this", "that", "from"})
LOOP_TOKENS = frozenset({"loop", "iterate", "until"})
TRAIN_TOKENS = frozenset({"train", "agent", "playbook"})


def tokenize(text: str) -> set[str]:
    return {t for t in TOKEN_RE.findall(text.lower()) if len(t) > 1}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def workflows_from_bundled(data: Any) -> list[dict]:
    items = data.get("workflows") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ValueError("bundled catalog must be an object with a workflows array")
    out = []
    for item in items:
        if isinstance(item, dict) and item.get("id"):
            out.append(item)
    return out


def workflows_from_live(data: Any) -> list[dict]:
    """Accept skills.sh.json groupings or a flat {skills: [...]} / list dump."""
    found: list[dict] = []

    if isinstance(data, dict) and "groupings" in data:
        for group in data.get("groupings") or []:
            if not isinstance(group, dict):
                continue
            group_title = group.get("title") or ""
            for name in group.get("skills") or []:
                if not isinstance(name, str) or not name.strip():
                    continue
                found.append(
                    {
                        "id": name.strip(),
                        "kind": "skill",
                        "skill": name.strip(),
                        "title": name.strip(),
                        "when": group_title,
                        "triggers": [name.strip().replace("-", " "), group_title],
                        "first_prompt": f"Use the {name.strip()} skill for this task.",
                        "install_hint": (
                            f"npx skills add nvidia/skills --skill {name.strip()} "
                            "--global --yes"
                        ),
                    }
                )
        return found

    names: list[str] = []
    if isinstance(data, dict) and isinstance(data.get("skills"), list):
        for entry in data["skills"]:
            if isinstance(entry, str):
                names.append(entry)
            elif isinstance(entry, dict):
                name = entry.get("name") or entry.get("id")
                if isinstance(name, str):
                    names.append(name)
    elif isinstance(data, list):
        for entry in data:
            if isinstance(entry, str):
                names.append(entry)
            elif isinstance(entry, dict):
                name = entry.get("name") or entry.get("id")
                if isinstance(name, str):
                    names.append(name)

    for name in names:
        slug = name.strip()
        if not slug:
            continue
        found.append(
            {
                "id": slug,
                "kind": "skill",
                "skill": slug,
                "title": slug,
                "when": "",
                "triggers": [slug.replace("-", " ")],
                "first_prompt": f"Use the {slug} skill for this task.",
                "install_hint": (
                    f"npx skills add nvidia/skills --skill {slug} --global --yes"
                ),
            }
        )
    return found


def score_workflow(
    goal_tokens: set[str], wants_loop: bool, wants_train: bool, item: dict
) -> tuple[int, str]:
    slug_text = f"{item.get('id') or ''} {item.get('skill') or ''}"
    trigger_text = " ".join(str(t) for t in item.get("triggers") or [])
    kind = str(item.get("kind") or "").lower()

    # One scan over every field decides whether this row is worth more work.
    # Most rows in a full catalog dump miss entirely and stop here.
    item_tokens = tokenize(
        " ".join(
            (
                slug_text,
                trigger_text,
                str(item.get("title") or ""),
                str(item.get("when") or ""),
                kind,
            )
        )
    )
    # Ultra-common tokens match everything, so they neither score nor explain.
    overlap = (goal_tokens & item_tokens) - STOP_TOKENS

    score = 0
    if overlap:
        # Slug and trigger hits outrank prose hits, so those two fields get
        # their own scan — once per row, not once per matched token.
        slug_tokens = tokenize(slug_text)
        trigger_tokens = tokenize(trigger_text)
        for token in overlap:
            score += 3 if len(token) >= 5 else 1
            if token in slug_tokens:
                score += 4
            if token in trigger_tokens:
                score += 2

    if wants_loop and kind == "loop":
        score += 5
    if wants_train and kind == "train":
        score += 5

    why_bits = sorted(overlap)
    why = (
        "matched: " + ", ".join(why_bits[:8])
        if why_bits
        else "weak lexical overlap; included as a catalog candidate"
    )
    return score, why


def merge_workflows(bundled: list[dict], live: list[dict]) -> list[dict]:
    """Live slugs fill gaps; bundled rows win on the same id (richer metadata)."""
    by_id: dict[str, dict] = {}
    for item in live:
        wid = str(item.get("id") or "").strip()
        if wid:
            by_id[wid] = dict(item)
    for item in bundled:
        wid = str(item.get("id") or "").strip()
        if wid:
            by_id[wid] = dict(item)
    return list(by_id.values())


def rank(goal: str, bundled: list[dict], live: list[dict], limit: int) -> list[dict]:
    goal_tokens = tokenize(goal)
    wants_loop = bool(goal_tokens & LOOP_TOKENS)
    wants_train = bool(goal_tokens & TRAIN_TOKENS)
    ranked: list[tuple[int, dict, str]] = []
    for item in merge_workflows(bundled, live):
        score, why = score_workflow(goal_tokens, wants_loop, wants_train, item)
        ranked.append((score, item, why))
    ranked.sort(key=lambda row: (-row[0], str(row[1].get("id") or "")))
    suggestions = []
    for score, item, why in ranked:
        if score <= 0:
            continue
        suggestions.append(
            {
                "id": item.get("id"),
                "kind": item.get("kind") or "skill",
                "skill": item.get("skill") or item.get("id"),
                "title": item.get("title") or item.get("id"),
                "score": score,
                "why": why,
                "first_prompt": item.get("first_prompt") or "",
                "install_hint": item.get("install_hint") or "",
            }
        )
        if len(suggestions) >= limit:
            break
    return suggestions


def format_plan(payload: dict) -> str:
    """Render the Manager Plan rows described in references/workflow-suggestion.md.

    The manager pastes these lines straight into the plan, so the script emits
    the final wording instead of JSON the agent has to restate.
    """
    lines: list[str] = []
    suggestions = payload["suggestions"]
    if suggestions:
        lines.append("Suggested workflows (highest first):")
        for position, row in enumerate(suggestions, start=1):
            lines.append(
                f"{position}. {row['id']} ({row['kind']}, skill={row['skill']}, "
                f"score={row['score']}) — {row['why']}"
            )
            if row["first_prompt"]:
                lines.append(f"   First prompt: {row['first_prompt']}")
            if row["install_hint"]:
                lines.append(f"   Install (ask first): {row['install_hint']}")
    else:
        lines.append(
            "Suggested workflows: none matched. Ask the user to restate the goal "
            "or name a skill; do not invent a slug."
        )
    checked = "yes" if payload["live_catalog_checked"] else "no (bundled index only)"
    lines.append(f"Live catalog checked?: {checked}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--live-catalog", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--format",
        choices=("plan", "json"),
        default="plan",
        dest="output_format",
        help="plan: Manager Plan rows (default). json: full objects for tooling.",
    )
    args = parser.parse_args(argv)

    if args.limit < 1:
        print("error: --limit must be >= 1", file=sys.stderr)
        return 2

    catalog_path = args.catalog.expanduser().resolve()
    if not catalog_path.is_file():
        print(f"error: catalog not found: {catalog_path}", file=sys.stderr)
        return 1

    try:
        bundled = workflows_from_bundled(load_json(catalog_path))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: failed to read bundled catalog: {exc}", file=sys.stderr)
        return 1

    live: list[dict] = []
    live_checked = False
    if args.live_catalog is not None:
        live_path = args.live_catalog.expanduser().resolve()
        if not live_path.is_file():
            print(f"error: live catalog not found: {live_path}", file=sys.stderr)
            return 1
        try:
            live = workflows_from_live(load_json(live_path))
            live_checked = True
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"error: failed to read live catalog: {exc}", file=sys.stderr)
            return 1

    suggestions = rank(args.goal, bundled, live, args.limit)
    payload = {
        "goal": args.goal,
        "live_catalog_checked": live_checked,
        "suggestions": suggestions,
    }
    if args.output_format == "json":
        json.dump(payload, sys.stdout, indent=2)
    else:
        sys.stdout.write(format_plan(payload))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
