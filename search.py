#!/opt/homebrew/opt/python@3.11/bin/python3.11
# -*- coding: utf-8 -*-

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# --- Configuration ---

DEFAULT_SETTINGS = {
    "search_depth": 3,
    "max_results": 50,
    "excluded_patterns": [".*", "*.app"],
    "search_paths": [
        "~/Documents",
        "~/Downloads",
        "~/Desktop",
        "~/Projects",
        "~/Applications",
    ],
    "use_fd": True,
    "grep_max_depth": 2,
    "tree_max_depth": 2,
    "respect_ignore_files": False,
}

DIR_FLAG = "1"
FILE_FLAG = "0"


def _get_workflow_data_dir() -> Path:
    """Returns the Alfred workflow data directory for logs and settings."""
    alfred_data = os.getenv("alfred_workflow_data")
    if alfred_data:
        path = Path(alfred_data)
    else:
        path = Path(__file__).parent / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _setup_logging() -> logging.Logger:
    """Sets up logging to file in workflow data directory."""
    logger = logging.getLogger("alfred_search")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    log_file = _get_workflow_data_dir() / "search.log"
    try:
        handler = logging.FileHandler(str(log_file))
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    except OSError:
        pass  # If we can't log, continue silently
    return logger


logger = _setup_logging()


def load_settings() -> dict:
    """Loads settings from settings.json, falls back to defaults."""
    settings_file = _get_workflow_data_dir() / "settings.json"
    settings = dict(DEFAULT_SETTINGS)
    if settings_file.exists():
        try:
            with open(settings_file, "r") as f:
                user_settings = json.load(f)
            settings.update(user_settings)
            logger.debug("Loaded settings from %s", settings_file)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load settings: %s", e)
    return settings


SETTINGS = load_settings()
SEARCH_DEPTH = SETTINGS["search_depth"]
MAX_RESULTS = SETTINGS["max_results"]
EXCLUDED_PATTERNS = SETTINGS["excluded_patterns"]


# --- Utility functions ---


def should_exclude(name: str) -> bool:
    """Checks if a file/folder should be excluded based on excluded_patterns.

    Supported patterns:
      .*         — dotfiles (starts with .)
      *.app      — by extension (ends with .app)
      node_modules — exact name match
    """
    for pattern in EXCLUDED_PATTERNS:
        if pattern.startswith("*.") and name.endswith(pattern[1:]):
            return True
        elif pattern.endswith("*") and name.startswith(pattern[:-1]):
            return True
        elif "*" not in pattern and name == pattern:
            return True
    return False


def fuzzy_match(query: str, text: str) -> bool:
    """Fuzzy match: all query chars must appear in text in order."""
    query = query.lower()
    text = text.lower()
    if query in text:
        return True
    text_pos = 0
    for char in query:
        text_pos = text.find(char, text_pos)
        if text_pos == -1:
            return False
        text_pos += 1
    return True


def match_score(query: str, name: str) -> int:
    """Returns match quality score (lower is better).
    0 = exact, 1 = prefix, 2 = substring, 3 = fuzzy, 99 = no match.
    """
    q = query.lower()
    n = name.lower()
    if q == n:
        return 0
    if n.startswith(q):
        return 1
    if q in n:
        return 2
    if fuzzy_match(query, name):
        return 3
    return 99


def _has_fd() -> bool:
    """Checks if fd is installed."""
    return SETTINGS.get("use_fd", True) and shutil.which("fd") is not None


def _format_size(size: int) -> str:
    """Formats file size to human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def _format_mtime(mtime: float) -> str:
    """Formats modification time."""
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))


def _file_info(path: Path) -> str:
    """Returns size and mtime string for a file."""
    try:
        stat = path.stat()
        size = _format_size(stat.st_size) if path.is_file() else ""
        mtime = _format_mtime(stat.st_mtime)
        parts = [mtime]
        if size:
            parts.append(size)
        return " | ".join(parts)
    except OSError:
        return ""


# --- Item creation ---


def create_item(path: Path, is_file: bool = True) -> Dict:
    """Creates an Alfred result item with file info in subtitle."""
    icon_prefix = "📄" if is_file else "📂"
    info = _file_info(path)
    subtitle_parts = [icon_prefix, str(path.parent)]
    if info:
        subtitle_parts.append(f"({info})")

    variables = {"is_dir": FILE_FLAG if is_file else DIR_FLAG}
    item = {
        "title": path.name or str(path),
        "subtitle": " ".join(subtitle_parts),
        "arg": str(path),
        "type": "file" if is_file else "default",
        "valid": True,
        "variables": variables,
        "mods": {
            "cmd": {
                "subtitle": "Open in Terminal",
                "arg": str(path if not is_file else path.parent),
                "variables": {"action": "terminal"},
            },
            "ctrl": {
                "subtitle": "Copy path to clipboard",
                "arg": str(path),
                "variables": {"action": "copy_path"},
            },
        },
    }

    item["icon"] = {"type": "fileicon", "path": str(path)}

    if not is_file:
        item["variables"]["scope"] = str(path)
        item["autocomplete"] = str(path)
        item["keepalive"] = True

    return item


# --- Core operations ---


def list_directory(scope: Path) -> List[Dict]:
    """Shows contents of the current directory."""
    items = []
    try:
        for item in sorted(scope.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if should_exclude(item.name):
                continue
            items.append(create_item(item, item.is_file()))
    except PermissionError:
        logger.warning("Permission denied: %s", scope)
        items.append(
            {
                "title": "Permission denied",
                "subtitle": f"Cannot access {scope}",
                "valid": False,
            }
        )
    return items


def search_files(
    query: str,
    scope: Path,
    depth: int = SEARCH_DEPTH,
    max_depth: int = 5,
    max_results: int = 50,
    use_fuzzy: bool = True,
) -> List[Dict]:
    """Searches for files by query with fuzzy matching and relevance sorting."""
    if not query:
        return []

    # Try fd first
    if _has_fd():
        results = _search_with_fd(query, scope, depth, max_results)
        if results is not None:
            return results

    # Python fallback
    scored_items: List[Tuple[int, Dict]] = []
    visited = set()

    def walk(current_path: Path, current_depth: int):
        if current_depth > depth or current_depth > max_depth or len(scored_items) >= max_results:
            return

        try:
            real_path = current_path.resolve()
            if real_path in visited:
                return
            visited.add(real_path)

            for item in current_path.iterdir():
                if should_exclude(item.name):
                    continue

                score = match_score(query, item.name)
                if score < 99:
                    scored_items.append((score, create_item(item, item.is_file())))
                    if len(scored_items) >= max_results:
                        return

                if item.is_dir() and not item.is_symlink():
                    walk(item, current_depth + 1)
                    if len(scored_items) >= max_results:
                        return

        except PermissionError:
            logger.debug("Permission denied during search: %s", current_path)
        except OSError as e:
            logger.debug("OS error during search: %s - %s", current_path, e)

    walk(scope, 0)
    scored_items.sort(key=lambda x: x[0])
    return [item for _, item in scored_items]


def _search_with_fd(
    query: str, scope: Path, depth: int, max_results: int
) -> Optional[List[Dict]]:
    """Searches using fd command for better performance."""
    try:
        cmd = ["fd", "--hidden=false"]
        if not SETTINGS.get("respect_ignore_files", False):
            cmd.append("--no-ignore")
        cmd += [
            "--max-depth",
            str(depth),
            "--max-results",
            str(max_results),
            query,
            str(scope),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10
        )
        if result.returncode not in (0, 1):
            logger.warning("fd returned code %d: %s", result.returncode, result.stderr)
            return None

        items: List[Tuple[int, Dict]] = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            path = Path(line)
            if should_exclude(path.name):
                continue
            score = match_score(query, path.name)
            items.append((score, create_item(path, path.is_file())))

        items.sort(key=lambda x: x[0])
        return [item for _, item in items]
    except subprocess.TimeoutExpired:
        logger.warning("fd search timed out")
        return None
    except FileNotFoundError:
        logger.debug("fd not found, falling back to Python search")
        return None
    except OSError as e:
        logger.warning("fd error: %s", e)
        return None


# --- New commands ---


def handle_cd_up(scope: Path) -> List[Dict]:
    """Handles cd.. command to move up one level."""
    parent = scope.parent
    item = create_item(parent, is_file=False)
    item["subtitle"] = "⬆️ Parent directory"
    return [item]


def handle_find(pattern: str, scope: Path) -> List[Dict]:
    """Deep recursive search by filename (no depth limit)."""
    if not pattern:
        return [{
            "title": "Usage: find <pattern>",
            "subtitle": "Deep search by filename",
            "valid": False,
        }]

    logger.info("find '%s' in %s", pattern, scope)

    # Try fd first (no depth limit)
    if _has_fd():
        try:
            cmd = ["fd", "--hidden=false"]
            if not SETTINGS.get("respect_ignore_files", False):
                cmd.append("--no-ignore")
            cmd += [
                "--max-results",
                str(MAX_RESULTS),
                pattern,
                str(scope),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode in (0, 1):
                items = []
                for line in result.stdout.strip().splitlines():
                    if not line:
                        continue
                    path = Path(line)
                    if should_exclude(path.name):
                        continue
                    items.append(create_item(path, path.is_file()))
                if items:
                    return items[:MAX_RESULTS]
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.warning("fd find failed: %s", e)

    # Python fallback: os.walk (unlimited depth)
    items = []
    query_lower = pattern.lower()
    for root, dirs, files in os.walk(str(scope)):
        # Filter excluded dirs in-place
        dirs[:] = [d for d in dirs if not should_exclude(d)]
        for name in dirs + files:
            if should_exclude(name):
                continue
            if query_lower in name.lower() or fuzzy_match(pattern, name):
                path = Path(root) / name
                items.append(create_item(path, path.is_file()))
                if len(items) >= MAX_RESULTS:
                    return items
    return items


def handle_grep(pattern: str, scope: Path) -> List[Dict]:
    """Searches file contents for pattern."""
    if not pattern:
        return [{
            "title": "Usage: grep <pattern>",
            "subtitle": "Search inside files",
            "valid": False,
        }]

    logger.info("grep '%s' in %s", pattern, scope)
    items = []
    max_depth = SETTINGS.get("grep_max_depth", 2)

    # Text file extensions to search
    text_extensions = {
        ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
        ".toml", ".cfg", ".ini", ".sh", ".zsh", ".bash", ".html", ".css",
        ".xml", ".csv", ".log", ".conf", ".env", ".rb", ".go", ".rs",
        ".java", ".c", ".cpp", ".h", ".hpp", ".swift", ".kt", ".sql",
    }

    for root, dirs, files in os.walk(str(scope)):
        # Depth control
        rel_depth = Path(root).relative_to(scope).parts
        if len(rel_depth) >= max_depth:
            dirs.clear()
            continue
        dirs[:] = [d for d in dirs if not should_exclude(d)]

        for fname in files:
            if should_exclude(fname):
                continue
            fpath = Path(root) / fname
            if fpath.suffix.lower() not in text_extensions:
                continue
            try:
                with open(fpath, "r", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        if pattern.lower() in line.lower():
                            snippet = line.strip()[:80]
                            items.append({
                                "title": f"{fname}:{lineno}",
                                "subtitle": f"📝 {snippet}",
                                "arg": str(fpath),
                                "type": "file",
                                "valid": True,
                                "variables": {"is_dir": FILE_FLAG},
                                "mods": {
                                    "cmd": {
                                        "subtitle": "Open in Terminal",
                                        "arg": str(fpath.parent),
                                        "variables": {"action": "terminal"},
                                    },
                                    "ctrl": {
                                        "subtitle": "Copy path to clipboard",
                                        "arg": str(fpath),
                                        "variables": {"action": "copy_path"},
                                    },
                                },
                            })
                            if len(items) >= MAX_RESULTS:
                                return items
                            break  # One match per file
            except OSError:
                continue

    return items


def handle_tree(scope: Path) -> List[Dict]:
    """Shows directory tree structure (2 levels deep)."""
    logger.info("tree %s", scope)
    max_depth = SETTINGS.get("tree_max_depth", 2)
    items = []

    def _tree(path: Path, prefix: str, depth: int):
        if depth > max_depth or len(items) >= MAX_RESULTS:
            return
        try:
            entries = sorted(
                [e for e in path.iterdir() if not should_exclude(e.name)],
                key=lambda p: (p.is_file(), p.name.lower()),
            )
        except (PermissionError, OSError):
            return

        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            icon = "📂 " if entry.is_dir() else ""
            name = entry.name + ("/" if entry.is_dir() else "")
            items.append({
                "title": f"{prefix}{connector}{icon}{name}",
                "subtitle": str(entry),
                "arg": str(entry),
                "type": "file" if entry.is_file() else "default",
                "valid": True,
                "variables": {
                    "is_dir": DIR_FLAG if entry.is_dir() else FILE_FLAG,
                    **({"scope": str(entry)} if entry.is_dir() else {}),
                },
            })
            if entry.is_dir() and depth < max_depth:
                next_prefix = prefix + ("    " if is_last else "│   ")
                _tree(entry, next_prefix, depth + 1)

    _tree(scope, "", 0)
    return items


def handle_recent(args: str, scope: Path) -> List[Dict]:
    """Shows recently modified files. Usage: recent [days]."""
    days = 1
    if args.strip():
        try:
            days = int(args.strip())
        except ValueError:
            return [{
                "title": "Usage: recent [days]",
                "subtitle": "Show files modified in last N days (default: 1)",
                "valid": False,
            }]

    logger.info("recent %d days in %s", days, scope)

    # Try fd first
    if _has_fd():
        try:
            cmd = ["fd", "--hidden=false", "--type", "f"]
            if not SETTINGS.get("respect_ignore_files", False):
                cmd.append("--no-ignore")
            cmd += [
                "--changed-within", f"{days}d",
                "--max-results", str(MAX_RESULTS),
                ".", str(scope),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode in (0, 1) and result.stdout.strip():
                items = []
                for line in result.stdout.strip().splitlines():
                    if not line:
                        continue
                    path = Path(line)
                    if should_exclude(path.name):
                        continue
                    items.append(create_item(path, is_file=True))
                # Sort by mtime newest first
                items.sort(
                    key=lambda x: _safe_mtime(Path(x["arg"])), reverse=True
                )
                return items[:MAX_RESULTS]
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.warning("fd recent failed: %s", e)

    # Python fallback
    cutoff = time.time() - days * 86400
    items = []
    for root, dirs, files in os.walk(str(scope)):
        dirs[:] = [d for d in dirs if not should_exclude(d)]
        for fname in files:
            if should_exclude(fname):
                continue
            fpath = Path(root) / fname
            try:
                if fpath.stat().st_mtime >= cutoff:
                    items.append(create_item(fpath, is_file=True))
                    if len(items) >= MAX_RESULTS * 2:
                        break
            except OSError:
                continue
        if len(items) >= MAX_RESULTS * 2:
            break

    items.sort(key=lambda x: _safe_mtime(Path(x["arg"])), reverse=True)
    return items[:MAX_RESULTS]


def _safe_mtime(path: Path) -> float:
    """Returns mtime or 0 on error."""
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def handle_size(args: str, scope: Path) -> List[Dict]:
    """Shows largest files. Usage: size [threshold like 10m, 100k]."""
    threshold = 0
    if args.strip():
        threshold = _parse_size(args.strip())
        if threshold < 0:
            return [{
                "title": "Usage: size [threshold]",
                "subtitle": "Examples: size 10m, size 100k, size 1g",
                "valid": False,
            }]

    logger.info("size threshold=%d in %s", threshold, scope)
    items = []

    for root, dirs, files in os.walk(str(scope)):
        dirs[:] = [d for d in dirs if not should_exclude(d)]
        for fname in files:
            if should_exclude(fname):
                continue
            fpath = Path(root) / fname
            try:
                st = fpath.stat()
                if st.st_size >= threshold:
                    items.append((st.st_size, create_item(fpath, is_file=True)))
            except OSError:
                continue

    items.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in items[:MAX_RESULTS]]


def _parse_size(s: str) -> int:
    """Parses size string like '10m', '100k', '1g'. Returns -1 on error."""
    s = s.lower().strip()
    multipliers = {"k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}
    if s[-1] in multipliers:
        try:
            return int(float(s[:-1]) * multipliers[s[-1]])
        except ValueError:
            return -1
    try:
        return int(s)
    except ValueError:
        return -1


# --- Search paths ---


def get_search_paths() -> List[Path]:
    """Returns list of directories for search."""
    paths = []
    scope_str = os.getenv("scope")
    if scope_str:
        paths.append(Path(scope_str))

    for path_str in SETTINGS.get("search_paths", []):
        path = Path(os.path.expanduser(path_str))
        if path.exists() and path.is_dir():
            paths.append(path)

    return paths if paths else [Path.home()]


# --- Main ---


def main():
    try:
        query = sys.argv[1] if len(sys.argv) > 1 else ""
        scope = Path(os.getenv("scope", os.path.expanduser("~")))
        items = []

        logger.debug("Query: '%s', Scope: %s", query, scope)

        # Handle special commands
        if query == "ls":
            items = list_directory(scope)
        elif query == "cd..":
            items = handle_cd_up(scope)
        elif query == "tree":
            items = handle_tree(scope)
        elif query.startswith("find "):
            items = handle_find(query[5:].strip(), scope)
        elif query.startswith("grep "):
            items = handle_grep(query[5:].strip(), scope)
        elif query == "recent" or query.startswith("recent "):
            items = handle_recent(query[6:].strip() if " " in query else "", scope)
        elif query == "size" or query.startswith("size "):
            items = handle_size(query[4:].strip() if " " in query else "", scope)
        else:
            # Regular file search with fuzzy matching
            search_paths = get_search_paths()
            for path in search_paths:
                if len(items) >= MAX_RESULTS:
                    break
                try:
                    path_items = search_files(
                        query, path, max_results=MAX_RESULTS - len(items)
                    )
                    items.extend(path_items)
                except (PermissionError, OSError):
                    continue

        if not items:
            items = [
                {
                    "title": "No matches found",
                    "subtitle": f"No items matching '{query}' in search paths",
                    "arg": str(scope),
                    "valid": False,
                }
            ]

        print(json.dumps({"items": items[:MAX_RESULTS]}))

    except KeyboardInterrupt:
        print(
            json.dumps(
                {
                    "items": [
                        {
                            "title": "Search interrupted",
                            "subtitle": "The search was interrupted by user",
                            "valid": False,
                        }
                    ]
                }
            )
        )


if __name__ == "__main__":
    main()
