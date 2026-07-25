"use client";

import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { ErrorBanner } from "@/components/ErrorBanner";


const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const TOOL_STYLES: Record<string, { color: string; emoji: string }> = {
  copilot: { color: "#22c55e", emoji: "🐙" },
  cursor:  { color: "#22d3ee", emoji: "🖱️" },
  claude:  { color: "#a855f7", emoji: "🧠" },
  unknown: { color: "#6b7280", emoji: "❓" },
};

interface ToolData {
  file_count: number;
  avg_ai_probability: number;
  avg_understanding: number | null;
}

interface CompareResponse {
  warning: string;
  tools: Record<string, ToolData>;
  total_files: number;
}

function ToolTooltip({ active, payload }: { active?: boolean; payload?: Array<{ value: number; payload: { tool: string } }> }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-gray-300 font-medium">{payload[0].payload.tool}</p>
      <p className="text-cyan-400 font-bold">{payload[0].value.toFixed(1)}/5</p>
    </div>
  );
}

export default function AIComparePage() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free" | "pro" | "team" | "enterprise">("free");
  const [data, setData] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => { setPlan(getCurrentPlan()); }, []);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/ai-compare`)
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  const chartData = Object.entries(data?.tools ?? {})
    .filter(([, v]) => v.avg_understanding != null)
    .map(([tool, v]) => ({
      tool,
      score: v.avg_understanding!,
      color: TOOL_STYLES[tool]?.color ?? "#6b7280",
    }));

  return (
    <FeatureGate feature="ai_comparison" plan={plan}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">🤖 {t("ai_compare_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("ai_compare_subtitle")}</p>
        </div>

        <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3">
          <span className="text-amber-400 mt-0.5">⚠️</span>
          <p className="text-xs text-amber-400/80">{t("ai_compare_disclaimer")}</p>
        </div>

        {error && <ErrorBanner />}

        {loading && (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-20 bg-gray-800 rounded-xl animate-pulse" />
            ))}
          </div>
        )}

        {!loading && chartData.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span> {t("ai_compare_col_understanding")}
            </h2>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={chartData} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                <XAxis dataKey="tool" tick={{ fill: "#6b7280", fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 5]} ticks={[0, 2.5, 3.5, 5]} tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<ToolTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {!loading && data && Object.keys(data.tools).length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span> {t("ai_compare_col_tool")}
              <span className="text-gray-600 text-xs font-normal">— {data.total_files} {t("files_results")}</span>
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
                  {Object.entries(data.tools)
                    .sort(([, a], [, b]) => b.file_count - a.file_count)
                    .map(([tool, v]) => {
                      const style = TOOL_STYLES[tool] ?? TOOL_STYLES.unknown;
                      const scoreColor = (v.avg_understanding ?? 0) >= 4 ? "text-green-400"
                        : (v.avg_understanding ?? 0) >= 2.5 ? "text-yellow-400" : "text-red-400";
                      return (
                        <tr key={tool} className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 transition-colors">
                          <td className="py-3">
                            <span className="flex items-center gap-2">
                              <span>{style.emoji}</span>
                              <span className="font-medium" style={{ color: style.color }}>
                                {t(`ai_tool_${tool}` as Parameters<typeof t>[0]) || tool}
                              </span>
                            </span>
                          </td>
                          <td className="py-3 text-right text-gray-400">{v.file_count}</td>
                          <td className="py-3 text-right text-gray-400">{(v.avg_ai_probability * 100).toFixed(0)}%</td>
                          <td className={`py-3 text-right font-medium ${scoreColor}`}>
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

        {!loading && !error && (!data || Object.keys(data.tools).length === 0) && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <p className="text-gray-600 text-sm">{t("ai_compare_no_data")}</p>
          </div>
        )}
      </div>
    </FeatureGate>
  );
}
