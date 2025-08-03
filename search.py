#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Union

# Константы
SEARCH_DEPTH = float('inf')  # Бесконечная глубина поиска по умолчанию
EXCLUDED_PATTERNS = ['.', '.app']  # Паттерны для исключения файлов

def should_exclude(name: str) -> bool:
    """Проверяет, нужно ли исключить файл/папку из результатов."""
    return name.startswith('.') or name.endswith('.app')

def create_item(path: Path, is_file: bool = True) -> Dict[str, str]:
    """Создает элемент для вывода в Alfred."""
    return {
        "title": path.name or str(path),  # Используем str(path) для корневой директории
        "subtitle": f"📄 {path.parent}" if is_file else f"📂 {path.parent}",
        "arg": str(path),
        "type": "file" if is_file else "default",
        "valid": True
    }

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

def search_files(query: str, scope: Path, depth: float = SEARCH_DEPTH) -> List[Dict[str, str]]:
    """Ищет файлы по запросу с учетом глубины поиска."""
    if not query:  # Если запрос пустой, возвращаем пустой список
        return []
        
    items = []
    current_depth = 0
    
    def walk(current_path: Path, current_depth: int):
        if current_depth > depth:
            return
            
        try:
            for item in current_path.iterdir():
                if should_exclude(item.name):
                    continue
                    
                # Проверяем соответствие запросу (нечеткий поиск)
                if query.lower() in item.name.lower():
                    items.append(create_item(item, item.is_file()))
                    
                # Рекурсивно обходим директории
                if item.is_dir():
                    walk(item, current_depth + 1)
        except PermissionError:
            pass  # Пропускаем директории без доступа
            
    walk(scope, current_depth)
    return items

def handle_cd_up(scope: Path) -> List[Dict[str, str]]:
    """Обрабатывает команду cd.. для перехода на уровень выше."""
    parent = scope.parent
    return [{
        "title": parent.name or "/",
        "subtitle": "⬆️ Parent directory",
        "arg": str(parent),
        "valid": True,
        "type": "default"
    }]

def main():
    # Получаем запрос от Alfred
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    
    # Получаем текущую область поиска из переменных окружения Alfred
    scope_str = os.getenv('scope', os.path.expanduser('~'))  # По умолчанию - домашняя директория
    scope = Path(scope_str)
    
    # Инициализируем список результатов
    items = []
    
    # Обрабатываем специальные команды
    if query == "ls":
        items = list_directory(scope)
    elif query == "cd..":
        items = handle_cd_up(scope)
    else:
        # Обычный поиск файлов
        items = search_files(query, scope)
    
    # Если нет результатов, показываем сообщение
    if not items:
        items = [{
            "title": "No matches found",
            "subtitle": f"No items matching '{query}' in {scope}",
            "arg": str(scope),  # Добавляем arg для совместимости
            "valid": False
        }]
    
    # Выводим результаты в формате JSON для Alfred
    print(json.dumps({"items": items}))

if __name__ == "__main__":
    main()