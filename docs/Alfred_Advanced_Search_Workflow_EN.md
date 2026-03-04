# Workflow "Alfred Advanced Search" — Step-by-Step Setup Guide

## 0. Final Result Overview

| **Context** | **Key / Input** | **Action** |
|---|---|---|
| **Anywhere** | `ff` | Start global search (root of filesystem) |
| **Folder** | **Return** | Enter folder → set it as new _scope_ |
| **Folder** | **⌥+Return** | Reveal folder in Finder |
| **Folder** | **⌘+Return** | Open folder in Terminal |
| **Any item** | **^+Return** | Copy path to clipboard |
| **In scope** | `ls` + Return | Show all contents of current folder (dirs first) |
| **In scope** | `cd..` + Return | Move up one directory level |
| **In scope** | `find <pattern>` | Deep recursive search by filename |
| **In scope** | `grep <pattern>` | Search text inside files |
| **In scope** | `tree` | Visualize directory structure |
| **In scope** | `recent` / `recent 7` | Files modified in last N days (default: 1) |
| **In scope** | `size` / `size 10m` | Largest files, optionally above threshold |
| **Any scope** | Type string | Fuzzy search within current scope |
| **File** | **Return** | Open file in default application |
| **File** | **⌥+Return** | Reveal file in Finder |

---

## 1. Create the Workflow Skeleton

1. In Alfred: **Workflows → + → Blank Workflow**
   Set _Name_ to **Alfred Advanced Search**.
   Leave _Bundle ID_ empty (optional).

2. In the canvas area, **add the following blocks**:
   - **Script Filter**
   - **Conditional**
   - **Arg and Vars**
   - **Call External Trigger** (name it `self.refresh`)
   - **Open File**
   - **Reveal File in Finder**

---

## 2. Copy Python Script into the Workflow Folder

1. Right-click the created workflow → **Open in Finder**
2. Copy `search.py` from your repository into the folder.

> **Note:** `utils.py` has been removed — all functionality is now in `search.py`.

---

## 3. Configure the Script Filter `ff`

1. **Double-click** the Script Filter block.
2. Set:
   - **Keyword**: `ff` (on with space) — Argument Required
   - **Language**: `/bin/zsh --no-rcs` with input as argv
   Run Behaviour:
   - Terminate previous script
   - The rest is Defaults
3. **Script**:
   ```
   /usr/bin/python3 "$PWD/search.py" "$1"
   ```

---

## 4. Configure the Conditional Block: "Folder or File"

1. **Open the Conditional block**
2. Add one condition:
   - If `{var:is_dir}` **is equal to** `0` (off "Ignoring Case") then: **Open File**
   - else: else
3. After closing, the canvas will show two output ports:
   - Top — **then** → **Open File**
   - Lower — **else**

---

## 5. Configure the Arg and Vars Block

- **Argument**: `{query}`
- **Variable**:
  - Name: `scope`
  - Value: `{var:scope}`

---

## 6. Configure External Trigger for Refresh

1. In **Call External Trigger** block, set:
   - _Workflow ID_: `self`
   - _Trigger ID_: `refresh`
   - **Pass input as argument**: Off
   - **Pass variables**: On

---

## 7. Configure the Open File Block

- Default behavior; no changes needed.

---

## 8. Configure Reveal File in Finder (⌥+Return)

1. Connect **Script Filter** to **Reveal File in Finder**
2. Click on the small circle on the connection line
   - **Action Modifier**: On → `Option`
   - **Modifier Subtext**: Reveal in Finder

---

## 9. Configure Modifier Keys (⌘+Return, ^+Return)

The modifier keys are configured in `search.py` via the `mods` field in Alfred JSON output:

- **⌘+Return** — Opens Terminal at the item's directory. Requires an additional **Run Script** block connected to the Script Filter's `⌘` output port:
  ```bash
  open -a Terminal "{query}"
  ```
- **^+Return** — Copies the full path to clipboard. Requires a **Copy to Clipboard** block connected to the Script Filter's `^` output port.

---

## 10. Connect the Blocks

| **From** | **To** | **Purpose** |
|---|---|---|
| **Script Filter** | Conditional (input) | Send all `Return` input for folder/file check |
| **Conditional then** | Open File | If it's a file → open it |
| **Conditional else** | Arg and Vars | If it's a folder → update scope |
| **Arg and Vars** | Call External Trigger | Trigger re-run with new scope |
| **Script Filter ⌥ port** | Reveal File in Finder | `⌥+Return` reveals item in Finder |
| **Script Filter ⌘ port** | Run Script (Terminal) | `⌘+Return` opens Terminal |
| **Script Filter ^ port** | Copy to Clipboard | `^+Return` copies path |

---

## 11. Set Default Scope Variable

1. Click top-right `[x]` of canvas.
2. **Environment Variables**:
   - Name: `scope`
   - Value: `~/`

---

## 12. Optional: Install `fd` for Faster Search

```bash
brew install fd
```

When `fd` is installed, the workflow automatically uses it for file search operations, providing 5-10x speed improvement. Falls back to Python if `fd` is not available.

---

## 13. Optional: Configure Settings

Create `settings.json` in the Alfred workflow data directory to customize behavior:

```json
{
  "search_depth": 3,
  "max_results": 50,
  "use_fd": true,
  "grep_max_depth": 2,
  "tree_max_depth": 2
}
```

See [README.md](../README.md) for the full list of settings.

---

## 14. Test the Workflow

1. Enable **Debugger** (bug icon in bottom-left of Alfred Preferences).
2. In Alfred bar, type `ff`.
3. Choose a folder → press `Return`
   → Should go to **else** in Conditional → refresh with folder content.
4. Choose a file → press `Return`
   → Should go to **Open File** → file opens.
5. Press `⌥+Return` on file → item reveals in Finder.
6. Type `ls` → shows sorted directory listing (dirs first, then files).
7. Type `cd..` → navigates to parent directory.
8. Type `find readme` → deep search for files named "readme".
9. Type `grep TODO` → searches file contents for "TODO".
10. Type `tree` → shows visual directory structure.
11. Type `recent` → shows files modified in last 24h.
12. Type `recent 7` → files modified in last 7 days.
13. Type `size` → shows largest files.
14. Type `size 10m` → files larger than 10MB.
15. Press `⌘+Return` → opens Terminal at location.
16. Press `^+Return` → copies path to clipboard.

---

## 15. Architecture Notes

### Single-file Design

All logic lives in `search.py`:
- Configuration loading (`settings.json`)
- Logging (to `search.log`)
- Fuzzy matching with relevance scoring
- `fd` integration with Python fallback
- All commands: `ls`, `cd..`, `find`, `grep`, `tree`, `recent`, `size`

### Search Scoring

Results are sorted by match quality:
1. **Exact match** (score 0) — query equals filename
2. **Prefix match** (score 1) — filename starts with query
3. **Substring match** (score 2) — query found inside filename
4. **Fuzzy match** (score 3) — all query characters appear in order

### Logging

Debug logs are written to `search.log` in the Alfred workflow data directory. Check logs when troubleshooting:
```bash
cat ~/Library/Application\ Support/Alfred/Workflow\ Data/<bundle-id>/search.log
```
