#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Union, Literal

# Constants
SEARCH_DEPTH = 3  # Default limited search depth
MAX_RESULTS = 50  # Maximum number of results
EXCLUDED_PATTERNS = ['.', '.app']  # File exclusion patterns
DIR_FLAG = "1"  # Directory flag
FILE_FLAG = "0"  # File flag
COMMON_SEARCH_PATHS = [
    '~/Documents',
    '~/Downloads',
    '~/Desktop',
    '~/Projects',
    '~/Applications'
]  # Popular search directories

def should_exclude(name: str) -> bool:
    """Checks if a file/folder should be excluded from results."""
    return name.startswith('.') or name.endswith('.app')

def create_item(path: Path, is_file: bool = True) -> Dict[str, str]:
    """
    Creates an item for Alfred output.
    
    Args:
        path (Path): Path to file or directory
        is_file (bool): Flag indicating if the path is a file (True) or directory (False)
    
    Returns:
        Dict[str, str]: Dictionary with Alfred information, including:
            - title: File/directory name
            - subtitle: Parent directory path with icon
            - arg: Full path
            - type: Item type ('file' or 'default')
            - valid: Item availability
            - variables: Additional variables (is_dir, scope for directories)
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
    """Shows contents of the current directory."""
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
    """Searches for files by query considering search depth."""
    if not query:  # If query is empty, return empty list
        return []
        
    items = []
    current_depth = 0
    visited = set()  # For tracking already visited directories
    
    def walk(current_path: Path, current_depth: int):
        if current_depth > depth or current_depth > max_depth or len(items) >= max_results:
            return
            
        try:
            real_path = current_path.resolve()
            if real_path in visited:
                return
            visited.add(real_path)
            
            # Skip checking current directory as we only search inside it
            
            # Check contents of current directory only
            for item in current_path.iterdir():
                if should_exclude(item.name):
                    continue
                
                if query.lower() in item.name.lower():
                    items.append(create_item(item, item.is_file()))
                    if len(items) >= max_results:
                        return
                
                # Recursively traverse only subdirectories of current directory
                if item.is_dir() and not item.is_symlink() and item.parent == scope:
                    walk(item, current_depth + 1)
                    if len(items) >= max_results:
                        return
                        
        except (PermissionError, OSError):
            pass
            
    walk(scope, current_depth)
    return items

def handle_cd_up(scope: Path) -> List[Dict[str, str]]:
    """Handles cd.. command to move up one level."""
    parent = scope.parent
    item = create_item(parent, is_file=False)  # Use existing function
    item["subtitle"] = "⬆️ Parent directory"  # Override subtitle
    return [item]

def get_search_paths() -> List[Path]:
    """Returns list of directories for search."""
    paths = []
    # Add current directory from Alfred environment variable
    scope_str = os.getenv('scope')
    if scope_str:
        paths.append(Path(scope_str))
    
    # Add popular directories
    for path_str in COMMON_SEARCH_PATHS:
        path = Path(os.path.expanduser(path_str))
        if path.exists() and path.is_dir():
            paths.append(path)
    
    return paths if paths else [Path.home()]

def main():
    try:
        # Get query from Alfred
        query = sys.argv[1] if len(sys.argv) > 1 else ""
        
        # Get current search scope
        scope = Path(os.getenv('scope', os.path.expanduser('~')))
        
        # Initialize results list
        items = []
        
        # Handle special commands
        if query == "ls":
            items = list_directory(scope)
        elif query == "cd..":
            items = handle_cd_up(scope)
        else:
            # Regular file search
            search_paths = get_search_paths()
            for path in search_paths:
                if len(items) >= MAX_RESULTS:
                    break
                try:
                    path_items = search_files(query, path, max_results=MAX_RESULTS - len(items))
                    items.extend(path_items)
                except (PermissionError, OSError):
                    continue
        
        # If no results, show message
        if not items:
            items = [{
                "title": "No matches found",
                "subtitle": f"No items matching '{query}' in search paths",
                "arg": str(scope),  # Add arg for compatibility
                "valid": False
            }]
        
        # Output results in JSON format for Alfred
        print(json.dumps({"items": items[:MAX_RESULTS]}))
        
    except KeyboardInterrupt:
        # Handle search interruption
        print(json.dumps({
            "items": [{
                "title": "Search interrupted",
                "subtitle": "The search was interrupted by user",
                "valid": False
            }]
        }))

if __name__ == "__main__":
    main()