# Skills Architecture, Plugins & Slash Command Reference

This project rule defines standard operational protocols for activating specialized modular skills, leveraging bundled plugins, and proactively recommending user-facing slash commands in Google Antigravity. It adapts Claude Code Opus 5's skills architecture (`review`, `simplify`, `dataviz`, `security-review`) into native Antigravity skill and command frameworks.

---

## 1. Antigravity Skills Architecture

Skills represent extensible folders of specialized technical domain instructions, reusable reference code, and automated execution scripts that empower the agent to solve complex specialized tasks without bloating standard prompt memory.

### Anatomy of a Skill
- Every functional skill resides within a structured plugin directory containing an authoritative instructions document: **`SKILL.md`** (featuring YAML frontmatter defining skill name and trigger heuristics).
- More complex domain skills incorporate specialized subdirectories: `scripts/` (executable helper utilities), `examples/` (canonical design patterns), `resources/` (templates and visual assets), and `references/` (deep technical documentation).

### Mandatory Pre-Read Workflow
- When a user's task matches an available skill's activation heuristics, you **MUST** call `view_file` directly on that skill's exact `SKILL.md` absolute path before commencing codebase exploration or implementing edits.
- Set parameter `IsSkillFile: true` when reading the file to execute its instructions for an active task (leave default `false` when merely inspecting or managing the markdown file).
- **Delegation Exemption**: You may bypass calling `view_file` on `SKILL.md` strictly when delegating the specialized task to a background subagent via `invoke_subagent` that will read and obey the instructions independently in its own conversation window.

---

## 2. Authoritative Available Skills Guide

Master the invocation criteria for Google Antigravity's core specialized skills suite:

### Frontend & Modern Web Guidance (`modern-web-guidance`)
- **Mandatory First Execution**: You **MUST** read and execute this skill FIRST for all HTML/CSS and client-side JavaScript tasks. Do **NOT** skip—browser web APIs evolve rapidly and standard LLM training weights encode obsolete patterns.
- **Immediate Trigger Vectors**: UI Layouts (modals, native dialogs, popovers, glassmorphism/backdrop-filters, CSS anchor positioning, container queries, `:has()`), Motion & Scroll (View Transitions API, scroll-driven animations, parallax), CWV Optimization (LCP, INP, fetch priority), and React/Vue modern layout adaptation.
- **Strict Exclusions**: Do NOT activate for backend SQL databases, ORMs, Express server routes, Docker pipelines, or local Python CLI scripts.

### Chrome DevTools & Debugging Suite
- `chrome-devtools`: Chrome DevTools MCP browser automation, network request inspection, DOM auditing, and runtime logging.
- `troubleshooting`: Diagnosing connection targets when browser commands (`list_pages`, `new_page`, `navigate_page`) fail or WebSocket targets detach.
- `debug-optimize-lcp`: Guided Largest Contentful Paint (LCP) and Core Web Vitals optimization. Activate whenever users report slow loads, delayed hero rendering, or poor CWV metrics.
- `memory-leak-debugging`: Diagnosing JavaScript/Node.js memory leaks, high memory usage, OOM faults, and heap snapshot analysis via memlab.
- `a11y-debugging`: Accessibility auditing against Web.dev standards (semantic HTML5, ARIA roles, keyboard traversal focus loops, tap target scaling, and WCAG color contrast ratios).

### Chrome Extension Engineering (`chrome-extensions`)
- Activate whenever the user commands creation, debugging, or publishing of Manifest V3 Chrome browser extensions.
- **Triggers**: Mentioning `manifest.json`, content scripts, background service workers, side panels, declarativeNetRequest, omnibox extensions, or drafting Chrome Web Store review justifications and privacy disclosures.

### Antigravity Multi-Agent SDK & CLI (`google-antigravity-sdk` & `antigravity-guide`)
- `google-antigravity-sdk`: Activate when designing, coding, or testing customized autonomous AI agents and multi-agent topologies using the official Google Antigravity (AGY) Python SDK.
- `antigravity-guide`: Comprehensive reference guide for the Antigravity IDE, CLI (`agy`), keybindings, slash commands, sidecars, and workspace customizations. Activate upon questions on how to operate or customize AGY 2.0.

---

## 3. Plugins Bundle Integration

Plugins aggregate modular capabilities into functional domain packages across workspace configurations:
- **Plugin Anatomy**: Stored under `<userHome>/.gemini/config/plugins/<plugin-name>/`, containing a root `plugin.json` metadata manifest alongside bundled `skills/` and `agents/` directories.
- **Domain Subagents**: Installed plugins frequently expose pre-configured specialized subagents (e.g., custom debugging agents or web auditors). Audit available plugin agents and invoke them via `invoke_subagent` using their assigned type names just like built-in agents.

---

## 4. Proactive Slash Command Recommendations

Slash commands represent interactive shortcuts in the Antigravity chat UI (e.g., typing `/goal` or `/schedule`) that automate robust workflows. You cannot execute these commands directly; your responsibility is to identify task synergy and explicitly recommend them in visible chat text:

### The Slash Command Inventory
- **`/goal`**: Recommend when a user initiates a massive, long-running engineering challenge (e.g., an overnight cross-repository migration or exhaustive test suite remediation) where they want an autonomous agent to execute continuously with self-auditing loops until total completion without halting for manual verification prompts.
- **`/schedule`**: Recommend when the user desires automated recurring background routines, one-shot reminders, or scheduled CI/CD monitoring triggered directly from chat without manual script authoring.
- **`/browser`**: Recommend when tasks require visual web browsing, dynamic single-page application (SPA) testing, or interactive DOM button clicking in a live browser window.
- **`/grill-me`**: Recommend when a user presents an ambiguous design idea or underspecified architecture and wants to engage in an intense, interactive alignment interview to resolve technical trade-offs before formal implementation planning commences.
- **`/teamwork-preview`**: Recommend when tackling massive monolithic engineering refactoring that would structurally benefit from a synchronized team of autonomous agents operating concurrently across shared git worktrees.
- **`/learn`**: Recommend immediately after the user corrects an operational mistake, debugs a complex compilation setup, or confirms a recurring design convention, ensuring the runtime synthesizes the solution directly into persistent project memory or `.agents/rules/`.
