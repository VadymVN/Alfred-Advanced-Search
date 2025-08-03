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

# Фикстуры для тестов
@pytest.fixture
def temp_directory(tmp_path):
    """Создает временную директорию с тестовыми файлами."""
    # Создаем обычные файлы
    (tmp_path / "test1.txt").touch()
    (tmp_path / "test2.py").touch()
    
    # Создаем скрытый файл
    (tmp_path / ".hidden").touch()
    
    # Создаем .app файл
    app_dir = tmp_path / "TestApp.app"
    app_dir.mkdir()
    
    # Создаем поддиректорию с файлами
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "subfile.txt").touch()
    
    return tmp_path

# Тесты для функции should_exclude
def test_should_exclude_hidden_files():
    """Тест исключения скрытых файлов."""
    assert should_exclude(".hidden") == True
    assert should_exclude("normal.txt") == False

def test_should_exclude_app_bundles():
    """Тест исключения .app бандлов."""
    assert should_exclude("TestApp.app") == True
    assert should_exclude("test.txt") == False

def test_should_exclude_patterns():
    """Тест всех паттернов исключения."""
    assert should_exclude(".test") == True  # Скрытый файл
    assert should_exclude("test.app") == True  # App бандл
    assert should_exclude("test.txt") == False  # Обычный файл

# Тесты для функции create_item
def test_create_item_file():
    """Тест создания элемента для файла."""
    path = Path("/test/file.txt")
    item = create_item(path, is_file=True)
    
    assert item["title"] == "file.txt"
    assert item["subtitle"].startswith("📄")
    assert item["arg"] == str(path)
    assert item["type"] == "file"
    assert item["valid"] == True

def test_create_item_directory():
    """Тест создания элемента для директории."""
    path = Path("/test/dir")
    item = create_item(path, is_file=False)
    
    assert item["title"] == "dir"
    assert item["subtitle"].startswith("📂")
    assert item["arg"] == str(path)
    assert item["type"] == "default"
    assert item["valid"] == True

def test_create_item_root():
    """Тест создания элемента для корневой директории."""
    path = Path("/")
    item = create_item(path, is_file=False)
    
    assert item["title"] == "/"
    assert item["subtitle"].startswith("📂")
    assert item["arg"] == "/"

# Тесты для функции list_directory
def test_list_directory_contents(temp_directory):
    """Тест листинга содержимого директории."""
    items = list_directory(temp_directory)
    
    # Проверяем количество видимых файлов (исключая .hidden и .app)
    assert len(items) == 3  # test1.txt, test2.py, subdir

def test_list_directory_permission_error(tmp_path):
    """Тест обработки ошибки доступа к директории."""
    # Создаем директорию без прав доступа
    no_access_dir = tmp_path / "no_access"
    no_access_dir.mkdir()
    os.chmod(no_access_dir, 0o000)
    
    items = list_directory(no_access_dir)
    assert len(items) == 1
    assert items[0]["title"] == "Permission denied"
    assert items[0]["valid"] == False
    
    # Восстанавливаем права для очистки
    os.chmod(no_access_dir, 0o755)

# Тесты для функции search_files
def test_search_files_basic(temp_directory):
    """Тест базового поиска файлов."""
    results = search_files("test", temp_directory)
    assert len(results) == 2  # test1.txt и test2.py

def test_search_files_case_insensitive(temp_directory):
    """Тест поиска файлов без учета регистра."""
    results = search_files("TEST", temp_directory)
    assert len(results) == 2  # должен найти test1.txt и test2.py

def test_search_files_with_depth(temp_directory):
    """Тест поиска файлов с ограничением глубины."""
    results = search_files("subfile", temp_directory, depth=1)
    assert len(results) == 1  # должен найти subfile.txt в поддиректории

def test_search_files_empty_query(temp_directory):
    """Тест поиска с пустым запросом."""
    results = search_files("", temp_directory)
    assert len(results) == 0

# Тесты для функции handle_cd_up
def test_handle_cd_up_normal():
    """Тест перехода на уровень выше."""
    current = Path("/test/directory")
    results = handle_cd_up(current)
    
    assert len(results) == 1
    assert results[0]["title"] == "test"
    assert results[0]["arg"] == "/test"

def test_handle_cd_up_root():
    """Тест перехода выше корневой директории."""
    current = Path("/")
    results = handle_cd_up(current)
    
    assert len(results) == 1
    assert results[0]["title"] == "/"
    assert results[0]["arg"] == "/"

# Тесты интеграции с Alfred
def test_alfred_json_output(temp_directory, capsys):
    """Тест формата вывода JSON для Alfred."""
    # Подготавливаем тестовое окружение
    os.environ['scope'] = str(temp_directory)
    sys.argv = ['search.py', 'test']
    
    # Запускаем main()
    from search import main
    main()
    
    # Получаем вывод
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    
    # Проверяем структуру JSON
    assert "items" in output
    assert isinstance(output["items"], list)
    for item in output["items"]:
        assert "title" in item
        assert "subtitle" in item
        assert "arg" in item
        assert "valid" in item
        assert "type" in item