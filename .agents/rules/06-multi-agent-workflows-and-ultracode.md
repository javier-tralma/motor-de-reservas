# Multi-Agent Workflows, Quality Patterns & Ultracode Adaptation

This project rule governs advanced multi-agent orchestration, deterministic pipeline structuring, and deep verification quality patterns within Google Antigravity. It adapts Claude Code Opus 5's `Workflow` tool, Ultracode mode, and `/teamwork-preview` concepts into scalable Antigravity multi-agent architectures.

---

## 1. Deterministic Orchestration & Ultracode Philosophy

When tackling massive codebase audits, cross-repository migrations, or adversarial security reviews, single-agent context windows can hit memory boundaries or overlook edge cases. Multi-agent orchestration resolves this by decomposing work into structured, deterministic fan-out workflows.

### Strict Opt-In Boundaries
Multi-agent workflows can spawn dozens of background subagents and consume extensive computational tokens. Adhere strictly to authorization boundaries:
- **Explicit Opt-In Required**: Do **NOT** initiate comprehensive multi-agent workflows or wide agent fan-outs unless the user explicitly opts into scaled orchestration by:
  - Mentioning keywords like **"ultracode"**, **"comprehensive multi-agent"**, or **"teamwork"** in their prompt.
  - Activating explicit slash commands such as **`/teamwork-preview`** or an autonomous **`/goal`** directive.
  - Directly requesting orchestration in their own words ("fan out subagents", "use a multi-agent workflow", "run an exhaustive parallel audit").
- **Proactive Consultation**: For standard tasks that would conceptually benefit from parallel multi-agent decomposition without explicit opt-in, execute standard single-agent exploration or briefly outline the potential multi-agent strategy, estimated scale, and token trade-offs, requesting user approval before launching.

### Standing Ultracode / Goal Execution
When an autonomous `/goal` directive or standing Ultracode reminder is active in the session:
- Author and execute structured multi-agent workflows by default for every substantive engineering challenge across all software lifecycle phases (Understand → Design → Implement → Review).
- Token cost is subordinated to exhaustive correctness and thoroughness. Coordinate sequential workflows across turns, staying in the control loop between distinct project milestones.
- Operate solo without subagent orchestration only on conversational clarifying turns or trivial mechanical edits.

---

## 2. The Six Canonical Quality Patterns

When formulating multi-agent orchestration structures, adapt Claude Code's six foundational verification and discovery patterns into native Antigravity subagent deployments:

### Pattern 1: Adversarial Verify (Skeptical Panel)
To prevent plausible-but-incorrect bug reports or speculative architecture from surviving implementation:
- For every material engineering finding, bug diagnosis, or security vulnerability discovered, invoke $N$ independent skeptical subagents (using `invoke_subagent` with built-in `research` or custom verifiers via `define_subagent`).
- **Skeptics Prompting**: Prompt each subagent explicitly to **REFUTE** the claim ("Analyze finding X with adversarial skepticism. Try to prove why this is not a bug or why the proposed fix will fail. Default to refuted=true if empirical proof is lacking").
- **Resolution Voting**: Eliminate any finding or architecture proposal that falls to majority refutation ($\ge 2$ out of 3 skeptics refute).

### Pattern 2: Perspective-Diverse Verify
When an implementation or code review can fail across distinct technical vectors, assign specialized analytical lenses to parallel subagents rather than deploying identical reviewers:
- **Diverse Lenses**: Launch concurrent subagents assigned to specific domain paradigms:
  - Subagent 1: *Logical Correctness & State Integrity*
  - Subagent 2: *Defensive Security & Input Validation*
  - Subagent 3: *Performance, LCP & Memory Leak Audition*
  - Subagent 4: *Web Accessibility (a11y) & UI Modernity*
- Diversity identifies structural failure modes that simple computational redundancy ignores.

### Pattern 3: Judge Panel (Competitive Synthesis)
When solving complex structural challenges where solution space is wide:
- **Parallel Prototyping**: Spawn concurrent subagents in isolated workspaces (`Workspace: 'branch'`) to implement independent solution prototypes from competing philosophical angles (e.g., *MVP Simple Approach* vs. *High-Performance Zero-Copy Approach* vs. *Extensible Enterprise Pattern*).
- **Evaluation & Grafting**: Deploy a high-reasoning judge agent to score the parallel designs against project invariants, synthesize the winning core architecture, and graft high-value secondary optimizations from runners-up.

### Pattern 4: Loop-Until-Dry (Exhaustive Discovery)
For unknown-size domain discovery (e.g., sweeping flaky test logs, scanning security sanitization flaws, or hunting memory leaks):
- **Dynamic Convergence**: Do not stop at arbitrary numeric counters (e.g., "stop after finding 10 bugs"). Execute iterative subagent search rounds until **$K$ consecutive sweeps yield zero fresh findings** ($K \ge 2$).
- Maintain a centralized deduplication inventory in `task.md` or a scratch artifact to compare incoming reports against previously recorded signatures.

### Pattern 5: Multi-Modal Sweep
When surveying broad repositories where a single querying strategy leaves blind spots, invoke parallel subagents deploying mutually independent discovery methods:
- Method A: Lexical pattern & regex scanning via `grep_search`.
- Method B: Filesystem hierarchy & packaging inspection via `list_dir`.
- Method C: Historical evolution tracking via git commit logs and bug tickets using `run_command` (`git log -n 50`, `gh pr list`).
- Method D: Dynamic application execution or unit test failure tracing using `run_command`.

### Pattern 6: Completeness Critic & No Silent Caps
Before declaring any exhaustive verification or multi-agent goal complete:
- **The Critic Pass**: Deploy a final diagnostic subagent tasked exclusively with answering: *"What remains missing? Which architectural modality was unexamined, which empirical claim remains unverified by test execution, or which documentation file went unread?"*. Convert critic findings into the subsequent operational task list.
- **No Silent Caps**: If compute limits or sampling caps constrain a workflow (e.g., analyzing only top-20 slow endpoints), explicitly document the truncation in user reports and artifacts. Never present silently bounded outputs as complete workspace coverage.

---

## 3. Executing Workflows in Antigravity

Translate abstract workflow scripts into resilient Google Antigravity implementation techniques:

### Coordination Architectures: Pipeline vs. Barrier Sync
When scheduling sequential multi-agent stages (e.g., Stage 1: Discovery $\to$ Stage 2: Verification $\to$ Stage 3: Synthesis):
- **Default to Pipeline (Asynchronous Streaming)**: Allow downstream verification stages to begin immediately as individual discovery subagents complete and report back via `send_message`. Never force fast subagents to sit idle waiting for slow peer workers.
- **When to Use Barrier Synchronization**: Impose a global barrier (awaiting completion of all parallel subagents before proceeding) strictly when Stage $N$ mathematically requires cross-item context across the complete aggregated output of Stage $N-1$ (e.g., performing global cross-file deduplication or sorting findings by structural dependency before initiating test verification).

### Script vs. Native Orchestration
- **Native Tool Coordination**: For straightforward multi-agent pipelines, coordinate subagents directly using sequential loops of `invoke_subagent`, `send_message`, and real-time progress tracking inside `<appDataDir>/brain/<conversation-id>/task.md`.
- **Scripted Deterministic Execution**: When orchestrating complex mathematical convergence loops, custom tournament brackets, or programmatic parsing across hundreds of files, construct self-contained Python or Node.js workflow scripts inside `<appDataDir>/brain/<conversation-id>/scratch/` and execute them deterministically using `run_command`.

### Token Budgeting & Model Tier Optimization
- During scaled multi-agent executions, actively govern token consumption across the shared session pool.
- Assign lightweight models (`Model: 'flash'` or `'flash_lite'`) to high-volume mechanical finders, linter sweeps, and multi-modal searchers.
- Reserve premier reasoning models (`Model: 'pro'`) exclusively for adversarial skeptics, competitive judge panels, and final architectural synthesizers.
