"use client";

import { useState, useEffect } from "react";
import { getCommits, CommitListResponse } from "@/lib/api";
import { CommitTable, CommitTableSkeleton } from "@/components/CommitTable";
import { ErrorBanner } from "@/components/ErrorBanner";
import { useTranslation } from "@/lib/i18n";

export default function CommitsPage() {
  const { t } = useTranslation();
  const [limit, setLimit] = useState(20);
  const [data, setData] = useState<CommitListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(false);
    getCommits(limit)
      .then(setData)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [limit]);

  const surveyedCommits = data?.commits.filter((c) => c.understanding_score != null) ?? [];
  const avgUnderstanding =
    surveyedCommits.length > 0
      ? surveyedCommits.reduce((s, c) => s + c.understanding_score!, 0) / surveyedCommits.length
      : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">🕒 {t("commits_title")}</h1>
        <p className="text-gray-500 text-sm mt-1">{t("commits_subtitle")}</p>
      </div>

      {data && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: t("commits_total"), value: data.total, color: "text-cyan-400" },
            { label: t("commits_surveyed"), value: surveyedCommits.length, color: "text-white" },
            {
              label: t("commits_avg_understanding"),
              value: avgUnderstanding != null ? `${avgUnderstanding.toFixed(1)}/5` : "—",
              color: avgUnderstanding == null
                ? "text-gray-600"
                : avgUnderstanding >= 4 ? "text-green-400"
                : avgUnderstanding >= 2.5 ? "text-yellow-400"
                : "text-red-400",
            },
          ].map((card) => (
            <div key={card.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{card.label}</p>
              <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
            </div>
          ))}
        </div>
      )}

      {error && <ErrorBanner />}

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("commits_section")}
          </h2>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500"
          >
            {[10, 20, 50, 100].map((n) => (
              <option key={n} value={n}>
                {t("commits_last")} {n}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <CommitTableSkeleton />
        ) : data ? (
          <CommitTable commits={data.commits} />
        ) : null}
      </div>
    </div>
  );
}
