"""Tests for the analyzer module."""

from pathlib import Path
from codedna.analyzer import (
    analyze_commit_message,
    explain_ai_score,
    FileAnalysisResult,
    analyze_file,
)


def test_analyze_commit_message_conventional():
    result = analyze_commit_message("feat(auth): add JWT token refresh endpoint")
    assert result["is_conventional"] is True
    assert result["type"] == "feat"
    assert result["category"] == "Feature"
    assert result["scope"] == "auth"
    assert result["quality_score"] >= 4.0


def test_analyze_commit_message_with_ticket():
    result = analyze_commit_message("fix: handle null pointer (JIRA-123)")
    assert result["is_conventional"] is True
    assert result["has_ticket"] is True


def test_analyze_commit_message_wip():
    result = analyze_commit_message("WIP: working on it")
    assert result["category"] == "WIP"
    assert result["quality_score"] <= 2.0


def test_analyze_commit_message_vague():
    result = analyze_commit_message("vague")
    assert result["category"] == "Vague"
    assert result["quality_score"] == 1.0


def test_analyze_commit_message_merge():
    result = analyze_commit_message("Merge branch main into feature/x")
    assert result["category"] == "Merge"
    assert result["quality_score"] == 2.0


def test_analyze_commit_message_empty():
    result = analyze_commit_message("")
    assert result["category"] is None


def test_explain_ai_score_high():
    r = FileAnalysisResult(
        file_path="test.py",
        ai_probability=0.75,
        complexity_score=12,
        comment_ratio=0.35,
        avg_function_length=65,
        single_commit_ratio=0.85,
        total_lines=100,
        function_count=3,
    )
    reasons = explain_ai_score(r)
    assert len(reasons) >= 3
    assert any("comment ratio" in reason.lower() for reason in reasons)
    assert any("function length" in reason.lower() for reason in reasons)
    assert any("single-commit" in reason.lower() for reason in reasons)


def test_explain_ai_score_low():
    r = FileAnalysisResult(
        file_path="test.py",
        ai_probability=0.05,
        complexity_score=2,
        comment_ratio=0.05,
        avg_function_length=15,
        single_commit_ratio=0.1,
        total_lines=30,
        function_count=2,
    )
    reasons = explain_ai_score(r)
    assert any("normal range" in reason for reason in reasons)


def test_analyze_file_python(tmp_path):
    py_file = tmp_path / "test.py"
    py_file.write_text("def hello():\n    print('hello world')\n")
    result = analyze_file(py_file)
    assert result.file_path == str(py_file)
    assert result.total_lines == 2
    assert result.function_count == 1
    assert result.error is None
    assert len(result.explanation) > 0


def test_analyze_file_unsupported(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("hello")
    result = analyze_file(txt_file)
    assert result.unsupported is True


def test_analyze_file_complex(tmp_path):
    py_file = tmp_path / "complex.py"
    py_file.write_text(
        "def process(data):\n"
        "    if data:\n"
        "        for item in data:\n"
        "            if item > 0:\n"
        "                print(item)\n"
        "    else:\n"
        "        return None\n"
    )
    result = analyze_file(py_file)
    assert result.function_count == 1
    assert result.complexity_score >= 3
    assert result.ai_probability >= 0


def test_file_analysis_result_properties():
    r = FileAnalysisResult(file_path="test.py", complexity_score=20, ai_probability=0.8)
    assert r.complexity_label == "High"
    assert r.ai_color == "🔴"

    r2 = FileAnalysisResult(file_path="test.py", complexity_score=3, ai_probability=0.2)
    assert r2.complexity_label == "Low"
    assert r2.ai_color == "🟢"

    r3 = FileAnalysisResult(file_path="test.py", complexity_score=8, ai_probability=0.5)
    assert r3.complexity_label == "Medium"
    assert r3.ai_color == "🟡"
