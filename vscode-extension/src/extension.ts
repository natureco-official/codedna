/**
 * CodeDNA VS Code Extension — giriş noktası.
 *
 * Davranış:
 *   - Dosya açıldığında/kaydedildiğinde AI% ve risk seviyesini status bar'da gösterir
 *   - codedna serve kapalıysa: sönük "bağlı değil" — popup/hata spam YOK
 *   - Status bar'a tıklanınca dashboard açılır
 *   - Yüksek riskli dosyalarda kenar vurgusu (göze batmayan)
 */

import * as vscode from "vscode";
import { CodeDNAStatusBar } from "./statusBar";
import { applyRiskDecoration, clearDecorations, disposeDecorations } from "./decorations";
import { getFileAnalysis, checkHealth } from "./apiClient";

let statusBar: CodeDNAStatusBar;
let healthCheckInterval: ReturnType<typeof setInterval> | null = null;
let lastKnownAlive = false;

/** Eklenti etkinleştiğinde çağrılır. */
export function activate(context: vscode.ExtensionContext): void {
  statusBar = new CodeDNAStatusBar();

  // Komut: Dashboard'u tarayıcıda aç
  context.subscriptions.push(
    vscode.commands.registerCommand("codedna.openDashboard", () => {
      const dashUrl = vscode.workspace
        .getConfiguration("codedna")
        .get<string>("dashboardUrl", "http://localhost:3000");
      vscode.env.openExternal(vscode.Uri.parse(dashUrl));
    })
  );

  // Komut: Aktif dosyayı yenile
  context.subscriptions.push(
    vscode.commands.registerCommand("codedna.refreshFile", () => {
      const editor = vscode.window.activeTextEditor;
      if (editor) {
        statusBar.analyzeFile(editor.document);
      }
    })
  );

  // Dosya açıldığında analiz et
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor) {
        analyzeAndDecorate(editor);
      } else {
        statusBar.hide();
      }
    })
  );

  // Dosya kaydedildiğinde analiz et
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      const editor = vscode.window.activeTextEditor;
      if (editor && editor.document === doc) {
        analyzeAndDecorate(editor);
      }
    })
  );

  // Ayarlar değiştiğinde yenile
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("codedna")) {
        statusBar.reload();
        const editor = vscode.window.activeTextEditor;
        if (editor) analyzeAndDecorate(editor);
      }
    })
  );

  // Periyodik sağlık kontrolü (30 saniyede bir) — bağlantı durumu değişince güncelle
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

  // Başlangıçta aktif dosyayı analiz et
  const activeEditor = vscode.window.activeTextEditor;
  if (activeEditor) {
    analyzeAndDecorate(activeEditor);
  }
}

/** Dosyayı analiz et ve hem status bar hem dekorasyonu güncelle. */
async function analyzeAndDecorate(editor: vscode.TextEditor): Promise<void> {
  const enabled = vscode.workspace
    .getConfiguration("codedna")
    .get<boolean>("enabled", true);

  if (!enabled) {
    statusBar.hide();
    clearDecorations(editor);
    return;
  }

  // Status bar'ı güncelle (debounce içeriyor)
  statusBar.analyzeFile(editor.document);

  // Dekorasyon için doğrudan API çağrısı (status bar'dan bağımsız)
  const apiUrl = vscode.workspace
    .getConfiguration("codedna")
    .get<string>("apiUrl", "http://localhost:8000");

  const result = await getFileAnalysis(apiUrl, editor.document.fileName);
  if (result) {
    applyRiskDecoration(editor, result.ai_yuzdesi);
  } else {
    clearDecorations(editor);
  }
}

/** Eklenti devre dışı bırakıldığında çağrılır. */
export function deactivate(): void {
  if (healthCheckInterval) clearInterval(healthCheckInterval);
}
