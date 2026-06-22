/**
 * CodeDNA status bar item — dosya bazlı AI% ve risk bilgisini alt çubukta gösterir.
 */

import * as vscode from "vscode";
import { getFileAnalysis, checkHealth } from "./apiClient";

// Desteklenen dosya uzantıları
const SUPPORTED_EXTS = new Set([".py", ".js", ".ts", ".jsx", ".tsx"]);

/** Risk seviyesine göre ikon */
function riskIcon(pct: number): string {
  if (pct >= 70) return "$(error)";
  if (pct >= 40) return "$(warning)";
  return "$(pass)";
}

/** Risk etiketi */
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

  /** Ayarları yeniden oku (yapılandırma değiştiğinde). */
  reload(): void {
    this.apiUrl = this.getConfig("apiUrl", "http://localhost:8000");
    this.enabled = this.getConfig("enabled", true);
  }

  /** Status bar'ı "bağlı değil" durumuna getir. */
  setDisconnected(): void {
    this.connected = false;
    this.item.text = "$(circle-slash) CodeDNA";
    this.item.tooltip = "CodeDNA: not connected — run 'codedna serve'";
    this.item.color = new vscode.ThemeColor("statusBarItem.warningForeground");
    this.item.show();
  }

  /** Status bar'ı analiz verisiyle güncelle. */
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

  /** Yükleniyor animasyonu. */
  setLoading(): void {
    this.item.text = "$(loading~spin) CodeDNA";
    this.item.tooltip = "CodeDNA: analyzing...";
    this.item.show();
  }

  /** Status bar'ı gizle. */
  hide(): void {
    this.item.hide();
  }

  /**
   * Aktif dosyayı analiz et — debounce ile (her tuş vuruşunda çalışmaz).
   * Sunucu kapalıysa sessizce "bağlı değil" gösterir.
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

    // Debounce — 800ms bekle
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(async () => {
      await this._doAnalyze(document.fileName);
    }, 800);
  }

  private async _doAnalyze(filePath: string): Promise<void> {
    this.setLoading();

    // Önce sunucu sağlığını kontrol et
    const alive = await checkHealth(this.apiUrl);
    if (!alive) {
      this.setDisconnected();
      return;
    }

    const result = await getFileAnalysis(this.apiUrl, filePath);
    if (!result) {
      // Dosya API'de henüz taranmamış — nötr göster
      this.item.text = "$(circle-large-outline) CodeDNA";
      this.item.tooltip = "CodeDNA: file not yet analyzed — run 'codedna scan'";
      this.item.color = undefined;
      this.item.show();
      return;
    }

    this.setAnalysis(result.ai_yuzdesi, result.karmasiklik_etiketi, result.toplam_satir);
  }

  dispose(): void {
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.item.dispose();
  }
}
