"use client";

import { RepoSummary } from "@/lib/api";
import { RiskBadge } from "./RiskBadge";
import { useTranslation } from "@/lib/i18n";

/** Top row summary cards */
export function SummaryCards({
  summary,
  totalFiles,
}: {
  summary: RepoSummary;
  totalFiles?: number;
}) {
  const { t } = useTranslation();

  const cards = [
    {
      title: t("card_total_files"),
      value: totalFiles != null ? String(totalFiles) : "—",
      sub: t("card_total_files_sub"),
      color: "text-cyan-400",
    },
    {
      title: t("card_avg_ai"),
      value:
        summary.avg_ai_percentage != null
          ? `${summary.avg_ai_percentage.toFixed(0)}%`
          : "—",
      sub: t("card_avg_ai_sub"),
      color:
        (summary.avg_ai_percentage ?? 0) >= 70
          ? "text-red-400"
          : (summary.avg_ai_percentage ?? 0) >= 40
          ? "text-yellow-400"
          : "text-green-400",
    },
    {
      title: t("card_risk"),
      value: <RiskBadge risk={summary.risk_level} size="lg" />,
      sub: t("card_risk_sub"),
      color: "",
    },
    {
      title: t("card_total_commits"),
      value: summary.total_commits,
      sub: t("card_total_commits_sub"),
      color: "text-cyan-400",
    },
    {
      title: t("card_avg_understanding"),
      value:
        summary.avg_understanding_score != null
          ? `${summary.avg_understanding_score.toFixed(1)}/5`
          : "—",
      sub: `${summary.commits_with_understanding} ${t("commits_surveyed").toLowerCase()}`,
      color:
        (summary.avg_understanding_score ?? 0) >= 4
          ? "text-green-400"
          : (summary.avg_understanding_score ?? 0) >= 2.5
          ? "text-yellow-400"
          : "text-red-400",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      {cards.map((card) => (
        <div
          key={card.title}
          className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-1"
        >
          <span className="text-xs text-gray-500 uppercase tracking-wider">
            {card.title}
          </span>
          <span className={`text-2xl font-bold ${card.color}`}>{card.value}</span>
          <span className="text-xs text-gray-600">{card.sub}</span>
        </div>
      ))}
    </div>
  );
}

/** Loading skeleton */
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
