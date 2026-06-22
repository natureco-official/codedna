"use strict";
/**
 * CodeDNA decorations — yüksek riskli dosyalarda başlık satırına
 * hafif bir vurgu ekler. Satır bazlı vurgulama değil, dosya bazlı.
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
exports.applyRiskDecoration = applyRiskDecoration;
exports.clearDecorations = clearDecorations;
exports.disposeDecorations = disposeDecorations;
const vscode = __importStar(require("vscode"));
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
function applyRiskDecoration(editor, aiPct) {
    // Önce mevcut dekorasyonları temizle
    editor.setDecorations(HIGH_RISK_DECORATION, []);
    editor.setDecorations(MEDIUM_RISK_DECORATION, []);
    if (aiPct < 40)
        return; // Düşük risk — dekorasyon yok
    // İlk satırın aralığı
    const firstLine = editor.document.lineAt(0);
    const range = new vscode.Range(firstLine.range.start, firstLine.range.end);
    if (aiPct >= 70) {
        editor.setDecorations(HIGH_RISK_DECORATION, [
            {
                range,
                hoverMessage: new vscode.MarkdownString(`⚠️ **CodeDNA**: High AI risk (${aiPct.toFixed(0)}%) detected in this file.`),
            },
        ]);
    }
    else {
        editor.setDecorations(MEDIUM_RISK_DECORATION, [
            {
                range,
                hoverMessage: new vscode.MarkdownString(`ℹ️ **CodeDNA**: Medium AI risk (${aiPct.toFixed(0)}%) detected in this file.`),
            },
        ]);
    }
}
/** Tüm dekorasyonları temizle. */
function clearDecorations(editor) {
    editor.setDecorations(HIGH_RISK_DECORATION, []);
    editor.setDecorations(MEDIUM_RISK_DECORATION, []);
}
/** Dekorasyonları serbest bırak. */
function disposeDecorations() {
    HIGH_RISK_DECORATION.dispose();
    MEDIUM_RISK_DECORATION.dispose();
}
//# sourceMappingURL=decorations.js.map