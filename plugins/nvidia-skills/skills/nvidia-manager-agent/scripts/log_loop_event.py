#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Append one loop event to loop_log.jsonl with a monotonic seq from disk.

Prints the protocol status line so the caller can echo it verbatim; pass
--json when a caller needs the stored event object instead.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

VALID_STAGES = ("plan", "execute", "evaluate", "decide", "stop")
VALID_STATUSES = ("ok", "error", "continue", "done")


def next_seq(log_path: Path) -> int:
    if not log_path.is_file():
        return 1
    seq = 0
    with log_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("seq"), int):
                seq = max(seq, obj["seq"])
    return seq + 1


def status_line(event: dict) -> str:
    """The one line references/loop-protocol.md requires after every stage."""
    return (
        f"manager iter={event['iteration']} stage={event['stage']} "
        f"status={event['status']} seq={event['seq']} — {event['summary']}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-path", required=True, type=Path)
    parser.add_argument("--iteration", required=True, type=int)
    parser.add_argument("--stage", required=True, choices=VALID_STAGES)
    parser.add_argument("--status", required=True, choices=VALID_STATUSES)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--duration-sec", type=int, default=None)
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print the stored event object instead of the status line.",
    )
    args = parser.parse_args(argv)

    if args.iteration < 0:
        print("error: --iteration must be >= 0", file=sys.stderr)
        return 2

    log_path = args.log_path.expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "seq": next_seq(log_path),
        "iteration": args.iteration,
        "stage": args.stage,
        "status": args.status,
        "summary": args.summary,
        "duration_sec": args.duration_sec,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")
    if args.as_json:
        print(json.dumps(event))
    else:
        print(status_line(event))
    return 0


if __name__ == "__main__":
    sys.exit(main())
