/**
 * CodeDNA status bar item — shows per-file AI% and risk info in the bottom bar.
 */

import * as vscode from "vscode";
import { getFileAnalysis, checkHealth } from "./apiClient";

// Supported file extensions
const SUPPORTED_EXTS = new Set([".py", ".js", ".ts", ".jsx", ".tsx"]);

/** Icon based on risk level */
function riskIcon(pct: number): string {
  if (pct >= 70) return "$(error)";
  if (pct >= 40) return "$(warning)";
  return "$(pass)";
}

/** Risk label */
function riskLabel(pct: number): string {
  if (pct >= 70) return "HIGH";
  if (pct >= 40) return "MED";
  return "LOW";
}

export class CodeDNAStatusBar {
  private item: vscode.StatusBarItem;
  private apiUrl: string;
  private enabled: boolean;
  private connected = false;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.item.command = "codedna.openDashboard";
    this.apiUrl = this.getConfig("apiUrl", "http://localhost:8000");
    this.enabled = this.getConfig("enabled", true);
  }

  private getConfig<T>(key: string, defaultVal: T): T {
    return vscode.workspace.getConfiguration("codedna").get<T>(key, defaultVal);
  }

  /** Reload settings (when configuration changes). */
  reload(): void {
    this.apiUrl = this.getConfig("apiUrl", "http://localhost:8000");
    this.enabled = this.getConfig("enabled", true);
  }

  /** Set status bar to "disconnected" state. */
  setDisconnected(): void {
    this.connected = false;
    this.item.text = "$(circle-slash) CodeDNA";
    this.item.tooltip = "CodeDNA: not connected — run 'codedna serve'";
    this.item.color = new vscode.ThemeColor("statusBarItem.warningForeground");
    this.item.show();
  }

  /** Update status bar with analysis data. */
  setAnalysis(aiPct: number, complexity: string, lines: number): void {
    this.connected = true;
    const icon = riskIcon(aiPct);
    const risk = riskLabel(aiPct);
    this.item.text = `${icon} AI: ${aiPct.toFixed(0)}% · ${risk}`;
    this.item.tooltip = new vscode.MarkdownString(
      `**CodeDNA Analysis**\n\n` +
      `- AI Probability: **${aiPct.toFixed(1)}%**\n` +
      `- Complexity: ${complexity}\n` +
      `- Lines: ${lines}\n\n` +
      `_Click to open dashboard_`
    );
    this.item.color = undefined;
    this.item.show();
  }

  /** Loading animation. */
  setLoading(): void {
    this.item.text = "$(loading~spin) CodeDNA";
    this.item.tooltip = "CodeDNA: analyzing...";
    this.item.show();
  }

  /** Hide status bar. */
  hide(): void {
    this.item.hide();
  }

  /**
   * Analyze the active file — with debounce (won't fire on every keystroke).
   * Shows "disconnected" silently when the server is down.
   */
  analyzeFile(document: vscode.TextDocument): void {
    if (!this.enabled) {
      this.hide();
      return;
    }

    const ext = document.fileName.slice(document.fileName.lastIndexOf("."));
    if (!SUPPORTED_EXTS.has(ext)) {
      this.hide();
      return;
    }

    // Debounce — wait 800ms
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(async () => {
      await this._doAnalyze(document.fileName);
    }, 800);
  }

  private async _doAnalyze(filePath: string): Promise<void> {
    this.setLoading();

    // Check server health first
    const alive = await checkHealth(this.apiUrl);
    if (!alive) {
      this.setDisconnected();
      return;
    }

    const result = await getFileAnalysis(this.apiUrl, filePath);
    if (!result) {
      // File not yet scanned by the API — show neutral state
      this.item.text = "$(circle-large-outline) CodeDNA";
      this.item.tooltip = "CodeDNA: file not yet analyzed — run 'codedna scan'";
      this.item.color = undefined;
      this.item.show();
      return;
    }

    this.setAnalysis(result.ai_percentage, result.complexity_label, result.total_lines);
  }

  dispose(): void {
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.item.dispose();
  }
}
