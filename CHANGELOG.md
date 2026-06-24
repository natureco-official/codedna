# Changelog

## [0.4.2] - 2026-06-24 — "Doctor Legacy Style"

### 🎨 Redesigned
- **`codedna doctor`** — restored to match the legacy CodeDNA CLI aesthetic
  - Old: Rich Table with show_lines + border_style="dim" (looked too plain)
  - New: `console.print()` with `[bold]─── Kategori ───[/bold]` headers
  - Per-line emoji markers: `[green]✓[/green]`, `[yellow]⚠[/yellow]`, `[red]✗[/red]`
  - Spinner: `console.status("[dim]Testler çalıştırılıyor...[/dim]")`
  - Summary panel: `border_style="green"|"yellow"|"red"` depending on result
  - All messages in Turkish (matching the legacy codebase)

## [0.4.1] - 2026-06-24 — "Legacy Style"

### 🎨 Redesigned
- **`codedna setup --show`** — now uses rich Table with cyan border, emoji title, status panel
  - Old style: bare `print()` lines
  - New style: "🧬 CodeDNA — AI Configuration" title, status panel ("AI Ready" green)
- **`codedna update`** — status panels replace plain text
  - "🧬 CodeDNA — Up to date" green panel when current
  - "🧬 CodeDNA — Update Check" yellow panel when update available
  - "🧬 CodeDNA — Update Complete" green panel after install

Matches the legacy CodeDNA CLI visual style (border_style="dim"/"cyan", padding, emoji titles).

## [0.4.0] - 2026-06-24 — "Setup Wizard"

### ✨ Added
- **`codedna setup` command** — interactive AI analysis configuration wizard
  - Provider selection (Anthropic / OpenAI / MiniMax)
  - API key entry (with secure file storage at `~/.codedna/ai_config.json`, chmod 600)
  - Model selection with sensible defaults
  - Enable/disable AI analysis toggle
  - Live connectivity test after save ("test ping" prompt)
  - Reconfigure existing setup (`codedna setup --reset`)
  - Reuses existing `codedna.ai` module — no new dependencies
- **`--reset` flag** — clear existing AI config and start fresh
- **`--show` flag** — display current AI configuration (no edits)

### 🔄 Changed
- Minor version bump (0.3.4 → 0.4.0) because `setup` is a new user-facing command

## [0.3.4] - 2026-06-24 — "Doctor Redesign"

### 🎨 Redesigned
- **`codedna doctor` — rich Table + Panel layout** matching the legacy CodeDNA CLI style
  - Header Panel with version + plan info (`border_style="cyan"`)
  - Animated spinner during checks (`console.status`, dots spinner)
  - Rich Table with `show_lines=True`, header_style cyan
  - Color-coded status column: ✓ green, ⚠ yellow, ✗ red, – dim
  - Summary Panel with color-coded border (green / yellow / red)
  - 9 categories, 19 individual checks

## [0.3.3] - 2026-06-24 — "One-Command Update"

### ✨ Added
- **`codedna update` command** — self-upgrade from PyPI in a single command
  - `codedna update` — upgrade to latest version
  - `codedna update --check` — only check, do not install
  - `codedna update --target 0.3.2` — install a specific version
  - Auto-detects installer (`uv` first, falls back to `pip`)
  - Verifies new version after install
  - User no longer needs to remember `pip install --upgrade` or PATH dance
- **`codedna update --check` exit code** — 0 if up-to-date, 1 if update available (CI-friendly)

## [0.3.2] - 2026-06-24 — "Windows PATH Fix"

### 📚 Documentation
- **Windows PATH setup section** added to README
  - Explains pip's "not on PATH" warning
  - One-time PowerShell fix for current session
  - Permanent fix via `[Environment]::SetEnvironmentVariable`
  - Notes that macOS / Linux users are unaffected
- **Verify Installation subsection** added (`codedna --version`, `codedna doctor`)

## [0.3.1] - 2026-06-24 — "Doctor Added"

### ✨ Added
- **`codedna doctor` command** — System health check
  - Python version (>= 3.10 required)
  - CodeDNA installation
  - Git integration
  - 4 tree-sitter parsers (core, python, javascript, typescript)
  - Local database (size, location)
  - Git hook status
  - 8 core dependencies (typer, rich, gitpython, fastapi, uvicorn, pydantic, pyjwt, bcrypt)
  - License & plan
  - Network reachability (PyPI)
  - **`--fix` flag** — auto-creates database + installs hook when missing
  - Color-coded output (✓ green, ! yellow, ✗ red)
  - Exit 1 on critical issues
  - Fully English output

## [0.3.0] - 2026-06-24 — "English First"

### 🌐 Internationalization
- **Full Turkish → English translation** across the entire project
  - All user-facing CLI strings, error messages, prompts
  - All dashboard pages, components, labels
  - All documentation files (CHANGELOG, CONTRIBUTING, SECURITY, README)
  - Lemon Squeezy integration copy, checkout, webhook responses
  - Tree-sitter risk labels and analyzer output

### 📚 Documentation
- **English-first README, CHANGELOG, CONTRIBUTING, LICENSE, SECURITY**
- **GitHub templates** (`.github/`):
  - `CODEOWNERS` — @gencay as default reviewer
  - `PULL_REQUEST_TEMPLATE.md` — standard PR checklist
  - `ISSUE_TEMPLATE/` — bug report + feature request forms
  - `dependabot.yml` — weekly dependency updates
  - `workflows/test.yml` — Python 3.10/3.11/3.12 matrix
  - `workflows/codeql.yml` — security scanning

### 🎨 Dashboard
- Component renames (Turkish → English):
  - `AnlamaGrafigi.tsx` → `UnderstandingChart.tsx`
  - `HataBanner.tsx` → `ErrorBanner.tsx`
  - `RiskBadge.tsx`, `LanguageSwitcher.tsx` updated

### 🔧 Versioning Note
- **0.2.29 → 0.3.0** (minor bump — language milestone, breaking for Turkish users)
- Breaks the patch-cascade pattern (0.2.2 → 0.2.29 undocumented versions)
- Turkish users on 0.2.x should pin or migrate English UI

## [0.2.1] - 2026-06-24

### Added
- Lemon Squeezy payment integration (Pro ₺400/mo, Team ₺800/mo, Enterprise ₺1,650/mo)
- Webhook handler with HMAC-SHA256 signature verification
- Customer ID tracking (lemonsqueezy_customer_id, subscription_id)
- Dashboard billing page with subscription details + cancel
- Ngrok public URL support for production webhooks
- Dashboard pricing page rewrite with TRY currency
- `codedna plan demo [plan]` command for quick license activation
- `codedna natureco` integration (Pro+ feature)
- Cookie-based authentication for Next.js dashboard

### Fixed
- Status command duplicate output (else if hook → else if results)
- JWT_SECRET missing → 500 error (development fallback)
- License API integration (file read on user registration)
- Frontend pricing button text "Try Free" → "Upgrade Now"

### Security
- HMAC-SHA256 webhook signature verification
- bcrypt password hashing
- JWT tokens (httpOnly cookies on frontend)
- Pydantic input validation
- SQL injection protection (parameterized queries)

## [0.2.0] - 2026-06-22

- Initial public release
- 25 commands: init, scan, status, history, report, debt, plan, etc.
- Lemon Squeezy checkout integration
- FastAPI REST API
- Next.js dashboard (13 pages)
- SQLite database
- JWT authentication
- Tree-sitter parsers (Python, JS, TS, JSX, TSX)
- Git hook integration
- AI risk scoring (4-metric fingerprint)
- Technical debt estimation
- Bus factor analysis
- Sprint health
- Developer onboarding tracking
- License key activation

## [0.1.0] - 2026-06-20

- Initial development release
