# Changelog

## [0.2.1] - 2026-06-24

### Added
- Lemon Squeezy payment integration (Pro ₺400, Team ₺800, Enterprise ₺1,650/ay)
- Webhook handler with HMAC-SHA256 signature verification
- Customer ID tracking (lemonsqueezy_customer_id, subscription_id)
- Dashboard billing page with subscription details + cancel
- Ngrok public URL support for production webhooks
- Dashboard pricing page rewrite with TRY currency
- `codedna plan demo [plan]` command for quick license activation
- `codedna natureco` integration (Pro+ feature)
- Cookie-based authentication for Next.js dashboard

### Fixed
- Status command duplicate output (else if hook → else if sonuclar)
- JWT_SECRET missing → 500 error (development fallback)
- License API integration (file read on user registration)
- Frontend pricing button text "Denemeye Başla" → "Hemen Yükselt"

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
