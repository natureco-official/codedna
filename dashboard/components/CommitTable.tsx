"use client";

import { useState, useEffect } from "react";
import { Commit, CommitDetail, getCommitDetail } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

/** Displays understanding score in color */
function UnderstandingScoreCell({ score }: { score: number | null }) {
  if (score == null) return <span className="text-gray-600 text-sm">—</span>;
  const color =
    score >= 4 ? "text-green-400" : score >= 2.5 ? "text-yellow-400" : "text-red-400";
  const emoji = score >= 4 ? "✅" : score >= 2.5 ? "🔶" : "🔴";
  return (
    <span className={`font-medium text-sm ${color}`}>
      {emoji} {score.toFixed(1)}/5
    </span>
  );
}

/** Detail modal for a single commit */
function CommitModal({ commit, onClose }: { commit: Commit; onClose: () => void }) {
  const { t } = useTranslation();
  const [detail, setDetail] = useState<CommitDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    getCommitDetail(commit.commit_hash)
      .then(setDetail)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [commit.commit_hash]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-800">
          <div>
            <h2 className="text-white font-semibold">
              {t("modal_commit_detail")}{" "}
              <code className="text-cyan-400 text-sm bg-gray-800 px-2 py-0.5 rounded">
                {commit.short_hash}
              </code>
            </h2>
            <p className="text-gray-500 text-sm mt-0.5">
              {commit.author} · {commit.date}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors p-1"
            aria-label={t("modal_close")}
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="p-5">
          {loading && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-8 bg-gray-800 rounded animate-pulse" />
              ))}
            </div>
          )}

          {error && (
            <p className="text-red-400 text-sm">{t("modal_loading_error")}</p>
          )}

          {detail && !loading && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-left border-b border-gray-800">
                  <th className="pb-2 font-medium">{t("modal_col_file")}</th>
                  <th className="pb-2 font-medium text-right">{t("modal_col_ai")}</th>
                  <th className="pb-2 font-medium text-right">{t("modal_col_complexity")}</th>
                  <th className="pb-2 font-medium text-right">{t("modal_col_understanding")}</th>
                </tr>
              </thead>
              <tbody>
                {detail.files.map((f) => {
                  const ai = (f.ai_probability ?? 0) * 100;
                  const aiColor =
                    ai >= 70 ? "text-red-400" : ai >= 40 ? "text-yellow-400" : "text-green-400";
                  return (
                    <tr key={f.file_path} className="border-b border-gray-800/50 last:border-0">
                      <td className="py-2.5 font-mono text-xs text-gray-300 max-w-[240px] truncate">
                        {f.file_path.split("/").slice(-2).join("/")}
                      </td>
                      <td className={`py-2.5 text-right font-medium ${aiColor}`}>
                        {ai.toFixed(0)}%
                      </td>
                      <td className="py-2.5 text-right text-gray-400">
                        {f.complexity_score?.toFixed(0) ?? "—"}
                      </td>
                      <td className="py-2.5 text-right">
                        <UnderstandingScoreCell score={f.understanding_score} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

/** Commit list table */
export function CommitTable({ commits }: { commits: Commit[] }) {
  const { t } = useTranslation();
  const [selectedCommit, setSelectedCommit] = useState<Commit | null>(null);

  if (commits.length === 0) {
    return (
      <p className="text-gray-600 text-sm text-center py-8">
        {t("commits_no_data")}
      </p>
    );
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-left border-b border-gray-800">
              <th className="pb-3 font-medium">{t("commits_col_hash")}</th>
              <th className="pb-3 font-medium">{t("commits_col_author")}</th>
              <th className="pb-3 font-medium">{t("commits_col_date")}</th>
              <th className="pb-3 font-medium text-right">{t("commits_col_files")}</th>
              <th className="pb-3 font-medium text-right">{t("commits_col_understanding")}</th>
            </tr>
          </thead>
          <tbody>
            {commits.map((c) => (
              <tr
                key={c.commit_hash}
                onClick={() => setSelectedCommit(c)}
                className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/40 cursor-pointer transition-colors"
              >
                <td className="py-3">
                  <code className="text-cyan-400 bg-gray-800 px-2 py-0.5 rounded text-xs">
                    {c.short_hash}
                  </code>
                </td>
                <td className="py-3 text-gray-300">{c.author ?? "?"}</td>
                <td className="py-3 text-gray-500">{c.date ?? "?"}</td>
                <td className="py-3 text-right text-gray-400">{c.files_changed}</td>
                <td className="py-3 text-right">
                  <UnderstandingScoreCell score={c.understanding_score} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selectedCommit && (
        <CommitModal commit={selectedCommit} onClose={() => setSelectedCommit(null)} />
      )}
    </>
  );
}

/** Loading skeleton */
export function CommitTableSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
      ))}
    </div>
  );
}
