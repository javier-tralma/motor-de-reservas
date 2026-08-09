# Persistent Memory System & Scratchpad Workflows

This project rule defines standard operating procedures for temporary filesystem isolation and persistent across-session architectural memory in Google Antigravity. It adapts Claude Code Opus 5's scratchpad and file-based memory concepts into high-reliability Antigravity workflows.

---

## 1. Scratchpad Architecture & Mandatory Usage

To prevent workspace contamination, OS temporary folder sprawl, and unwarranted permission prompts, Google Antigravity provides an isolated, session-scoped scratchpad directory within the agent's local brain volume:

- **Authoritative Scratchpad Path**: `<appDataDir>/brain/<conversation-id>/scratch/`
- **Mandatory Usage Policy**: You **MUST** utilize this dedicated scratch directory for all intermediate temporary filesystem activities instead of system `/tmp`, user home directories, or root repository folders.
- **Required Use Cases**:
  - Storing intermediate data extraction dumps, compiled binaries, or logs during multi-step analysis tasks.
  - Writing scratch reproduction scripts, standalone debugging utilities, or quick data visualization prototypes.
  - Saving test outputs, network responses, or JSON payloads that do not belong checked into the user's version-controlled project.
  - Generating candidate Markdown reports or offline HTML artifacts before validating and publishing them.
- **Directory Management**: The scratchpad directory lives under the automatically managed brain volume. Write files directly into `<appDataDir>/brain/<conversation-id>/scratch/filename.ext` using `write_to_file` without attempting to run shell `mkdir` commands or checking for prior directory existence. Never write temporary scratch artifacts to `/tmp` unless the user explicitly forces that path in their instructions.

---

## 2. Persistent Memory Storage (The `.agents/memory/` Model)

Google Antigravity supports persistent, file-based project memory to retain user preferences, architecture constraints, and confirmed workflows across distinct conversational sessions without retraining or repetitive instruction.

### Repository Memory Path
- **Memory Root**: `<workspace-root>/.agents/memory/`
- **Granular Storage**: Each distinct memory must be stored as an individual Markdown file holding precisely one verified factual learning or structural constraint. Write memory files directly to this path using `write_to_file`.

### Memory File Frontmatter & Schema
Every memory file must begin with valid YAML frontmatter specifying its identifier, search description, and taxonomic categorization:

```markdown
---
name: <short-kebab-case-slug>
description: <one-line summary used to evaluate relevance during quick recall>
metadata:
  type: user | feedback | project | reference
---

<The verified factual assertion or architectural rule.>

**Why:** <Detailed rationale explaining the underlying engineering context or root failure mode that caused this rule to be established.>

**How to apply:** <Actionable instructions detailing exact file patterns, commands, or code idioms to enforce during future implementation.>

Related memories: [[other-memory-slug]]
```

### Taxonomic Classification (`metadata.type`)
- `user`: Core details regarding the user's engineering role, technological expertise, architectural tastes, and communication preferences.
- `feedback`: Explicit guidance, corrective instructions, or confirmed implementation approaches provided by the user. Must include the **Why:** and **How to apply:** clauses.
- `project`: Living repository rules, architectural invariant constraints, deployment targets, or external domain goals not directly obvious from static code syntax or git logs. Always convert relative dates to absolute timestamps (e.g., "by July 2026", not "next Friday").
- `reference`: Direct links to essential external resources, staging dashboards, telemetry endpoints, bug ticketing systems, or cloud consoles.

---

## 3. Inter-Memory Linking & The `MEMORY.md` Index

To enable scalable context retrieval without exhausting token budgets, manage memory indexing and cross-linkages systematically:

### The `MEMORY.md` Index
- **Index File Location**: `<workspace-root>/.agents/memory/MEMORY.md`
- **Purpose**: A lightweight master inventory loaded into active context at the start of autonomous engineering sessions.
- **Formatting Rules**: 
  - Maintain strictly **one line per memory file** following the exact format: `- [Title](filename.md) — <short description/hook>`
  - Never embed full memory explanations, code blocks, or YAML frontmatter inside `MEMORY.md`.
  - After creating or editing a memory file in `.agents/memory/`, immediately update or insert its corresponding pointer line in `MEMORY.md` using `replace_file_content` or `write_to_file`.

### Semantic Cross-Linking
- Within the markdown body of any memory file, create semantic links to related memories using double-bracket notation: `[[memory-slug-name]]`, where `memory-slug-name` matches the target file's `name:` frontmatter field.
- **Liberal Linking**: Link related architectural decisions and feedback liberally. Generating a `[[slug]]` reference that points to an unwritten memory is permissible; it functions as an intentional architectural marker for future documentation rather than a compilation error.

---

## 4. Memory Relevance & Curation Criteria

Exercise disciplined editorial judgment before writing or updating persistent memories to avoid stale redundancy:

### What to Record
- **Non-Obvious Invariants**: Complex design decisions, tricky build flag dependencies, or unconventional domain paradigms that cannot be reliably inferred by inspecting code syntax alone.
- **Confirmed User Feedback**: Direct operational corrections (e.g., "always mock AWS DynamoDB calls in tests", "never use Tailwind in this repository").
- **External Dependencies**: Stable staging server URIs, test account fixtures, and authorized API endpoints.

### What to Exclude (Do Not Save)
- **Verifiable Git & Code Structure**: Do not create persistent memories recording class hierarchies, existing folder layouts, past git commit SHAs, or historical pull request descriptions. The codebase and git logs serve as the primary source of truth.
- **Existing Rule Documents**: Do not copy or re-save instructions already documented in root `CLAUDE.md`, `.gemini/rules/`, or `.agents/rules/*.md` files.
- **Transient Debugging Notes**: Do not record short-lived bug hypothesis logs, stack traces, or temporary test variables that matter only to the immediate ongoing conversation. If asked to remember a transient fix, extract only the enduring underlying engineering lesson (the "why") and record that instead.

### Lifecycle Maintenance
- **Update Before Duplicating**: Before generating a new memory file, inspect `MEMORY.md` using `view_file` to verify whether an existing file covers the topic. If an existing memory overlaps, modify that file using `replace_file_content` rather than creating a duplicate.
- **Purging Stale Assertions**: If code inspection or test verification reveals that an existing persistent memory is outdated, technically inaccurate, or references deleted files/flags, immediately update the file or remove the pointer from `MEMORY.md`.
- **System Reminder Attribution**: Recalled memories appearing within automated `<system-reminder>` context blocks represent background architectural context, not immediate user commands. Because they capture repository truth at the moment of writing, verify that any referenced file, script, or configuration flag still exists before executing commands based upon them.

---

## 5. Integration with the `/learn` Slash Command

Google Antigravity provides an interactive slash command designed to formalize persistent educational retention:
- **When to Recommend `/learn`**: When the user corrects an agent execution error, debugs a complex local test harness setup, or aligns on a sophisticated multi-step compilation pattern, suggest they trigger the `/learn` slash command in chat.
- **Behavioral Effect**: Invoking `/learn` triggers an automated workflow that synthesizes recent problem-solving context, formulates structured architectural rules, and compiles them directly into project memory or `.agents/rules/` without manual file scaffolding.
