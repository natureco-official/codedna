"""AST analysis and AI signature detection module."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


CONVENTIONAL_COMMIT_PATTERNS = {
    "feat": "Feature",
    "fix": "Bug Fix",
    "docs": "Documentation",
    "refactor": "Refactor",
    "style": "Style",
    "test": "Test",
    "chore": "Chore",
    "ci": "CI",
    "build": "Build",
    "perf": "Performance",
    "revert": "Revert",
    "wip": "WIP",
    "merge": "Merge",
    "release": "Release",
}

COMMIT_QUALITY_MAP = {
    "Feature": 4.5,
    "Bug Fix": 4.0,
    "Refactor": 3.5,
    "Documentation": 3.5,
    "Style": 2.0,
    "Test": 4.0,
    "Chore": 2.5,
    "CI": 3.0,
    "Build": 3.0,
    "Performance": 4.5,
    "Revert": 1.0,
    "WIP": 1.5,
    "Merge": 2.0,
    "Release": 3.5,
}

import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser, Node

# TypeScript parser — fall back to JS parser if not installed
try:
    import tree_sitter_typescript as tstypescript
    _TS_LANG = tstypescript.language_typescript()
    _TSX_LANG = tstypescript.language_tsx()
except Exception:
    _TS_LANG = tsjavascript.language()
    _TSX_LANG = tsjavascript.language()

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
    content_ai_signal: float = 0.0   # content-based AI signal (code patterns, 0–1)
    total_lines: int = 0
    function_count: int = 0
    unsupported: bool = False   # kept for internal use
    error: Optional[str] = None     # kept for internal use
    explanation: list[str] = field(default_factory=list)
    commit_type: Optional[str] = None
    commit_quality: float = 2.5

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

    # Calculate AI probability (continuous + content-based)
    result.ai_probability = _calculate_ai_probability(result, source)

    # Generate explanation
    result.explanation = explain_ai_score(result)

    return result


def analyze_commit_message(message: str) -> dict:
    """
    Analyze a commit message and return:
      - type: conventional commit type (feat, fix, etc.)
      - category: human-readable category
      - quality_score: estimated quality (0-5)
      - has_ticket: whether it references a ticket (JIRA/GitHub issue)
      - is_conventional: whether it follows conventional commit format
      - scope: the scope if present (e.g. "auth" in "feat(auth): ...")
    """
    result = {
        "type": None,
        "category": None,
        "quality_score": 2.5,
        "has_ticket": False,
        "is_conventional": False,
        "scope": None,
    }

    if not message:
        return result

    first_line = message.strip().split("\n")[0]

    # Ticket reference detection
    ticket_patterns = [
        r"[A-Z]+-\d+",           # JIRA: PROJ-123
        r"#\d+",                 # GitHub: #42
        r"gh-\d+",               # GitHub CLI: gh-42
    ]
    for pat in ticket_patterns:
        if re.search(pat, first_line, re.IGNORECASE):
            result["has_ticket"] = True
            break

    # Conventional commit: type(scope): description
    conv_match = re.match(
        r"^(fix|feat|docs|refactor|style|test|chore|ci|build|perf|revert)"
        r"(\(([^)]+)\))?\s*:\s*(.+)",
        first_line,
        re.IGNORECASE,
    )
    if conv_match:
        result["is_conventional"] = True
        result["type"] = conv_match.group(1).lower()
        result["scope"] = conv_match.group(3)
        raw_type = conv_match.group(1).lower()
        category = CONVENTIONAL_COMMIT_PATTERNS.get(raw_type, "Unknown")
        result["category"] = category
        result["quality_score"] = COMMIT_QUALITY_MAP.get(category, 2.5)

        # Bonus for having a scope
        if result["scope"]:
            result["quality_score"] = min(result["quality_score"] + 0.5, 5.0)

        # Bonus for having a ticket reference
        if result["has_ticket"]:
            result["quality_score"] = min(result["quality_score"] + 0.5, 5.0)
    else:
        # Non-conventional message — estimate quality
        words = len(first_line.split())
        if words < 3:
            result["quality_score"] = 1.0
            result["category"] = "Vague"
        elif first_line.startswith("Merge"):
            result["category"] = "Merge"
            result["quality_score"] = 2.0
        elif "wip" in first_line.lower() or "work in progress" in first_line.lower():
            result["category"] = "WIP"
            result["quality_score"] = 1.5
        elif words > 10:
            result["quality_score"] = 3.5
            result["category"] = "Descriptive"
        else:
            result["category"] = "Standard"
            result["quality_score"] = 2.5

    return result


def explain_ai_score(result: FileAnalysisResult) -> list[str]:
    """
    Generate human-readable explanations for the AI probability score.
    Returns a list of reasons why the file scored as it did.
    """
    reasons: list[str] = []

    if result.content_ai_signal >= 0.15:
        pct = int(result.content_ai_signal * 100)
        reasons.append(
            f"Code carries AI-style patterns ({pct}% content signal) — e.g. type hints, "
            f"defensive boilerplate, 'step' comments, emoji"
        )

    if result.comment_ratio > 0.3:
        pct = int(result.comment_ratio * 100)
        reasons.append(
            f"High comment ratio ({pct}%) — AI-generated code tends to over-comment"
        )

    if result.avg_function_length > 50:
        reasons.append(
            f"Long avg. function length ({result.avg_function_length:.0f} lines) — "
            f"AI tends to produce larger blocks"
        )

    if result.single_commit_ratio > 0.7:
        pct = int(result.single_commit_ratio * 100)
        reasons.append(
            f"High single-commit ratio ({pct}%) — bulk paste indicator"
        )

    if result.complexity_score > 10 and result.single_commit_ratio > 0.5:
        reasons.append(
            f"High complexity ({result.complexity_score:.0f}) combined with bulk change — "
            f"complex AI-generated code pattern"
        )

    if result.function_count == 0:
        reasons.append("No functions detected — may be a config/data file")

    if not reasons:
        reasons.append("All metrics within normal range — likely human-written code")

    return reasons


def _smoothstep(x: float, lo: float, hi: float) -> float:
    """Continuous 0→1 ramp between lo and hi (replaces hard thresholds so scores
    are file-specific and granular instead of clustering on a few binned values)."""
    if hi <= lo:
        return 1.0 if x >= hi else 0.0
    t = max(0.0, min(1.0, (x - lo) / (hi - lo)))
    return t * t * (3.0 - 2.0 * t)


# Content-based AI-authorship patterns (regex, weight). These look at what the code
# actually *is* — the stylistic fingerprints AI assistants tend to leave — rather than
# only git history. Density of matches feeds the score directly.
_AI_CONTENT_PATTERNS: list[tuple[str, float]] = [
    (r"#\s*(Step\s*\d|Initialize|Return the|Create the|Loop through|Iterate over|Handle the|Validate|Check if|Set up|Ensure|First,|Finally,)", 1.0),
    (r"//\s*(Step\s*\d|Initialize|Return the|Create the|Handle the|Validate|Check if|Set up|Ensure)", 1.0),
    (r'"""', 0.25),                                      # docstrings (AI documents everything)
    (r"->\s*[A-Za-z_\[\"']", 0.45),                     # return type hints
    (r":\s*(str|int|float|bool|list|dict|tuple|Optional|Any|Dict|List|Union)\b", 0.35),  # param type hints
    (r"^\s*try:\s*$", 0.4),                              # defensive try/except everywhere
    (r"if\s+\w+\s+is\s+None", 0.4),                      # explicit None guards
    (r"except\s+Exception\b", 0.35),                     # broad catch-alls
    (r"[\U0001F300-\U0001FAFF☀-➿←-⇿✓✗]", 0.6),  # emoji/✓/✗/→ in code
    (r"\b(helper|handler|wrapper|manager|processor|validator)\b", 0.2),  # generic role names
    (r"console\.(log|error)\(.*(✓|✗|→|✅|❌|🧬|⚠)", 0.5),
]


def _content_ai_signal(source: str) -> float:
    """A content-based AI signal in [0,1], independent of git history: how strongly
    the code carries the stylistic fingerprints AI assistants tend to leave."""
    lines = source.splitlines()
    n = max(len(lines), 1)
    total = 0.0
    for pattern, weight in _AI_CONTENT_PATTERNS:
        try:
            matches = sum(1 for line in lines if re.search(pattern, line))
        except re.error:
            continue
        total += (matches / n) * weight
    # Saturating density → [0,1]; small densities still register, high ones plateau.
    return 1.0 - math.exp(-4.0 * total)


def _calculate_ai_probability(result: FileAnalysisResult, source: str = "") -> float:
    """Continuous, content-aware AI probability score (0.0 – 1.0).

    Combines graded structural signals (comments, function size, cyclomatic
    complexity), git-history signals (bulk single-commit paste) and a
    content-based fingerprint of AI code style. Unlike the previous four binary
    rules, every input is continuous so scores reflect each file individually.
    """
    # Graded structural / history signals — smooth ramps, not on/off thresholds.
    comment = _smoothstep(result.comment_ratio, 0.12, 0.45)
    func_len = _smoothstep(result.avg_function_length, 25.0, 90.0)
    bulk = _smoothstep(result.single_commit_ratio, 0.35, 0.90)
    complexity = _smoothstep(result.complexity_score, 6.0, 25.0)

    # Content fingerprint — the actual code style (strongest single signal).
    content = _content_ai_signal(source) if source else 0.0
    result.content_ai_signal = round(content, 4)

    # Weighted blend (weights sum to 1.0). Content carries the most weight because
    # it inspects what the code *is*, not just how it landed in git.
    score = (
        0.14 * comment
        + 0.12 * func_len
        + 0.20 * bulk
        + 0.12 * (complexity * bulk)   # complexity matters most when bulk-committed
        + 0.42 * content
    )
    return round(min(max(score, 0.0), 1.0), 4)
