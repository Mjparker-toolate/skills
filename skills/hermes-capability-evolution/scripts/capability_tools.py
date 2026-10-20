#!/usr/bin/env python3
"""Safe, metadata-only capability indexing and evidence validation (stdlib only)."""
import argparse, hashlib, json, math, os, re, sys
from pathlib import Path

_EFFECTS = {"read", "write", "delete", "arbitrary_http", "unknown"}
_KINDS = {"skill", "tool"}
_REQUIRED = ("id", "name", "description", "kind", "source", "available", "authorized", "effect", "path")


def _scalar(v):
    v = v.strip()
    if not v: return ""
    if len(v) >= 2 and v[:1] == v[-1:] and v[:1] in "'\"": return v[1:-1]
    if v.lower() in ("true", "false"): return v.lower() == "true"
    return v


def _frontmatter(path):
    """Parse top-level YAML-like front matter only; never read the markdown body."""
    with open(path, "r", encoding="utf-8") as f:
        if f.readline().strip() != "---": raise ValueError("missing front matter")
        out = {}
        lines = iter(f); pending = None
        while True:
            line = pending if pending is not None else next(lines, None); pending = None
            if line is None: break
            if line.strip() == "---": return out
            if not line.strip() or line.lstrip().startswith("#") or line[:1].isspace(): continue
            if ":" not in line: raise ValueError("malformed metadata")
            k, v = line.split(":", 1); k = k.strip()
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", k): raise ValueError("bad metadata key")
            raw = v.strip()
            if raw in ("|", ">", "|-", ">-"):
                vals = []
                for continuation in lines:
                    if continuation.strip() and not continuation[:1].isspace():
                        pending = continuation; break
                    if not continuation.strip():
                        vals.append("")
                    else:
                        vals.append(continuation.strip())
                out[k] = ("\n" if raw.startswith("|") else " ").join(vals).rstrip()
                continue
            out[k] = _scalar(v)
        raise ValueError("unterminated front matter")


def _safe(path, roots):
    try:
        rp = os.path.realpath(path)
        return any(os.path.commonpath((rp, os.path.realpath(r))) == os.path.realpath(r) for r in roots)
    except (OSError, ValueError): return False


def _record(path, root):
    meta = _frontmatter(path)
    name, desc = meta.get("name"), meta.get("description")
    if not isinstance(name, str) or not isinstance(desc, str) or not name.strip() or not desc.strip():
        raise ValueError("name and description required")
    ident = str(meta.get("id", name)).strip()
    # A discovered SKILL.md is only descriptive local metadata.  Its frontmatter
    # cannot authorize it or grant an effect/kind.
    rec = {"id": ident, "name": name.strip(), "description": desc.strip(), "kind": "skill",
           "source": "local", "available": True, "authorized": False, "effect": "unknown",
           "path": os.path.abspath(path)}
    return rec


def validate_manifest(records):
    if not isinstance(records, list): raise ValueError("manifest must be a list")
    seen = set()
    for r in records:
        if not isinstance(r, dict) or any(k not in r for k in _REQUIRED): raise ValueError("malformed manifest record")
        if not isinstance(r["id"], str) or not r["id"] or r["id"] in seen: raise ValueError("invalid/duplicate id")
        seen.add(r["id"])
        for key in ("name", "description", "source"):
            if not isinstance(r[key], str): raise ValueError(f"{key} must be string")
        if r["kind"] not in _KINDS or r["effect"] not in _EFFECTS: raise ValueError("invalid kind/effect")
        if not isinstance(r["available"], bool) or not isinstance(r["authorized"], bool): raise ValueError("availability flags must be bool")
        if not isinstance(r["path"], str): raise ValueError("path must be string")
        for key in ("browser", "profile"):
            if key in r and not isinstance(r[key], str): raise ValueError(f"{key} must be string")
    return records


def discover(roots):
    """Discover SKILL.md files under explicitly supplied roots, without symlink traversal."""
    roots = [os.path.abspath(os.fspath(r)) for r in roots]; records = []
    for root in roots:
        if not os.path.isdir(root) or os.path.islink(root): continue
        for base, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not os.path.islink(os.path.join(base, d)))
            if "SKILL.md" in files:
                p = os.path.join(base, "SKILL.md")
                if not os.path.islink(p) and _safe(p, roots):
                    try: records.append(_record(p, root))
                    except (OSError, UnicodeError, ValueError): continue
    return sorted(records, key=lambda r: (r["id"], r["path"]))


def _tokens(s): return re.findall(r"[\w]+", str(s).lower(), flags=re.UNICODE)


def search(records, query, dense_scores=None, limit=10):
    """Deterministic lexical search, optionally fused with validated dense scores via RRF."""
    validate_manifest(records)
    if not isinstance(query, str): raise ValueError("query must be string")
    if dense_scores is not None and not isinstance(dense_scores, dict): raise ValueError("dense scores must be an object")
    by_id = {r["id"]: i for i, r in enumerate(records)}
    dense = dense_scores or {}
    if any(k not in by_id for k in dense): raise ValueError("unknown dense id")
    for score in dense.values():
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)):
            raise ValueError("dense scores must be finite numbers")
    docs = [_tokens(r["id"] + " " + r["name"] + " " + r["description"] + " " + r["kind"] + " " + r["effect"]) for r in records]
    q = _tokens(query); n = len(docs); avg = sum(map(len, docs)) / n if n else 1
    df = {t: sum(t in d for d in docs) for t in set(q)}; lexical = []
    for d in docs:
        tf = {t: d.count(t) for t in set(d)}; score = 0.0
        for t in q:
            if t in tf:
                idf = math.log(1 + (n - df.get(t, 0) + .5) / (df.get(t, 0) + .5))
                score += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (.25 + .75 * len(d) / avg))
        lexical.append(score)
    lexical_ids = {i for i, score in enumerate(lexical) if score > 0}
    order_l = sorted(lexical_ids, key=lambda i: (-lexical[i], records[i]["id"])); rank_l = {i:k+1 for k,i in enumerate(order_l)}
    has_dense = dense_scores is not None and bool(dense)
    order_d = sorted((by_id[k] for k in dense), key=lambda i: (-float(dense[records[i]["id"]]), records[i]["id"])) if has_dense else []
    rank_d = {i:k+1 for k,i in enumerate(order_d)}
    candidates = lexical_ids | set(order_d)
    mode = "hybrid" if has_dense else "lexical-only"; scored = []
    for i in candidates:
        x = dict(records[i]); x["score"] = (1/(60+rank_l[i]) if i in rank_l else 0) + (1/(60+rank_d[i]) if i in rank_d else 0); x["match_mode"] = mode; scored.append(x)
    return sorted(scored, key=lambda x: (-x["score"], x["id"]))[:max(0, int(limit))]


def decision(record, browser=None, profile=None):
    """Return an allow/deny decision; approval booleans supplied by agents are advisory only."""
    try: validate_manifest([record])
    except ValueError as e: return {"allowed": False, "reason": "malformed_manifest", "detail": str(e)}
    if not record["available"]: return {"allowed": False, "reason": "unavailable"}
    if not record["authorized"]: return {"allowed": False, "reason": "unauthorized"}
    if record["effect"] in {"unknown", "delete", "arbitrary_http"}: return {"allowed": False, "reason": record["effect"]}
    if record.get("browser") and (browser != "helium" or profile != "Home"): return {"allowed": False, "reason": "browser_requires_helium_home"}
    if record["effect"] == "write": return {"allowed": False, "reason": "approval_required", "advisory_approval": True}
    return {"allowed": True, "reason": "allowed"}


def validate_report(report, calls, installed):
    """Validate references and call safety against caller-supplied ledgers (not semantic proof)."""
    if not isinstance(report, dict) or not isinstance(report.get("task"), str) or not isinstance(report.get("status"), str) or not isinstance(report.get("summary"), str): return {"valid": False, "reason": "invalid_report_fields"}
    if report["status"] not in {"completed", "partial", "blocked", "failed"}: return {"valid": False, "reason": "invalid_status"}
    if report["status"] == "completed" and (not report["summary"].strip() or not isinstance(report.get("evidence"), list) or not report["evidence"]): return {"valid": False, "reason": "completed_requires_evidence"}
    ev, skills, lim = report.get("evidence"), report.get("skills_used"), report.get("limitations")
    if not isinstance(ev, list) or not isinstance(skills, list) or not isinstance(lim, list) or any(not isinstance(x, str) for x in lim): return {"valid": False, "reason": "invalid_report_fields"}
    if not isinstance(calls, list): return {"valid": False, "reason": "invalid_calls"}
    ledger = {}; allowed_effects = {"read", "write"}
    for c in calls:
        if not isinstance(c, dict) or not isinstance(c.get("call_id"), str) or not c["call_id"] or c["call_id"] in ledger: return {"valid": False, "reason": "invalid_calls"}
        if c.get("effect") not in allowed_effects: return {"valid": False, "reason": "invalid_call_effect"}
        ledger[c["call_id"]] = c
        if c["effect"] == "write":
            a = c.get("approval") if isinstance(c.get("approval"), dict) else {}
            if not (c.get("host_approved") is True or (a.get("source") == "host" and a.get("approved") is True)): return {"valid": False, "reason": "write_not_host_approved"}
    if not isinstance(installed, list) or any(not isinstance(x, str) and not (isinstance(x, dict) and isinstance(x.get("id"), str)) for x in installed):
        return {"valid": False, "reason": "invalid_installed_skills"}
    ids = {x if isinstance(x, str) else x["id"] for x in installed}
    if any(not isinstance(x, str) or x not in ids for x in skills): return {"valid": False, "reason": "unknown_skill"}
    for x in ev:
        if not isinstance(x, dict) or not isinstance(x.get("call_id"), str) or not isinstance(x.get("claim"), str) or x["call_id"] not in ledger: return {"valid": False, "reason": "fabricated_reference"}
        c = ledger[x["call_id"]]
        if not (c.get("success") is True or c.get("status") == "success"): return {"valid": False, "reason": "call_not_successful"}
    return {"valid": True, "reason": "validated"}


def _load(path):
    with open(path, encoding="utf-8") as f: return json.load(f)


def main(argv=None):
    p = argparse.ArgumentParser(description="Hermes capability metadata tools"); sp = p.add_subparsers(dest="cmd", required=True)
    d = sp.add_parser("discover"); d.add_argument("--root", action="append", required=True)
    s = sp.add_parser("search"); s.add_argument("--manifest", required=True); s.add_argument("--query", required=True); s.add_argument("--dense-scores"); s.add_argument("--limit", type=int, default=10)
    g = sp.add_parser("gate"); g.add_argument("--manifest", required=True); g.add_argument("--id", required=True); g.add_argument("--browser"); g.add_argument("--profile")
    v = sp.add_parser("validate-report"); v.add_argument("--report", required=True); v.add_argument("--calls", required=True); v.add_argument("--installed", required=True)
    a = p.parse_args(argv)
    try:
        if a.cmd == "discover": out = discover(a.root)
        elif a.cmd == "search": out = search(validate_manifest(_load(a.manifest)), a.query, _load(a.dense_scores) if a.dense_scores else None, a.limit)
        elif a.cmd == "gate":
            rs = validate_manifest(_load(a.manifest)); out = decision(next(r for r in rs if r["id"] == a.id), a.browser, a.profile)
        else: out = validate_report(_load(a.report), _load(a.calls), _load(a.installed))
        print(json.dumps(out, ensure_ascii=False, sort_keys=True)); return 0
    except (OSError, ValueError, json.JSONDecodeError, StopIteration) as e:
        print(json.dumps({"error": "invalid_input", "detail": str(e)}, ensure_ascii=False), file=sys.stderr); return 2


if __name__ == "__main__": sys.exit(main())
