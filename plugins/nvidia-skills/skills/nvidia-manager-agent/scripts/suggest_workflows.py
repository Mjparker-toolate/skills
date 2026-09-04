#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Rank bundled (and optional live) workflows against a user goal.

Prints a JSON object with a `suggestions` array. Does not install skills.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9]+")


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


def score_workflow(goal_tokens: set[str], item: dict) -> tuple[int, str]:
    haystacks = [
        item.get("id") or "",
        item.get("skill") or "",
        item.get("title") or "",
        item.get("when") or "",
        item.get("kind") or "",
        " ".join(item.get("triggers") or []),
    ]
    blob = " ".join(str(h) for h in haystacks)
    item_tokens = tokenize(blob)
    overlap = goal_tokens & item_tokens
    score = 0
    for token in overlap:
        # Prefer distinctive tokens over ultra-common ones.
        if token in {"the", "and", "for", "with", "this", "that", "from"}:
            continue
        score += 3 if len(token) >= 5 else 1
        if token in tokenize(item.get("id") or "") or token in tokenize(
            item.get("skill") or ""
        ):
            score += 4
        if token in tokenize(" ".join(item.get("triggers") or [])):
            score += 2

    kind = (item.get("kind") or "").lower()
    if "loop" in goal_tokens or "iterate" in goal_tokens or "until" in goal_tokens:
        if kind == "loop":
            score += 5
    if "train" in goal_tokens or "agent" in goal_tokens or "playbook" in goal_tokens:
        if kind == "train":
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
    ranked: list[tuple[int, dict, str]] = []
    for item in merge_workflows(bundled, live):
        score, why = score_workflow(goal_tokens, item)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--live-catalog", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=5)
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
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
