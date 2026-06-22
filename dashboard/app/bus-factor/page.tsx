"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { HataBanner } from "@/components/HataBanner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface BusFaktorDosya {
  dosya_yolu: string;
  bus_factor: number;
  birincil_sahip: string | null;
  sahiplik_yuzdesi: number;
  risk: string;
  anlayan_yazarlar: string[];
  toplam_satir: number;
}

interface BusFaktorYanit {
  toplam_dosya: number;
  kritik_sayisi: number;
  riskli_sayisi: number;
  dosyalar: BusFaktorDosya[];
}

/** Risk seviyesine göre stil */
function riskStil(risk: string) {
  if (risk === "KRİTİK" || risk === "CRITICAL")
    return { bg: "bg-red-500/10 border-red-500/30", badge: "bg-red-500/20 text-red-400", emoji: "🔴" };
  if (risk === "RİSKLİ" || risk === "RISKY")
    return { bg: "bg-yellow-500/10 border-yellow-500/30", badge: "bg-yellow-500/20 text-yellow-400", emoji: "🟡" };
  return { bg: "bg-green-500/10 border-green-500/30", badge: "bg-green-500/20 text-green-400", emoji: "🟢" };
}

/** Tek dosya kartı */
function DosyaKarti({ dosya, t }: { dosya: BusFaktorDosya; t: (k: string) => string }) {
  const stil = riskStil(dosya.risk);
  const riskLabel =
    dosya.risk === "KRİTİK" ? t("bus_factor_critical")
    : dosya.risk === "RİSKLİ" ? t("bus_factor_risky")
    : t("bus_factor_safe");

  return (
    <div className={`border rounded-xl p-5 ${stil.bg}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-mono text-sm text-gray-200 truncate" title={dosya.dosya_yolu}>
            {dosya.dosya_yolu.split("/").slice(-2).join("/")}
          </p>
          <p className="text-xs text-gray-600 mt-0.5">{dosya.dosya_yolu}</p>
        </div>
        <span className={`shrink-0 text-xs font-bold px-2.5 py-1 rounded-full ${stil.badge}`}>
          🚌 {t("bus_factor_col_bf")}: {dosya.bus_factor} · {stil.emoji} {riskLabel}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
        <div>
          <p className="text-gray-600">{t("bus_factor_primary_owner")}</p>
          <p className="text-gray-200 font-medium mt-0.5">{dosya.birincil_sahip ?? "?"}</p>
        </div>
        <div>
          <p className="text-gray-600">{t("bus_factor_ownership_pct")}</p>
          <p className="text-gray-200 font-medium mt-0.5">%{dosya.sahiplik_yuzdesi.toFixed(1)}</p>
        </div>
        <div>
          <p className="text-gray-600">{t("commits_col_files")} ({t("files_col_lines")})</p>
          <p className="text-gray-200 font-medium mt-0.5">{dosya.toplam_satir}</p>
        </div>
      </div>

      {/* Kritik uyarı */}
      {(dosya.risk === "KRİTİK" || dosya.risk === "CRITICAL") && (
        <p className="mt-3 text-xs text-red-400/80 flex items-center gap-1.5">
          <span>⚠️</span>
          {t("bus_factor_warning_text")}
        </p>
      )}
    </div>
  );
}

export default function BusFactorSayfasi() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free" | "pro" | "team" | "enterprise">("free");
  const [veri, setVeri] = useState<BusFaktorYanit | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(false);
  const [sadecKritik, setSadecKritik] = useState(false);

  useEffect(() => {
    setPlan(getCurrentPlan());
  }, []);

  useEffect(() => {
    setYukleniyor(true);
    setHata(false);
    const endpoint = sadecKritik ? "/bus-factor/critical" : "/bus-factor?max_dosya=200";
    fetch(`${API_URL}${endpoint}`)
      .then((r) => {
        if (r.status === 403) throw new Error("plan_required");
        return r.json();
      })
      .then((d) => {
        // /bus-factor/critical farklı shape döndürür — normalize et
        if ("kritik_sayisi" in d && !("toplam_dosya" in d)) {
          setVeri({ toplam_dosya: d.kritik_sayisi, kritik_sayisi: d.kritik_sayisi, riskli_sayisi: 0, dosyalar: d.dosyalar });
        } else {
          setVeri(d);
        }
      })
      .catch(() => setHata(true))
      .finally(() => setYukleniyor(false));
  }, [sadecKritik]);

  const gorunenDosyalar = veri?.dosyalar ?? [];

  return (
    <FeatureGate feature="bus_factor" plan={plan}>
      <div className="space-y-6">
        {/* Başlık */}
        <div>
          <h1 className="text-2xl font-bold text-white">🚌 {t("bus_factor_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("bus_factor_subtitle")}</p>
        </div>

        {/* Özet kartlar */}
        {veri && (
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{t("files_col_functions")}</p>
              <p className="text-2xl font-bold text-cyan-400">{veri.toplam_dosya}</p>
            </div>
            <div className="bg-gray-900 border border-red-900/40 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{t("bus_factor_critical_count")}</p>
              <p className="text-2xl font-bold text-red-400">{veri.kritik_sayisi}</p>
            </div>
            <div className="bg-gray-900 border border-yellow-900/40 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{t("bus_factor_risky")}</p>
              <p className="text-2xl font-bold text-yellow-400">{veri.riskli_sayisi}</p>
            </div>
          </div>
        )}

        {/* Filtre */}
        <div className="flex gap-3">
          {[false, true].map((kritik) => (
            <button
              key={String(kritik)}
              onClick={() => setSadecKritik(kritik)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                sadecKritik === kritik
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                  : "bg-gray-800 text-gray-400 hover:text-gray-200 border border-gray-700"
              }`}
            >
              {kritik ? t("bus_factor_filter_critical") : t("bus_factor_filter_all")}
            </button>
          ))}
        </div>

        {hata && <HataBanner />}

        {/* Dosya kartları */}
        <div className="space-y-3">
          {yukleniyor ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-28 bg-gray-800 rounded-xl animate-pulse" />
            ))
          ) : gorunenDosyalar.length === 0 ? (
            <p className="text-gray-600 text-sm text-center py-8">{t("bus_factor_no_data")}</p>
          ) : (
            gorunenDosyalar.map((d) => (
              <DosyaKarti key={d.dosya_yolu} dosya={d} t={t} />
            ))
          )}
        </div>
      </div>
    </FeatureGate>
  );
}
