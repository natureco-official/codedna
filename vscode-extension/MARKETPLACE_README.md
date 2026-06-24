# CodeDNA — AI Code Transparency for VS Code

**Understand every line of code you commit. Is it really yours, or AI's?**

CodeDNA shows AI risk and developer understanding scores directly in your editor. Inline decorations flag AI-heavy code, the status bar displays the current file's risk level, and a single click opens the full dashboard for sprint health, bus factor, and technical debt analysis.

## Features

- **Status bar indicator** — current file's AI risk score, color-coded (green/yellow/red)
- **Inline decorations** — gutter icons next to AI-generated lines
- **Dashboard link** — one-click access to the full CodeDNA dashboard
- **Auto-refresh** — pulls latest scores from your local CodeDNA server
- **Free & open source** — works offline, no telemetry, no cloud lock-in

## Requirements

- **Python 3.10+**
- **codedna package** — `pip install codedna` (or `uv tool install codedna`)
- **Local API server** — `codedna serve` must be running (default: `http://localhost:8000`)

## Quick Start

1. **Install the CLI:**
   ```bash
   pip install codedna
   # or
   uv tool install codedna
   ```

2. **Start the API server** in your project:
   ```bash
   cd your-project
   codedna init
   codedna serve
   ```

3. **Install this extension** from the VS Code marketplace, then open any file in your project. The status bar will show the AI risk score for the current file.

## Extension Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `codedna.apiUrl` | `http://localhost:8000` | CodeDNA API server URL |
| `codedna.dashboardUrl` | `http://localhost:3000` | CodeDNA dashboard URL |
| `codedna.enabled` | `true` | Enable/disable the extension |

## Commands

- `CodeDNA: Refresh` — re-fetch scores from the API
- `CodeDNA: Open Dashboard` — open the dashboard in your browser
- `CodeDNA: Show File Risk` — show detailed risk breakdown for the current file

## Known Limitations

- Requires a local `codedna serve` instance (no cloud mode yet)
- Status bar shows the latest commit score, not real-time analysis
- Dashboard requires a separate Next.js process (`codedna dashboard`)

## Links

- [GitHub](https://github.com/natureco-official/codedna)
- [PyPI](https://pypi.org/project/codedna/)
- [Documentation](https://github.com/natureco-official/codedna/blob/main/README.md)
- [Issue tracker](https://github.com/natureco-official/codedna/issues)

## License

MIT © 2026 NatureCo
