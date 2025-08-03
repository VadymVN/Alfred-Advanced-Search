# Alfred Advanced Search Workflow

## Purpose

Speed‑up navigation and scoped file search in Alfred while **excluding apps and hidden files**. Hotkey `ff` launches the workflow and the current scope determines how deep you search.

---

## How It Works

1. **Global trigger** – press `` to start a search across every *visible* file and folder (no `.dot` items, no `.app` bundles).
2. **Drill‑in** – hit `` on a highlighted **folder** to open that folder *inside Alfred*.
3. **List contents** – once inside a folder, type `` *(keyword, then Return)* to list **all immediate files and sub‑folders** so you can see what lives there even if you don’t remember any names.
4. **Move up one level** – type `` *(keyword, then Return)* to jump to the **parent directory** and reset Alfred’s scope accordingly.
5. **Scoped search** – start typing inside the scoped folder to fuzzy‑match items **only within that directory tree**.
6. **Open items** –
   - Folder + `` → drill deeper.
   - File   + `` → open with default app.
7. **Reveal in Finder** – select any item and press `` (Command‑Return) to reveal it in Finder (uses Alfred’s default File Action).
8. **Reset scope** – hit `ff` again at any time to pop back to a global search.

---

## Feature Matrix

| Context      | Key / Input       | Action                           |
| ------------ | ----------------- | -------------------------------- |
| Anywhere     | `ff`              | Global search (filesystem root). |
| Folder       | `Return`          | Enter folder; set scope.         |
| Folder       | `⌘ + Return`      | Open folder in Finder.           |
| Folder scope | `ls` + `Return`   | List every item in that folder.  |
| Folder scope | `cd..` + `Return` | Move **up** to parent folder.    |
| Scoped dir   | Type query        | Fuzzy search inside scope.       |
| File         | `Return`          | Open file (default app).         |
| File         | `⌘ + Return`      | Reveal file in Finder.           |

> **Tip** — Re‑entering `ff` from any scope jumps back to the full‑disk context, saving you from tapping multiple `cd..` steps.

---

## Installation

1. **Import** `alfred-advanced-search.alfredworkflow` into Alfred.
2. Optionally create a **virtual environment** for Python ≥ 3.9:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. In Alfred → *Workflows* → *Advanced Search* set **Keyword** to `ff`.

---

## Implementation Notes

### Keywords `ls` & `cd..`

```python
# inside search.py (pseudo‑implementation)
if scope and query in {"ls", "cd.."}:
    if query == "ls":
        for item in listdir(scope):
            if item.startswith('.') or item.endswith('.app'):
                continue  # skip hidden & app bundles
            wf.add_item(title=item.name,
                        subtitle="📄 File" if item.is_file() else "📂 Folder",
                        arg=item.path,
                        valid=True,
                        type='file' if item.is_file() else 'default')
    else:  # cd..
        parent = Path(scope).parent
        wf.add_item(title=parent.name or "/",
                    subtitle="Parent directory",
                    arg=str(parent),
                    valid=True,
                    type='default',
                    icon="icon.png")
```

*Result:* `ls` reveals children; `cd..` offers one result — the parent folder — so pressing `Return` scopes Alfred to it.

### Recursion Depth Options

| Mode                | `SEARCH_DEPTH`                                  | Use Case                                                               | Pros                             | Cons                                 |
| ------------------- | ----------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------- | ------------------------------------ |
| Unlimited (default) | `∞`                                             | Full‑disk search; most flexible.                                       | Finds anything.                  | Large result set; marginally slower. |
| Fixed number        | `n` (e.g. `3`)                                  | Keep traversal shallow in global mode.                                 | Faster; avoids deep system dirs. | May miss deeply nested files.        |
| Dynamic             | `0` in global → unlimited,`1` in scoped folders | Global search thorough, but scoped search stays in *current* dir only. | Predictable; fewer surprises.    | Adds config complexity.              |

Set `SEARCH_DEPTH` in *Workflow Environment Variables* to switch modes.

### Spotlight Dependency

Alfred relies on the **macOS metadata (Spotlight) index** for file discovery; keeping Spotlight healthy ensures identical results to Alfred’s default engine. ([alfredapp.com](https://www.alfredapp.com/help/kb/search-your-mac-with-alfred/))

---

## Repository Layout

```text
alfred-advanced-search/
├── search.py
├── utils.py
├── docs/
│   └── Интеграция Python and Alfred.md
├── README.md
└── requirements.txt
```

The Markdown reference file is accessible in Cursor via `@file`, and all external docs can be pulled with `@Web` or `@Docs` links.

---

## Step‑by‑Step Workflow with `ls` and `cd..`

Use this sequence to explore a folder when you’re unsure about its contents, and navigate back up if needed:

| Step | Keys / Input                        | Alfred State                     | Purpose                                                                   |
| ---- | ----------------------------------- | -------------------------------- | ------------------------------------------------------------------------- |
| 1    | `ff`                                | Global scope                     | Launch Advanced Search.                                                   |
| 2    | Start typing folder name → `Return` | Folder highlighted → **scoped**  | Enter the target folder. Alfred now limits all queries to this directory. |
| 3    | Type `ls` → `Return`                | Items list (files & sub‑folders) | View **every** visible child item.                                        |
| 4‑a  | Select a sub‑folder → `Return`      | Deeper scope                     | Drill further and repeat `ls` or search by name.                          |
| 4‑b  | Type `cd..` → `Return`              | Parent scope                     | Go **up** one directory.                                                  |
| 4‑c  | Select a file → `Return`            | —                                | Open file with its default app.                                           |
| 4‑d  | Any item → ``                       | —                                | Reveal selected item in Finder.                                           |
| 5    | Type `ff` again                     | Global scope restored            | Jump back out to whole‑disk search when finished.                         |

> **Why both **``** and **``**?**\
> Together they emulate a mini‑shell inside Alfred: `ls` to inspect, `cd..` to ascend, all without leaving the keyboard.



