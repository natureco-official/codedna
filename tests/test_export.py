"""Tests for the export feature."""

import json
from pathlib import Path
from codedna.db import export_all_data, get_db_path, init_db, save_commit


def test_export_all_data_empty(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    data = export_all_data(db_path)
    assert "commits" in data
    assert "file_scores" in data
    assert "sprints" in data
    assert "protected_modules" in data
    assert "file_ownership" in data
    assert "interview_sessions" in data
    assert "exported_at" in data
    assert len(data["commits"]) == 0


def test_export_all_data_with_data(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    save_commit("abc123", "testuser", 1000000, 3, 4.0, db_path)
    data = export_all_data(db_path)
    assert len(data["commits"]) == 1
    assert data["commits"][0]["commit_hash"] == "abc123"


def test_export_json_serializable(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    save_commit("abc123", "testuser", 1000000, 3, 4.0, db_path)
    data = export_all_data(db_path)
    # Verify it can be serialized to JSON
    json_str = json.dumps(data, indent=2, default=str)
    assert len(json_str) > 0
    parsed = json.loads(json_str)
    assert parsed["commits"][0]["commit_hash"] == "abc123"
