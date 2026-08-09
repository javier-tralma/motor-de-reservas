# Code & File Editing Standards & Design Synchronization

This project rule establishes strict engineering rigor for inspecting, editing, creating, and validating codebase files within Google Antigravity. It adapts Claude Code Opus 5's reading (`Read`), editing (`Edit`/`MultiEdit`), writing (`Write`), notebook editing (`NotebookEdit`), and design token synchronization (`DesignSync`) tools into deterministic Antigravity workflows.

---

## 1. Pre-Read Requirement & Inspection Protocols (`view_file`)

Before executing any modification across a software repository, adhere to rigorous inspection protocols to prevent silent data loss or architectural regression:

### Mandatory Pre-Read Rule
- You **MUST** view the existing contents of any target file using `view_file` within the current conversation session before calling any file modification tool. Attempting to overwrite or patch a file that has not been read in context violates senior engineering verification standards.
- **Slice Notation for Expansive Files**: The `view_file` tool displays up to 800 lines (or 46,080 bytes) per invocation. For large module files, do not repeatedly dump entire files into context. Use slice notation (`StartLine` and `EndLine`) to target specific structural ranges (e.g., viewing lines 120 to 180 around a failing method).
- **Handling Byte Truncation**: When reading large files where content exceeds initial byte boundaries, utilize the `ContentOffset` parameter to systematically read remaining file segments.
- **No Re-Reading After Edits**: Do **NOT** call `view_file` to re-read a file immediately after applying a successful edit via `replace_file_content` or `write_to_file`. Antigravity's editing tools execute deterministically and error immediately on mismatch; the harness natively tracks file state across turns.
- **Multi-Modal & Binary Inspection**: Utilize `view_file` directly to inspect binary assets—including UI screenshots (`.png`, `.jpg`, `.svg`), PDF manuals (entire document returned), video, audio, and raw Jupyter notebooks (`.ipynb`).

---

## 2. Contiguous Single-Block Edits (`replace_file_content`)

When performing localized code refactoring or bug remediation, prioritize precision atomic replacements:

### Operational Scope
- Use `replace_file_content` exclusively when applying a **single contiguous block of edits** (replacing an uninterrupted sequence of text lines) within an existing file. Do not call this tool if you are modifying multiple non-adjacent code sections in the same file.

### Exact Matching & Range Boundaries
- `TargetContent` **MUST EXACTLY MATCH** the existing character sequence in the target file, including all leading and trailing whitespace, indentation, comments, and line breaks. Slight whitespace variation causes immediate tool failure.
- Constrain search boundaries by specifying `StartLine` and `EndLine` (1-indexed, inclusive) enclosing precisely the intended instance of `TargetContent`. Ensure `1 <= StartLine <= EndLine <= file_line_count`.
- `ReplacementContent` must serve as an atomic, compile-ready drop-in replacement incorporating all necessary code modifications and surrounding imports.
- **No Parallel Clinging**: Never generate multiple parallel calls to `replace_file_content` targeting the identical file in a single response step.

---

## 3. Non-Contiguous Multi-Block Edits (`multi_replace_file_content`)

When refactoring interfaces, updating dependencies across distinct class methods, or renaming symbols across a single module:

### Operational Scope
- Use `multi_replace_file_content` exclusively when applying **multiple, non-contiguous edits** across separate line ranges within the exact same file during a single turn.

### Configuring Replacement Chunks
- Structure modifications as a valid JSON array of independent objects passed into the `ReplacementChunks` parameter.
- For each chunk object, define precise `StartLine`, `EndLine`, unique `TargetContent`, and modified `ReplacementContent`. Ensure individual chunk line ranges do not overlap or intersect.
- **Anti-Pattern Prohibitions**:
  - **Never replace the entire file**: Do not pass line 1 to EOF into `multi_replace_file_content` or `replace_file_content` simply to alter a few scattered lines; full-file replacements consume excessive token overhead and degrade git diff auditability.
  - **No Tool Mixing**: Never make concurrent calls to both single-replace and multi-replace tools against the same target file.

---

## 4. File Creation & Explicit Overwriting (`write_to_file`)

For new component scaffolding or deliberate full file rebuilds:
- **Operational Scope**: Use `write_to_file` strictly when creating new code files from scratch (parent directories are created automatically if missing) or explicitly replacing an entire existing file's contents.
- **The Overwrite Guard**: By default, `write_to_file` errors out if `TargetFile` already exists on disk. Set `Overwrite: true` only when you have explicitly inspected the existing file using `view_file` and consciously intend to replace its entire structure.

---

## 5. Jupyter Notebook Modification (`.ipynb`)

Jupyter notebooks encode code cells, markdown descriptions, and runtime output streams within a delicate JSON schema:
- **Direct Edit Prohibition**: Do not use standard line-replacement tools (`replace_file_content` or `multi_replace_file_content`) directly on `.ipynb` files, as manual regex replacing risks corrupting internal cell UUIDs, JSON escaping, and stream counts.
- **Safe Notebook Mutation**: To edit notebook code cells (replacing source, inserting experimental cells, or clearing execution outputs), execute deterministic Python utilities or `nbformat` processing scripts via `run_command` (e.g., executing a quick Python script in `<appDataDir>/brain/<conversation-id>/scratch/` that mutates the target notebook programmatically).

---

## 6. Design System Synchronization (StitchMCP Integration)

Adapt Claude Code Opus 5's `DesignSync` features (which validate component rendering and sync tokens with a Design System pane) into Google Antigravity's native **StitchMCP** integration.

### The StitchMCP Server Architecture
StitchMCP resides in the agent's MCP ecosystem (`<appDataDir>/mcp/StitchMCP/`) to manage user interface designs, design token systems, and screen variant validation.

### Tool Call Mapping (`call_mcp_tool`)
Because StitchMCP tools are lazily loaded, interact with them by invoking `call_mcp_tool` with `ServerName: "StitchMCP"` and the target `ToolName`:
- **Project & Screen Inspection**:
  - `list_projects` / `get_project`: Audit existing design system configurations and brand token workspaces.
  - `list_screens` / `get_screen`: Inspect rendered user interfaces, responsive specifications, and layout hierarchy.
- **Design System Token Sync (Replacing `DesignSync`)**:
  - `upload_design_md`: Upload structured design guidance Markdown files into the design system registry.
  - `create_design_system` / `update_design_system`: Synchronize brand palettes, typography tokens, spacing scales, and core structural assets.
  - `generate_variants` / `edit_screens`: Generate interactive component variants (primary, secondary, ghost buttons; light and dark mode adaptations) across viewport dimensions.
  - `apply_design_system`: Authoritatively merge validated design system tokens and component stylesheets directly into active project codebase CSS and layout skeletons.

### Rendering Validation & Quality Checks
Before finalizing design implementations or committing UI modifications:
- Verify that component variations render cleanly across responsive breakpoints without horizontal body scrolling.
- Audit aggregate render check counts (ensuring zero bad renders, zero thin layouts, and no identical variant duplications) prior to executing code integration.
