/**
 * CodeDNA VS Code Extension — entry point.
 *
 * Behavior:
 *   - Shows AI% and risk level in the status bar when a file is opened/saved
 *   - When codedna serve is not running: dim "not connected" — NO popup/error spam
 *   - Clicking the status bar opens the dashboard
 *   - Subtle border highlight on high-risk files (non-intrusive)
 */

import * as vscode from "vscode";
import { CodeDNAStatusBar } from "./statusBar";
import { applyRiskDecoration, clearDecorations, disposeDecorations } from "./decorations";
import { getFileAnalysis, checkHealth } from "./apiClient";

let statusBar: CodeDNAStatusBar;
let healthCheckInterval: ReturnType<typeof setInterval> | null = null;
let lastKnownAlive = false;

/** Called when the extension is activated. */
export function activate(context: vscode.ExtensionContext): void {
  statusBar = new CodeDNAStatusBar();

  // Command: open dashboard in browser
  context.subscriptions.push(
    vscode.commands.registerCommand("codedna.openDashboard", () => {
      const dashUrl = vscode.workspace
        .getConfiguration("codedna")
        .get<string>("dashboardUrl", "http://localhost:3000");
      vscode.env.openExternal(vscode.Uri.parse(dashUrl));
    })
  );

  // Command: refresh active file
  context.subscriptions.push(
    vscode.commands.registerCommand("codedna.refreshFile", () => {
      const editor = vscode.window.activeTextEditor;
      if (editor) {
        statusBar.analyzeFile(editor.document);
      }
    })
  );

  // Analyze when a file is opened
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor) {
        analyzeAndDecorate(editor);
      } else {
        statusBar.hide();
      }
    })
  );

  // Analyze when a file is saved
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      const editor = vscode.window.activeTextEditor;
      if (editor && editor.document === doc) {
        analyzeAndDecorate(editor);
      }
    })
  );

  // Reload when settings change
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("codedna")) {
        statusBar.reload();
        const editor = vscode.window.activeTextEditor;
        if (editor) analyzeAndDecorate(editor);
      }
    })
  );

  // Periodic health check (every 30 seconds) — update when connection state changes
  healthCheckInterval = setInterval(async () => {
    const apiUrl = vscode.workspace
      .getConfiguration("codedna")
      .get<string>("apiUrl", "http://localhost:8000");
    const alive = await checkHealth(apiUrl);

    if (alive !== lastKnownAlive) {
      lastKnownAlive = alive;
      const editor = vscode.window.activeTextEditor;
      if (editor) analyzeAndDecorate(editor);
      else if (!alive) statusBar.setDisconnected();
    }
  }, 30_000);

  context.subscriptions.push({ dispose: () => statusBar.dispose() });
  context.subscriptions.push({ dispose: () => disposeDecorations() });
  context.subscriptions.push({
    dispose: () => {
      if (healthCheckInterval) clearInterval(healthCheckInterval);
    },
  });

  // Analyze active file on startup
  const activeEditor = vscode.window.activeTextEditor;
  if (activeEditor) {
    analyzeAndDecorate(activeEditor);
  }
}

/** Analyze a file and update both the status bar and decoration. */
async function analyzeAndDecorate(editor: vscode.TextEditor): Promise<void> {
  const enabled = vscode.workspace
    .getConfiguration("codedna")
    .get<boolean>("enabled", true);

  if (!enabled) {
    statusBar.hide();
    clearDecorations(editor);
    return;
  }

  // Update status bar (includes debounce)
  statusBar.analyzeFile(editor.document);

  // Direct API call for decoration (independent of status bar)
  const apiUrl = vscode.workspace
    .getConfiguration("codedna")
    .get<string>("apiUrl", "http://localhost:8000");

  const result = await getFileAnalysis(apiUrl, editor.document.fileName);
  if (result) {
    applyRiskDecoration(editor, result.ai_percentage);
  } else {
    clearDecorations(editor);
  }
}

/** Called when the extension is deactivated. */
export function deactivate(): void {
  if (healthCheckInterval) clearInterval(healthCheckInterval);
}
