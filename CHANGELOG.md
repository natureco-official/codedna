# Changelog

## [0.6.0] - 2026-06-24 - "MAIL MONITOR" (MINOR)

### Added
- **`codedna mail` command** - Gmail monitor with importance scoring
  - Reads `timurhanhz3@gmail.com` via IMAP + App Password
  - App Password stored at `~/.codedna/gmail_app_password` (chmod 600)
  - State persisted at `~/.codedna/mail_state.json` (last UID, incremental check)
  - 6 importance categories with scoring:
    - `security` (10): token found, breach, 2FA, compromised
    - `security` (9): password reset, suspicious login, locked account
    - `infra` (8): deploy fail, build fail, crash, outage, domain expire
    - `billing` (8): invoice, payment failed, subscription, card declined
    - `business` (6): meeting, call, proposal, contract
    - `project` (4): published, release, deploy success
  - Noise detection auto-skips: `Re:`, newsletter, marketing, noreply
  - Options:
    - `--since N` (default 7): look back N days
    - `--threshold N` (default 5): min importance score
    - `--new-only`: only show messages newer than last check (uses UID tracking)
    - `--show-noise`: also display noise/promo messages
    - `--reset`: reset state and re-check all messages
  - Output: legacy CLI aesthetic (bold cyan header, category-colored boxes, summary panel)
  - Use case: cron `codedna mail --new-only` for daily digest

### Changed
- Minor version bump 0.5.2 -> 0.6.0 (new user-facing command)

## [0.5.2] - 2026-06-24 - "SECURITY CHECK"

### Added
- `codedna security-check` command - Pre-release security scanner
  - Personal machine path detection (e.g. `/Users/yourname/`, `/home/user/`)
  - Tracked secret detection (`.npmrc`, `.env*` in git)
  - Secret pattern detection (npm, GitHub PAT, OpenAI, Anthropic, PyPI, generic API keys)
  - `.gitignore` rule verification (.env, .npmrc, node_modules, __pycache__)
  - Options: `--path` (custom root), `--strict` (exit on warnings)
  - Output: legacy CLI aesthetic (4 categories, emoji markers, summary panel)
  - Use case: run BEFORE `uv publish` or `git push` to catch leaks
  - Critical response: exit 1 on personal paths, tracked secrets, or missing .env rules
  - Detected the recent NatureCo CLI v5.7.0 issue (sasuke-notes paths + tracked .npmrc)

## [0.5.1] - 2026-06-24 — "Doctor English"

### 🔄 Changed
- **`codedna doctor`** — translated all messages back to English
  - Old (0.5.0): "Sistem sağlık kontrolü", "Python Ortamı", "Veritabanı", "Lisans", "Ağ Bağlantısı"
  - New: "System health check", "Python Environment", "Database", "License & Plan", "Network"
  - Style preserved: `[bold]─── Category ───[/bold]` headers, emoji markers, summary panel
- Matches the project's "English-first" policy (README.md, CLI output, docstrings)

## [0.5.0] - 2026-06-24 — "Phase 8: Demo Mode + VS Code Marketplace"

### ✨ Added — Demo Mode (Part A)
- **`codedna/demo.py`** — new module with `seed_demo_data`, `clear_demo_data`, `is_demo_active`
  - 47 fake commits over 30 days, varying AI probability (0.1–0.9)
  - 4 authors, 8 files, 3 sprints with realistic health scores
  - 20% null understanding scores, 80% in [3.0, 5.0]
  - Idempotent: tags demo rows with `__demo__` prefix
- **`codedna demo` CLI command** — seed + auto-start dashboard
  - `codedna demo` — seed and start dashboard
  - `codedna demo --reset` — clear all demo rows
  - `codedna demo --data-only` — seed without starting dashboard
- **FastAPI endpoints** — `/demo/status`, `/demo/seed`, `/demo/reset`
- **Dashboard banner** — orange banner at top of dashboard when demo is active
  - Dismissable, persisted in localStorage
  - i18n keys: `demo_banner`, `demo_close`, `demo_init_cta`

### ✨ Added — VS Code Marketplace (Part B)
- **`vscode-extension/package.json`** — full marketplace metadata
  - `icon` (128x128 PNG), `galleryBanner`, `badges`, `keywords`, `categories`
  - `homepage`, `bugs`, `repository`, `license: MIT`
  - `scripts` for `compile`/`watch`/`package`/`publish`
  - `devDependencies`: `@vscode/vsce ^2.24.0`
- **`vscode-extension/images/icon.png`** — 128x128 dark cyan/emerald DNA helix
- **`vscode-extension/.vscodeignore`** — excludes `src/`, `node_modules/`, `*.ts`
- **`vscode-extension/MARKETPLACE_README.md`** — full English marketplace description
- **`vscode-extension/PUBLISH.md`** — step-by-step publishing instructions

### 🔄 Changed
- Minor version bump (0.4.2 → 0.5.0) — major feature release, breaks the 7-patch cascade

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
