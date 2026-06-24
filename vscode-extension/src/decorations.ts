/**
 * CodeDNA decorations — adds a subtle highlight to the first line of
 * high-risk files. File-level decoration, not line-level.
 */

import * as vscode from "vscode";

// Header area decoration for high-risk files
const HIGH_RISK_DECORATION = vscode.window.createTextEditorDecorationType({
  isWholeLine: true,
  overviewRulerColor: new vscode.ThemeColor("charts.red"),
  overviewRulerLane: vscode.OverviewRulerLane.Right,
  // Thin red left border — subtle warning
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
 * Apply editor decoration based on the file's AI risk level.
 * Places a thin border highlight on the first line only (file header).
 * Non-intrusive warning — does not block work.
 */
export function applyRiskDecoration(
  editor: vscode.TextEditor,
  aiPct: number
): void {
  // Clear existing decorations first
  editor.setDecorations(HIGH_RISK_DECORATION, []);
  editor.setDecorations(MEDIUM_RISK_DECORATION, []);

  if (aiPct < 40) return; // Low risk — no decoration

  // Range of the first line
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

/** Clear all decorations. */
export function clearDecorations(editor: vscode.TextEditor): void {
  editor.setDecorations(HIGH_RISK_DECORATION, []);
  editor.setDecorations(MEDIUM_RISK_DECORATION, []);
}

/** Dispose all decorations. */
export function disposeDecorations(): void {
  HIGH_RISK_DECORATION.dispose();
  MEDIUM_RISK_DECORATION.dispose();
}
