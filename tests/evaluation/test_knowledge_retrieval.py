import pytest
import os
from unittest.mock import patch, mock_open
from src.skills.knowledge_retrieval import retrieve_knowledge

def test_retrieve_knowledge_success():
    with patch("src.skills.knowledge_retrieval.Path.exists", return_value=True), \
         patch("src.skills.knowledge_retrieval.Path.is_file", return_value=True), \
         patch("builtins.open", mock_open(read_data="Rules data")):
        result = retrieve_knowledge("rules.txt")
        assert result == "Rules data"

def test_retrieve_knowledge_not_found():
    with patch("src.skills.knowledge_retrieval.Path.exists", return_value=False):
        result = retrieve_knowledge("notfound.txt")
        assert "Error: assets directory not found." in result

def test_retrieve_knowledge_file_not_found():
    with patch("src.skills.knowledge_retrieval.ASSETS_DIR.exists", return_value=True), \
         patch("src.skills.knowledge_retrieval.Path.exists", side_effect=lambda: True if "assets" in str(locals().get('self', '')) else False):
        result = retrieve_knowledge("notfound.txt")
        assert "Error:" in result
