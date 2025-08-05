#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Union
from functools import lru_cache

class FileSystemHelper:
    """Class for working with file system and metadata."""
    
    def __init__(self, use_spotlight: bool = True):
        self.use_spotlight = use_spotlight
        self._setup_spotlight() if use_spotlight else None
    
    def _setup_spotlight(self) -> None:
        """Checks Spotlight availability and its index."""
        try:
            os.system('mdutil -s / > /dev/null 2>&1')
            self.spotlight_available = True
        except:
            self.spotlight_available = False

    @lru_cache(maxsize=100)
    def get_file_metadata(self, file_path: Path) -> Dict[str, str]:
        """Gets file metadata, caches results for performance."""
        metadata = {
            "name": file_path.name,
            "path": str(file_path),
            "type": "file" if file_path.is_file() else "directory",
            "parent": str(file_path.parent),
            "icon": "📄" if file_path.is_file() else "📂"
        }
        
        if self.use_spotlight and self.spotlight_available and file_path.is_file():
            # Add metadata from Spotlight for files
            try:
                import subprocess
                cmd = ['mdls', '-name', 'kMDItemDisplayName', '-name', 'kMDItemKind', str(file_path)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    metadata.update(self._parse_spotlight_metadata(result.stdout))
            except:
                pass
                
        return metadata

    def _parse_spotlight_metadata(self, metadata_str: str) -> Dict[str, str]:
        """Parses mdls command output."""
        metadata = {}
        for line in metadata_str.splitlines():
            if '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip(' "')
            if key and value != '(null)':
                metadata[key] = value
        return metadata

class SearchHelper:
    """Class for enhanced file search."""
    
    def __init__(self, fs_helper: FileSystemHelper):
        self.fs_helper = fs_helper
        
    def fuzzy_match(self, query: str, text: str) -> bool:
        """Implements fuzzy search."""
        query = query.lower()
        text = text.lower()
        
        # Simple case - direct match
        if query in text:
            return True
            
        # Fuzzy search for complex cases
        query_chars = list(query)
        text_pos = 0
        
        for char in query_chars:
            text_pos = text.find(char, text_pos)
            if text_pos == -1:
                return False
            text_pos += 1
            
        return True

    def filter_by_pattern(self, items: List[Path], pattern: str) -> List[Path]:
        """Filters file list by pattern."""
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            return [item for item in items if regex.search(item.name)]
        except re.error:
            # If pattern is not a valid regular expression,
            # use simple substring search
            return [item for item in items if pattern.lower() in item.name.lower()]

class WorkflowHelper:
    """Class for working with Alfred Workflow."""
    
    @staticmethod
    def format_item(
        title: str,
        subtitle: str,
        arg: str,
        valid: bool = True,
        item_type: str = "default",
        icon: Optional[str] = None,
        text: Optional[Dict[str, str]] = None
    ) -> Dict[str, Union[str, bool, Dict]]:
        """Formats an item for Alfred output."""
        item = {
            "title": title,
            "subtitle": subtitle,
            "arg": arg,
            "valid": valid,
            "type": item_type
        }
        
        if icon:
            item["icon"] = {"path": icon}
        if text:
            item["text"] = text
            
        return item

    @staticmethod
    def get_scope() -> Path:
        """Gets current search scope from Alfred environment variables."""
        scope_str = os.getenv('scope', os.path.expanduser('~'))
        return Path(scope_str)

    @staticmethod
    def set_scope(path: Path) -> None:
        """Sets new search scope."""
        os.environ['scope'] = str(path)

    @staticmethod
    def get_search_depth() -> float:
        """Gets configured search depth."""
        try:
            return float(os.getenv('SEARCH_DEPTH', 'inf'))
        except ValueError:
            return float('inf')