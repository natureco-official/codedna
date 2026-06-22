/**
 * CodeDNA decorations — yüksek riskli dosyalarda başlık satırına
 * hafif bir vurgu ekler. Satır bazlı vurgulama değil, dosya bazlı.
 */

import * as vscode from "vscode";

// Yüksek riskli dosya için başlık alanı decoration
const HIGH_RISK_DECORATION = vscode.window.createTextEditorDecorationType({
  isWholeLine: true,
  overviewRulerColor: new vscode.ThemeColor("charts.red"),
  overviewRulerLane: vscode.OverviewRulerLane.Right,
  // Solda ince kırmızı çizgi — göze batmayan uyarı
  gutterIconPath: undefined,
  borderWidth: "0 0 0 3px",
  borderStyle: "solid",
  borderColor: new vscode.ThemeColor("charts.red"),
  rangeBehavior: vscode.DecorationRangeBehavior.ClosedClosed,
});

const MEDIUM_RISK_DECORATION = vscode.window.createTextEditorDecorationType({
  isWholeLine: true,
  overviewRulerColor: new vscode.ThemeColor("charts.yellow"),
  overviewRulerLane: vscode.OverviewRulerLane.Right,
  borderWidth: "0 0 0 3px",
  borderStyle: "solid",
  borderColor: new vscode.ThemeColor("charts.yellow"),
  rangeBehavior: vscode.DecorationRangeBehavior.ClosedClosed,
});

/**
 * Dosyanın AI riskine göre editör dekorasyonunu uygula.
 * Sadece ilk satıra (dosya başlığı) ince bir kenar vurgusu koyar.
 * Göze batmayan uyarı — çalışmayı engellemez.
 */
export function applyRiskDecoration(
  editor: vscode.TextEditor,
  aiPct: number
): void {
  // Önce mevcut dekorasyonları temizle
  editor.setDecorations(HIGH_RISK_DECORATION, []);
  editor.setDecorations(MEDIUM_RISK_DECORATION, []);

  if (aiPct < 40) return; // Düşük risk — dekorasyon yok

  // İlk satırın aralığı
  const firstLine = editor.document.lineAt(0);
  const range = new vscode.Range(firstLine.range.start, firstLine.range.end);

  if (aiPct >= 70) {
    editor.setDecorations(HIGH_RISK_DECORATION, [
      {
        range,
        hoverMessage: new vscode.MarkdownString(
          `⚠️ **CodeDNA**: High AI risk (${aiPct.toFixed(0)}%) detected in this file.`
        ),
      },
    ]);
  } else {
    editor.setDecorations(MEDIUM_RISK_DECORATION, [
      {
        range,
        hoverMessage: new vscode.MarkdownString(
          `ℹ️ **CodeDNA**: Medium AI risk (${aiPct.toFixed(0)}%) detected in this file.`
        ),
      },
    ]);
  }
}

/** Tüm dekorasyonları temizle. */
export function clearDecorations(editor: vscode.TextEditor): void {
  editor.setDecorations(HIGH_RISK_DECORATION, []);
  editor.setDecorations(MEDIUM_RISK_DECORATION, []);
}

/** Dekorasyonları serbest bırak. */
export function disposeDecorations(): void {
  HIGH_RISK_DECORATION.dispose();
  MEDIUM_RISK_DECORATION.dispose();
}
