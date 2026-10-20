"""Offline structural checks for the owner-maintained Hermes skill (stdlib only)."""
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "hermes-capability-evolution"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate():
    tools = load_module("hermes_validation_tools", SKILL / "scripts" / "capability_tools.py")
    metadata = tools._frontmatter(SKILL / "SKILL.md")
    if metadata.get("name") != SKILL.name or not isinstance(metadata.get("description"), str) or not metadata["description"].strip():
        raise ValueError("invalid skill metadata")
    if len((SKILL / "SKILL.md").read_text(encoding="utf-8").splitlines()) >= 500:
        raise ValueError("keep SKILL.md below 500 lines")
    for doc in SKILL.rglob("*.md"):
        for link in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", doc.read_text(encoding="utf-8")):
            if ":" in link or link.startswith("#"):
                continue
            target = (doc.parent / link.split("#", 1)[0]).resolve()
            if not target.is_relative_to(SKILL.resolve()) or not target.is_file():
                raise ValueError(f"broken or escaping local reference in {doc.name}: {link}")
    for template in (SKILL / "templates").glob("*.json"):
        if not isinstance(json.loads(template.read_text(encoding="utf-8")), dict):
            raise ValueError(f"template must be an object: {template.name}")
    state = load_module("hermes_run_state", SKILL / "scripts" / "run_state.py")
    state.validate_state(json.loads((SKILL / "templates" / "run-state.json").read_text(encoding="utf-8")))
    exceptions = (ROOT / "catalog-exceptions.yml").read_text(encoding="utf-8")
    # Check the exact list-entry line, not an incidental mention in a comment.
    if not re.search(r"^  - dir: hermes-capability-evolution\s*$", exceptions, re.MULTILINE):
        raise ValueError("Hermes skill must be preserved by catalog sync")
    print("Hermes metadata, local links, JSON templates, run state, and sync preservation: valid")


if __name__ == "__main__":
    try:
        validate()
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"Hermes validation failed: {exc}", file=sys.stderr)
        sys.exit(1)
