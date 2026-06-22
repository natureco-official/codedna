"use strict";
/**
 * CodeDNA VS Code Extension — giriş noktası.
 *
 * Davranış:
 *   - Dosya açıldığında/kaydedildiğinde AI% ve risk seviyesini status bar'da gösterir
 *   - codedna serve kapalıysa: sönük "bağlı değil" — popup/hata spam YOK
 *   - Status bar'a tıklanınca dashboard açılır
 *   - Yüksek riskli dosyalarda kenar vurgusu (göze batmayan)
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const statusBar_1 = require("./statusBar");
const decorations_1 = require("./decorations");
const apiClient_1 = require("./apiClient");
let statusBar;
let healthCheckInterval = null;
let lastKnownAlive = false;
/** Eklenti etkinleştiğinde çağrılır. */
function activate(context) {
    statusBar = new statusBar_1.CodeDNAStatusBar();
    // Komut: Dashboard'u tarayıcıda aç
    context.subscriptions.push(vscode.commands.registerCommand("codedna.openDashboard", () => {
        const dashUrl = vscode.workspace
            .getConfiguration("codedna")
            .get("dashboardUrl", "http://localhost:3000");
        vscode.env.openExternal(vscode.Uri.parse(dashUrl));
    }));
    // Komut: Aktif dosyayı yenile
    context.subscriptions.push(vscode.commands.registerCommand("codedna.refreshFile", () => {
        const editor = vscode.window.activeTextEditor;
        if (editor) {
            statusBar.analyzeFile(editor.document);
        }
    }));
    // Dosya açıldığında analiz et
    context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor) {
            analyzeAndDecorate(editor);
        }
        else {
            statusBar.hide();
        }
    }));
    // Dosya kaydedildiğinde analiz et
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument((doc) => {
        const editor = vscode.window.activeTextEditor;
        if (editor && editor.document === doc) {
            analyzeAndDecorate(editor);
        }
    }));
    // Ayarlar değiştiğinde yenile
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("codedna")) {
            statusBar.reload();
            const editor = vscode.window.activeTextEditor;
            if (editor)
                analyzeAndDecorate(editor);
        }
    }));
    // Periyodik sağlık kontrolü (30 saniyede bir) — bağlantı durumu değişince güncelle
    healthCheckInterval = setInterval(async () => {
        const apiUrl = vscode.workspace
            .getConfiguration("codedna")
            .get("apiUrl", "http://localhost:8000");
        const alive = await (0, apiClient_1.checkHealth)(apiUrl);
        if (alive !== lastKnownAlive) {
            lastKnownAlive = alive;
            const editor = vscode.window.activeTextEditor;
            if (editor)
                analyzeAndDecorate(editor);
            else if (!alive)
                statusBar.setDisconnected();
        }
    }, 30000);
    context.subscriptions.push({ dispose: () => statusBar.dispose() });
    context.subscriptions.push({ dispose: () => (0, decorations_1.disposeDecorations)() });
    context.subscriptions.push({
        dispose: () => {
            if (healthCheckInterval)
                clearInterval(healthCheckInterval);
        },
    });
    // Başlangıçta aktif dosyayı analiz et
    const activeEditor = vscode.window.activeTextEditor;
    if (activeEditor) {
        analyzeAndDecorate(activeEditor);
    }
}
/** Dosyayı analiz et ve hem status bar hem dekorasyonu güncelle. */
async function analyzeAndDecorate(editor) {
    const enabled = vscode.workspace
        .getConfiguration("codedna")
        .get("enabled", true);
    if (!enabled) {
        statusBar.hide();
        (0, decorations_1.clearDecorations)(editor);
        return;
    }
    // Status bar'ı güncelle (debounce içeriyor)
    statusBar.analyzeFile(editor.document);
    // Dekorasyon için doğrudan API çağrısı (status bar'dan bağımsız)
    const apiUrl = vscode.workspace
        .getConfiguration("codedna")
        .get("apiUrl", "http://localhost:8000");
    const result = await (0, apiClient_1.getFileAnalysis)(apiUrl, editor.document.fileName);
    if (result) {
        (0, decorations_1.applyRiskDecoration)(editor, result.ai_yuzdesi);
    }
    else {
        (0, decorations_1.clearDecorations)(editor);
    }
}
/** Eklenti devre dışı bırakıldığında çağrılır. */
function deactivate() {
    if (healthCheckInterval)
        clearInterval(healthCheckInterval);
}
//# sourceMappingURL=extension.js.map