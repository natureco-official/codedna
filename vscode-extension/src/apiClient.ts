/**
 * CodeDNA API client — FastAPI'ye (codedna serve) istek gönderir.
 * Sunucu kapalıysa sessizce null döndürür, kullanıcıya popup spam yapmaz.
 */

import * as https from "https";
import * as http from "http";
import { URL } from "url";

export interface FileAnalysisResult {
  dosya_yolu: string;
  ai_yuzdesi: number;
  karmasiklik_etiketi: string;
  toplam_satir: number;
}

export interface RepoSummary {
  toplam_dosya: number;
  ortalama_ai_yuzdesi: number | null;
  risk_seviyesi: string;
}

/**
 * Belirtilen endpoint'ten JSON veri çek.
 * Hata durumunda null döndür — exception fırlatma.
 */
async function apiFetch<T>(baseUrl: string, path: string): Promise<T | null> {
  return new Promise((resolve) => {
    try {
      const url = new URL(path, baseUrl);
      const lib = url.protocol === "https:" ? https : http;

      const req = lib.get(
        url.toString(),
        { timeout: 3000 },
        (res) => {
          let data = "";
          res.on("data", (chunk) => (data += chunk));
          res.on("end", () => {
            try {
              resolve(JSON.parse(data) as T);
            } catch {
              resolve(null);
            }
          });
        }
      );

      req.on("error", () => resolve(null));
      req.on("timeout", () => {
        req.destroy();
        resolve(null);
      });
    } catch {
      resolve(null);
    }
  });
}

/** Sunucunun ayakta olup olmadığını kontrol et. */
export async function checkHealth(apiUrl: string): Promise<boolean> {
  const result = await apiFetch<{ durum: string }>(apiUrl, "/health");
  return result?.durum === "çalışıyor";
}

/** Repo genel özetini al. */
export async function getRepoSummary(apiUrl: string): Promise<RepoSummary | null> {
  return apiFetch<RepoSummary>(apiUrl, "/repo/summary");
}

/**
 * Belirli bir dosyanın analiz sonucunu al.
 * /repo/files endpoint'inden dosya yoluyla filtrele.
 */
export async function getFileAnalysis(
  apiUrl: string,
  filePath: string
): Promise<FileAnalysisResult | null> {
  const result = await apiFetch<{ dosyalar: FileAnalysisResult[] }>(
    apiUrl,
    "/repo/files?max_dosya=500"
  );

  if (!result?.dosyalar) return null;

  // Tam yol veya son iki parça ile eşleştir
  const parts = filePath.replace(/\\/g, "/").split("/");
  const tail2 = parts.slice(-2).join("/");
  const tail1 = parts.slice(-1)[0];

  return (
    result.dosyalar.find(
      (d) =>
        d.dosya_yolu === filePath ||
        d.dosya_yolu.endsWith(tail2) ||
        d.dosya_yolu.endsWith(tail1)
    ) ?? null
  );
}
