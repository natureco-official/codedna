"use client";

import { useState, useEffect } from "react";
import { getRepoFiles, FilesResponse } from "@/lib/api";
import { FileHeatmap, FileHeatmapSkeleton } from "@/components/FileHeatmap";
import { ErrorBanner } from "@/components/ErrorBanner";
import { useTranslation } from "@/lib/i18n";

export default function FilesPage() {
  const { t } = useTranslation();
  const [minRisk, setMinRisk] = useState(0);
  const [data, setData] = useState<FilesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    getRepoFiles(minRisk / 100)
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [minRisk]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">📁 {t("files_title")}</h1>
        <p className="text-gray-500 text-sm mt-1">{t("files_subtitle")}</p>
      </div>

      {/* Filter card */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex-1">
            <label className="text-sm text-gray-400 mb-2 block">
              {t("files_filter")}:{" "}
              <span className="text-cyan-400 font-semibold">{minRisk}%</span>
            </label>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={minRisk}
              onChange={(e) => setMinRisk(Number(e.target.value))}
              className="w-full accent-cyan-400"
            />
            <div className="flex justify-between text-xs text-gray-700 mt-1">
              <span>{t("files_filter_all")}</span>
              <span>{t("files_filter_medium")}</span>
              <span>{t("files_filter_high")}</span>
              <span>100%</span>
            </div>
          </div>

          {data && (
            <div className="sm:text-right">
              <p className="text-2xl font-bold text-cyan-400">{data.total_files}</p>
              <p className="text-xs text-gray-500">
                {t("files_results")} · {t("files_avg_ai")}:{" "}
                <span className="text-gray-300">
                  {(data.avg_ai_score * 100).toFixed(0)}%
                </span>
              </p>
            </div>
          )}
        </div>
      </div>

      {error && <ErrorBanner />}

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
          <span className="text-cyan-400">◈</span> {t("files_section")}
          {data && (
            <span className="text-gray-600 text-xs font-normal">
              — {data.total_files} {t("files_results")}
            </span>
          )}
        </h2>
        {loading ? (
          <FileHeatmapSkeleton />
        ) : data ? (
          <FileHeatmap files={data.files} />
        ) : null}
      </div>
    </div>
  );
}
