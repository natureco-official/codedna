"use client";

import { RepoSummary } from "@/lib/api";
import { RiskBadge } from "./RiskBadge";
import { useTranslation } from "@/lib/i18n";

/** Üst satırdaki 5 özet kart */
export function SummaryCards({
  ozet,
  toplamDosya,
}: {
  ozet: RepoSummary;
  toplamDosya?: number;
}) {
  const { t } = useTranslation();

  const kartlar = [
    {
      baslik: t("card_total_files"),
      deger: toplamDosya != null ? String(toplamDosya) : "—",
      alt: t("card_total_files_sub"),
      renk: "text-cyan-400",
    },
    {
      baslik: t("card_avg_ai"),
      deger:
        ozet.ortalama_ai_yuzdesi != null
          ? `%${ozet.ortalama_ai_yuzdesi.toFixed(0)}`
          : "—",
      alt: t("card_avg_ai_sub"),
      renk:
        (ozet.ortalama_ai_yuzdesi ?? 0) >= 70
          ? "text-red-400"
          : (ozet.ortalama_ai_yuzdesi ?? 0) >= 40
          ? "text-yellow-400"
          : "text-green-400",
    },
    {
      baslik: t("card_risk"),
      deger: <RiskBadge risk={ozet.risk_seviyesi} size="lg" />,
      alt: t("card_risk_sub"),
      renk: "",
    },
    {
      baslik: t("card_total_commits"),
      deger: ozet.toplam_commit,
      alt: t("card_total_commits_sub"),
      renk: "text-cyan-400",
    },
    {
      baslik: t("card_avg_understanding"),
      deger:
        ozet.ortalama_anlama_skoru != null
          ? `${ozet.ortalama_anlama_skoru.toFixed(1)}/5`
          : "—",
      alt: `${ozet.anlama_skoru_olan_commit} ${t("commits_surveyed").toLowerCase()}`,
      renk:
        (ozet.ortalama_anlama_skoru ?? 0) >= 4
          ? "text-green-400"
          : (ozet.ortalama_anlama_skoru ?? 0) >= 2.5
          ? "text-yellow-400"
          : "text-red-400",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      {kartlar.map((k) => (
        <div
          key={k.baslik}
          className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-1"
        >
          <span className="text-xs text-gray-500 uppercase tracking-wider">
            {k.baslik}
          </span>
          <span className={`text-2xl font-bold ${k.renk}`}>{k.deger}</span>
          <span className="text-xs text-gray-600">{k.alt}</span>
        </div>
      ))}
    </div>
  );
}

/** Yükleme iskeleti */
export function SummaryCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="bg-gray-900 border border-gray-800 rounded-xl p-5 animate-pulse"
        >
          <div className="h-3 bg-gray-800 rounded w-20 mb-3" />
          <div className="h-7 bg-gray-800 rounded w-16 mb-2" />
          <div className="h-2 bg-gray-800 rounded w-24" />
        </div>
      ))}
    </div>
  );
}
