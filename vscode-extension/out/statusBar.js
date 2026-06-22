"use strict";
/**
 * CodeDNA status bar item — dosya bazlı AI% ve risk bilgisini alt çubukta gösterir.
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
exports.CodeDNAStatusBar = void 0;
const vscode = __importStar(require("vscode"));
const apiClient_1 = require("./apiClient");
// Desteklenen dosya uzantıları
const SUPPORTED_EXTS = new Set([".py", ".js", ".ts", ".jsx", ".tsx"]);
/** Risk seviyesine göre ikon */
function riskIcon(pct) {
    if (pct >= 70)
        return "$(error)";
    if (pct >= 40)
        return "$(warning)";
    return "$(pass)";
}
/** Risk etiketi */
function riskLabel(pct) {
    if (pct >= 70)
        return "HIGH";
    if (pct >= 40)
        return "MED";
    return "LOW";
}
class CodeDNAStatusBar {
    constructor() {
        this.connected = false;
        this.debounceTimer = null;
        this.item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.item.command = "codedna.openDashboard";
        this.apiUrl = this.getConfig("apiUrl", "http://localhost:8000");
        this.enabled = this.getConfig("enabled", true);
    }
    getConfig(key, defaultVal) {
        return vscode.workspace.getConfiguration("codedna").get(key, defaultVal);
    }
    /** Ayarları yeniden oku (yapılandırma değiştiğinde). */
    reload() {
        this.apiUrl = this.getConfig("apiUrl", "http://localhost:8000");
        this.enabled = this.getConfig("enabled", true);
    }
    /** Status bar'ı "bağlı değil" durumuna getir. */
    setDisconnected() {
        this.connected = false;
        this.item.text = "$(circle-slash) CodeDNA";
        this.item.tooltip = "CodeDNA: not connected — run 'codedna serve'";
        this.item.color = new vscode.ThemeColor("statusBarItem.warningForeground");
        this.item.show();
    }
    /** Status bar'ı analiz verisiyle güncelle. */
    setAnalysis(aiPct, complexity, lines) {
        this.connected = true;
        const icon = riskIcon(aiPct);
        const risk = riskLabel(aiPct);
        this.item.text = `${icon} AI: ${aiPct.toFixed(0)}% · ${risk}`;
        this.item.tooltip = new vscode.MarkdownString(`**CodeDNA Analysis**\n\n` +
            `- AI Probability: **${aiPct.toFixed(1)}%**\n` +
            `- Complexity: ${complexity}\n` +
            `- Lines: ${lines}\n\n` +
            `_Click to open dashboard_`);
        this.item.color = undefined;
        this.item.show();
    }
    /** Yükleniyor animasyonu. */
    setLoading() {
        this.item.text = "$(loading~spin) CodeDNA";
        this.item.tooltip = "CodeDNA: analyzing...";
        this.item.show();
    }
    /** Status bar'ı gizle. */
    hide() {
        this.item.hide();
    }
    /**
     * Aktif dosyayı analiz et — debounce ile (her tuş vuruşunda çalışmaz).
     * Sunucu kapalıysa sessizce "bağlı değil" gösterir.
     */
    analyzeFile(document) {
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
        if (this.debounceTimer)
            clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(async () => {
            await this._doAnalyze(document.fileName);
        }, 800);
    }
    async _doAnalyze(filePath) {
        this.setLoading();
        // Önce sunucu sağlığını kontrol et
        const alive = await (0, apiClient_1.checkHealth)(this.apiUrl);
        if (!alive) {
            this.setDisconnected();
            return;
        }
        const result = await (0, apiClient_1.getFileAnalysis)(this.apiUrl, filePath);
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
    dispose() {
        if (this.debounceTimer)
            clearTimeout(this.debounceTimer);
        this.item.dispose();
    }
}
exports.CodeDNAStatusBar = CodeDNAStatusBar;
//# sourceMappingURL=statusBar.js.map