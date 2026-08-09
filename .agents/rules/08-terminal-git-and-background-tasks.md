# Terminal Execution, Git Discipline & Background Task Management

This project rule establishes operating standards for executing command-line instructions, managing persistent daemon background processes, and interacting with version control within Google Antigravity. It adapts Claude Code Opus 5's terminal commands (`Bash`), task utilities (`Monitor`, `TaskOutput`, `TaskStop`), and git worktree tools (`EnterWorktree`/`ExitWorktree`) into high-reliability Antigravity execution workflows.

---

## 1. Terminal Command Execution (`run_command`)

When filesystem tools are insufficient for build compilation, environment diagnostics, or system administration, leverage the native Linux shell via `run_command`:

### Working Directory & Command Syntax Discipline
- **Absolute Workspace Constraint**: The current working directory (`Cwd`) **MUST** reside within an active workspace URI or an authorized scratchpad directory (`<appDataDir>/brain/<conversation-id>/scratch/`). Never execute commands in `/tmp`, `/home`, or out-of-workspace locations unless explicitly authorized by user rules.
- **Never Propose Standalone `cd` Commands**: Never invoke a terminal command consisting solely of `cd <dir>`. Working directory navigation across turns must be handled by setting the appropriate `Cwd` parameter on subsequent invocations.
- **Pager & Output Volume Limitation**: Automated terminal execution runs under `PAGER=cat`. For commands that typically rely on interactive pagers or generate immense log output (e.g., `git log`, verbose unit tests, packet sniffer traces), explicitly limit output volume using native flags or piping (e.g., use `git log -n 15` or `pytest --quiet | head -n 50`).

---

## 2. Sandboxing & Persistent Terminals

Google Antigravity secures terminal execution through controlled sandboxing while providing advanced persistence for complex compilation environments:

### The Sandbox Policy (Try Sandboxed First)
- By default, `run_command` executes inside a secure sandbox (`BypassSandbox: false`) that permits read/write operations across your workspace but isolates external network access and system root alterations.
- **Mandatory Try-First Rule**: You **MUST** attempt to run all command invocations in Standard Sandbox Mode first. Do not pre-judiciously assume a command will fail without bypass; users frequently configure local mock services or out-of-band whitelists.
- **Elevation Protocol**: Switch to `BypassSandbox: true` ONLY after an initial sandboxed attempt fails due to proven network or isolation constraints, and only after securing explicit user confirmation or verified global authorization.

### Persistent Terminal Environments (`RunPersistent` & `RequestedTerminalID`)
Standard terminal executions represent isolated `bash -c` subshells that discard exported environment variables upon termination. To execute sequential builds requiring stateful environment configurations:
- Set `RunPersistent: true` on the initial setup command (e.g., exporting API secrets or activating virtual Python environments).
- Capture the returned `TerminalID` and pass it into the `RequestedTerminalID` argument on subsequent `run_command` calls to share environment variables and exported shell definitions seamlessly across turns.

### Standing Daemon Processes (`IsDaemon: true`)
- When launching long-running support servers that are meant to run indefinitely in the background without finishing on their own (e.g., dev servers like `npm run dev`, Vite servers, webpack hot-reload file watchers, local port tunnels), explicitly set `IsDaemon: true`.
- Leave `IsDaemon: false` (default) for ordinary commands that are expected to terminate autonomously after executing their task.

---

## 3. Background Tasks & Event Monitoring (`manage_task`)

Adapt Claude Code's background Bash loops, log stream monitoring (`Monitor`), and output fetching (`TaskOutput`/`TaskStop`) into Antigravity's centralized task manager:

### Automated Asynchronous Transitions
- When executing long-running builds or test suites, configure `WaitMsBeforeAsync` (between 500ms and 10,000ms). If command execution exceeds this threshold, the runtime detaches the process into a running background task and returns immediately with a unique human-readable Task ID.

### Reactive Wakeups (Zero Polling Required)
- **Never Poll in a Loop**: DO NOT execute repetitive loops calling `manage_task` with `Action: "status"` to wait for command completion or monitor progress.
- Once a command goes to the background, proceed with independent concurrent work or cease calling tools to yield your turn. The Antigravity runtime automatically re-invokes you with an instant message notification the moment a background task concludes or emits significant output events.

### Task Administration Actions (`manage_task`)
Control background jobs and standing daemons using explicit operational actions:
- `list`: Enumerate all currently running background tasks, daemons, and cron jobs.
- `status`: Retrieve running status and obtain the authoritative log file URI. Use `view_file` directly on that log URI to inspect historical stdout/stderr execution dumps (replacing Claude Code's deprecated `TaskOutput`).
- `send_input`: Inject interactive standard input (`Input`) directly into a running background process (useful for answering CLI confirmation dialogs or entering test passwords).
- `kill`: Immediately terminate running processes, hanging scripts, or completed monitoring watches (replacing `TaskStop`).

### Streaming Event Monitoring (Replacing `Monitor`)
When tasked with watching long-running logs or process event streams:
- Launch a detached background pipeline using `run_command` with line-buffered flushing: `tail -f /var/log/app.log | grep --line-buffered -E "Server running|ERROR|Exception|Crash|Killed"`.
- **Failure Signature Coverage (Silence is not Success)**: When watching a job for an outcome, your regular expression filter must match every terminal failure state (crashes, stack traces, out-of-memory stops), not just happy-path progress markers. A filter watching only for success stays completely silent through a crashloop, which looks indistinguishable from a running job.
- Always ensure piping tools flush per line (`grep --line-buffered`, `awk -W interactive`); never pipe through `head -n`, which buffers until full line accumulation and hangs monitoring streams.

---

## 4. Git Discipline & GitHub Operations

Enforce professional version control hygiene across all collaborative repositories:

### Strict Command Prohibitions
- **No Interactive Flags**: Never execute interactive git flags (`-i`, such as `git rebase -i`, `git add -i`, or `git commit -v`). Interactive pagers freeze automated agent execution.
- **Exclusive GitHub Platform CLI**: Use the official `gh` command-line tool exclusively for GitHub repository operations (creating pull requests, inspecting issues, querying GitHub Actions API logs, and triggering workflow runs). Never scrape GitHub web pages with curl when `gh api` is accessible.

### Commit & Branching Protection
- **No Unsolicited Commits or Pushes**: Never execute `git commit`, `git push`, or alter remote branch ref states unless the user explicitly commands it.
- **Branch First**: If initiated on the repository's default branch (`main` or `master`), proactively generate and switch to a descriptive feature branch (`git checkout -b <feature-slug>`) before mutating codebase files.

### Mandatory Attribution Footers
Ensure all automated commits and PR summaries carry standardized AI co-authorship attribution:
- **Git Commit Message Trailer**: End all git commit messages with the literal attribution line:
  `Co-Authored-By: Google Antigravity Agent <no-reply@google.com>`
- **Pull Request Description Footer**: End all generated GitHub PR descriptions with the exact block:
  ```markdown
  🤖 Generated with [Google Antigravity](https://antigravity.google)
  ```

---

## 5. Worktree Isolation & Workspace Management

Adapt Claude Code Opus 5's git worktree utilities (`EnterWorktree` and `ExitWorktree`) into scalable Google Antigravity multi-workspace procedures:

### When to Implement Worktrees
- Utilize git worktree isolation **ONLY** when explicitly commanded by the user ("start an isolated worktree", "work in a worktree") or when launching concurrent write-enabled subagents via `invoke_subagent` (`Workspace: "branch"` or `"share"`). Never reach for worktree creation when standard git branch switching suffices.

### Manual Worktree Management via Terminal
When manual worktree isolation is explicitly authorized in a standard turn:
- **Creating an Isolated Worktree**: Execute `git worktree add -b <new-branch> .gemini/worktrees/<worktree-name> origin/main` via `run_command`. Subsequently set your `Cwd` to that worktree path for isolated build experiments.
- **Exiting and Cleanup (Replacing `ExitWorktree`)**: Upon task completion or user exit instructions, return your `Cwd` to the primary repository root. If clean removal is specified (`remove`), execute `git worktree remove .gemini/worktrees/<worktree-name>` after verifying uncommitted changes with the user.
