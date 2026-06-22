"use client";

import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { HataBanner } from "@/components/HataBanner";
import { CostInfoTooltip } from "@/components/CostInfoTooltip";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Araç renk ve emoji eşlemesi
const ARAC_STILI: Record<string, { renk: string; emoji: string }> = {
  copilot: { renk: "#22c55e", emoji: "🐙" },
  cursor:  { renk: "#22d3ee", emoji: "🖱️" },
  claude:  { renk: "#a855f7", emoji: "🧠" },
  unknown: { renk: "#6b7280", emoji: "❓" },
};

interface AracVeri {
  dosya_sayisi: number;
  avg_ai_probability: number;
  avg_understanding: number | null;
}

interface KarsilastirmaYanit {
  uyari: string;
  araclar: Record<string, AracVeri>;
  toplam_dosya: number;
}

function AracTooltip({ active, payload }: { active?: boolean; payload?: Array<{ value: number; name: string; payload: { arac: string } }> }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-gray-300 font-medium">{payload[0].payload.arac}</p>
      <p className="text-cyan-400 font-bold">{payload[0].value.toFixed(1)}/5</p>
    </div>
  );
}

export default function AIKarsilastirmaSayfasi() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free" | "pro" | "team" | "enterprise">("free");
  const [veri, setVeri] = useState<KarsilastirmaYanit | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(false);

  useEffect(() => { setPlan(getCurrentPlan()); }, []);

  useEffect(() => {
    setYukleniyor(true);
    fetch(`${API_URL}/ai-compare`)
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then(setVeri)
      .catch(() => setHata(true))
      .finally(() => setYukleniyor(false));
  }, []);

  // Bar chart için veri hazırla
  const grafikVeri = Object.entries(veri?.araclar ?? {})
    .filter(([, v]) => v.avg_understanding != null)
    .map(([arac, v]) => ({
      arac,
      anlama: v.avg_understanding!,
      renk: ARAC_STILI[arac]?.renk ?? "#6b7280",
    }));

  return (
    <FeatureGate feature="ai_comparison" plan={plan}>
      <div className="space-y-6">
        {/* Başlık */}
        <div>
          <h1 className="text-2xl font-bold text-white">🤖 {t("ai_compare_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("ai_compare_subtitle")}</p>
        </div>

        {/* Disclaimer banner */}
        <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3">
          <span className="text-amber-400 mt-0.5">⚠️</span>
          <p className="text-xs text-amber-400/80">{t("ai_compare_disclaimer")}</p>
          <CostInfoTooltip />
        </div>

        {hata && <HataBanner />}

        {/* Yükleniyor */}
        {yukleniyor && (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-20 bg-gray-800 rounded-xl animate-pulse" />
            ))}
          </div>
        )}

        {/* Bar chart */}
        {!yukleniyor && grafikVeri.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span> {t("ai_compare_col_understanding")}
            </h2>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={grafikVeri} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                <XAxis dataKey="arac" tick={{ fill: "#6b7280", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 5]} ticks={[0, 2.5, 3.5, 5]} tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<AracTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="anlama" radius={[4, 4, 0, 0]}>
                  {grafikVeri.map((entry, i) => (
                    <Cell key={i} fill={entry.renk} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Araç tablosu */}
        {!yukleniyor && veri && Object.keys(veri.araclar).length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span> {t("ai_compare_col_tool")}
              <span className="text-gray-600 text-xs font-normal">
                — {veri.toplam_dosya} {t("files_results")}
              </span>
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 text-left border-b border-gray-800">
                    <th className="pb-3 font-medium">{t("ai_compare_col_tool")}</th>
                    <th className="pb-3 font-medium text-right">{t("ai_compare_col_files")}</th>
                    <th className="pb-3 font-medium text-right">{t("ai_compare_col_ai_score")}</th>
                    <th className="pb-3 font-medium text-right">{t("ai_compare_col_understanding")}</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(veri.araclar)
                    .sort(([, a], [, b]) => b.dosya_sayisi - a.dosya_sayisi)
                    .map(([arac, v]) => {
                      const stil = ARAC_STILI[arac] ?? ARAC_STILI.unknown;
                      const anlamaRenk =
                        (v.avg_understanding ?? 0) >= 4 ? "text-green-400"
                        : (v.avg_understanding ?? 0) >= 2.5 ? "text-yellow-400"
                        : "text-red-400";
                      return (
                        <tr key={arac} className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 transition-colors">
                          <td className="py-3">
                            <span className="flex items-center gap-2">
                              <span>{stil.emoji}</span>
                              <span className="font-medium text-gray-200"
                                style={{ color: stil.renk }}>
                                {t(`ai_tool_${arac}` as Parameters<typeof t>[0]) || arac}
                              </span>
                            </span>
                          </td>
                          <td className="py-3 text-right text-gray-400">{v.dosya_sayisi}</td>
                          <td className="py-3 text-right text-gray-400">
                            %{(v.avg_ai_probability * 100).toFixed(0)}
                          </td>
                          <td className={`py-3 text-right font-medium ${anlamaRenk}`}>
                            {v.avg_understanding != null ? `${v.avg_understanding.toFixed(1)}/5` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Veri yok */}
        {!yukleniyor && !hata && (!veri || Object.keys(veri.araclar).length === 0) && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <p className="text-gray-600 text-sm">{t("ai_compare_no_data")}</p>
          </div>
        )}
      </div>
    </FeatureGate>
  );
}
