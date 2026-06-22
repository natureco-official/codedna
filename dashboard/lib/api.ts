/**
 * CodeDNA API istemcisi — tüm fetch çağrıları burada merkezi yönetilir.
 */

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Tip tanımları (FastAPI yanıtlarıyla birebir eşleşir)
// ---------------------------------------------------------------------------

export interface RepoSummary {
  toplam_commit: number;
  ortalama_ai_skoru: number | null;
  ortalama_ai_yuzdesi: number | null;
  risk_seviyesi: "YÜKSEK" | "ORTA" | "DÜŞÜK" | "BİLİNMİYOR";
  anlama_skoru_olan_commit: number;
  ortalama_anlama_skoru: number | null;
}

export interface DosyaSkoru {
  dosya_yolu: string;
  ai_olasıligi: number;
  ai_yuzdesi: number;
  karmasiklik_skoru: number;
  karmasiklik_etiketi: "Düşük" | "Orta" | "Yüksek";
  yorum_orani: number;
  ortalama_fonksiyon_uzunlugu: number;
  tek_commit_orani: number;
  toplam_satir: number;
  fonksiyon_sayisi: number;
}

export interface DosyalarYanit {
  toplam_dosya: number;
  ortalama_ai_skoru: number;
  dosyalar: DosyaSkoru[];
}

export interface Commit {
  commit_hash: string;
  hash_kisa: string;
  yazar: string | null;
  zaman_dam: number | null;
  tarih: string | null;
  degisen_dosya_sayisi: number;
  anlama_skoru: number | null;
  olusturulma: string | null;
}

export interface CommitListYanit {
  toplam: number;
  commitler: Commit[];
}

export interface CommitDosyaSkoru {
  dosya_yolu: string;
  ai_olasıligi: number | null;
  karmasiklik_skoru: number | null;
  yorum_orani: number | null;
  anlama_skoru: number | null;
}

export interface CommitDetay {
  commit_hash: string;
  yazar: string | null;
  tarih: string | null;
  degisen_dosya_sayisi: number;
  anlama_skoru: number | null;
  dosyalar: CommitDosyaSkoru[];
}

export interface HealthYanit {
  durum: string;
  versiyon: string;
  zaman: string;
}

// ---------------------------------------------------------------------------
// API fonksiyonları
// ---------------------------------------------------------------------------

/** Belirtilen endpoint'ten veri çek, hata durumunda null döndür */
async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    // Her istekte güncel veri almak için cache'i devre dışı bırak
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    throw new Error(`API hatası: ${res.status} ${path}`);
  }

  return res.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthYanit> {
  return apiFetch<HealthYanit>("/health");
}

export async function getRepoSummary(): Promise<RepoSummary> {
  return apiFetch<RepoSummary>("/repo/summary");
}

export async function getRepoDosyalar(minRisk = 0): Promise<DosyalarYanit> {
  return apiFetch<DosyalarYanit>(`/repo/files?min_risk=${minRisk}`);
}

export async function getCommitler(limit = 20): Promise<CommitListYanit> {
  return apiFetch<CommitListYanit>(`/commits?limit=${limit}`);
}

export async function getCommitDetay(hash: string): Promise<CommitDetay> {
  return apiFetch<CommitDetay>(`/commits/${hash}`);
}
