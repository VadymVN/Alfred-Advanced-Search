# Alfred Advanced Search Workflow

## Purpose

Speed-up navigation and scoped file search in Alfred while **excluding apps and hidden files**. Hotkey `ff` launches the workflow. Supports fuzzy matching, deep search, content search, and tree visualization.

## Features

- **Fuzzy search** — type partial names (`tst` finds `test1.txt`)
- **Relevance sorting** — exact > prefix > substring > fuzzy matches
- **`fd` integration** — 5-10x faster search when [`fd`](https://github.com/sharkdp/fd) is installed (automatic fallback to Python)
- **New commands** — `find`, `grep`, `tree` alongside existing `ls` and `cd..`
- **File metadata** — size and modification date shown in subtitles
- **Modifier keys** — `⌘+Return` opens Terminal, `^+Return` copies path
- **Configurable** — `settings.json` for depth, max results, excluded patterns, etc.
- **Logging** — debug log written to Alfred workflow data directory

## Commands

| Context | Key / Input | Action |
|---|---|---|
| Anywhere | `ff` | Global search (filesystem root) |
| Folder | `Return` | Enter folder; set scope |
| Folder | `⌥+Return` | Reveal in Finder |
| Folder | `⌘+Return` | Open in Terminal |
| Any item | `^+Return` | Copy path to clipboard |
| Folder scope | `ls` | List all contents of current folder (dirs first) |
| Folder scope | `cd..` | Move up to parent directory |
| Folder scope | `find <pattern>` | Deep recursive search by filename (no depth limit) |
| Folder scope | `grep <pattern>` | Search inside text files (2 levels deep) |
| Folder scope | `tree` | Visualize directory structure (2 levels deep) |
| Folder scope | `recent` / `recent 7` | Files modified in last N days (default: 1) |
| Folder scope | `size` / `size 10m` | Largest files, optionally above threshold |
| Scoped dir | Type query | Fuzzy search within current scope |
| File | `Return` | Open file with default app |
| File | `⌥+Return` | Reveal file in Finder |

## Search Behavior

### Fuzzy Matching

The search uses a 4-tier scoring system:

| Priority | Match Type | Example (`query` → `filename`) |
|---|---|---|
| 1 (best) | Exact | `test` → `test` |
| 2 | Prefix | `test` → `testing.py` |
| 3 | Substring | `est` → `testing.py` |
| 4 | Fuzzy | `tst` → `test.py` |

Results are sorted by match quality — exact matches always appear first.

### `fd` Integration

If [`fd`](https://github.com/sharkdp/fd) is installed (`brew install fd`), it is used automatically for file search, providing significantly faster results. If `fd` is not available, the workflow falls back to Python's `os.walk`. You can disable `fd` in settings.

## Configuration

Settings are stored in `settings.json` in the Alfred workflow data directory (`$alfred_workflow_data/settings.json`). If the file doesn't exist, defaults are used.

```json
{
  "search_depth": 3,
  "max_results": 50,
  "excluded_patterns": [".*", "*.app"],
  "search_paths": [
    "~/Documents",
    "~/Downloads",
    "~/Desktop",
    "~/Projects",
    "~/Applications"
  ],
  "use_fd": true,
  "grep_max_depth": 2,
  "tree_max_depth": 2,
  "respect_ignore_files": false
}
```

| Parameter | Default | Description |
|---|---|---|
| `search_depth` | `3` | Max directory depth for regular search |
| `max_results` | `50` | Maximum number of results returned |
| `excluded_patterns` | `[".*", "*.app"]` | Glob patterns to exclude (`.*` dotfiles, `*.app` bundles, `node_modules` exact) |
| `search_paths` | See above | Directories to search in global mode |
| `use_fd` | `true` | Use `fd` if installed |
| `grep_max_depth` | `2` | Max depth for `grep` command |
| `tree_max_depth` | `2` | Max depth for `tree` command |
| `respect_ignore_files` | `false` | If `true`, fd respects `.gitignore`/`.fdignore` |

## Installation

1. **Import** `alfred-advanced-search.alfredworkflow` into Alfred.
2. Ensure **Python >= 3.9** is available.
3. (Optional) Install `fd` for faster search:
   ```bash
   brew install fd
   ```
4. In Alfred → *Workflows* → *Advanced Search* set **Keyword** to `ff`.

## Repository Layout

```text
alfred-advanced-search/
├── search.py              # Main script (search, commands, config)
├── tests/
│   ├── conftest.py        # Test path setup
│   └── test_search.py     # 50 tests
├── docs/
│   └── Alfred_Advanced_Search_Workflow_EN.md  # Alfred setup guide
├── README.md
└── requirements.txt
```

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Install dev dependencies
pip install -r requirements.txt
```

## Logging

Debug logs are written to `search.log` in the Alfred workflow data directory. Useful for troubleshooting search issues, `fd` integration, and permission errors.
