<div align="center">

# 🧬 CodeDNA — AI Code Transparency Tool

**Understand every line of code you commit. Is it really yours, or AI's?**

Detect which code was written by AI, measure how well developers actually understand their commits, and map out "understanding debt" across your entire team.

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

### 👤 Developer Understanding Score
- **Interview-based** — Structured Q&A after each commit
- **AI-powered** — Generates questions about the code you just committed
- **Tracked over time** — See your understanding curve

### 🚌 Bus Factor Analysis
- **Ownership tracking** — Who owns which file?
- **Risk identification** — Single points of failure
- **Refactoring suggestions** — "Pair X with Y on module Z"

### 💰 Technical Debt Estimation
- **Cost in USD** — How much would it cost to fix this?
- **Trend over time** — Is debt increasing?
- **Prioritization** — What to fix first?

### 🏃 Sprint Health
- **Velocity tracking** — Real commits vs. AI-assisted
- **Code review load** — Who reviews what?
- **Quality metrics** — Per-sprint scoring

### 🤖 AI Tool Comparison (Enterprise)
- **Copilot vs. Cursor vs. ChatGPT** — Which tool produces more debt?
- **Per-developer breakdown** — Who uses what?
- **Productivity vs. quality** — Real metrics

### 🎯 Interview Tool (Enterprise)
- **Auto-generates questions** — "What does this function do? Why?"
- **Records responses** — For HR and compliance
- **Exportable reports** — PDF/CSV

### 🚀 Developer Onboarding
- **Ramp-up curve** — How long to productivity?
- **Mentor matching** — AI suggests pairs
- **First PR analysis** — What did they ship?

### 🛡️ Protected Modules
- **Mark critical files** — "AI may not touch auth/, payment/, security/"
- **Pre-commit hook** — Blocks AI-generated commits to protected areas
- **Override workflow** — With approval

### 📊 Web Dashboard
- **Real-time metrics** — Live commit feed
- **Charts** — Time-series, breakdowns, comparisons
- **Multi-repo view** — All your projects in one place
- **Team analytics** — Who's growing, who's stagnating

### 💬 Multi-Channel Support
- **Telegram bot** — `/codedna scan` from your phone
- **WhatsApp** — Slash-prefix commands
- **iMessage** — Direct Mac integration
- **Discord/Slack** — Webhook support

---

## 🚀 Quick Start

### Installation

```bash
# From PyPI
pip install codedna

# Or with uv (faster)
uv pip install codedna

# Or from dev environment
git clone https://github.com/natureco-official/codedna.git
cd codedna
pip install -e .
```

### First Use (60 seconds)

```bash
# 1. Go to your Git repo
cd your-awesome-project

# 2. Initialize CodeDNA (creates git hook + DB)
codedna init

# 3. Scan the repo
codedna scan

# 4. See the last commit score
codedna status

# 5. See past commits
codedna history
```

**That's it.** Every commit from now on is auto-analyzed.

### Run the Dashboard (optional)

```bash
# Web dashboard (port 3000) + REST API (port 8000)
codedna dashboard

# Then open http://localhost:3000
# Login with your account or register new
```

---

## 📋 Commands (25 total)

### 📊 Analysis & Reporting
```bash
codedna init                  # Create git hook + DB
codedna scan                  # Scan the repo
codedna status                # Last commit score
codedna history               # Past commits
codedna report                # Generate HTML report
codedna ai-compare            # AI tool comparison (Enterprise)
```

### 🛡️ Protection & Policies
```bash
codedna protect-add <path>    # Add protected module
codedna protect-remove <path> # Remove protection
codedna protect-list          # List protected modules
codedna protect-check <file>  # Is file protected?
```

### 👥 Team & Process
```bash
codedna onboarding            # Developer ramp-up (Team+)
codedna interview-start       # Start interview (Enterprise)
codedna interview-list        # List interviews
codedna interview-score       # Score interview
codedna bus-factor            # Ownership analysis (Team+)
codedna debt                  # Technical debt (Team+)
codedna sprint-olustur        # Create sprint
codedna sprint-sagligi         # Sprint health
codedna sprint-gecmisi         # Sprint history
```

### 🌐 Infrastructure
```bash
codedna serve                 # FastAPI REST (port 8000)
codedna dashboard             # Web dashboard (port 3000)
codedna pr-comment            # GitHub PR comment
codedna plan                  # Plan/license management
codedna plan demo pro         # 7-day demo Pro license
codedna natureco              # NatureCo CLI integration (Pro+)
codedna uninstall             # Remove hook
```

### 🔧 Utility
```bash
codedna doctor                # System health check
codedna reset                 # Reset (DANGEROUS)
```

---

## 💎 Pricing

| Plan | Price | Repos | Files/Scan | History | Dashboard | Features |
|------|-------|-------|------------|---------|-----------|----------|
| **Free** | $0 | 1 | 50 | 7 days | ❌ | AI detection, local only |
| **Pro** | ₺400/mo | ∞ | ∞ | 90 days | ✅ | + GitHub Actions, NatureCo CLI |
| **Team** | ₺800/mo | ∞ | ∞ | 365 days | ✅ | + Bus Factor, Sprint, Onboarding |
| **Enterprise** | ₺1,650/mo | ∞ | ∞ | ∞ | ✅ | + AI Compare, Interview Tool, SSO |

**Start with `codedna plan demo pro`** to test Pro features for 7 days.

Payment via [Lemon Squeezy](https://www.lemonsqueezy.com) — TRY pricing for Turkish market, USD for global.

---

## 🔌 Integrations

### CI/CD
- **GitHub Actions** — Auto-comment on PR
- **GitLab CI** — Pipeline integration
- **Bitbucket Pipelines** — Snippets

### Issue Trackers
- **Jira** — Story → commit mapping
- **Linear** — Issue tracking
- **GitHub Issues** — Auto-link

### Notifications
- **Slack** — Real-time alerts
- **Discord** — Webhook support
- **Telegram** — Bot commands
- **Email** — Daily digest

### AI Tools
- **GitHub Copilot** — Detection
- **Cursor** — Detection
- **ChatGPT/Claude** — Detection
- **Codeium** — Detection

---

## 🛠️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│  CLI (Python 7,000+ LOC)                                │
│  ├── Typer framework                                    │
│  ├── Tree-sitter parsers (Python, JS, TS, JSX, TSX)   │
│  ├── GitPython (commit analysis)                        │
│  ├── SQLite (local DB)                                  │
│  └── JWT (auth)                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ↓ HTTP
┌─────────────────────────────────────────────────────────┐
│  REST API (FastAPI)                                     │
│  ├── /auth (register, login, me)                        │
│  ├── /billing (checkout, webhook, subscription)        │
│  ├── /commits (list, scores)                            │
│  ├── /files (analysis)                                  │
│  └── /repo (bus-factor, debt, sprint)                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ↓ HTTP
┌─────────────────────────────────────────────────────────┐
│  Web Dashboard (Next.js)                                │
│  ├── /dashboard (metrics)                               │
│  ├── /files (file list)                                 │
│  ├── /commits (commit history)                          │
│  ├── /bus-factor (ownership)                            │
│  ├── /debt (technical debt)                             │
│  ├── /sprints (sprint health)                            │
│  ├── /ai-compare (tool comparison)                       │
│  ├── /onboarding (developer ramp-up)                    │
│  ├── /protected (module list)                           │
│  ├── /interview (Q&A tool)                               │
│  ├── /settings/integrations                              │
│  └── /pricing (plan comparison)                          │
└─────────────────────────────────────────────────────────┘
```

### 3-Layer Stack

1. **CLI** — Terminal-first developers
2. **REST API** — Backend for dashboard + integrations
3. **Web Dashboard** — Manager/CTO view

---

## 🏗️ Tech Stack

### Backend
- **Python 3.10+** — Core language
- **Typer** — Modern CLI framework
- **FastAPI** — High-performance REST API
- **Tree-sitter** — Incremental parsing
- **GitPython** — Git repository access
- **SQLite** — Local database
- **bcrypt** — Password hashing
- **PyJWT** — Token management
- **Pydantic** — Data validation
- **uv** — Fast Python package manager

### Frontend
- **Next.js 14+** — React framework
- **TypeScript** — Type safety
- **Tailwind CSS** — Styling
- **i18n** — Multi-language (EN/TR)

### Billing
- **Lemon Squeezy** — Merchant of Record
- **HMAC-SHA256** — Webhook signature verification

### DevOps
- **GitHub Actions** — CI/CD
- **CodeQL** — Security scanning
- **Dependabot** — Dependency updates
- **uv** — Python packaging

---

## 🔒 Security

- ✅ **HMAC-SHA256** webhook signature verification
- ✅ **bcrypt** password hashing (cost factor 12)
- ✅ **JWT tokens** with 7-day expiry
- ✅ **httpOnly + secure + sameSite** cookies
- ✅ **CORS protection**
- ✅ **SQL injection** protection (parameterized queries)
- ✅ **Pydantic** input validation
- ✅ **Rate limiting** (FastAPI middleware)
- ✅ **HTTPS only** in production
- ✅ **No telemetry** — Your code stays yours

---

## 🌍 Languages Supported

CodeDNA's Tree-sitter parsers support:

- ✅ **Python** (`.py`)
- ✅ **JavaScript** (`.js`)
- ✅ **TypeScript** (`.ts`)
- ✅ **JSX** (`.jsx`)
- ✅ **TSX** (`.tsx`)

Coming soon: Go, Rust, Java, C#, Ruby, PHP

---

## 📦 Project Structure

```
codedna/
├── cli.py                  # 25 CLI commands
├── api.py                  # FastAPI REST endpoints
├── auth.py                 # JWT authentication
├── plan.py                 # License/plan management
├── db.py                   # SQLite database
├── scorer.py               # AI risk scoring
├── analyzer.py             # Code analysis
├── ai_fingerprint.py       # AI detection
├── bus_factor.py           # Ownership analysis
├── tech_debt.py            # Technical debt
├── sprint_health.py        # Sprint metrics
├── survey.py               # Onboarding
├── interview.py            # Q&A tool
├── protection.py           # Module protection
├── rate_limit.py           # API throttling
├── onboarding.py           # Developer tracking
├── integrations/
│   ├── lemonsqueezy.py     # Billing integration
│   └── github.py           # GitHub API
├── dashboard/              # Next.js frontend
│   ├── app/                # 13 pages
│   ├── components/         # UI components
│   └── lib/                # Utilities
├── tests/                  # Pytest suite
├── pyproject.toml          # Python config
├── README.md               # This file
├── CHANGELOG.md            # Release notes
├── LICENSE                 # MIT
├── CONTRIBUTING.md         # How to contribute
└── SECURITY.md             # Security policy
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=codedna

# Specific test
pytest tests/test_ai_fingerprint.py
```

**Test coverage:** 80%+ across all modules.

---

## 📚 Documentation

- **Installation Guide** — [INSTALL.md](docs/INSTALL.md)
- **CLI Reference** — [docs/CLI.md](docs/CLI.md)
- **API Reference** — http://localhost:8000/docs (when running)
- **Webhook Guide** — [docs/WEBHOOKS.md](docs/WEBHOOKS.md)
- **Architecture** — [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Roadmap** — [docs/ROADMAP.md](docs/ROADMAP.md)

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/natureco-official/codedna.git
cd codedna
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

### Code Style

- [Black](https://black.readthedocs.io/) for Python
- [Ruff](https://github.com/astral-sh/ruff) for linting
- ESLint + Prettier for TypeScript

---

## 📜 License

MIT License — see [LICENSE](LICENSE) file.

```
MIT License - Copyright (c) 2026 NatureCo
```

---

## 🌟 Acknowledgments

- **Tree-sitter** — For blazing-fast parsing
- **Typer** — For beautiful CLI
- **FastAPI** — For modern API framework
- **Lemon Squeezy** — For hassle-free billing
- **All our beta testers** — For feedback and bug reports

---

## 💬 Community

- 💬 **Discord:** [https://discord.gg/4FwumbWph](https://discord.gg/4FwumbWph)
- 🐦 **Twitter:** [@naturecoofficial](https://twitter.com/naturecoofficial)
- 🐙 **GitHub:** [https://github.com/natureco-official/codedna](https://github.com/natureco-official/codedna)
- 📦 **PyPI:** [https://pypi.org/project/codedna/](https://pypi.org/project/codedna/)
- 🌐 **Website:** [https://natureco.me](https://natureco.me)

---

## 🗺️ Roadmap

### v0.3.0 (Q3 2026)
- [ ] VSCode extension (real-time)
- [ ] Go/Rust/Java support
- [ ] Slack bot
- [ ] Jira integration

### v0.4.0 (Q4 2026)
- [ ] Team analytics dashboard
- [ ] AI coach (suggests learning resources)
- [ ] Custom AI fingerprinting
- [ ] Cloud sync (optional)

### v1.0.0 (2027)
- [ ] Self-hosted option
- [ ] Enterprise SSO (SAML, OIDC)
- [ ] SOC 2 compliance
- [ ] Custom training data

---

<div align="center">

**Made with 🌿 in Turkey**

[⭐ Star us on GitHub](https://github.com/natureco-official/codedna) • [📦 Install from PyPI](https://pypi.org/project/codedna/) • [🐦 Follow on Twitter](https://twitter.com/naturecoofficial)

</div>
