"use client";

import { DosyaSkoru } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

function kisaYol(yol: string): string {
  const parcalar = yol.split("/");
  return parcalar.length > 2 ? parcalar.slice(-2).join("/") : yol;
}

function AIProgressBar({ yuzde }: { yuzde: number }) {
  const renk = yuzde >= 70 ? "bg-red-500" : yuzde >= 40 ? "bg-yellow-500" : "bg-green-500";
  const emoji = yuzde >= 70 ? "🔴" : yuzde >= 40 ? "🟡" : "🟢";
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <span className="text-sm">{emoji}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-2">
        <div
          className={`${renk} h-2 rounded-full transition-all`}
          style={{ width: `${Math.min(yuzde, 100)}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 w-10 text-right">%{yuzde.toFixed(0)}</span>
    </div>
  );
}

function KarmasiklikBadge({ etiket }: { etiket: string }) {
  const { t } = useTranslation();

  // API'den gelen değeri normalleştir (TR veya EN) → t() ile çevir
  const normalize = (e: string): string => {
    const map: Record<string, string> = {
      Yüksek: "complexity_high", High: "complexity_high",
      Orta: "complexity_medium", Medium: "complexity_medium",
      Düşük: "complexity_low", Low: "complexity_low",
    };
    return map[e] ?? e;
  };

  const renkMap: Record<string, string> = {
    complexity_high: "bg-red-500/20 text-red-400",
    complexity_medium: "bg-yellow-500/20 text-yellow-400",
    complexity_low: "bg-green-500/20 text-green-400",
  };

  const key = normalize(etiket);
  const renk = renkMap[key] ?? "bg-gray-500/20 text-gray-400";
  const label = t(key as Parameters<typeof t>[0]) ?? etiket;

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${renk}`}>
      {label}
    </span>
  );
}

export function FileHeatmap({ dosyalar }: { dosyalar: DosyaSkoru[] }) {
  const { t } = useTranslation();

  if (dosyalar.length === 0) {
    return (
      <p className="text-gray-600 text-sm text-center py-8">{t("files_no_data")}</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 text-left border-b border-gray-800">
            <th className="pb-3 font-medium">{t("files_col_path")}</th>
            <th className="pb-3 font-medium">{t("files_col_ai")}</th>
            <th className="pb-3 font-medium">{t("files_col_complexity")}</th>
            <th className="pb-3 font-medium text-right">{t("files_col_lines")}</th>
            <th className="pb-3 font-medium text-right">{t("files_col_functions")}</th>
          </tr>
        </thead>
        <tbody>
          {dosyalar.map((d) => (
            <tr
              key={d.dosya_yolu}
              className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 transition-colors"
            >
              <td className="py-3 font-mono text-xs text-gray-300 max-w-[240px]">
                <span title={d.dosya_yolu}>{kisaYol(d.dosya_yolu)}</span>
              </td>
              <td className="py-3 min-w-[160px]">
                <AIProgressBar yuzde={d.ai_yuzdesi} />
              </td>
              <td className="py-3">
                <KarmasiklikBadge etiket={d.karmasiklik_etiketi} />
              </td>
              <td className="py-3 text-right text-gray-400">{d.toplam_satir}</td>
              <td className="py-3 text-right text-gray-400">{d.fonksiyon_sayisi}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function FileHeatmapSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
      ))}
    </div>
  );
}
