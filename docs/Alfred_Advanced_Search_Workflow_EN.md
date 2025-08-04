
# ✅ Workflow "Alfred Advanced Search" — Step-by-Step Setup Guide

## 0. Final Result Overview

| **Context**         | **Key / Input** | **Action**                                      |
|---------------------|-----------------|--------------------------------------------------|
| **Anywhere**        | `ff`            | Start global search (root of filesystem).        |
| **Folder**          | **Return**      | Enter folder → set it as new _scope_.           |
| **Folder**          | **⌥ + Return**  | Open folder in Finder.                           |
| **In scope folder** | `ls` + Return   | Show _all_ contents of the current folder.       |
| **In scope folder** | `cd..` + Return | Move up one directory level.                     |
| **Any scope**       | Type string     | Fuzzy search within the current scope only.      |
| **File**            | **Return**      | Open file in default application.                |
| **File**            | **⌥ + Return**  | Reveal file in Finder.                           |

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

## 2. Copy Python Scripts into the Workflow Folder

1. Right-click the created workflow → **Open in Finder**
2. Copy `search.py` and `utils.py` from your repository into the folder.

---

## 3. Configure the Script Filter `ff`

1. **Double-click** the Script Filter block.
2. Set:
   - **Keyword**: `ff` (on with space_) - Argument Required
   - **Language**: `/bin/zsh --no-rcs`.  with input as argv. 
   Run Behaviour: 
    - Terminate previous script
    - The rest is Defaults
3. **Script**:
   /usr/bin/python3 "$PWD/search.py" "$1"
   
---

## 4. Configure the Conditional Block: "Folder or File"

1. **Open the Conditional block**
2. Add one condition:
   - If `{var:is_dir}` **is equal to** `0` (off «Ignoring Case» ) then: **Open File**
   - else: else
3. After closing, the canvas will show two output ports:  
   • Top — **then** → **Open File**  
   • Lower — **else**

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

## 8. Configure Reveal File in Finder (⌥ + Return)

1. Connect **Script Filter** to **Reveal File in Finder**
2. Click on the small circle on the connection line
   - **Action Modifier**: On → `Option`  
   - **Modifier Subtext**: Reveal in Finder

---

## 9. Connect the Blocks

| **From**                | **To**                     | **Purpose**                                     |
|-------------------------|----------------------------|-------------------------------------------------|
| **Script Filter ▢**     | Conditional (input)        | Send all `Return` input for folder/file check.  |
| **Conditional then**    | Open File                  | If it's a file → open it.                       |
| **Conditional else**    | Arg and Vars               | If it's a folder → update scope.                |
| **Arg and Vars**        | Call External Trigger      | Trigger re-run with new scope.                  |
| **Script Filter ⌥ port**| Reveal File in Finder      | `⌥ + Return` reveals item in Finder.            |

---

## 10. Set Default Scope Variable

1. Click top-right `[x]` of canvas.
2. **Environment Variables**:
   - Name: `scope`  
   - Value: `~/`

---

## 11. Test the Workflow

1. Enable **Debugger** (bug icon in bottom-left of Alfred Preferences).
2. In Alfred bar, type `ff`.
3. Choose a folder → press `Return`  
   → Should go to **else** in Conditional → refresh with folder content.
4. Choose a file → press `Return`  
   → Should go to **Open File** → file opens.
5. Press `⌥ + Return` on file → item reveals in Finder.

---

## 12. Additional Commands: `ls` and `cd..`

These are handled **within the `search.py` Script Filter**:

- If user types `ls`, ignore search and list **all contents** of current scope.
- If user types `cd..`, update scope to **parent directory**, then trigger `self.refresh`.
