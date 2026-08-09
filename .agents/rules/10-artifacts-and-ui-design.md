# Artifacts, Web UI Aesthetics & Visual Demonstration

This project rule establishes rigorous engineering standards for producing structured documentation artifacts, developing interactive web applications, and delivering high-impact visual user interfaces in Google Antigravity. It adapts Claude Code Opus 5's `Artifact` publishing capabilities and web design protocols into native Antigravity visual workflows.

---

## 1. Antigravity Artifacts System & Storage Anatomy

Artifacts represent specialized, structured Markdown documents created to deliver comprehensive reports, living architectural plans, and interactive design summaries directly into the Antigravity UI canvas.

### Authoritative Artifact Storage Path
- **Brain Directory Root**: All user-facing artifacts **MUST** be written directly to `<appDataDir>/brain/<conversation-id>/filename.md` using `write_to_file`. The runtime creates this parent directory automatically upon invocation.
- **Descriptive Naming Discipline**: Assign clear, domain-specific basenames (`analysis_results.md`, `security_audit_report.md`, `architecture_spec.md`). Do not save ephemeral scratch scripts or temporary processing logs in root artifact storage; route transient files to `<appDataDir>/brain/<conversation-id>/scratch/`.

### When to Construct Artifacts
- **Mandatory Artifact Targets**: Use artifacts exclusively for comprehensive architectural specifications, multi-dimensional comparison tables, extensive research findings, Living TODO tracking checklists (`task.md`), Implementation Plans (`implementation_plan.md`), and historical validation records (`walkthrough.md`).
- **Strict Prohibition for Brief Interaction**: Do **NOT** generate artifacts for conversational single-paragraph answers, simple one-off questions, code refactoring diffs intended for direct application, or brief exploratory replies. Respond directly in standard chat text instead.

### The Zero-Resummarization Policy
- After creating or modifying an artifact file, **DO NOT** re-summarize the full text or duplicate extensive code blocks back into visible chat. 
- Point the user directly to the clickable file link (`[analysis_results.md](file:///path/to/artifact/analysis_results.md)`) and concisely highlight solely the open engineering decisions, action items, or critical warnings requiring user alignment.

---

## 2. Advanced Markdown Formatting Excellence

When composing markdown artifacts, enforce high-readability architectural styling:

### Strategic GitHub Alerts
Highlight critical engineering constraints using GitHub alert formatting. Do not place alerts consecutively or nest them within fenced code blocks:
- `>[!NOTE]` Background system context, configuration subtleties, or helpful architectural explanations.
- `>[!TIP]` Performance optimizations, algorithmic complexity improvements, or best practice efficiencies.
- `>[!IMPORTANT]` Essential build prerequisites, critical deployment requirements, or mandatory step sequences.
- `>[!WARNING]` Deprecation notices, breaking compatibility changes, or potential regression vectors.
- `>[!CAUTION]` High-risk destructive database alterations or dangerous security exposures.

### Fenced Syntax Blocks & Diff Visualization
- Enforce exact language syntax labels on all code blocks (`python`, `typescript`, `rust`, `html`, `css`).
- For structural design proposals not yet committed to codebase files, display code modifications using standard diff syntax blocks (leading `+` for additions, `-` for deletions, and a space for unaltered context lines).

### Mermaid Diagrammatic Integrity
Visualize multi-tiered dependencies, state transitions, and network pipelines using fenced `mermaid` diagrams:
- Always enclose node labels containing special characters, parentheses, mathematical operators, or brackets within quotation marks (e.g., `id["User Authentication (OAuth 2.0)"]`) to prevent compiler rendering breaks.
- Never embed raw HTML tags within Mermaid node syntax.

### Sequential Carousels (`carousel`)
Condense lengthy comparative walkthroughs, multi-step UI progressions, or alternative layout proposals using Antigravity carousel code blocks:
- Enclose the entire carousel section within four backticks labeled with the `carousel` identifier (` ````carousel `).
- Separate distinct visual slides or code blocks using explicit literal HTML comments: `<!-- slide -->`.
- Four backticks enable clean nesting of standard three-backtick code blocks and tables inside individual slides.

### Media & Image Embedding Rules
To embed images, architectural diagrams, or video captures inside an artifact document:
- You **MUST** utilize explicit Markdown image syntax accompanied by absolute file paths: `![caption description](/absolute/path/to/image.png)`. Standard hyperlinks (`[link](/path/to/image.png)`) will **NOT** render visual assets in the UI canvas.
- **Mandatory Brain Directory Colocation**: Only embed visual files located inside `<appDataDir>/brain/<conversation-id>/`. If referencing an external image from workspace storage or screenshot utilities, you **MUST** copy the file directly into the active conversation brain directory before embedding its absolute URI.

---

## 3. Web Application Development & Design Aesthetics

When tasked with building interactive prototypes, demonstrations, or full web applications, enforce premier modern design engineering standards:

### Technology Stack Standards
- **Core Architecture**: Utilize semantic HTML5 for DOM structure and robust JavaScript (ES6+) for client-side state logic.
- **Styling Flexibility (Vanilla CSS Priority)**: Default strictly to Vanilla CSS to guarantee complete animation control and zero compilation dependencies. Avoid incorporating TailwindCSS unless the user explicitly commands it; in that event, confirm the exact target Tailwind version before authoring utility classnames.
- **Framework Initialization**: If a sophisticated web app framework (Vite, Next.js, React) is explicitly requested, invoke non-interactive scaffolding via sandboxed terminal commands: ALWAYS run `--help` first to inspect CLI options, deploy directly into current working directories using `./` (`npx -y create-vite@latest ./ --template vanilla-ts`), and execute with non-interactive flags to prevent CLI hang states.

### Prioritize Visual Excellence (The "WOW" Factor)
Implement state-of-the-art user interfaces that project exceptional polish and premium craftsmanship at first glance. Building a basic, uninspired MVP design is **UNACCEPTABLE**:
- **Curated Color Palettes**: Completely reject generic primitive colors (plain red, blue, green). Engineer harmonious, tailored color palettes utilizing sophisticated HSL color ratios, sleek dark modes, subtle linear gradients, and vibrant accent contrasts.
- **Modern Typography**: Import premier sans-serif font families from Google Fonts (e.g., Inter, Outfit, Roboto, Plus Jakarta Sans) instead of defaulting to sterile system browser fonts. Maintain proper typographic scale and hierarchy across headings (`<h1>` strictly once per page).
- **Dynamic Micro-Animations & Glassmorphism**: Bring interfaces to life using responsive interactivity. Incorporate smooth hover transitions, glassmorphic backdrop filter effects (`backdrop-filter: blur(12px)`), custom styled scrollbars, and tactile button micro-animations to maximize UX interaction satisfaction.

---

## 4. Zero-Placeholder Policy & Image Generation (`generate_image`)

When assembling interactive demonstrations, layout mockups, or custom user interfaces:
- **Absolute Prohibition of Placeholders**: **NEVER** insert sterile gray wireframe boxes, generic placeholder text loops, or broken third-party mock URLs (`placehold.co`, `placekitten.com`, `via.placeholder.com`) into generated presentation layouts or HTML prototypes!
- **Dynamic Asset Generation (`generate_image`)**: When visual assets, UI mockups, icons, or background illustrations are required, invoke your native `generate_image` tool proactively:
  - Provide an imaginative, comprehensive text `Prompt` describing exact lighting, compositional depth, and aesthetic style.
  - Define a clean, lowercase `ImageName` under 3 words separated by underscores (e.g., `hero_dashboard_bg` or `avatar_profile_icon`).
  - Specify appropriate aspect ratios (`AspectRatio: "16:9"` for desktop containers, `"1:1"` for avatars, `"9:16"` for mobile viewports).
  - Save generated artifact images directly into active brain directory storage and embed them natively into your HTML prototypes or Markdown reports to deliver a functional, turnkey demonstration.

---

## 5. Safety & Ethical Publishing Boundaries

Adapt Claude Code Opus 5's strict publishing ethics into Antigravity artifact and web development execution:
- **Zero Deception or Phishing**: Never generate, publish, or deploy artifacts or web applications that imitate real-world corporate brands, financial institution portals, or authentication modals designed to collect user credentials deceptively.
- **Prohibitions on Fabrication**: Refuse instructions requesting the programmatic fabrication of realistic bank statements, verifiable government identification documents, fraudulent receipts, or official corporate legal records.
- **Protection of Privacy**: Do not compile or publish investigatory dossiers, scraping summaries, or defamatory tracking artifacts targeting private civilian individuals. Maintain unwavering defensive engineering integrity across all published output.
