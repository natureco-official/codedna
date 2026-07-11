<div align="center">

# 🧬 CodeDNA — AI Code Transparency Tool

**Understand every line of code you commit. Is it really yours, or AI's?**

Detect which code was written by AI, measure how well developers actually understand their commits, analyze commit quality, track trends, and map out "understanding debt" across your entire team.

[![PyPI version](https://badge.fury.io/py/codedna.svg)](https://pypi.org/project/codedna/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/natureco-official/codedna.svg)](https://github.com/natureco-official/codedna/stargazers)

[**Quick Start**](#-quick-start) • [**Features**](#-features) • [**Commands**](#-commands) • [**Pricing**](#-pricing) • [**Docs**](#-documentation)

</div>

---

## 🎯 The Problem

In 2026, developers write **78% of their code with AI help** (Copilot, Cursor, ChatGPT, Claude). The result?

- 😰 **"Understanding Debt"** — Code is committed, but no one actually knows how it works
- 🚌 **Bus Factor = 1** — Everyone uses the same AI, no one understands the codebase
- 💰 **Technical Debt Explosion** — Without human review, AI-generated code decays fast
- 🐛 **Bug Multiplication** — 3 months later: "Who wrote this? I don't even know what it does"

**CodeDNA solves this.** Every commit is scored. Every developer is measured. Every team gets visibility.

---

## ✨ Features

### 🔍 AI Detection (4-metric fingerprint)
CodeDNA uses 4 heuristics to detect AI-generated code:

| Metric | AI Signature | Score |
|--------|--------------|-------|
| `comment_ratio > 0.3` | AI over-comments its code | +0.20 |
| `avg_function_length > 50` | AI produces large monolithic blocks | +0.15 |
| `single_commit_ratio > 0.7` | Bulk-paste commits are AI-red flag | +0.30 |
| High complexity + single commit | AI signature → +0.25 |

**Total > 0.50 → AI suspected.** Combined with Tree-sitter AST analysis, this gives 80%+ accuracy.

### 🤖 AI Score Explanation
Each file's score includes a plain-English breakdown of why it scored that way:
- *"High comment ratio (35%) — AI-generated code tends to over-comment (+0.20)"*
- *"High single-commit ratio (85%) — bulk paste indicator (+0.30)"*

### 📝 Commit Message Quality Analysis
- Detects conventional commit types (`feat:`, `fix:`, `docs:`, etc.)
- Estimates quality score (0-5) based on message clarity
- Detects ticket references (JIRA, GitHub Issues)
- Score bonus for scope + ticket references

### 📊 Export & Import
- `codedna export --format json|csv` — export all data
- `codedna import file.json` — restore from export
- API endpoints: `GET /export`, `POST /import`

### 👤 Developer Understanding Score
- **Survey-based** — Quick Q&A after each commit
- **Tracked over time** — See your understanding curve
- **Trend charts** — Dashboard `/trends` page

### 🚌 Bus Factor Analysis
- **Ownership tracking** — Who owns which file?
- **Risk identification** — Single points of failure

### 💰 Technical Debt Estimation
- **Cost in USD** — How much would it cost to fix this?
- **Trend over time** — Is debt increasing?

### 🏃 Sprint Health
- **Velocity tracking** — Real commits vs. AI-assisted
- **Quality metrics** — Per-sprint scoring

### 📈 Trend Charts (Dashboard)
Time-series visualization of:
- Daily average AI probability over time
- Understanding score trend
- Commit frequency bar chart

### 👀 Live Monitoring (`codedna watch`)
- Polls git repo for new commits (configurable interval)
- Auto-runs analysis on each new commit
- `--once` flag for cron-based usage
- `--notify` for webhook alerts

### 🔔 Webhook Notifications (Slack/Discord)
- Configure via `codedna webhook` interactive wizard
- Automatic alerts on high AI risk detection
- Protected module violation notifications
- Configurable risk threshold

### 💬 Feedback Loop
- Dashboard `/feedback` page
- Mark AI detections as correct/incorrect/unsure
- API endpoints for CRUD operations
- Historical view of all feedback

### 📂 Multi-Repo Dashboard
- Add/remove repositories via dashboard `/repos`
- API-backed CRUD with `~/.codedna/repos.json`
- Centralized view across projects

### 🤖 AI Tool Comparison (Enterprise)
Copilot vs. Cursor vs. Claude — which tool produces more debt?

### 🎯 Interview Tool (Enterprise)
Auto-generates questions from real code, records responses, exports reports.

### 🚀 Developer Onboarding
Ramp-up curve, mentor matching, first PR analysis.

### 🛡️ Protected Modules
Mark critical files — "AI may not touch auth/, payment/, security/"

### 🐳 Docker Self-Hosted
```bash
docker compose up
# API → http://localhost:8000
# Dashboard → http://localhost:3000
```

---

## 🚀 Quick Start

### Installation

```bash
pip install codedna
```

### First Use (60 seconds)

```bash
cd your-awesome-project
codedna init       # Install git hook + create DB
codedna scan       # Analyze all files
codedna status     # Last commit score
codedna history    # Past commits
```

### Run the Dashboard

```bash
codedna dashboard       # Web UI (port 3000) + API (port 8000)
codedna serve           # API only (port 8000)
```

---

## 📋 Commands (30+ total)

### 📊 Analysis & Reporting
```bash
codedna scan                  # Full repo AI scan
codedna status                # Last commit score + commit message analysis
codedna history               # Commit history with understanding scores
codedna report                # Generate HTML report
codedna ai-compare            # AI tool comparison (Enterprise)
codedna export --format json  # Export all data (JSON/CSV)
codedna import file.json      # Restore from export
```

### 👀 Monitoring
```bash
codedna watch                 # Live repo monitoring (poll mode)
codedna watch --once          # Single analysis (cron-friendly)
codedna watch --notify        # With webhook alerts
codedna webhook --show        # Show webhook config
codedna webhook --test        # Send test notification
codedna webhook --reset       # Clear webhook config
```

### 🛡️ Protection & Policies
```bash
codedna protect add <path>    # Add protected module
codedna protect remove <path> # Remove protection
codedna protect list          # List protected modules
codedna protect check         # Show violations
```

### 👥 Team & Process
```bash
codedna onboarding            # Developer ramp-up (Team+)
codedna interview start       # Start interview (Enterprise)
codedna interview list        # List interviews
codedna interview score       # Score interview
codedna bus-factor            # Ownership analysis (Team+)
codedna debt                  # Technical debt (Team+)
codedna sprint create         # Create sprint
codedna sprint health         # Latest sprint score
codedna sprint history        # All sprints
```

### 🌐 Infrastructure
```bash
codedna serve                 # FastAPI REST (port 8000)
codedna dashboard             # Web dashboard (port 3000)
codedna pr-comment            # GitHub PR comment
codedna plan                  # Plan/license management
codedna setup                 # AI analysis config wizard
codedna security-check        # Pre-publish secret scanner
codedna doctor                # System health check
codedna update                # Self-upgrade from PyPI
codedna uninstall             # Remove git hook
```

---

## 💎 Pricing

| Plan | Price | Repos | History | Dashboard | Key Features |
|------|-------|-------|---------|-----------|--------------|
| **Free** | $0 | 1 | 7 days | ❌ | AI detection, local only |
| **Pro** | $12/mo | ∞ | 90 days | ✅ | + Export, Webhooks, Watch |
| **Team** | $24/mo | ∞ | 365 days | ✅ | + Bus Factor, Sprint, Onboarding |
| **Enterprise** | $49/mo | ∞ | ∞ | ✅ | + AI Compare, Interview Tool, SSO |

---

## 🔌 Integrations

- **GitHub Actions** — Auto-comment on PR
- **Jira** — Sprint health webhook
- **Slack** — AI risk notifications
- **Discord** — Webhook alerts
- **GitHub Copilot / Cursor / Claude** — AI tool detection
- **Docker** — Self-hosted deployment

---

## 🛠️ Architecture

```
CLI (Python, Typer, Tree-sitter, GitPython, SQLite)
  │
  ├── codedna scan / status / history
  ├── codedna export / import
  ├── codedna watch / webhook
  ├── codedna protect / bus-factor / debt
  ├── codedna sprint / onboarding
  ├── codedna serve / dashboard
  └── codedna doctor / update / security-check
        │
        ↓ HTTP
REST API (FastAPI, JWT Auth, Rate Limiting)
  ├── /health, /repo/*
  ├── /commits, /files, /report
  ├── /survey, /sprints, /bus-factor, /debt
  ├── /trends, /trends/commits
  ├── /feedback (POST + GET)
  ├── /repos (GET + POST + DELETE)
  ├── /export, /import
  ├── /auth (register, login, me)
  └── /billing (checkout, webhook, subscription)
        │
        ↓ HTTP
Web Dashboard (Next.js 14, TypeScript, Tailwind)
  ├── / (overview + metrics)
  ├── /files, /commits, /report
  ├── /bus-factor, /debt, /sprints
  ├── /trends (charts)
  ├── /feedback (AI accuracy feedback)
  ├── /repos (multi-repo management)
  ├── /ai-compare, /onboarding
  ├── /protected, /interview
  ├── /pricing, /billing
  └── /login, /register
```

### Self-Hosted (Docker)

```bash
git clone https://github.com/natureco-official/codedna.git
cd codedna
docker compose up
```

---

## 🏗️ Tech Stack

- **Python 3.10+** with Typer, FastAPI, Tree-sitter, GitPython, SQLite
- **Next.js 14** with TypeScript, Tailwind CSS
- **Docker** — API + Dashboard containers
- **Lemon Squeezy** — Billing
- **uv** — Python packaging

---

## 🔒 Security

- HMAC-SHA256 webhook verification
- bcrypt password hashing (cost 12)
- JWT tokens (7-day expiry)
- httpOnly + secure + sameSite cookies
- Parameterized SQL queries
- Pydantic input validation
- Rate limiting
- No telemetry — your code stays yours

---

## 🌍 Supported Languages

Python (`.py`), JavaScript (`.js`), TypeScript (`.ts`), JSX (`.jsx`), TSX (`.tsx`)

---

## 🧪 Testing

```bash
pytest                    # 23+ tests
pytest --cov=codedna      # With coverage
```

---

## 📚 Documentation

- CLI Reference — `codedna --help` or per-command `--help`
- API Reference — http://localhost:8000/docs (when running)
- [Contributing Guide](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

---

## 📜 License

MIT License — Copyright (c) 2026 NatureCo

---

<div align="center">

**Made with 🌿 in Turkey**

[⭐ Star us on GitHub](https://github.com/natureco-official/codedna) • [📦 Install from PyPI](https://pypi.org/project/codedna/)

</div>
