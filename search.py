#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Union, Literal

# Константы
SEARCH_DEPTH = 3  # Ограниченная глубина поиска по умолчанию
MAX_RESULTS = 50  # Максимальное количество результатов
EXCLUDED_PATTERNS = ['.', '.app']  # Паттерны для исключения файлов
DIR_FLAG = "1"  # Флаг для директорий
FILE_FLAG = "0"  # Флаг для файлов
COMMON_SEARCH_PATHS = [
    '~/Documents',
    '~/Downloads',
    '~/Desktop',
    '~/Projects',
    '~/Applications'
]  # Популярные директории для поиска

def should_exclude(name: str) -> bool:
    """Проверяет, нужно ли исключить файл/папку из результатов."""
    return name.startswith('.') or name.endswith('.app')

def create_item(path: Path, is_file: bool = True) -> Dict[str, str]:
    """
    Создает элемент для вывода в Alfred.
    
    Args:
        path (Path): Путь к файлу или директории
        is_file (bool): Флаг, указывающий является ли путь файлом (True) или директорией (False)
    
    Returns:
        Dict[str, str]: Словарь с информацией для Alfred, включая:
            - title: Имя файла/директории
            - subtitle: Путь к родительской директории с иконкой
            - arg: Полный путь
            - type: Тип элемента ('file' или 'default')
            - valid: Доступность элемента
            - variables: Дополнительные переменные (is_dir, scope для директорий)
    """
    variables = {
        "is_dir": FILE_FLAG if is_file else DIR_FLAG
    }
    
    item = {
        "title": path.name or str(path),
        "subtitle": f"📄 {path.parent}" if is_file else f"📂 {path.parent}",
        "arg": str(path),
        "type": "file" if is_file else "default",
        "valid": True,
        "variables": variables
    }

    if not is_file:
        item["variables"]["scope"] = str(path)
        item["autocomplete"] = str(path)
        item["keepalive"] = True
        
    return item

def list_directory(scope: Path) -> List[Dict[str, str]]:
    """Показывает содержимое текущей директории."""
    items = []
    try:
        for item in scope.iterdir():
            if should_exclude(item.name):
                continue
            items.append(create_item(item, item.is_file()))
    except PermissionError:
        items.append({
            "title": "Permission denied",
            "subtitle": f"Cannot access {scope}",
            "valid": False
        })
    return items

def search_files(query: str, scope: Path, depth: float = SEARCH_DEPTH, max_depth: int = 5, max_results: int = 50) -> List[Dict[str, str]]:
    """Ищет файлы по запросу с учетом глубины поиска."""
    if not query:  # Если запрос пустой, возвращаем пустой список
        return []
        
    items = []
    current_depth = 0
    visited = set()  # Для отслеживания уже посещенных директорий
    
    def walk(current_path: Path, current_depth: int):
        if current_depth > depth or current_depth > max_depth or len(items) >= max_results:
            return
            
        try:
            real_path = current_path.resolve()
            if real_path in visited:
                return
            visited.add(real_path)
            
            # Пропускаем проверку текущей директории, так как мы ищем только внутри неё
            
            # Проверяем содержимое только текущей директории
            for item in current_path.iterdir():
                if should_exclude(item.name):
                    continue
                
                if query.lower() in item.name.lower():
                    items.append(create_item(item, item.is_file()))
                    if len(items) >= max_results:
                        return
                
                # Рекурсивно обходим только поддиректории текущей директории
                if item.is_dir() and not item.is_symlink() and item.parent == scope:
                    walk(item, current_depth + 1)
                    if len(items) >= max_results:
                        return
                        
        except (PermissionError, OSError):
            pass
            
    walk(scope, current_depth)
    return items

def handle_cd_up(scope: Path) -> List[Dict[str, str]]:
    """Обрабатывает команду cd.. для перехода на уровень выше."""
    parent = scope.parent
    item = create_item(parent, is_file=False)  # Используем существующую функцию
    item["subtitle"] = "⬆️ Parent directory"  # Переопределяем subtitle
    return [item]

def get_search_paths() -> List[Path]:
    """Возвращает список директорий для поиска."""
    paths = []
    # Добавляем текущую директорию из переменной окружения Alfred
    scope_str = os.getenv('scope')
    if scope_str:
        paths.append(Path(scope_str))
    
    # Добавляем популярные директории
    for path_str in COMMON_SEARCH_PATHS:
        path = Path(os.path.expanduser(path_str))
        if path.exists() and path.is_dir():
            paths.append(path)
    
    return paths if paths else [Path.home()]

def main():
    try:
        # Получаем запрос от Alfred
        query = sys.argv[1] if len(sys.argv) > 1 else ""
        
        # Получаем текущую область поиска
        scope = Path(os.getenv('scope', os.path.expanduser('~')))
        
        # Инициализируем список результатов
        items = []
        
        # Обрабатываем специальные команды
        if query == "ls":
            items = list_directory(scope)
        elif query == "cd..":
            items = handle_cd_up(scope)
        else:
            # Обычный поиск файлов
            search_paths = get_search_paths()
            for path in search_paths:
                if len(items) >= MAX_RESULTS:
                    break
                try:
                    path_items = search_files(query, path, max_results=MAX_RESULTS - len(items))
                    items.extend(path_items)
                except (PermissionError, OSError):
                    continue
        
        # Если нет результатов, показываем сообщение
        if not items:
            items = [{
                "title": "No matches found",
                "subtitle": f"No items matching '{query}' in search paths",
                "arg": str(scope),  # Добавляем arg для совместимости
                "valid": False
            }]
        
        # Выводим результаты в формате JSON для Alfred
        print(json.dumps({"items": items[:MAX_RESULTS]}))
        
    except KeyboardInterrupt:
        # Обрабатываем прерывание поиска
        print(json.dumps({
            "items": [{
                "title": "Search interrupted",
                "subtitle": "The search was interrupted by user",
                "valid": False
            }]
        }))

if __name__ == "__main__":
    main()