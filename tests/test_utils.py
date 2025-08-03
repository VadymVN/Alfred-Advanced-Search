#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from utils import FileSystemHelper, SearchHelper, WorkflowHelper

class TestFileSystemHelper:
    @pytest.fixture
    def fs_helper(self):
        return FileSystemHelper(use_spotlight=False)
    
    @pytest.fixture
    def fs_helper_spotlight(self):
        return FileSystemHelper(use_spotlight=True)
    
    def test_init_without_spotlight(self, fs_helper):
        assert fs_helper.use_spotlight is False
        
    @patch('os.system')
    def test_init_with_spotlight(self, mock_system):
        mock_system.return_value = 0
        helper = FileSystemHelper(use_spotlight=True)
        assert helper.use_spotlight is True
        assert helper.spotlight_available is True
        mock_system.assert_called_once_with('mdutil -s / > /dev/null 2>&1')
        
    @patch('os.system')
    def test_init_with_spotlight_failure(self, mock_system):
        mock_system.side_effect = Exception("Failed")
        helper = FileSystemHelper(use_spotlight=True)
        assert helper.spotlight_available is False
        
    def test_get_file_metadata_file(self, fs_helper, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.touch()
        
        metadata = fs_helper.get_file_metadata(test_file)
        assert metadata["name"] == "test.txt"
        assert metadata["type"] == "file"
        assert metadata["icon"] == "📄"
        assert str(tmp_path) in metadata["path"]
        
    def test_get_file_metadata_directory(self, fs_helper, tmp_path):
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        
        metadata = fs_helper.get_file_metadata(test_dir)
        assert metadata["name"] == "test_dir"
        assert metadata["type"] == "directory"
        assert metadata["icon"] == "📂"
        assert str(tmp_path) in metadata["path"]
        
    @patch('subprocess.run')
    def test_get_file_metadata_with_spotlight(self, mock_run, fs_helper_spotlight, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.touch()
        
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = """kMDItemDisplayName = "Test File"
kMDItemKind = "Text Document"
invalid_line
key = (null)"""
        mock_run.return_value = mock_process
        
        metadata = fs_helper_spotlight.get_file_metadata(test_file)
        assert "kMDItemDisplayName" in metadata
        assert metadata["kMDItemDisplayName"] == "Test File"
        assert metadata["kMDItemKind"] == "Text Document"
        
    @patch('subprocess.run')
    def test_get_file_metadata_with_spotlight_exception(self, mock_run, fs_helper_spotlight, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.touch()
        mock_run.side_effect = Exception("Failed to get metadata")
        metadata = fs_helper_spotlight.get_file_metadata(test_file)
        assert metadata["name"] == "test.txt"
        assert metadata["type"] == "file"

class TestSearchHelper:
    @pytest.fixture
    def search_helper(self):
        fs_helper = FileSystemHelper(use_spotlight=False)
        return SearchHelper(fs_helper)
    
    def test_fuzzy_match_exact(self, search_helper):
        assert search_helper.fuzzy_match("test", "test file") is True
        assert search_helper.fuzzy_match("file", "test file") is True
        
    def test_fuzzy_match_case_insensitive(self, search_helper):
        assert search_helper.fuzzy_match("TEST", "test file") is True
        assert search_helper.fuzzy_match("test", "TEST FILE") is True
        
    def test_fuzzy_match_partial(self, search_helper):
        assert search_helper.fuzzy_match("tst", "test") is True
        assert search_helper.fuzzy_match("fl", "file") is True
        
    def test_fuzzy_match_negative(self, search_helper):
        assert search_helper.fuzzy_match("xyz", "test file") is False
        assert search_helper.fuzzy_match("tset", "test") is False
        
    def test_filter_by_pattern_regex(self, search_helper):
        items = [Path("test.txt"), Path("best.txt"), Path("rest.doc")]
        filtered = search_helper.filter_by_pattern(items, r".*\.txt$")
        assert len(filtered) == 2
        assert Path("test.txt") in filtered
        assert Path("best.txt") in filtered
        
    def test_filter_by_pattern_simple(self, search_helper):
        items = [Path("test.txt"), Path("best.txt"), Path("rest.doc")]
        filtered = search_helper.filter_by_pattern(items, "test")
        assert len(filtered) == 1
        assert Path("test.txt") in filtered
        
    def test_filter_by_pattern_invalid_regex(self, search_helper):
        items = [Path("test.txt"), Path("best.txt"), Path("rest.doc")]
        filtered = search_helper.filter_by_pattern(items, "[invalid")  # Invalid regex pattern
        assert len(filtered) == 0

class TestWorkflowHelper:
    def test_format_item_basic(self):
        item = WorkflowHelper.format_item(
            title="Test Title",
            subtitle="Test Subtitle",
            arg="test-arg"
        )
        assert item["title"] == "Test Title"
        assert item["subtitle"] == "Test Subtitle"
        assert item["arg"] == "test-arg"
        assert item["valid"] is True
        assert item["type"] == "default"
        
    def test_format_item_with_icon(self):
        item = WorkflowHelper.format_item(
            title="Test",
            subtitle="Test",
            arg="test",
            icon="icon.png"
        )
        assert "icon" in item
        assert item["icon"]["path"] == "icon.png"
        
    def test_format_item_with_text(self):
        text = {"copy": "Copy text", "largetype": "Large text"}
        item = WorkflowHelper.format_item(
            title="Test",
            subtitle="Test",
            arg="test",
            text=text
        )
        assert "text" in item
        assert item["text"] == text
        
    @patch.dict(os.environ, {'scope': '/test/path'})
    def test_get_scope(self):
        scope = WorkflowHelper.get_scope()
        assert isinstance(scope, Path)
        assert str(scope) == '/test/path'
        
    def test_get_scope_default(self):
        with patch.dict(os.environ, clear=True):
            scope = WorkflowHelper.get_scope()
            assert isinstance(scope, Path)
            assert str(scope) == str(Path.home())
            
    def test_set_scope(self):
        test_path = Path("/test/new/path")
        WorkflowHelper.set_scope(test_path)
        assert os.environ['scope'] == str(test_path)
        
    @patch.dict(os.environ, {'SEARCH_DEPTH': '2.5'})
    def test_get_search_depth_float(self):
        depth = WorkflowHelper.get_search_depth()
        assert depth == 2.5
        
    @patch.dict(os.environ, {'SEARCH_DEPTH': 'inf'})
    def test_get_search_depth_inf(self):
        depth = WorkflowHelper.get_search_depth()
        assert depth == float('inf')
        
    def test_get_search_depth_default(self):
        with patch.dict(os.environ, clear=True):
            depth = WorkflowHelper.get_search_depth()
            assert depth == float('inf')
            
    def test_get_search_depth_invalid(self):
        with patch.dict(os.environ, {'SEARCH_DEPTH': 'invalid'}):
            depth = WorkflowHelper.get_search_depth()
            assert depth == float('inf')