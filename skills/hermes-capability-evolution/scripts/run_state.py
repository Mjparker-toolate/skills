#!/usr/bin/env python3
"""Validate bounded resumable task state and provide a non-executing next step."""
import argparse
import json
import sys
from pathlib import Path

STATUSES = {"pending", "running", "blocked", "completed", "failed"}
OUTCOMES = {"pending", "unknown", "succeeded", "failed"}
REQUIRED = {"task_id", "goal", "constraints", "done_when", "base_revision",
            "status", "attempts", "max_attempts", "verification", "pending_actions"}


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _strings(value, name):
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{name} must be a nonempty list of strings")
    if len(set(value)) != len(value):
        raise ValueError(f"{name} must not contain duplicates")


def validate_state(state):
    if not isinstance(state, dict):
        raise ValueError("state must be an object")
    if set(state) != REQUIRED:
        missing = sorted(REQUIRED - set(state))
        extra = sorted(set(state) - REQUIRED)
        raise ValueError(f"schema keys invalid; missing={missing}, extra={extra}")
    _text(state["task_id"], "task_id")
    _text(state["goal"], "goal")
    _strings(state["constraints"], "constraints")
    _strings(state["done_when"], "done_when")
    _text(state["base_revision"], "base_revision")
    if not isinstance(state["status"], str) or state["status"] not in STATUSES:
        raise ValueError("status is invalid")
    for name in ("attempts", "max_attempts"):
        value = state[name]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        if name == "attempts" and value < 0:
            raise ValueError("attempts must be >= 0")
        if name == "max_attempts" and not 1 <= value <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
    if state["attempts"] > state["max_attempts"]:
        raise ValueError("attempts cannot exceed max_attempts")

    criteria = set(state["done_when"])
    seen = set()
    if not isinstance(state["verification"], list):
        raise ValueError("verification must be a list")
    for item in state["verification"]:
        if not isinstance(item, dict) or set(item) != {"criterion", "passed", "evidence"}:
            raise ValueError("invalid verification item")
        _text(item["criterion"], "verification criterion")
        if item["criterion"] not in criteria:
            raise ValueError("verification criterion must match done_when")
        if item["criterion"] in seen:
            raise ValueError("duplicate verification criterion")
        seen.add(item["criterion"])
        if not isinstance(item["passed"], bool):
            raise ValueError("verification passed must be bool")
        _text(item["evidence"], "verification evidence")

    if not isinstance(state["pending_actions"], list):
        raise ValueError("pending_actions must be a list")
    action_ids = set()
    for item in state["pending_actions"]:
        if not isinstance(item, dict) or set(item) != {"action_id", "outcome"}:
            raise ValueError("invalid pending action")
        _text(item["action_id"], "action_id")
        if item["action_id"] in action_ids:
            raise ValueError("duplicate action_id")
        action_ids.add(item["action_id"])
        if not isinstance(item["outcome"], str) or item["outcome"] not in OUTCOMES:
            raise ValueError("invalid action outcome")

    if state["status"] == "completed":
        if seen != criteria or any(not item["passed"] for item in state["verification"]):
            raise ValueError("completed requires passed verification for every criterion")
        if any(item["outcome"] in {"pending", "unknown"} for item in state["pending_actions"]):
            raise ValueError("completed cannot have pending or unknown actions")
    return state


def advisory(state):
    """Return advice only; this function never authorizes or performs an action."""
    validate_state(state)
    uncertain = [a for a in state["pending_actions"] if a["outcome"] in {"pending", "unknown"}]
    if uncertain:
        return {"next_step": "verify_existing_outcome", "reason": "inspect pending or uncertain outcomes; do not replay"}
    if state["status"] == "completed":
        return {"next_step": "stop", "reason": "task is completed"}
    if state["status"] == "failed":
        return {"next_step": "stop", "reason": "task is terminally failed"}
    if state["status"] == "blocked":
        return {"next_step": "escalate", "reason": "task is blocked"}
    if state["attempts"] >= state["max_attempts"]:
        return {"next_step": "stop", "reason": "attempt budget exhausted"}
    return {"next_step": "continue", "reason": "bounded task may continue"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate resumable task state (advisory only).")
    parser.add_argument("--state", required=True)
    args = parser.parse_args(argv)
    try:
        state = json.loads(Path(args.state).read_text(encoding="utf-8"))
        validate_state(state)
        result = {"valid": True, **advisory(state)}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"valid": False, "error": "invalid_state", "detail": str(error)}, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
