"""Hermes native plugin: pure in-memory tools; no external dispatch or hooks."""
import importlib.util
import json
from pathlib import Path


def _library():
    path = Path(__file__).resolve().parent / "scripts" / "capability_tools.py"
    spec = importlib.util.spec_from_file_location("hermes_capability_tools", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _handler(operation):
    def handle(args, **kwargs):
        try:
            if not isinstance(args, dict):
                raise ValueError("arguments must be an object")
            lib = _library()
            if operation == "search":
                result = lib.search(args["records"], args["query"],
                                    args.get("dense_scores"), args.get("limit", 10))
            elif operation == "preflight":
                result = lib.decision(args["record"], args.get("browser"), args.get("profile"))
            else:
                result = lib.validate_report(args["report"], args["calls"], args["installed"])
            return json.dumps(result, ensure_ascii=False, allow_nan=False)
        except Exception:
            # Do not echo arguments, file paths, or secret-bearing error strings.
            return json.dumps({"error": "invalid_input", "operation": operation})
    return handle


def _schema(name, description, properties, required):
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": required, "additionalProperties": False}}


_ARRAY = {"type": "array", "items": {"type": "object"}}
TOOLS = [
    ("capability_search", "search", _schema(
        "capability_search",
        "Search supplied capability metadata using BM25; optionally fuse genuine supplied dense scores. Does not discover or invoke external tools.",
        {"records": _ARRAY, "query": {"type": "string"},
         "dense_scores": {"type": "object", "additionalProperties": {"type": "number"}},
         "limit": {"type": "integer", "minimum": 1, "maximum": 100}}, ["records", "query"])),
    ("capability_preflight", "preflight", _schema(
        "capability_preflight",
        "Advisory fail-closed preflight. Writes always require real host approval; this tool grants no permissions and executes nothing.",
        {"record": {"type": "object"}, "browser": {"type": "string"},
         "profile": {"type": "string"}}, ["record"])),
    ("capability_report_check", "report", _schema(
        "capability_report_check",
        "Check report references against supplied calls and installed skills. Use a host-owned ledger; model-supplied records are not proof of execution or semantic truth.",
        {"report": {"type": "object"}, "calls": _ARRAY,
         "installed": {"type": "array", "items": {"type": "string"}}},
        ["report", "calls", "installed"])),
]


def register(ctx):
    """Use only the documented additive PluginContext registration surface."""
    for name, operation, schema in TOOLS:
        ctx.register_tool(name=name, toolset="capability_evolution", schema=schema,
                          handler=_handler(operation))
