import pytest
from pathlib import Path
from unittest.mock import patch
from src.skills.knowledge_retrieval import retrieve_knowledge

def test_retrieve_knowledge_success(tmp_path):
    # Setup temporary assets dir and file
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "rules.txt").write_text("Rules data", encoding="utf-8")

    with patch("src.skills.knowledge_retrieval.ASSETS_DIR", assets):
        result = retrieve_knowledge("rules.txt")
        assert result == "Rules data"

def test_retrieve_knowledge_not_found(tmp_path):
    # Empty dir without 'assets'
    with patch("src.skills.knowledge_retrieval.ASSETS_DIR", tmp_path / "assets_not_exist"):
        result = retrieve_knowledge("notfound.txt")
        assert "Error: assets directory not found." in result

def test_retrieve_knowledge_file_not_found(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()

    with patch("src.skills.knowledge_retrieval.ASSETS_DIR", assets):
        result = retrieve_knowledge("notfound.txt")
        assert "Error:" in result
