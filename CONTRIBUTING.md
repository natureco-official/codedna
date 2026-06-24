# Contributing to CodeDNA

Thanks for your interest in contributing! We welcome pull requests, bug reports, and feature suggestions.

## How to Contribute

### Reporting Bugs
Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md) when filing an issue.

### Suggesting Features
Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md).

### Pull Requests
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Run `pytest` and `uv build` locally
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to your fork (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Development Setup

```bash
# Clone
git clone https://github.com/natureco-official/codedna.git
cd codedna

# Create virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Build
uv build
```

## Code Style

- We use [Black](https://black.readthedocs.io/) for Python formatting
- [Ruff](https://github.com/astral-sh/ruff) for linting
- TypeScript/React: ESLint + Prettier

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
