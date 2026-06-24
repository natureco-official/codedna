"""AST analysis and AI signature detection module."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser, Node

# TypeScript parser — fall back to JS parser if not installed
try:
    import tree_sitter_typescript as tstypescript
    _TS_LANG = tstypescript.language_typescript()
    _TSX_LANG = tstypescript.language_tsx()
    _TS_AVAILABLE = True
except Exception:
    _TS_LANG = tsjavascript.language()
    _TSX_LANG = tsjavascript.language()
    _TS_AVAILABLE = False

# Supported language map
LANGUAGE_MAP: dict[str, tuple] = {
    ".py":  ("python",     tspython.language()),
    ".js":  ("javascript", tsjavascript.language()),
    ".jsx": ("javascript", tsjavascript.language()),
    ".ts":  ("typescript", _TS_LANG),
    ".tsx": ("tsx",        _TSX_LANG),
}


@dataclass
class FileAnalysisResult:
    """Analysis result for a single file."""

    file_path: str
    ai_probability: float = 0.0
    complexity_score: float = 0.0
    comment_ratio: float = 0.0
    avg_function_length: float = 0.0
    single_commit_ratio: float = 0.0
    total_lines: int = 0
    function_count: int = 0
    unsupported: bool = False   # kept for internal use
    error: Optional[str] = None     # kept for internal use

    @property
    def complexity_label(self) -> str:
        """Return complexity level as a string."""
        if self.complexity_score < 5:
            return "Low"
        elif self.complexity_score < 15:
            return "Medium"
        else:
            return "High"

    @property
    def ai_color(self) -> str:
        """Return color emoji based on AI probability."""
        if self.ai_probability >= 0.7:
            return "🔴"
        elif self.ai_probability >= 0.4:
            return "🟡"
        else:
            return "🟢"


def _build_parser(ext: str) -> Optional[Parser]:
    """Build a tree-sitter parser for the given file extension."""
    if ext not in LANGUAGE_MAP:
        return None
    _, lang_obj = LANGUAGE_MAP[ext]
    language = Language(lang_obj)
    parser = Parser(language)
    return parser


def _count_lines(source: str) -> tuple[int, int]:
    """Return (total_lines, comment_lines) count."""
    lines = source.splitlines()
    total = len(lines)
    comments = 0
    for line in lines:
        stripped = line.strip()
        # Python, JS, TS single-line comments
        if stripped.startswith("#") or stripped.startswith("//"):
            comments += 1
        # Simple heuristic for multi-line comments
        elif stripped.startswith("*") or stripped.startswith("/*") or stripped.startswith('"""') or stripped.startswith("'''"):
            comments += 1
    return total, comments


def _collect_functions(node: Node, functions: list[Node]) -> None:
    """Recursively collect all function nodes from the AST."""
    function_types = {
        "function_definition",          # Python
        "function_declaration",         # JS/TS
        "method_definition",            # JS/TS class method
        "method_signature",             # TS interface method
        "abstract_method_signature",    # TS abstract
        "arrow_function",               # JS/TS arrow
        "function_expression",          # JS/TS
        "generator_function",           # JS/TS generator
        "generator_function_declaration",
    }
    if node.type in function_types:
        functions.append(node)
    for child in node.children:
        _collect_functions(child, functions)


def _calculate_cyclomatic_complexity(node: Node) -> float:
    """
    Calculate simple cyclomatic complexity.
    Count decision points (if, for, while, case, &&, ||).
    """
    decision_types = {
        "if_statement", "elif_clause", "for_statement", "while_statement",
        "with_statement", "try_statement", "except_clause",
        "if_expression",   # Python ternary
        "switch_case", "case_clause",
        # JS/TS
        "if", "for", "while", "switch", "catch",
        "ternary_expression",
        "&&", "||", "??",
    }
    count = 1  # Base path

    def _traverse(n: Node) -> None:
        nonlocal count
        if n.type in decision_types:
            count += 1
        # Logical operators
        if n.type in {"boolean_operator", "logical_expression"}:
            count += 1
        for child in n.children:
            _traverse(child)

    _traverse(node)
    return float(count)


def analyze_file(
    file_path: Path,
    single_commit_ratio: float = 0.0,
) -> FileAnalysisResult:
    """
    Analyze a file with AST and calculate AI signature metrics.

    Args:
        file_path: Path to the file to analyze
        single_commit_ratio: Fraction of lines added in a single commit (provided externally)

    Returns:
        FileAnalysisResult object
    """
    result = FileAnalysisResult(
        file_path=str(file_path),
        single_commit_ratio=single_commit_ratio,
    )

    # Can we read the file?
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        result.error = f"Cannot read file: {e}"
        return result

    ext = file_path.suffix.lower()
    parser = _build_parser(ext)

    if parser is None:
        result.unsupported = True
        return result

    # Line counts
    total_lines, comment_lines = _count_lines(source)
    result.total_lines = total_lines
    result.comment_ratio = (comment_lines / total_lines) if total_lines > 0 else 0.0

    # Parse AST
    try:
        tree = parser.parse(bytes(source, "utf8"))
    except Exception as e:
        result.error = f"AST parse error: {e}"
        return result

    # Function analysis
    functions: list[Node] = []
    _collect_functions(tree.root_node, functions)
    result.function_count = len(functions)

    if functions:
        lengths = [
            f.end_point[0] - f.start_point[0] + 1
            for f in functions
        ]
        result.avg_function_length = sum(lengths) / len(lengths)
    else:
        # No functions — treat entire file as one block
        result.avg_function_length = float(total_lines)

    # Cyclomatic complexity (whole file)
    result.complexity_score = _calculate_cyclomatic_complexity(tree.root_node)

    # Calculate AI probability
    result.ai_probability = _calculate_ai_probability(result)

    return result


def _calculate_ai_probability(result: FileAnalysisResult) -> float:
    """
    Calculate a rule-based AI probability score (0.0 – 1.0).

    Rules:
      - comment_ratio > 0.3       → +0.20  (AI tends to over-comment)
      - avg_function_length > 50  → +0.15  (AI tends to produce large blocks)
      - single_commit_ratio > 0.7 → +0.30  (bulk paste indicator)
      - high complexity + single commit → +0.25
    """
    score = 0.0

    # Rule 1: Excessive comment ratio (AI code tends to over-comment)
    if result.comment_ratio > 0.3:
        score += 0.20

    # Rule 2: Long functions (AI tends to produce large blocks)
    if result.avg_function_length > 50:
        score += 0.15

    # Rule 3: Large change in a single commit (bulk paste indicator)
    if result.single_commit_ratio > 0.7:
        score += 0.30

    # Rule 4: High complexity + single-commit
    if result.complexity_score > 10 and result.single_commit_ratio > 0.5:
        score += 0.25

    # Normalize to 0.0 – 1.0
    return min(score, 1.0)
