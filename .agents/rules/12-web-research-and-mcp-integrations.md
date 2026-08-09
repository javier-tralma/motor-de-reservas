# Web Research, MCP Integrations & Browser Automation

This project rule establishes operating standards for conducting external internet research, automating live browser interactions, and calling external tools via the Model Context Protocol (MCP) within Google Antigravity. It adapts Claude Code Opus 5's web fetchers (`WebFetch`), search utilities (`WebSearch`), and external tool APIs into native Antigravity integrations.

---

## 1. Web Exploration Tools (`read_url_content` & `search_web`)

When architectural validation, API documentation verification, or third-party dependency analysis requires external web reconnaissance, deploy Google Antigravity's native internet suite:

### Silent URL Content Extraction (`read_url_content`)
- **Operational Scope**: Converts public static HTML web pages and online technical documentation directly into readable Markdown via optimized HTTP requests (completely invisible to user UI observation).
- **Ideal Use Cases**: Fast batch reading of public software documentation, developer reference manuals, open-source repository readmes, or static tutorials where parsing speed is paramount and no interactive DOM manipulation is required.
- **Tool Limitations**: Executes standard HTTP GET requests without JavaScript compilation or DOM rendering. Cannot bypass authentication logins, CAPTCHAs, or client-side single-page applications (SPAs). For JavaScript-dependent pages, transition to live Chrome DevTools MCP automation.

### Domain-Targeted Web Searching (`search_web`)
- **Operational Scope**: Performs semantic web searching across open internet indices, returning structured documentation summaries and URL citations.
- **Targeted Domain Priority**: When investigating specialized frameworks, SDKs, or cloud providers, always leverage the optional `domain` parameter (e.g., `domain: "developer.mozilla.org"`, `domain: "kubernetes.io"`, or `domain: "docs.python.org"`) to constrain search algorithms toward authoritative official developer guidance over unverified secondary forums.
- **Mandatory Source Citations**: When incorporating external research findings into chat reports, engineering plans, or architectural artifacts, you **MUST** provide clickable Markdown hyperlinks directly citing the source origin (`[Mozilla Web API Docs](https://...)`) to guarantee verifiable technical accountability. Never invent or hallucinate API definitions when network lookups fail.

---

## 2. Interactive Browser Automation (Chrome DevTools via MCP)

When documentation portals demand user authentication, complex single-page application (SPA) client rendering, performance profiling, or visual interactive testing:

### Deploying Browser Automation
- Standard HTTP tools (`read_url_content`) fail silently on dynamic client web frameworks. To interact with dynamic targets, deploy Chrome DevTools tools exposed via MCP (or advise the user to activate the **`/browser`** slash command).
- **Capabilities**: Navigate live target pages, execute dynamic JavaScript injections, click authentication dialog modals, capture heap snapshots, and trace network request lifecycles in real time.
- **Visual & Performance LCP Debugging**: When executing UI frontend adjustments, leverage live DevTools connections to capture visual rendering screenshots and measure Largest Contentful Paint (LCP) execution timelines directly inside the runtime browser canvas.

---

## 3. Model Context Protocol (MCP) Architecture

Google Antigravity interfaces with third-party software servers, database connections, and specialized domain tools through the standardized **Model Context Protocol (MCP)**.

### MCP Server Repository Structure
- Every connected MCP server resides inside `<appDataDir>/mcp/<serverName>/`. This directory houses explicit JSON tool schemas (`<toolName>.json`) defining exact argument properties, alongside optional operational documentation (`instructions.md`).

### Eager vs. Lazy Tool Invocation Strategies
Antigravity categorizes MCP tool registrations into two execution tiers:
- **Eager Tools (Native Call Style)**: Eagerly loaded MCP tools register directly into your primary native tool vocabulary under the naming convention `mcp_<serverName>_<toolName>`. Invoke eager tools directly without routing through wrapper tools.
- **Lazy Tools (`call_mcp_tool`)**: High-volume domain servers (e.g., `StitchMCP` for UI design design systems) register lazily to preserve token context limits. 
  - **Mandatory Schema Inspection**: Before invoking any lazy MCP tool, you **MUST** inspect its parameter definitions by reading its schema file using `view_file`: `<appDataDir>/mcp/<serverName>/<toolName>.json`.
  - **Wrapper Execution**: Once arguments are understood, execute the lazy tool by calling `call_mcp_tool` passing exact strings for `ServerName`, `ToolName`, and a properly typed JSON object for `Arguments`.

### Server Resource Retrieval (`list_resources` & `read_resource`)
When an attached MCP server provides virtual filesystem templates, database design schemas, or remote design bundles:
- **Enumerate Offerings**: Invoke `list_resources` specifying the target `ServerName` to discover available remote URIs and asset names.
- **Extract Content Streams**: Call `read_resource` passing the target server and exact unique `Uri` string to ingest raw resource payloads directly into active analytical context.

---

## 4. Security, Offline Resilience & Sandbox Fallbacks

Maintain engineering resilience when web networking or MCP server channels encounter security roadblocks:

### Sandbox Isolation Handling
- In Google Antigravity, terminal commands via `run_command` operate sandboxed by default (`BypassSandbox: false`), which restricts raw command-line network utilities (`curl`, `wget`, `ssh`).
- **Offline Contingency Protocols**: If direct network fetching or MCP servers become unreachable or offline due to security restrictions:
  - Do **NOT** fabricate SDK methods, function signatures, or configuration syntax from LLM training memory.
  - State the network isolation constraint plainly in your technical report.
  - Turn immediately to offline local repository resources: use `grep_search` to audit installed dependency vendor directories (e.g., searching within `node_modules/`, local `.venv/` packages, or checked-in markdown documentation) to verify authentic symbol usages directly from locally compiled library sources.
  - Request user authorization for elevated network bypass (`BypassSandbox: true` or checking network whitelists) only if local offline repository reconnaissance proves completely insufficient.
