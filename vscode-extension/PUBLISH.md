# Publishing to VS Code Marketplace

## One-time setup

1. **Create a publisher** at https://marketplace.visualstudio.com/manage
   - Publisher ID must be exactly: `codedna`

2. **Get a Personal Access Token** from https://dev.azure.com
   - Organization: `Marketplace`
   - Scopes: `Marketplace → Manage`

3. **Login locally:**
   ```bash
   npx vsce login codedna
   ```
   (paste the PAT when prompted)

## Publish

```bash
cd vscode-extension
npm install
npm run compile
npx vsce package        # creates codedna-vscode-0.1.0.vsix
npx vsce publish        # publishes to marketplace
```

The extension will be live at:
`https://marketplace.visualstudio.com/items?itemName=codedna.codedna-vscode`

## Update

Bump version in `package.json`, then:

```bash
npx vsce publish patch  # 0.1.0 → 0.1.1
npx vsce publish minor  # 0.1.0 → 0.2.0
npx vsce publish major  # 0.1.0 → 1.0.0
```

Or edit `package.json` manually and run `npx vsce publish` (no flag = use new version).

## Test locally

```bash
# Build the .vsix
npx vsce package

# Install in your VS Code
code --install-extension codedna-vscode-0.1.0.vsix

# Or use the development version
code --install-extension .

# Then test by opening a project that has `codedna serve` running
```

## Pre-flight checklist

- [ ] `package.json` icon path resolves to a valid 128x128 PNG
- [ ] `MARKETPLACE_README.md` is up to date with current features
- [ ] `npm run compile` produces `out/extension.js` without errors
- [ ] `npx vsce package` creates a `.vsix` file (no errors about missing icon, repository, license)
- [ ] Bumped version (can't publish same version twice)
