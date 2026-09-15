#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
"""Bootstrap third-party agent skills into this workspace, and verify them.

A skill is "bootstrapped" when three artifacts agree:

  1. ``.agents/skills/<name>/``  - the vendored skill content.
  2. ``skills-lock.json``        - the manifest entry recording where the
                                   content came from and its folder hash.
  3. ``<agent>/skills/<name>``   - a relative symlink per agent client that
                                   reads skills from its own directory
                                   (``.claude/skills`` today).

Those three are written by ``npx skills add`` and are easy to desynchronise by
hand: a vendored folder with no lock entry is invisible to ``npx skills
list``/``update``, and a lock entry with no symlink never loads in Claude Code.
``--check`` fails on any such structural break.

The lock's ``computedHash`` is the hash of the folder *as installed*, so the
skills CLI can tell whether a skill was edited locally after install. This
script therefore never rewrites an existing hash: content drift is reported as
a warning, because for a locally-patched skill the drift is the true state and
silently "fixing" it would forge a claim that the content still matches
upstream.

Usage
-----
Verify every bootstrapped skill (default)::

    python3 .github/scripts/bootstrap_skills.py --check

Bootstrap a new skill from a local directory::

    python3 .github/scripts/bootstrap_skills.py --add apify-ultimate-scraper \\
        --from /path/to/apify-ultimate-scraper \\
        --source apify/apify-cursor-plugin \\
        --skill-path apify/skills/apify-ultimate-scraper/SKILL.md

Exit code 0 = bootstrap is consistent; 1 = structural break or failed add.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

AGENTS_SKILLS_DIR = Path(".agents/skills")
LOCK_PATH = Path("skills-lock.json")
LOCK_VERSION = 1

# Agent clients that read skills from their own directory. Only directories
# that already exist are mirrored - creating `.cline/skills` in a repo that
# does not use Cline would add dead weight.
AGENT_SKILL_DIRS = (
    Path(".claude/skills"),
    Path(".cline/skills"),
    Path(".codebuddy/skills"),
    Path(".cursor/skills"),
    Path(".windsurf/skills"),
)

# Directory names the skills CLI excludes when hashing a skill folder.
HASH_EXCLUDED_DIRS = frozenset({".git", "node_modules"})


# --------------------------------------------------------------------------
# Folder hashing
# --------------------------------------------------------------------------
#
# Port of `computeSkillFolderHash` from the skills CLI (vercel-labs/skills):
# collect every file under the skill folder, sort by POSIX-relative path, then
# feed `path` followed by raw `content` into one sha256.
#
# The CLI sorts with JavaScript's `String.prototype.localeCompare`, which is
# ICU root collation - NOT byte order. Byte order disagrees with it on almost
# every real skill folder ("references/..." sorts before "SKILL.md" because
# collation compares letters case-insensitively at the primary level), so the
# table below reproduces the ICU root ordering for the characters that occur
# in file paths. `test_bootstrap_skills.py` pins this against the catalog.

_COLLATION_GROUPS = (
    "\t\n\v\f\r ",                       # whitespace
    "_-,;:!?.'\"()[]{}@*/\\&#%",         # punctuation
    "`^",                                # modifier symbols
    "$",                                 # currency
    "+<=>|~",                            # math symbols
    "0123456789",                        # digits
)


def _build_primary_weights() -> dict[str, int]:
    weights: dict[str, int] = {}
    weight = 0
    for group in _COLLATION_GROUPS:
        for char in group:
            weights[char] = weight
            weight += 1
    for letter in "abcdefghijklmnopqrstuvwxyz":
        # Case is a tertiary difference: 'a' and 'A' share a primary weight.
        weights[letter] = weights[letter.upper()] = weight
        weight += 1
    return weights


_PRIMARY: dict[str, int] = _build_primary_weights()

# Characters outside the table (e.g. non-ASCII) sort after every known
# character, ordered by code point. This is an approximation of ICU's full
# collation, so `collation_warnings()` reports paths that rely on it.
_UNKNOWN_BASE = max(_PRIMARY.values()) + 1


def _collation_key(text: str) -> tuple[list[int], list[int]]:
    """ICU-root-style sort key: primary weights first, then case."""
    primary = [_PRIMARY.get(ch, _UNKNOWN_BASE + ord(ch)) for ch in text]
    # ICU root orders lowercase before uppercase at the tertiary level.
    tertiary = [1 if ch.isupper() else 0 for ch in text]
    return primary, tertiary


def collation_warnings(paths: list[str]) -> list[str]:
    """Paths containing characters the collation table does not model."""
    return sorted({p for p in paths if any(ch not in _PRIMARY for ch in p)})


def collect_files(skill_dir: Path) -> list[str]:
    """POSIX-relative paths of every hashed file, in skills-CLI order.

    Symlinks are skipped: the CLI classifies entries from ``readdir`` Dirents,
    whose ``isFile()`` is lstat-based and therefore false for a symlink.
    """
    found: list[str] = []
    for root, dirnames, filenames in os.walk(skill_dir):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in HASH_EXCLUDED_DIRS and not (Path(root) / d).is_symlink()
        ]
        for name in filenames:
            full = Path(root) / name
            if full.is_symlink():
                continue
            found.append(full.relative_to(skill_dir).as_posix())
    found.sort(key=_collation_key)
    return found


def compute_skill_folder_hash(skill_dir: Path) -> str:
    """sha256 over every file's relative path and content, in sorted order."""
    digest = hashlib.sha256()
    for relative_path in collect_files(skill_dir):
        digest.update(relative_path.encode("utf-8"))
        digest.update((skill_dir / relative_path).read_bytes())
    return digest.hexdigest()


# --------------------------------------------------------------------------
# Lock file
# --------------------------------------------------------------------------


def load_lock(root: Path) -> dict:
    path = root / LOCK_PATH
    if not path.exists():
        return {"version": LOCK_VERSION, "skills": {}}
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_lock(root: Path, lock: dict) -> None:
    """Write the lock with the skills CLI's formatting (2-space, sorted)."""
    lock["skills"] = dict(sorted(lock["skills"].items()))
    path = root / LOCK_PATH
    with path.open("w", encoding="utf-8") as handle:
        json.dump(lock, handle, indent=2)
        handle.write("\n")


def mirror_dirs(root: Path) -> list[Path]:
    """Agent skill directories present in this workspace."""
    return [d for d in AGENT_SKILL_DIRS if (root / d).is_dir()]


# --------------------------------------------------------------------------
# Check
# --------------------------------------------------------------------------


def check(root: Path) -> tuple[list[str], list[str]]:
    """Verify the lock, vendored content, and agent symlinks agree.

    Returns ``(errors, warnings)``. Errors are structural breaks that make a
    skill unusable or invisible; warnings are content drift, which is a
    legitimate state for a locally-patched skill.
    """
    errors: list[str] = []
    warnings: list[str] = []

    lock = load_lock(root)
    locked = lock.get("skills", {})
    agents_root = root / AGENTS_SKILLS_DIR

    if not agents_root.is_dir():
        return [f"missing vendored skills directory: {AGENTS_SKILLS_DIR}"], []

    vendored = {p.name for p in sorted(agents_root.iterdir()) if p.is_dir()}
    mirrors = mirror_dirs(root)

    for name in sorted(set(locked) - vendored):
        errors.append(
            f"{name}: in {LOCK_PATH} but not vendored at {AGENTS_SKILLS_DIR}/{name}"
        )
    for name in sorted(vendored - set(locked)):
        errors.append(
            f"{name}: vendored at {AGENTS_SKILLS_DIR}/{name} but missing from {LOCK_PATH}"
        )

    for name in sorted(set(locked) & vendored):
        entry = locked[name]
        skill_dir = agents_root / name

        for field in ("source", "sourceType", "skillPath", "computedHash"):
            if not entry.get(field):
                errors.append(f"{name}: {LOCK_PATH} entry is missing '{field}'")

        if not (skill_dir / "SKILL.md").is_file():
            errors.append(f"{name}: vendored folder has no SKILL.md")
            continue

        expected = entry.get("computedHash")
        if expected:
            actual = compute_skill_folder_hash(skill_dir)
            if actual != expected:
                warnings.append(
                    f"{name}: content differs from the hash recorded at install "
                    f"(locked {expected[:12]}…, on disk {actual[:12]}…) - "
                    "expected if the skill was patched locally"
                )

        stray = collation_warnings(collect_files(skill_dir))
        if stray:
            warnings.append(
                f"{name}: path(s) outside the collation table, hash may not "
                f"match the skills CLI: {', '.join(stray)}"
            )

    for mirror in mirrors:
        present = {p.name for p in (root / mirror).iterdir()}
        for name in sorted(set(locked) - present):
            errors.append(f"{name}: no {mirror}/{name} symlink")
        for name in sorted(present - set(locked)):
            errors.append(f"{name}: {mirror}/{name} exists but is not in {LOCK_PATH}")
        for name in sorted(set(locked) & present):
            link = root / mirror / name
            if not link.is_symlink():
                errors.append(f"{mirror}/{name} is not a symlink")
            elif not link.resolve().is_dir():
                errors.append(f"{mirror}/{name} is a broken symlink")

    return errors, warnings


# --------------------------------------------------------------------------
# Add
# --------------------------------------------------------------------------


def add(
    root: Path,
    name: str,
    src: Path,
    source: str,
    skill_path: str,
    source_type: str = "github",
    force: bool = False,
) -> list[str]:
    """Vendor ``src`` as skill ``name`` and register it. Returns errors."""
    if not (src / "SKILL.md").is_file():
        return [f"{src} has no SKILL.md - not a skill folder"]

    lock = load_lock(root)
    dest = root / AGENTS_SKILLS_DIR / name
    if dest.exists() and not force:
        return [f"{AGENTS_SKILLS_DIR}/{name} already exists (use --force to replace)"]

    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)

    lock.setdefault("version", LOCK_VERSION)
    lock.setdefault("skills", {})
    lock["skills"][name] = {
        "source": source,
        "sourceType": source_type,
        "skillPath": skill_path,
        "computedHash": compute_skill_folder_hash(dest),
    }
    write_lock(root, lock)

    for mirror in mirror_dirs(root):
        link = root / mirror / name
        if link.is_symlink() or link.exists():
            link.unlink()
        # Relative so the checkout stays portable.
        link.symlink_to(
            Path(os.path.relpath(root / AGENTS_SKILLS_DIR / name, root / mirror)),
            target_is_directory=True,
        )

    return []


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root (default: this script's repo)",
    )
    parser.add_argument("--check", action="store_true", help="verify the bootstrap")
    parser.add_argument("--add", metavar="NAME", help="bootstrap a new skill")
    parser.add_argument("--from", dest="src", type=Path, help="source skill folder")
    parser.add_argument("--source", help="upstream identifier, e.g. owner/repo")
    parser.add_argument("--skill-path", help="path to SKILL.md within the source")
    parser.add_argument("--source-type", default="github", help="default: github")
    parser.add_argument("--force", action="store_true", help="replace if vendored")
    args = parser.parse_args(argv)

    root: Path = args.root

    if args.add:
        missing = [
            flag
            for flag, value in (
                ("--from", args.src),
                ("--source", args.source),
                ("--skill-path", args.skill_path),
            )
            if not value
        ]
        if missing:
            parser.error(f"--add requires {', '.join(missing)}")
        errors = add(
            root,
            args.add,
            args.src,
            args.source,
            args.skill_path,
            args.source_type,
            args.force,
        )
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 1
        print(f"bootstrapped {args.add}")

    errors, warnings = check(root)
    for warning in warnings:
        print(f"warning: {warning}")
    for error in errors:
        print(f"error: {error}", file=sys.stderr)

    if errors:
        print(f"\n{len(errors)} structural problem(s) found.", file=sys.stderr)
        return 1

    count = len(load_lock(root).get("skills", {}))
    mirrors = ", ".join(str(m) for m in mirror_dirs(root)) or "none"
    print(f"\nbootstrap OK: {count} skills in {LOCK_PATH}, mirrored into {mirrors}.")
    if warnings:
        print(f"{len(warnings)} warning(s) - content drift, not a structural break.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
