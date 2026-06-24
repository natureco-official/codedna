"use client";

import { useState, useEffect } from "react";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { ErrorBanner } from "@/components/ErrorBanner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface BusFactorFile {
  file_path: string;
  bus_factor: number;
  primary_owner: string | null;
  ownership_percentage: number;
  risk: string;
  knowledgeable_authors: string[];
  total_lines: number;
}

interface BusFactorResponse {
  total_files: number;
  critical_count: number;
  risky_count: number;
  files: BusFactorFile[];
}

function riskStyle(risk: string) {
  if (risk === "CRITICAL")
    return { bg: "bg-red-500/10 border-red-500/30", badge: "bg-red-500/20 text-red-400", emoji: "🔴" };
  if (risk === "RISKY")
    return { bg: "bg-yellow-500/10 border-yellow-500/30", badge: "bg-yellow-500/20 text-yellow-400", emoji: "🟡" };
  return { bg: "bg-green-500/10 border-green-500/30", badge: "bg-green-500/20 text-green-400", emoji: "🟢" };
}

function FileCard({ file, t }: { file: BusFactorFile; t: (k: string) => string }) {
  const style = riskStyle(file.risk);
  const riskLabel =
    file.risk === "CRITICAL" ? t("bus_factor_critical")
    : file.risk === "RISKY" ? t("bus_factor_risky")
    : t("bus_factor_safe");

  return (
    <div className={`border rounded-xl p-5 ${style.bg}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-mono text-sm text-gray-200 truncate" title={file.file_path}>
            {file.file_path.split("/").slice(-2).join("/")}
          </p>
          <p className="text-xs text-gray-600 mt-0.5">{file.file_path}</p>
        </div>
        <span className={`shrink-0 text-xs font-bold px-2.5 py-1 rounded-full ${style.badge}`}>
          🚌 {t("bus_factor_col_bf")}: {file.bus_factor} · {style.emoji} {riskLabel}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
        <div>
          <p className="text-gray-600">{t("bus_factor_primary_owner")}</p>
          <p className="text-gray-200 font-medium mt-0.5">{file.primary_owner ?? "?"}</p>
        </div>
        <div>
          <p className="text-gray-600">{t("bus_factor_ownership_pct")}</p>
          <p className="text-gray-200 font-medium mt-0.5">{file.ownership_percentage.toFixed(1)}%</p>
        </div>
        <div>
          <p className="text-gray-600">{t("commits_col_files")} ({t("files_col_lines")})</p>
          <p className="text-gray-200 font-medium mt-0.5">{file.total_lines}</p>
        </div>
      </div>

      {file.risk === "CRITICAL" && (
        <p className="mt-3 text-xs text-red-400/80 flex items-center gap-1.5">
          <span>⚠️</span>
          {t("bus_factor_warning_text")}
        </p>
      )}
    </div>
  );
}

export default function BusFactorPage() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free" | "pro" | "team" | "enterprise">("free");
  const [data, setData] = useState<BusFactorResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [criticalOnly, setCriticalOnly] = useState(false);

  useEffect(() => {
    setPlan(getCurrentPlan());
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(false);
    const endpoint = criticalOnly ? "/bus-factor/critical" : "/bus-factor?max_files=200";
    fetch(`${API_URL}${endpoint}`)
      .then((r) => {
        if (r.status === 403) throw new Error("plan_required");
        return r.json();
      })
      .then((d) => {
        // /bus-factor/critical returns a different shape — normalize it
        if ("critical_count" in d && !("total_files" in d)) {
          setData({ total_files: d.critical_count, critical_count: d.critical_count, risky_count: 0, files: d.files });
        } else {
          setData(d);
        }
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [criticalOnly]);

  const visibleFiles = data?.files ?? [];

  return (
    <FeatureGate feature="bus_factor" plan={plan}>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">🚌 {t("bus_factor_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("bus_factor_subtitle")}</p>
        </div>

        {/* Summary cards */}
        {data && (
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{t("files_col_functions")}</p>
              <p className="text-2xl font-bold text-cyan-400">{data.total_files}</p>
            </div>
            <div className="bg-gray-900 border border-red-900/40 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{t("bus_factor_critical_count")}</p>
              <p className="text-2xl font-bold text-red-400">{data.critical_count}</p>
            </div>
            <div className="bg-gray-900 border border-yellow-900/40 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{t("bus_factor_risky")}</p>
              <p className="text-2xl font-bold text-yellow-400">{data.risky_count}</p>
            </div>
          </div>
        )}

        {/* Filter */}
        <div className="flex gap-3">
          {[false, true].map((critical) => (
            <button
              key={String(critical)}
              onClick={() => setCriticalOnly(critical)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                criticalOnly === critical
                  ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                  : "bg-gray-800 text-gray-400 hover:text-gray-200 border border-gray-700"
              }`}
            >
              {critical ? t("bus_factor_filter_critical") : t("bus_factor_filter_all")}
            </button>
          ))}
        </div>

        {error && <ErrorBanner />}

        {/* File cards */}
        <div className="space-y-3">
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-28 bg-gray-800 rounded-xl animate-pulse" />
            ))
          ) : visibleFiles.length === 0 ? (
            <p className="text-gray-600 text-sm text-center py-8">{t("bus_factor_no_data")}</p>
          ) : (
            visibleFiles.map((f) => (
              <FileCard key={f.file_path} file={f} t={t} />
            ))
          )}
        </div>
      </div>
    </FeatureGate>
  );
}
