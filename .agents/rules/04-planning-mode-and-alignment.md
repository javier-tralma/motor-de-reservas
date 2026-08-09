# Planning Mode, Task Tracking & Interactive Alignment

This project rule defines standard procedures for architectural planning, structured TODO task tracking, and interactive user alignment within Google Antigravity. It adapts Claude Code Opus 5's plan mode (`EnterPlanMode`/`ExitPlanMode`), task list utilities (`TaskCreate`/`TaskUpdate`), and user questioning tools (`AskUserQuestion`) into native Antigravity planning workflows.

---

## 1. Proactive Planning Mode Philosophy

When confronted with software engineering tasks, exercise careful senior engineering judgment on whether to pause and formulate a formal technical plan before mutating repository source code:

### When to Initiate Planning
Stop and construct a formal implementation plan when a user request involves:
- **Major Architectural Refactoring**: Modifications affecting multiple subsystem layers, data models, or core interface contracts.
- **Non-Trivial Feature Implementation**: Adding meaningful functionality where design decisions (e.g., component hierarchy, state persistence, middleware structure) impact existing architecture.
- **Multiple Valid Implementation Patterns**: Technologies or patterns where reasonable engineers could differ (e.g., Redis vs. in-memory caching, polling vs. WebSockets, REST vs. GraphQL).
- **Multi-File Modifications**: Any non-trivial refactoring or feature implementation expected to modify more than 2–3 distinct files across the workspace.
- **Significant Plan Deviations**: Discovering unexpected codebase complexity or legacy bugs mid-execution that require deviating significantly from a previously approved architecture.

### When NOT to Plan (Direct Execution)
Do not generate planning overhead or block execution for tasks that are:
- **Trivially Simple & One-Off**: Single-line bug fixes, typo corrections, adding clear console logs, formatting syntax output, or running diagnostic linting sweeps.
- **Purely Investigatory & Research-Oriented**: Read-only exploration queries ("how does auth middleware work?", "where do we define routing?", "why did build test #4 fail?"). Use direct search tools or read-only research subagents instead.
- **Minor Approved Plan Follow-Ups**: Clear incremental tasks arising directly from an already executing plan (e.g., "now plot the test results", "add a unit test for that new utility", "convert that type to an enum").

---

## 2. The Three Core Planning Artifacts

In Google Antigravity, architectural alignment and task tracking operate deterministically through three specialized Markdown artifacts stored in the agent's session brain directory: `<appDataDir>/brain/<conversation-id>/`.

### A. Implementation Plan (`implementation_plan.md`)
When planning is required, construct a comprehensive technical design document before making code edits:
- **File Location**: `<appDataDir>/brain/<conversation-id>/implementation_plan.md`
- **Required Sections & Structure**:
  ```markdown
  # [Goal Description]
  Brief problem description, background context, and target technical outcome.

  ## User Review Required
  Document breaking changes, destructive database migrations, or controversial design choices. Use GitHub alerts (e.g., `>[!IMPORTANT]` or `>[!WARNING]`) for prominence.

  ## Open Questions
  Unresolved design decisions or clarifying questions for the user that materially affect architecture. Do NOT use the `ask_question` tool for these; embed them directly here.

  ## Proposed Changes
  Group files logically by component or dependency tier (dependencies first). Separate components with horizontal rules. Use explicit tags and clickable absolute file links:
  ### [Component Name]
  #### [MODIFY] [app.py](file:///absolute/path/to/app.py)
  #### [NEW] [service.ts](file:///absolute/path/to/service.ts)
  #### [DELETE] [legacy.js](file:///absolute/path/to/legacy.js)

  ## Verification Plan
  ### Automated Tests
  Exact shell commands for automated test verification (e.g., `pytest tests/test_auth.py`).
  ### Manual Verification
  Actionable procedures for inspecting rendered UI components or staging behaviors.
  ```
- **Feedback & Approval Workflow**: When writing or modifying `implementation_plan.md` using `write_to_file` or `replace_file_content`, **MUST** set `ArtifactMetadata: { RequestFeedback: true, UserFacing: true, Summary: "<detailed description>" }`. 
- **No Chat Resummarization**: The Antigravity UI renders modified plans automatically with an interactive 'Proceed' review button. Never re-summarize the full plan contents in visible chat; link to the artifact and highlight only critical open decisions requiring user focus. Stop tool execution and await explicit user sign-off before commencing code mutation.

### B. Task Tracking Checklist (`task.md`)
Adapt Claude Code's structured task list into an explicit living TODO artifact to organize execution and demonstrate engineering rigor:
- **File Location**: `<appDataDir>/brain/<conversation-id>/task.md`
- **When to Create**: Create this checklist immediately upon receiving user approval on an implementation plan, or at the outset of an extensive autonomous task (such as a `/goal` directive).
- **Mandatory Syntax Notation**:
  - `[ ]` Uncompleted pending tasks
  - `[/]` In-progress active task (custom Antigravity notation—mark BEFORE starting work on an item)
  - `[x]` Completed verified tasks
- **Staleness & Progress Rules**:
  - Maintain strictly **one item in-progress (`[/]`) at any given moment** unless running concurrent independent subagents.
  - As each milestone concludes, immediately update `task.md` using `replace_file_content` or `write_to_file`.
  - **Zero Completion Without Verification**: Never mark a task as completed (`[x]`) if compilation fails, unit tests error, implementation remains partial, or unverified stubs exist. When blocked, revert status to `[/]` or `[ ]` and append a explicit sub-task defining the required bug remediation.
  - Skip generating `task.md` only when the user request can be fully resolved in fewer than 3 trivial, atomic operational steps.

### C. Walkthrough Summary (`walkthrough.md`)
Upon concluding implementation work, construct an evidence-backed completion report:
- **File Location**: `<appDataDir>/brain/<conversation-id>/walkthrough.md`
- **Content Standards**: Document precise structural changes made, exact automated test commands executed with literal output confirmations, and empirical validation results. For frontend design adjustments, embed localized screenshots or recordings (`![caption](/absolute/path/to/artifact/image.png)`) to visually prove UI correctness.
- **Iterative Updates**: For follow-up modifications within the same session, update the existing `walkthrough.md` artifact rather than generating redundant historical files.

---

## 3. Interactive Alignment & Questioning (`ask_question` & `/grill-me`)

When execution is blocked on decisions that belong strictly to the user, adapt interactive questioning protocols:

### Using the `ask_question` Tool
The `ask_question` tool renders an interactive modal containing multiple-choice selections in the UI:
- **When to Call**: Use exclusively when blocked on underspecified product requirements, soliciting user design preference among mutually exclusive architectural options, or resolving ambiguous user intent that cannot be deduced from existing repository patterns.
- **Strict Anti-Patterns**:
  - **Do NOT ask trivial questions**: Never call `ask_question` for simple single-word yes/no queries; output normal chat text instead.
  - **Do NOT ask for plan approval**: Never call `ask_question` to ask "Is my plan ready?", "Does this plan look good?", or "Should I proceed with execution?". Submitting `implementation_plan.md` with `RequestFeedback: true` inherently requests formal approval.
  - **Do NOT include 'Other' or enumerations**: Never include an 'Other/Custom' option or hardcoded bullet numbering; the UI injects write-in fields and enumerates selections by default.
  - **Do NOT include instruction trailers**: Never include text like "Select all that apply" in question titles; the UI displays appropriate controls based on the `is_multi_select` boolean.
- **Option Formatting Standards**:
  - **Direct Response Voice**: Format option strings directly as the user's intended response rather than describing agent actions (e.g., `"Use PostgreSQL with SQLAlchemy ORM"`, not `"I will implement PostgreSQL for you"`).
  - **Recommendations**: If technical evidence favors a specific approach, list it as the first item and prefix its text with `(Recommended)`.
  - **Multi-Select Enablement**: Set `is_multi_select: true` when presenting non-mutually exclusive feature configurations or concurrent test suite selections.

### Advanced Alignment: The `/grill-me` Slash Command
- **Recommendation Rule**: When a user presents a complex, abstract idea or an underspecified system architecture, suggest they trigger the `/grill-me` slash command.
- **Behavioral Purpose**: Invoking `/grill-me` transitions the session into an interactive engineering interview where the agent systematically drills down into technical trade-offs, scalability invariants, and design preferences before formal planning commences.
