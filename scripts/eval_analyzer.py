#!/usr/bin/env python3
"""
Static Analyzer for Skill Scripts using AST.

Scans Python scripts bundled in skills for risky patterns,
code quality issues, and structural problems.

Usage:
    python -m scripts.eval_analyzer <path>           # file or directory
    python -m scripts.eval_analyzer scripts/          # scan all .py in dir
    python -m scripts.eval_analyzer my_script.py --json

Exit codes:
    0 = no issues found (or warnings/info only)
    1 = error-severity issues found
    2 = parse error / invalid input
"""

import argparse
import ast
import json
import sys
from pathlib import Path


# ──────────────────────────────────────────────
# Rule definitions
# ──────────────────────────────────────────────

class Issue:
    """A single detected issue."""
    __slots__ = ("file", "line", "severity", "code", "message")

    def __init__(self, file: str, line: int, severity: str, code: str, message: str):
        self.file = file
        self.line = line
        self.severity = severity  # "error", "warning", "info"
        self.code = code
        self.message = message

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }

    def __str__(self) -> str:
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(self.severity, "?")
        return f"{icon} {self.file}:{self.line} [{self.code}] {self.message}"


def _get_func_name(node: ast.Call) -> str | None:
    """Extract function name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _get_full_name(node: ast.Call) -> str:
    """Extract full dotted name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    elif isinstance(node.func, ast.Attribute):
        parts = []
        current = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


class ASTAnalyzer(ast.NodeVisitor):
    """Walk AST and collect issues."""

    # Dangerous builtins
    DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__"}

    # Subprocess functions that need shell=False or careful use
    SUBPROCESS_FUNCS = {"run", "Popen", "call", "check_call", "check_output"}

    # os functions that modify filesystem dangerously
    DANGEROUS_OS = {"system", "remove", "unlink", "rmdir", "removedirs", "rmtree"}

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues: list[Issue] = []
        self._imports: set[str] = set()
        self._has_main_guard = False
        self._function_count = 0
        self._class_count = 0
        self._total_lines = 0

    def _add(self, node: ast.AST, severity: str, code: str, message: str):
        line = getattr(node, "lineno", 0)
        self.issues.append(Issue(self.filepath, line, severity, code, message))

    # ── Visitors ──────────────────────────────

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self._imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self._imports.add(node.module)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        name = _get_func_name(node)
        full_name = _get_full_name(node)

        # Rule: eval/exec/compile
        if name in self.DANGEROUS_CALLS:
            self._add(node, "error", "SEC001",
                      f"Dangerous builtin '{name}()' — avoid in skill scripts. "
                      f"Use json.loads(), ast.literal_eval(), or importlib instead.")

        # Rule: subprocess with shell=True
        if name in self.SUBPROCESS_FUNCS and "subprocess" in full_name:
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self._add(node, "warning", "SEC002",
                              f"subprocess.{name}() with shell=True — "
                              f"risk of command injection. Use shell=False with list args.")

        # Rule: os.system / os.remove etc.
        if name in self.DANGEROUS_OS and "os" in full_name:
            self._add(node, "warning", "SEC003",
                      f"'{full_name}()' — potentially dangerous filesystem operation. "
                      f"Ensure paths are validated and not user-controlled.")

        # Rule: hardcoded absolute paths
        if name in ("open", "Path") and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                path_str = arg.value
                if path_str.startswith("/") and not path_str.startswith("/tmp"):
                    self._add(node, "warning", "PORT001",
                              f"Hardcoded absolute path '{path_str}' — "
                              f"use relative paths or arguments for portability.")

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.type is None:
            self._add(node, "warning", "QUAL001",
                      "Bare 'except:' — catches all exceptions including "
                      "KeyboardInterrupt and SystemExit. Use 'except Exception:'.")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._function_count += 1
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._function_count += 1
        self._check_function(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self._class_count += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        # Detect if __name__ == "__main__"
        if (isinstance(node.test, ast.Compare)
                and len(node.test.comparators) == 1):
            left = node.test.left
            comp = node.test.comparators[0]
            if (isinstance(left, ast.Name) and left.id == "__name__"
                    and isinstance(comp, ast.Constant)
                    and comp.value == "__main__"):
                self._has_main_guard = True
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant):
        # Rule: potential secrets/tokens in string literals
        if isinstance(node.value, str) and len(node.value) > 20:
            lower = node.value.lower()
            for pattern in ("api_key", "secret", "password", "token=", "bearer "):
                if pattern in lower:
                    self._add(node, "warning", "SEC004",
                              f"Possible hardcoded credential in string literal "
                              f"(contains '{pattern}'). Use environment variables.")
                    break
        self.generic_visit(node)

    def _check_function(self, node):
        """Check function-level issues."""
        # Complexity heuristic: too many branches
        branch_count = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try,
                                  ast.ExceptHandler, ast.With)):
                branch_count += 1
        if branch_count > 15:
            self._add(node, "info", "QUAL002",
                      f"Function '{node.name}' has high cyclomatic complexity "
                      f"({branch_count} branches). Consider splitting.")

        # Too many lines
        if hasattr(node, "end_lineno") and node.end_lineno:
            length = node.end_lineno - node.lineno
            if length > 100:
                self._add(node, "info", "QUAL003",
                          f"Function '{node.name}' is {length} lines long. "
                          f"Consider splitting into smaller functions.")

    # ── Post-analysis ─────────────────────────

    def post_analyze(self, source: str):
        """Run checks that need full-file context."""
        lines = source.split("\n")
        self._total_lines = len(lines)

        # Check for main guard in scripts
        if not self._has_main_guard and self._function_count > 0:
            tree = ast.parse(source)
            has_module_level_calls = False
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                    func_name = _get_func_name(node.value)
                    if func_name not in ("print",):
                        has_module_level_calls = True
                        break
            if has_module_level_calls:
                self.issues.append(Issue(
                    self.filepath, 1, "info", "QUAL004",
                    "No 'if __name__ == \"__main__\"' guard — module-level "
                    "code will execute on import."
                ))


def analyze_file(filepath: Path) -> tuple[list[Issue], dict]:
    """
    Analyze a single Python file.

    Returns: (issues, stats)
    """
    source = filepath.read_text()

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        return [Issue(str(filepath), e.lineno or 0, "error", "PARSE",
                      f"Syntax error: {e.msg}")], {}

    analyzer = ASTAnalyzer(str(filepath))
    analyzer.visit(tree)
    analyzer.post_analyze(source)

    stats = {
        "lines": analyzer._total_lines,
        "functions": analyzer._function_count,
        "classes": analyzer._class_count,
        "imports": sorted(analyzer._imports),
    }

    return analyzer.issues, stats


def analyze_directory(dirpath: Path) -> tuple[list[Issue], dict]:
    """Analyze all .py files in a directory."""
    all_issues = []
    all_stats = {}

    for py_file in sorted(dirpath.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        issues, stats = analyze_file(py_file)
        all_issues.extend(issues)
        all_stats[str(py_file)] = stats

    return all_issues, all_stats


def main():
    parser = argparse.ArgumentParser(
        description="Static analysis for skill Python scripts"
    )
    parser.add_argument("path", help="Python file or directory to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--severity", choices=["error", "warning", "info"],
                        default="info", help="Minimum severity to report (default: info)")
    args = parser.parse_args()

    target = Path(args.path)
    severity_order = {"error": 3, "warning": 2, "info": 1}
    min_severity = severity_order[args.severity]

    if target.is_dir():
        issues, stats = analyze_directory(target)
    elif target.is_file() and target.suffix == ".py":
        issues, stats = analyze_file(target)
    else:
        print(f"Error: {target} is not a .py file or directory", file=sys.stderr)
        sys.exit(2)

    # Filter by severity
    issues = [i for i in issues if severity_order.get(i.severity, 0) >= min_severity]

    if args.json:
        output = {
            "issues": [i.to_dict() for i in issues],
            "stats": stats,
            "summary": {
                "total": len(issues),
                "errors": sum(1 for i in issues if i.severity == "error"),
                "warnings": sum(1 for i in issues if i.severity == "warning"),
                "info": sum(1 for i in issues if i.severity == "info"),
            },
        }
        print(json.dumps(output, indent=2))
    else:
        if issues:
            for issue in sorted(issues, key=lambda i: (i.file, i.line)):
                print(str(issue))
            print(f"\n총 {len(issues)}건 "
                  f"(error: {sum(1 for i in issues if i.severity == 'error')}, "
                  f"warning: {sum(1 for i in issues if i.severity == 'warning')}, "
                  f"info: {sum(1 for i in issues if i.severity == 'info')})")
        else:
            print("✅ No issues found.")

    has_errors = any(i.severity == "error" for i in issues)
    sys.exit(1 if has_errors else 0)


if __name__ == "__main__":
    main()
