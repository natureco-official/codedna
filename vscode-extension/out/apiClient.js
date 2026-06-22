"use strict";
/**
 * CodeDNA API client — FastAPI'ye (codedna serve) istek gönderir.
 * Sunucu kapalıysa sessizce null döndürür, kullanıcıya popup spam yapmaz.
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
exports.checkHealth = checkHealth;
exports.getRepoSummary = getRepoSummary;
exports.getFileAnalysis = getFileAnalysis;
const https = __importStar(require("https"));
const http = __importStar(require("http"));
const url_1 = require("url");
/**
 * Belirtilen endpoint'ten JSON veri çek.
 * Hata durumunda null döndür — exception fırlatma.
 */
async function apiFetch(baseUrl, path) {
    return new Promise((resolve) => {
        try {
            const url = new url_1.URL(path, baseUrl);
            const lib = url.protocol === "https:" ? https : http;
            const req = lib.get(url.toString(), { timeout: 3000 }, (res) => {
                let data = "";
                res.on("data", (chunk) => (data += chunk));
                res.on("end", () => {
                    try {
                        resolve(JSON.parse(data));
                    }
                    catch {
                        resolve(null);
                    }
                });
            });
            req.on("error", () => resolve(null));
            req.on("timeout", () => {
                req.destroy();
                resolve(null);
            });
        }
        catch {
            resolve(null);
        }
    });
}
/** Sunucunun ayakta olup olmadığını kontrol et. */
async function checkHealth(apiUrl) {
    const result = await apiFetch(apiUrl, "/health");
    return result?.durum === "çalışıyor";
}
/** Repo genel özetini al. */
async function getRepoSummary(apiUrl) {
    return apiFetch(apiUrl, "/repo/summary");
}
/**
 * Belirli bir dosyanın analiz sonucunu al.
 * /repo/files endpoint'inden dosya yoluyla filtrele.
 */
async function getFileAnalysis(apiUrl, filePath) {
    const result = await apiFetch(apiUrl, "/repo/files?max_dosya=500");
    if (!result?.dosyalar)
        return null;
    // Tam yol veya son iki parça ile eşleştir
    const parts = filePath.replace(/\\/g, "/").split("/");
    const tail2 = parts.slice(-2).join("/");
    const tail1 = parts.slice(-1)[0];
    return (result.dosyalar.find((d) => d.dosya_yolu === filePath ||
        d.dosya_yolu.endsWith(tail2) ||
        d.dosya_yolu.endsWith(tail1)) ?? null);
}
//# sourceMappingURL=apiClient.js.map