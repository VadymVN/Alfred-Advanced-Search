#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import sys
import pytest
from pathlib import Path
from search import (
    should_exclude,
    create_item,
    list_directory,
    search_files,
    handle_cd_up,
    EXCLUDED_PATTERNS,
)

# Test fixtures
@pytest.fixture
def temp_directory(tmp_path):
    """Creates a temporary directory with test files."""
    # Create regular files
    (tmp_path / "test1.txt").touch()
    (tmp_path / "test2.py").touch()
    
    # Create hidden file
    (tmp_path / ".hidden").touch()
    
    # Create .app file
    app_dir = tmp_path / "TestApp.app"
    app_dir.mkdir()
    
    # Create subdirectory with files
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "subfile.txt").touch()
    
    return tmp_path

# Tests for should_exclude function
def test_should_exclude_hidden_files():
    """Test hidden files exclusion."""
    assert should_exclude(".hidden") == True
    assert should_exclude("normal.txt") == False

def test_should_exclude_app_bundles():
    """Test .app bundles exclusion."""
    assert should_exclude("TestApp.app") == True
    assert should_exclude("test.txt") == False

def test_should_exclude_patterns():
    """Test all exclusion patterns."""
    assert should_exclude(".test") == True  # Hidden file
    assert should_exclude("test.app") == True  # App bundle
    assert should_exclude("test.txt") == False  # Regular file

# Tests for create_item function
def test_create_item_file():
    """Test creating item for file."""
    path = Path("/test/file.txt")
    item = create_item(path, is_file=True)
    
    assert item["title"] == "file.txt"
    assert item["subtitle"].startswith("📄")
    assert item["arg"] == str(path)
    assert item["type"] == "file"
    assert item["valid"] == True

def test_create_item_directory():
    """Test creating item for directory."""
    path = Path("/test/dir")
    item = create_item(path, is_file=False)
    
    assert item["title"] == "dir"
    assert item["subtitle"].startswith("📂")
    assert item["arg"] == str(path)
    assert item["type"] == "default"
    assert item["valid"] == True

def test_create_item_root():
    """Test creating item for root directory."""
    path = Path("/")
    item = create_item(path, is_file=False)
    
    assert item["title"] == "/"
    assert item["subtitle"].startswith("📂")
    assert item["arg"] == "/"

# Tests for list_directory function
def test_list_directory_contents(temp_directory):
    """Test directory contents listing."""
    items = list_directory(temp_directory)
    
    # Check number of visible files (excluding .hidden and .app)
    assert len(items) == 3  # test1.txt, test2.py, subdir

def test_list_directory_permission_error(tmp_path):
    """Test directory access error handling."""
    # Create directory without access rights
    no_access_dir = tmp_path / "no_access"
    no_access_dir.mkdir()
    os.chmod(no_access_dir, 0o000)
    
    items = list_directory(no_access_dir)
    assert len(items) == 1
    assert items[0]["title"] == "Permission denied"
    assert items[0]["valid"] == False
    
    # Restore permissions for cleanup
    os.chmod(no_access_dir, 0o755)

# Tests for search_files function
def test_search_files_basic(temp_directory):
    """Test basic file search."""
    results = search_files("test", temp_directory)
    assert len(results) == 2  # test1.txt and test2.py

def test_search_files_case_insensitive(temp_directory):
    """Test case-insensitive file search."""
    results = search_files("TEST", temp_directory)
    assert len(results) == 2  # should find test1.txt and test2.py

def test_search_files_with_depth(temp_directory):
    """Test file search with depth limit."""
    results = search_files("subfile", temp_directory, depth=1)
    assert len(results) == 1  # should find subfile.txt in subdirectory

def test_search_files_empty_query(temp_directory):
    """Test search with empty query."""
    results = search_files("", temp_directory)
    assert len(results) == 0

# Tests for handle_cd_up function
def test_handle_cd_up_normal():
    """Test moving up one level."""
    current = Path("/test/directory")
    results = handle_cd_up(current)
    
    assert len(results) == 1
    assert results[0]["title"] == "test"
    assert results[0]["arg"] == "/test"

def test_handle_cd_up_root():
    """Test moving up from root directory."""
    current = Path("/")
    results = handle_cd_up(current)
    
    assert len(results) == 1
    assert results[0]["title"] == "/"
    assert results[0]["arg"] == "/"

# Alfred integration tests
def test_alfred_json_output(temp_directory, capsys):
    """Test JSON output format for Alfred."""
    # Prepare test environment
    os.environ['scope'] = str(temp_directory)
    sys.argv = ['search.py', 'test']
    
    # Run main()
    from search import main
    main()
    
    # Get output
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    
    # Check JSON structure
    assert "items" in output
    assert isinstance(output["items"], list)
    for item in output["items"]:
        assert "title" in item
        assert "subtitle" in item
        assert "arg" in item
        assert "valid" in item
        assert "type" in item