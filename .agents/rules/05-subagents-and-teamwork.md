# Subagent Orchestration, Communication & Teamwork

This project rule sets standard operational protocols for delegating tasks, managing background workspaces, and communicating across autonomous agent teams in Google Antigravity. It adapts Claude Code Opus 5's `Agent`, `SendMessage`, and `TaskStop` tools into native Antigravity subagent workflows.

---

## 1. Subagent Invocation & Architecture

When confronting multifaceted software engineering tasks, leverage specialized subagents to decompose complexity, execute concurrent explorations, and protect the parent agent's context window from raw data sprawl.

### When to Invoke Subagents
- **Broad Fan-Out Research**: Performing codebase-wide sweeps across dozens of files, log directories, or structural conventions where only the synthesized engineering conclusion is needed in primary context.
- **Concurrent Independent Workflows**: Executing isolated bug remediation, documentation auditing, and unit test compilation simultaneously across disparate repository domains.
- **Specialized Domain Expertise**: Leveraging focused tools or restricted permissions for targeted tasks (e.g., read-only code exploration, deep web scraping, or database debugging).

### When to Avoid Subagents
- Do not spawn subagents for single-fact lookups where the exact target file path, configuration variable, or symbol name is already known. Use direct native tools (`view_file`, `grep_search`, `list_dir`) instead.
- Once a research subagent is deployed for a specific discovery task, never execute parallel redundant search queries directly in the parent turn; allow the background subagent to deliver its report.

---

## 2. Subagent Types & Custom Definitions

Google Antigravity provides both eager built-in subagent profiles and runtime custom agent definition capabilities:

### Built-in Subagent Types
- `research`: A read-only research assistant equipped exclusively with read tools (`view_file`, `grep_search`, `list_dir`, `read_url_content`, `search_web`). Reach for `research` when surveying documentation, inspecting codebases, or conducting web research without any risk of unexpected workspace file mutation.
- `self`: An identical subagent cloning the parent agent's complete configuration, model capabilities, and read/write tool suite. Reach for `self` when delegating full end-to-end implementation tasks that require independent multi-step testing and code modification.

### Dynamic Custom Subagents (`define_subagent`)
When a specialized engineering workflow requires tailored system instructions or restrictive tool group boundaries, define a dedicated subagent type on the fly using `define_subagent`:
- **Required Parameters**:
  - `name`: Unique identification slug (e.g., `sql-debugger`, `security-auditor`).
  - `description`: Human-readable summary defining exact operational scope and when to reach for this agent.
  - `system_prompt`: Rigorous, domain-specific instructions governing the subagent's execution rigor and formatting standards.
  - **Tool Permissions**: Explicitly configure granular capabilities via boolean flags (`enable_write_tools`, `enable_mcp_tools`, `enable_subagent_tools`).
- **Lifecycle Persistence**: Once defined in a session via `define_subagent`, the custom agent type persists throughout the conversation. Invoke it repeatedly using `invoke_subagent` without executing redundant re-definition tool calls.

---

## 3. Concurrent Invocation & Workspace Modes (`invoke_subagent`)

The `invoke_subagent` tool launches one or more background agents concurrently. Master its parameterization to ensure high-performance execution:

### Batching Concurrent Agents
- To execute parallel work streams, pass multiple task specifications inside the `Subagents` JSON array within a single `invoke_subagent` tool call. Each array entry instantiates an independent subagent with a unique `conversationID`.
- **Mandatory Configuration**: For every subagent entry, specify:
  - `TypeName`: Target built-in (`research`/`self`) or custom defined name.
  - `Role`: A professional 2–5 word description formatted like an engineering job title (e.g., `Frontend LCP Analyzer`, `Database Migration Auditor`) to distinguish concurrent workers.
  - `Prompt`: An actionable, precise task description detailing exact goals, target directory boundaries, and required output formatting.

### Model Selection Strategy (`Model` argument)
- Default strictly to `'inherit'` to utilize the calling agent's model class unless user instructions or budget constraints demand otherwise.
- Select `'flash_lite'` or `'flash'` for high-speed, lightweight tasks like simple regex keyword sweeps, syntax lint checking, or single-file summary extraction.
- Select `'pro'` exclusively for complex architectural tasks requiring deep contextual reasoning, multi-step refactoring, or adversarial review synthesis.

### Workspace Isolation Modes (`Workspace` argument)
Adapt legacy git worktree and remote isolation concepts into Antigravity workspace modes:
- `inherit` (Default): The subagent operates directly inside the parent agent's active filesystem workspace. Use when subagents perform read-only searches or cooperative non-overlapping edits.
- `branch`: Creates an isolated workspace cloned or branched from the parent repository. **Must use** when launching concurrent write-enabled subagents that mutate identical files or compile conflicting experimental builds, completely avoiding filesystem race conditions.
- `share`: Creates a lightweight shared workspace utilizing the underlying repository directory (analogous to git worktrees or Mercurial `hg share`), enabling independent branching without duplicating storage disk volume.

---

## 4. Inter-Agent Communication & Messaging (`send_message`)

Maintain structured communication across team subagents without leaking conversational metadata into user UI chat:

### Direct Agent-to-Agent Messaging
- Your plain text output rendered in terminal chat is **NEVER** visible to background subagents or teammates. To deliver instructions or relay context, you **MUST** call the `send_message` tool targeting the recipient's unique `Recipient` ID (the subagent's `conversationID`).
- **Continuity Over Spawning**: Before deploying a new subagent via `invoke_subagent`, check whether an existing running or recently completed subagent already possesses the necessary architectural context. If the new requirement is a natural continuation of prior work, transmit the follow-up prompt to that agent via `send_message` to conserve tokens and preserve historical continuity.
- **Strict User Prohibition**: **NEVER** invoke `send_message` to communicate with the human user. Always emit visible plain text and Markdown in chat for user interactions.

---

## 5. Reactive Wakeup & Lifecycle Management

Google Antigravity operates an asynchronous event messaging topology equipped with reactive wakeups:

### Zero-Polling Asynchrony
- After launching background subagents via `invoke_subagent`, **DO NOT** execute polling loops, repetitive status checks, or intentional thread sleeps. 
- Simply proceed with independent concurrent tasks or cease calling tools to yield your turn. The Antigravity runtime automatically resumes execution and delivers complete message contents directly into active context the moment a background subagent completes or transmits an interim message.

### Subagent Lifecycle Administration (`manage_subagents`)
Adapt legacy task termination utilities (`TaskStop`) to Antigravity's centralized agent administration tool:
- **Audit Active Workers**: Invoke `manage_subagents` with `Action: 'list'` to enumerate all active background subagents and retrieve their conversation IDs.
- **Terminating Runaways**: When an exploratory subagent hangs, enters an unproductive recursive loop, or becomes superseded by user plan modifications, invoke `manage_subagents` with `Action: 'kill'` accompanied by targeted `ConversationIds` (or `Action: 'kill_all'` for global cleanup). 
- **Preservation Semantics**: Terminating a subagent instantly purges its temporary branched disk workspaces while permanently preserving its historical logs, conversation transcripts, and generated artifacts in the session brain directory.
