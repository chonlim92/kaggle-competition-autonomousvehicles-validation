import pytest
import os
from unittest.mock import patch, mock_open, MagicMock
from src.skills.kaggle.pipeline import KagglePipeline

def test_kaggle_pipeline_download_success():
    pipeline = KagglePipeline("test-comp")
    with patch("os.makedirs"), \
         patch("src.skills.kaggle.pipeline.kaggle") as mock_kaggle:
        result = pipeline.download_dataset("data/test")
        assert result is True
        mock_kaggle.api.authenticate.assert_called_once()
        mock_kaggle.api.competition_download_files.assert_called_once_with("test-comp", path="data/test", quiet=False)

def test_kaggle_pipeline_download_failure():
    pipeline = KagglePipeline()
    with patch("os.makedirs"), \
         patch("src.skills.kaggle.pipeline.kaggle") as mock_kaggle:
        mock_kaggle.api.authenticate.side_effect = Exception("Auth failed")
        result = pipeline.download_dataset("data/test")
        assert result is False

def test_generate_submission_success():
    pipeline = KagglePipeline()
    with patch("builtins.open", mock_open()) as mock_file:
        result = pipeline.generate_submission([{"id": 1}], "out.jsonl")
        assert result is True
        mock_file().write.assert_called_once_with('{"id": 1}\n')

def test_generate_submission_failure():
    pipeline = KagglePipeline()
    with patch("builtins.open", side_effect=Exception("Disk error")):
        result = pipeline.generate_submission([{"id": 1}], "out.jsonl")
        assert result is False
