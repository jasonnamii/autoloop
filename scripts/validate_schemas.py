#!/usr/bin/env python3
"""
JSON Schema Validator for Skill Builder artifacts.

Validates evals.json, grading.json, benchmark.json, history.json,
metrics.json, timing.json, comparison.json, analysis.json against
the schemas defined in references/schemas.md.

Usage:
    python -m scripts.validate_schemas <json_file> [--type TYPE]
    python -m scripts.validate_schemas evals/evals.json --type evals
    python -m scripts.validate_schemas workspace/grading.json
    python -m scripts.validate_schemas --all <workspace_dir>

Exit codes:
    0 = valid
    1 = validation errors found
    2 = file not found / parse error
"""

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

# ──────────────────────────────────────────────
# Schema definitions (derived from references/schemas.md)
# ──────────────────────────────────────────────

EVALS_SCHEMA = {
    "type": "object",
    "required": ["skill_name", "evals"],
    "properties": {
        "skill_name": {"type": "string", "minLength": 1},
        "evals": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "prompt", "expected_output"],
                "properties": {
                    "id": {"type": "integer"},
                    "prompt": {"type": "string", "minLength": 1},
                    "expected_output": {"type": "string"},
                    "files": {"type": "array", "items": {"type": "string"}},
                    "expectations": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}

HISTORY_SCHEMA = {
    "type": "object",
    "required": ["started_at", "skill_name", "current_best", "iterations"],
    "properties": {
        "started_at": {"type": "string"},
        "skill_name": {"type": "string", "minLength": 1},
        "current_best": {"type": "string"},
        "iterations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "version", "parent", "expectation_pass_rate",
                    "grading_result", "is_current_best",
                ],
                "properties": {
                    "version": {"type": "string"},
                    "parent": {"type": ["string", "null"]},
                    "expectation_pass_rate": {"type": "number", "minimum": 0, "maximum": 1},
                    "grading_result": {
                        "type": "string",
                        "enum": ["baseline", "won", "lost", "tie"],
                    },
                    "is_current_best": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}

_EXPECTATION_ITEM = {
    "type": "object",
    "required": ["text", "passed", "evidence"],
    "properties": {
        "text": {"type": "string"},
        "passed": {"type": "boolean"},
        "evidence": {"type": "string"},
    },
    "additionalProperties": False,
}

GRADING_SCHEMA = {
    "type": "object",
    "required": ["expectations", "summary"],
    "properties": {
        "expectations": {"type": "array", "items": _EXPECTATION_ITEM},
        "summary": {
            "type": "object",
            "required": ["passed", "failed", "total", "pass_rate"],
            "properties": {
                "passed": {"type": "integer", "minimum": 0},
                "failed": {"type": "integer", "minimum": 0},
                "total": {"type": "integer", "minimum": 0},
                "pass_rate": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "additionalProperties": False,
        },
        "execution_metrics": {"type": "object"},
        "timing": {"type": "object"},
        "claims": {"type": "array"},
        "user_notes_summary": {"type": "object"},
        "eval_feedback": {"type": "object"},
    },
    "additionalProperties": False,
}

METRICS_SCHEMA = {
    "type": "object",
    "required": ["tool_calls", "total_tool_calls", "total_steps",
                  "files_created", "errors_encountered", "output_chars",
                  "transcript_chars"],
    "properties": {
        "tool_calls": {"type": "object"},
        "total_tool_calls": {"type": "integer", "minimum": 0},
        "total_steps": {"type": "integer", "minimum": 0},
        "files_created": {"type": "array", "items": {"type": "string"}},
        "errors_encountered": {"type": "integer", "minimum": 0},
        "output_chars": {"type": "integer", "minimum": 0},
        "transcript_chars": {"type": "integer", "minimum": 0},
    },
    "additionalProperties": False,
}

TIMING_SCHEMA = {
    "type": "object",
    "properties": {
        "total_tokens": {"type": "integer", "minimum": 0},
        "duration_ms": {"type": "number", "minimum": 0},
        "total_duration_seconds": {"type": "number", "minimum": 0},
        "executor_start": {"type": "string"},
        "executor_end": {"type": "string"},
        "executor_duration_seconds": {"type": "number", "minimum": 0},
        "grader_start": {"type": "string"},
        "grader_end": {"type": "string"},
        "grader_duration_seconds": {"type": "number", "minimum": 0},
    },
    "additionalProperties": False,
}

_STAT_BLOCK = {
    "type": "object",
    "required": ["mean", "stddev"],
    "properties": {
        "mean": {"type": "number"},
        "stddev": {"type": "number"},
        "min": {"type": "number"},
        "max": {"type": "number"},
    },
    "additionalProperties": False,
}

BENCHMARK_SCHEMA = {
    "type": "object",
    "required": ["metadata", "runs", "run_summary"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["skill_name", "timestamp", "evals_run", "runs_per_configuration"],
            "properties": {
                "skill_name": {"type": "string"},
                "skill_path": {"type": "string"},
                "executor_model": {"type": "string"},
                "analyzer_model": {"type": "string"},
                "timestamp": {"type": "string"},
                "evals_run": {"type": "array"},
                "runs_per_configuration": {"type": "integer", "minimum": 1},
            },
            "additionalProperties": False,
        },
        "runs": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["eval_id", "configuration", "run_number", "result"],
                "properties": {
                    "eval_id": {"type": "integer"},
                    "eval_name": {"type": "string"},
                    "configuration": {
                        "type": "string",
                        "enum": ["with_skill", "without_skill"],
                    },
                    "run_number": {"type": "integer", "minimum": 1},
                    "result": {
                        "type": "object",
                        "required": ["pass_rate", "passed", "total"],
                        "properties": {
                            "pass_rate": {"type": "number", "minimum": 0, "maximum": 1},
                            "passed": {"type": "integer", "minimum": 0},
                            "failed": {"type": "integer", "minimum": 0},
                            "total": {"type": "integer", "minimum": 0},
                            "time_seconds": {"type": "number", "minimum": 0},
                            "tokens": {"type": "integer", "minimum": 0},
                            "tool_calls": {"type": "integer", "minimum": 0},
                            "errors": {"type": "integer", "minimum": 0},
                        },
                        "additionalProperties": False,
                    },
                    "expectations": {"type": "array", "items": _EXPECTATION_ITEM},
                    "notes": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": False,
            },
        },
        "run_summary": {
            "type": "object",
            "properties": {
                "with_skill": {
                    "type": "object",
                    "properties": {
                        "pass_rate": _STAT_BLOCK,
                        "time_seconds": _STAT_BLOCK,
                        "tokens": _STAT_BLOCK,
                    },
                    "additionalProperties": False,
                },
                "without_skill": {
                    "type": "object",
                    "properties": {
                        "pass_rate": _STAT_BLOCK,
                        "time_seconds": _STAT_BLOCK,
                        "tokens": _STAT_BLOCK,
                    },
                    "additionalProperties": False,
                },
                "delta": {"type": "object"},
            },
            "additionalProperties": False,
        },
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}

COMPARISON_SCHEMA = {
    "type": "object",
    "required": ["winner", "reasoning", "rubric"],
    "properties": {
        "winner": {"type": "string", "enum": ["A", "B"]},
        "reasoning": {"type": "string"},
        "rubric": {"type": "object"},
        "output_quality": {"type": "object"},
        "expectation_results": {"type": "object"},
    },
    "additionalProperties": False,
}

ANALYSIS_SCHEMA = {
    "type": "object",
    "required": ["comparison_summary", "winner_strengths",
                  "loser_weaknesses", "improvement_suggestions"],
    "properties": {
        "comparison_summary": {
            "type": "object",
            "required": ["winner"],
            "properties": {
                "winner": {"type": "string"},
                "winner_skill": {"type": "string"},
                "loser_skill": {"type": "string"},
                "comparator_reasoning": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "winner_strengths": {"type": "array", "items": {"type": "string"}},
        "loser_weaknesses": {"type": "array", "items": {"type": "string"}},
        "instruction_following": {"type": "object"},
        "improvement_suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["priority", "suggestion"],
                "properties": {
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "category": {"type": "string"},
                    "suggestion": {"type": "string"},
                    "expected_impact": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
        "transcript_insights": {"type": "object"},
    },
    "additionalProperties": False,
}

# ──────────────────────────────────────────────
# Schema registry + auto-detection
# ──────────────────────────────────────────────

SCHEMA_MAP = {
    "evals": EVALS_SCHEMA,
    "history": HISTORY_SCHEMA,
    "grading": GRADING_SCHEMA,
    "metrics": METRICS_SCHEMA,
    "timing": TIMING_SCHEMA,
    "benchmark": BENCHMARK_SCHEMA,
    "comparison": COMPARISON_SCHEMA,
    "analysis": ANALYSIS_SCHEMA,
}


def detect_schema_type(filepath: Path) -> str | None:
    """Auto-detect schema type from filename."""
    stem = filepath.stem.lower()
    for key in SCHEMA_MAP:
        if key in stem:
            return key
    return None


def validate_json(data: dict, schema_type: str) -> list[str]:
    """Validate JSON data against a schema. Returns list of error messages."""
    schema = SCHEMA_MAP.get(schema_type)
    if schema is None:
        return [f"Unknown schema type: {schema_type}. Available: {', '.join(sorted(SCHEMA_MAP))}"]

    validator = Draft7Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = " → ".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"[{path}] {error.message}")
    return errors


def validate_cross_consistency(data: dict, schema_type: str) -> list[str]:
    """Cross-field consistency checks beyond schema validation."""
    warnings = []

    if schema_type == "grading":
        summary = data.get("summary", {})
        expectations = data.get("expectations", [])
        actual_passed = sum(1 for e in expectations if e.get("passed"))
        actual_total = len(expectations)
        if summary.get("total") != actual_total:
            warnings.append(
                f"summary.total ({summary.get('total')}) != "
                f"expectations count ({actual_total})"
            )
        if summary.get("passed") != actual_passed:
            warnings.append(
                f"summary.passed ({summary.get('passed')}) != "
                f"actual passed ({actual_passed})"
            )
        expected_rate = actual_passed / actual_total if actual_total else 0
        if abs(summary.get("pass_rate", 0) - expected_rate) > 0.01:
            warnings.append(
                f"summary.pass_rate ({summary.get('pass_rate')}) != "
                f"computed ({expected_rate:.2f})"
            )

    elif schema_type == "history":
        iterations = data.get("iterations", [])
        current_best = data.get("current_best")
        best_count = sum(1 for it in iterations if it.get("is_current_best"))
        if best_count != 1:
            warnings.append(
                f"Expected exactly 1 is_current_best=true, found {best_count}"
            )
        best_versions = [it["version"] for it in iterations if it.get("is_current_best")]
        if best_versions and best_versions[0] != current_best:
            warnings.append(
                f"current_best ({current_best}) != "
                f"is_current_best version ({best_versions[0]})"
            )

    elif schema_type == "benchmark":
        runs = data.get("runs", [])
        configs = set(r.get("configuration") for r in runs)
        if "with_skill" not in configs:
            warnings.append("No 'with_skill' runs found in benchmark")

    elif schema_type == "evals":
        evals = data.get("evals", [])
        ids = [e.get("id") for e in evals]
        if len(ids) != len(set(ids)):
            warnings.append("Duplicate eval IDs detected")

    return warnings


def validate_file(filepath: Path, schema_type: str | None = None,
                  verbose: bool = False) -> tuple[bool, list[str], list[str]]:
    """
    Validate a JSON file.

    Returns: (is_valid, errors, warnings)
    """
    if not filepath.exists():
        return False, [f"File not found: {filepath}"], []

    try:
        data = json.loads(filepath.read_text())
    except json.JSONDecodeError as e:
        return False, [f"JSON parse error: {e}"], []

    if schema_type is None:
        schema_type = detect_schema_type(filepath)
    if schema_type is None:
        return False, [
            f"Cannot detect schema type from filename '{filepath.name}'. "
            f"Use --type to specify: {', '.join(sorted(SCHEMA_MAP))}"
        ], []

    errors = validate_json(data, schema_type)
    warnings = validate_cross_consistency(data, schema_type)

    if verbose:
        print(f"Schema: {schema_type}")
        print(f"File: {filepath}")

    return len(errors) == 0, errors, warnings


def validate_workspace(workspace_dir: Path, verbose: bool = False) -> dict:
    """Scan a workspace directory for known JSON artifacts and validate all."""
    results = {}
    for json_file in sorted(workspace_dir.rglob("*.json")):
        schema_type = detect_schema_type(json_file)
        if schema_type is None:
            continue
        is_valid, errors, warnings = validate_file(json_file, schema_type, verbose)
        results[str(json_file)] = {
            "type": schema_type,
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
        }
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Validate skill-builder JSON artifacts against schemas"
    )
    parser.add_argument("path", help="JSON file or workspace directory (with --all)")
    parser.add_argument("--type", choices=sorted(SCHEMA_MAP.keys()),
                        help="Schema type (auto-detected from filename if omitted)")
    parser.add_argument("--all", action="store_true",
                        help="Scan directory for all known JSON artifacts")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    target = Path(args.path)

    if args.all:
        if not target.is_dir():
            print(f"Error: --all requires a directory, got: {target}", file=sys.stderr)
            sys.exit(2)
        results = validate_workspace(target, args.verbose)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            any_error = False
            for fpath, info in results.items():
                status = "✅" if info["valid"] else "❌"
                print(f"{status} [{info['type']}] {fpath}")
                for e in info["errors"]:
                    print(f"   ERROR: {e}")
                    any_error = True
                for w in info["warnings"]:
                    print(f"   WARN:  {w}")
            if not results:
                print("No known JSON artifacts found.")
        sys.exit(1 if any_error else 0)

    else:
        is_valid, errors, warnings = validate_file(target, args.type, args.verbose)
        if args.json:
            print(json.dumps({
                "file": str(target),
                "type": args.type or detect_schema_type(target),
                "valid": is_valid,
                "errors": errors,
                "warnings": warnings,
            }, indent=2))
        else:
            if is_valid:
                print(f"✅ Valid ({args.type or detect_schema_type(target)}): {target}")
            else:
                print(f"❌ Invalid ({args.type or detect_schema_type(target)}): {target}")
            for e in errors:
                print(f"   ERROR: {e}")
            for w in warnings:
                print(f"   WARN:  {w}")
        sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
