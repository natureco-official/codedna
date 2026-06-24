# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately:

**Email:** security@natureco.me
**Subject:** [Security] CodeDNA Vulnerability Report

Please do not file public issues for security vulnerabilities.

We will respond within 48 hours and provide a fix timeline.

## Security Features

- HMAC-SHA256 webhook signature verification (Lemon Squeezy)
- bcrypt password hashing (cost factor 12)
- JWT tokens with 7-day expiry
- httpOnly + secure + sameSite cookies
- CORS protection
- SQL injection protection (parameterized queries)
- Pydantic input validation
- Rate limiting (FastAPI)
- HTTPS only in production

## Disclosure Policy

We follow [responsible disclosure](https://en.wikipedia.org/wiki/Responsible_disclosure):

1. Reporter privately notifies us
2. We confirm and develop a fix (typically 7-14 days)
3. We release the fix and credit the reporter (if desired)
4. Public disclosure after fix is deployed
