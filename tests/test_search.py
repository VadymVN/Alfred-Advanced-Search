#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import sys
import pytest
from pathlib import Path
from unittest.mock import patch
from search import (
    should_exclude,
    create_item,
    list_directory,
    search_files,
    handle_cd_up,
    handle_find,
    handle_grep,
    handle_tree,
    fuzzy_match,
    match_score,
    load_settings,
    _format_size,
)


# --- Fixtures ---


@pytest.fixture
def temp_directory(tmp_path):
    """Creates a temporary directory with test files."""
    (tmp_path / "test1.txt").write_text("hello world")
    (tmp_path / "test2.py").write_text("print('test')")
    (tmp_path / ".hidden").touch()

    app_dir = tmp_path / "TestApp.app"
    app_dir.mkdir()

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "subfile.txt").write_text("nested content here")

    deep = subdir / "deep"
    deep.mkdir()
    (deep / "deepfile.txt").write_text("deep content")

    return tmp_path


# --- should_exclude ---


def test_should_exclude_hidden_files():
    assert should_exclude(".hidden") is True
    assert should_exclude("normal.txt") is False


def test_should_exclude_app_bundles():
    assert should_exclude("TestApp.app") is True
    assert should_exclude("test.txt") is False


# --- fuzzy_match ---


def test_fuzzy_match_exact():
    assert fuzzy_match("test", "test file") is True
    assert fuzzy_match("file", "test file") is True


def test_fuzzy_match_case_insensitive():
    assert fuzzy_match("TEST", "test file") is True
    assert fuzzy_match("test", "TEST FILE") is True


def test_fuzzy_match_partial():
    assert fuzzy_match("tst", "test") is True
    assert fuzzy_match("fl", "file") is True


def test_fuzzy_match_negative():
    assert fuzzy_match("xyz", "test file") is False
    assert fuzzy_match("tset", "test") is False


# --- match_score ---


def test_match_score_exact():
    assert match_score("test", "test") == 0


def test_match_score_prefix():
    assert match_score("test", "testing") == 1


def test_match_score_substring():
    assert match_score("est", "testing") == 2


def test_match_score_fuzzy():
    assert match_score("tst", "test") == 3


def test_match_score_no_match():
    assert match_score("xyz", "test") == 99


# --- create_item ---


def test_create_item_file():
    path = Path("/test/file.txt")
    item = create_item(path, is_file=True)
    assert item["title"] == "file.txt"
    assert "📄" in item["subtitle"]
    assert item["arg"] == str(path)
    assert item["type"] == "file"
    assert item["valid"] is True
    assert "mods" in item
    assert "cmd" in item["mods"]
    assert "ctrl" in item["mods"]


def test_create_item_directory():
    path = Path("/test/dir")
    item = create_item(path, is_file=False)
    assert item["title"] == "dir"
    assert "📂" in item["subtitle"]
    assert item["type"] == "default"
    assert item["variables"]["scope"] == str(path)
    assert "keepalive" in item


def test_create_item_root():
    path = Path("/")
    item = create_item(path, is_file=False)
    assert item["title"] == "/"
    assert item["arg"] == "/"


# --- list_directory ---


def test_list_directory_contents(temp_directory):
    items = list_directory(temp_directory)
    names = [i["title"] for i in items]
    # Should exclude .hidden and TestApp.app
    assert ".hidden" not in names
    assert "TestApp.app" not in names
    assert "test1.txt" in names
    assert "test2.py" in names
    assert "subdir" in names


def test_list_directory_sorted(temp_directory):
    """Directories should come before files."""
    items = list_directory(temp_directory)
    types = [i["type"] for i in items]
    # default (dirs) should come before file types
    dir_indices = [i for i, t in enumerate(types) if t == "default"]
    file_indices = [i for i, t in enumerate(types) if t == "file"]
    if dir_indices and file_indices:
        assert max(dir_indices) < min(file_indices)


def test_list_directory_permission_error(tmp_path):
    no_access_dir = tmp_path / "no_access"
    no_access_dir.mkdir()
    os.chmod(no_access_dir, 0o000)
    items = list_directory(no_access_dir)
    assert len(items) == 1
    assert items[0]["title"] == "Permission denied"
    os.chmod(no_access_dir, 0o755)


# --- search_files ---


@patch("search._has_fd", return_value=False)
def test_search_files_basic(mock_fd, temp_directory):
    results = search_files("test", temp_directory)
    names = [r["title"] for r in results]
    assert "test1.txt" in names
    assert "test2.py" in names


@patch("search._has_fd", return_value=False)
def test_search_files_case_insensitive(mock_fd, temp_directory):
    results = search_files("TEST", temp_directory)
    assert len(results) >= 2


@patch("search._has_fd", return_value=False)
def test_search_files_with_depth(mock_fd, temp_directory):
    results = search_files("subfile", temp_directory, depth=1)
    assert len(results) == 1


@patch("search._has_fd", return_value=False)
def test_search_files_deep_recursion(mock_fd, temp_directory):
    """Tests that recursion works beyond 1 level (bug fix)."""
    results = search_files("deepfile", temp_directory, depth=3)
    names = [r["title"] for r in results]
    assert "deepfile.txt" in names


@patch("search._has_fd", return_value=False)
def test_search_files_empty_query(mock_fd, temp_directory):
    results = search_files("", temp_directory)
    assert len(results) == 0


@patch("search._has_fd", return_value=False)
def test_search_files_fuzzy(mock_fd, temp_directory):
    """Fuzzy match should find 'tst' -> 'test'."""
    results = search_files("tst", temp_directory, depth=1)
    names = [r["title"] for r in results]
    assert "test1.txt" in names


@patch("search._has_fd", return_value=False)
def test_search_files_relevance_order(mock_fd, tmp_path):
    """Exact matches should come before prefix, substring, fuzzy."""
    (tmp_path / "abc").touch()
    (tmp_path / "abcdef").touch()
    (tmp_path / "xabcx").touch()
    results = search_files("abc", tmp_path, depth=1)
    names = [r["title"] for r in results]
    assert names[0] == "abc"  # exact match first
    assert names[1] == "abcdef"  # prefix second


# --- handle_cd_up ---


def test_handle_cd_up_normal():
    current = Path("/test/directory")
    results = handle_cd_up(current)
    assert len(results) == 1
    assert results[0]["title"] == "test"
    assert results[0]["arg"] == "/test"


def test_handle_cd_up_root():
    current = Path("/")
    results = handle_cd_up(current)
    assert len(results) == 1
    assert results[0]["arg"] == "/"


# --- handle_find ---


@patch("search._has_fd", return_value=False)
def test_handle_find_basic(mock_fd, temp_directory):
    results = handle_find("deepfile", temp_directory)
    names = [r["title"] for r in results]
    assert "deepfile.txt" in names


def test_handle_find_empty():
    results = handle_find("", Path("/tmp"))
    assert len(results) == 1
    assert results[0]["valid"] is False


# --- handle_grep ---


def test_handle_grep_basic(temp_directory):
    results = handle_grep("hello", temp_directory)
    assert len(results) >= 1
    assert "test1.txt:1" in results[0]["title"]


def test_handle_grep_nested(temp_directory):
    results = handle_grep("nested content", temp_directory)
    assert len(results) >= 1
    assert "subfile.txt" in results[0]["title"]


def test_handle_grep_empty():
    results = handle_grep("", Path("/tmp"))
    assert len(results) == 1
    assert results[0]["valid"] is False


def test_handle_grep_no_match(temp_directory):
    results = handle_grep("zzz_no_match_zzz", temp_directory)
    assert len(results) == 0


# --- handle_tree ---


def test_handle_tree_basic(temp_directory):
    results = handle_tree(temp_directory)
    assert len(results) > 0
    titles = [r["title"] for r in results]
    # Should contain tree connectors
    assert any("├──" in t or "└──" in t for t in titles)


def test_handle_tree_contains_files(temp_directory):
    results = handle_tree(temp_directory)
    all_titles = " ".join(r["title"] for r in results)
    assert "subdir" in all_titles
    assert "test1.txt" in all_titles


# --- format_size ---


def test_format_size():
    assert _format_size(0) == "0B"
    assert _format_size(512) == "512B"
    assert "KB" in _format_size(1024)
    assert "MB" in _format_size(1024 * 1024)


# --- settings ---


def test_load_settings_defaults():
    settings = load_settings()
    assert "search_depth" in settings
    assert "max_results" in settings
    assert settings["search_depth"] == 3


# --- Alfred JSON output integration ---


def test_alfred_json_output(temp_directory, capsys):
    os.environ["scope"] = str(temp_directory)
    sys.argv = ["search.py", "test"]
    from search import main

    main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "items" in output
    assert isinstance(output["items"], list)
    for item in output["items"]:
        assert "title" in item
        assert "arg" in item


def test_alfred_ls_command(temp_directory, capsys):
    os.environ["scope"] = str(temp_directory)
    sys.argv = ["search.py", "ls"]
    from search import main

    main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "items" in output
    assert len(output["items"]) >= 3


def test_alfred_tree_command(temp_directory, capsys):
    os.environ["scope"] = str(temp_directory)
    sys.argv = ["search.py", "tree"]
    from search import main

    main()
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert "items" in output
    assert len(output["items"]) > 0
