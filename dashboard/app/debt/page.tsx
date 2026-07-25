"use client";

import { useState, useEffect, useCallback } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { ErrorBanner } from "@/components/ErrorBanner";
import { CostInfoTooltip } from "@/components/CostInfoTooltip";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DebtFile {
  file_path: string;
  debt_hours: number;
  monthly_cost_usd: number | null;
  risk_level: string;
  ai_probability: number;
  complexity: number;
  total_lines: number;
}

interface DebtSummary {
  total_debt_hours: number;
  total_monthly_cost_usd: number | null;
  dollars_hidden: boolean;
  hourly_rate: number;
  total_files: number;
  top_5_most_expensive: { file_path: string; debt_hours: number; monthly_cost_usd: number | null; risk_level: string }[];
}

interface DebtFilesResponse {
  total_files: number;
  dollars_hidden: boolean;
  hourly_rate: number;
  files: DebtFile[];
}

function riskColor(risk: string): string {
  if (risk === "CRITICAL") return "#ef4444";
  if (risk === "HIGH") return "#f97316";
  if (risk === "MEDIUM") return "#eab308";
  return "#22c55e";
}

function riskTailwind(risk: string): string {
  if (risk === "CRITICAL") return "text-red-400";
  if (risk === "HIGH") return "text-orange-400";
  if (risk === "MEDIUM") return "text-yellow-400";
  return "text-green-400";
}

function shortPath(path: string): string {
  const p = path.split("/");
  return p.length > 2 ? p.slice(-2).join("/") : path;
}

function DebtTooltip({
  active,
  payload,
  dollarsHidden,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: { path: string; monthly: number | null } }>;
  dollarsHidden: boolean;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-gray-300 font-mono">{d.payload.path}</p>
      <p className="text-cyan-400 font-semibold mt-1">{d.value.toFixed(1)} hours</p>
      {!dollarsHidden && d.payload.monthly != null && (
        <p className="text-green-400">${d.payload.monthly.toFixed(2)}/mo</p>
      )}
    </div>
  );
}

export default function DebtPage() {
  const { t } = useTranslation();
  const [rate, setRate] = useState(75);
  const [inputRate, setInputRate] = useState("75");
  const [summary, setSummary] = useState<DebtSummary | null>(null);
  const [files, setFiles] = useState<DebtFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [plan, setPlan] = useState<string>("free");

  useEffect(() => {
    setPlan(getCurrentPlan());
  }, []);

  const loadData = useCallback(async (r: number) => {
    setLoading(true);
    setError(false);
    try {
      const [summaryRes, filesRes] = await Promise.all([
        fetch(`${API_URL}/debt/summary?rate=${r}`),
        fetch(`${API_URL}/debt/files?rate=${r}&limit=10`),
      ]);
      if (!summaryRes.ok || !filesRes.ok) throw new Error("api_error");
      const [summaryData, filesData]: [DebtSummary, DebtFilesResponse] = await Promise.all([
        summaryRes.json(),
        filesRes.json(),
      ]);
      setSummary(summaryData);
      setFiles(filesData.files);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData(rate);
  }, [rate, loadData]);

  const handleRateChange = () => {
    const val = parseFloat(inputRate);
    if (!isNaN(val) && val > 0) setRate(val);
  };

  const dollarsHidden = summary?.dollars_hidden ?? plan === "free";

  const chartData = files.slice(0, 8).map((f) => ({
    path: shortPath(f.file_path),
    hours: f.debt_hours,
    monthly: f.monthly_cost_usd,
    risk: f.risk_level,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">💰 {t("debt_title")}</h1>
        <p className="text-gray-500 text-sm mt-1">{t("debt_subtitle")}</p>
      </div>

      {/* Hourly rate control */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex-1">
            <label className="text-sm text-gray-400 mb-2 block">
              {t("debt_rate_label")}:{" "}
              <span className="text-cyan-400 font-semibold">${rate}/h</span>
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                min={1}
                max={1000}
                value={inputRate}
                onChange={(e) => setInputRate(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleRateChange()}
                className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 w-28 focus:outline-none focus:border-cyan-500"
              />
              <button
                onClick={handleRateChange}
                className="bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
              >
                ↵
              </button>
            </div>
          </div>

          {dollarsHidden && (
            <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
              <span>🔒</span>
              <span>{t("debt_free_hint")}</span>
            </div>
          )}
        </div>
      </div>

      {error && <ErrorBanner />}

      {/* Summary cards */}
      {summary && !loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
              {t("debt_total_hours")}
            </p>
            <p className="text-2xl font-bold text-cyan-400">
              {summary.total_debt_hours.toFixed(1)}h
            </p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
              {t("debt_monthly_cost")}
            </p>
            {dollarsHidden ? (
              <p className="text-2xl font-bold text-gray-700 select-none blur-sm">$999/mo</p>
            ) : (
              <p className="text-2xl font-bold text-green-400 flex items-center">
                ${summary.total_monthly_cost_usd?.toFixed(0) ?? "—"}/mo
                <CostInfoTooltip />
              </p>
            )}
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
              {t("debt_hourly_rate")}
            </p>
            <p className="text-2xl font-bold text-white">${rate}/h</p>
          </div>
        </div>
      )}

      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 bg-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {/* Bar chart */}
      {chartData.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("debt_top_files")}
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} margin={{ top: 4, right: 8, left: -8, bottom: 40 }}>
              <XAxis
                dataKey="path"
                tick={{ fill: "#6b7280", fontSize: 10, fontFamily: "monospace" }}
                axisLine={false}
                tickLine={false}
                angle={-30}
                textAnchor="end"
                interval={0}
              />
              <YAxis
                tick={{ fill: "#6b7280", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                unit="h"
              />
              <Tooltip
                content={<DebtTooltip dollarsHidden={dollarsHidden} />}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar dataKey="hours" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={riskColor(entry.risk)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* File table */}
      {files.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("debt_col_file")}
            <span className="text-gray-600 text-xs font-normal">
              — {files.length} {t("files_results")}
            </span>
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-left border-b border-gray-800">
                  <th className="pb-3 font-medium">{t("debt_col_file")}</th>
                  <th className="pb-3 font-medium text-right">{t("debt_col_hours")}</th>
                  <th className="pb-3 font-medium text-right">{t("debt_col_monthly")}</th>
                  <th className="pb-3 font-medium text-center">{t("debt_col_risk")}</th>
                </tr>
              </thead>
              <tbody>
                {files.map((f) => (
                  <tr
                    key={f.file_path}
                    className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 transition-colors"
                  >
                    <td className="py-2.5 font-mono text-xs text-gray-300 max-w-[240px] truncate" title={f.file_path}>
                      {shortPath(f.file_path)}
                    </td>
                    <td className="py-2.5 text-right text-gray-300">{f.debt_hours.toFixed(1)}h</td>
                    <td className="py-2.5 text-right">
                      {dollarsHidden ? (
                        <span className="text-gray-700 blur-sm select-none">$99</span>
                      ) : f.monthly_cost_usd != null ? (
                        <span className={riskTailwind(f.risk_level)}>${f.monthly_cost_usd.toFixed(2)}</span>
                      ) : (
                        <span className="text-gray-600">—</span>
                      )}
                    </td>
                    <td className="py-2.5 text-center">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                        f.risk_level === "CRITICAL" ? "bg-red-500/20 text-red-400"
                        : f.risk_level === "HIGH" ? "bg-orange-500/20 text-orange-400"
                        : f.risk_level === "MEDIUM" ? "bg-yellow-500/20 text-yellow-400"
                        : "bg-green-500/20 text-green-400"
                      }`}>
                        {f.risk_level}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {dollarsHidden && (
            <p className="mt-4 text-xs text-amber-400/70 text-center">
              🔒 {t("debt_locked_pro")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
