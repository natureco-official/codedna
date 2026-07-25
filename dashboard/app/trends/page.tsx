"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "@/lib/i18n";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface TrendPoint {
  day: string;
  avg_understanding: number | null;
  avg_ai_probability: number | null;
  commit_count: number;
  file_count: number;
}

export default function TrendsPage() {
  const { t } = useTranslation();
  const [data, setData] = useState<TrendPoint[]>([]);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/trends?limit=30`, { cache: "no-store" })
      .then((r) => r.json())
      .then((d) => {
        setData((d.trends || []).reverse());
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-cyan-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800 rounded-xl p-6 text-red-400">
        {t("error_api")}
      </div>
    );
  }

  const aiValues = data.map((d) => d.avg_ai_probability).filter((v): v is number => v !== null);
  const understandingValues = data.map((d) => d.avg_understanding).filter((v): v is number => v !== null);
  const maxAiValue = aiValues.length > 0 ? Math.max(...aiValues) : 0;
  const maxUnderstandingValue = understandingValues.length > 0 ? Math.max(...understandingValues) : 0;
  const maxCommits = data.length > 0 ? Math.max(...data.map((d) => d.commit_count)) : 1;

  return (
    <div className="space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-bold text-white">{t("trends_title")}</h1>
        <p className="text-gray-400 text-sm mt-1">{t("trends_subtitle")}</p>
      </div>

      {data.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-10 text-center text-gray-500">
          {t("trends_no_data")}
        </div>
      ) : (
        <>
          {/* AI Score Trend */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">{t("trends_ai_trend")}</h2>
            <div className="relative h-48">
              <svg viewBox={`0 0 ${data.length * 30} 200`} className="w-full h-full">
                {/* Y axis reference lines */}
                {[0, 0.25, 0.5, 0.75, 1].map((val) => (
                  <line
                    key={val}
                    x1="0"
                    y1={200 - val * 180}
                    x2={data.length * 30}
                    y2={200 - val * 180}
                    stroke="#1f2937"
                    strokeWidth="1"
                  />
                ))}
                {/* AI line */}
                <polyline
                  fill="none"
                  stroke="#06b6d4"
                  strokeWidth="2"
                  points={data
                    .map((d, i) => {
                      const x = i * 30 + 15;
                      const y = 200 - ((d.avg_ai_probability ?? 0) / (maxAiValue || 1)) * 160 - 10;
                      return `${x},${y}`;
                    })
                    .join(" ")}
                />
                {/* X axis labels (every 5th) */}
                {data.map((d, i) =>
                  i % 5 === 0 ? (
                    <text
                      key={i}
                      x={i * 30 + 15}
                      y="195"
                      fill="#6b7280"
                      fontSize="10"
                      textAnchor="middle"
                    >
                      {d.day?.slice(5) || ""}
                    </text>
                  ) : null
                )}
              </svg>
            </div>
            <div className="flex gap-4 mt-2 text-sm text-gray-400">
              <span className="flex items-center gap-1">
                <span className="w-3 h-0.5 bg-cyan-500 inline-block" /> AI Probability
              </span>
            </div>
          </div>

          {/* Understanding Trend */}
          {understandingValues.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-white mb-4">{t("trends_understanding_trend")}</h2>
              <div className="relative h-48">
                <svg viewBox={`0 0 ${data.length * 30} 200`} className="w-full h-full">
                  {[0, 1, 2, 3, 4, 5].map((val) => (
                    <line
                      key={val}
                      x1="0"
                      y1={200 - (val / 5) * 160 - 10}
                      x2={data.length * 30}
                      y2={200 - (val / 5) * 160 - 10}
                      stroke="#1f2937"
                      strokeWidth="1"
                    />
                  ))}
                  <polyline
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="2"
                    points={data
                      .map((d, i) => {
                        const x = i * 30 + 15;
                        const y = 200 - ((d.avg_understanding ?? 0) / 5) * 160 - 10;
                        return `${x},${y}`;
                      })
                      .join(" ")}
                  />
                  {data.map((d, i) =>
                    i % 5 === 0 ? (
                      <text
                        key={i}
                        x={i * 30 + 15}
                        y="195"
                        fill="#6b7280"
                        fontSize="10"
                        textAnchor="middle"
                      >
                        {d.day?.slice(5) || ""}
                      </text>
                    ) : null
                  )}
                </svg>
              </div>
              <div className="flex gap-4 mt-2 text-sm text-gray-400">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-0.5 bg-emerald-500 inline-block" /> Understanding Score
                </span>
              </div>
            </div>
          )}

          {/* Commit count bar chart */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4">{t("trends_commit_count")}</h2>
            <div className="relative h-32 flex items-end gap-1">
              {data.map((d, i) => {
                const height = maxCommits > 0 ? (d.commit_count / maxCommits) * 100 : 0;
                return (
                  <div
                    key={i}
                    className="flex-1 bg-cyan-500/30 hover:bg-cyan-500/50 rounded-t transition-colors relative group"
                    style={{ height: `${Math.max(height, 2)}%` }}
                    title={`${d.day}: ${d.commit_count} commits`}
                  >
                    <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs text-gray-500 opacity-0 group-hover:opacity-100 whitespace-nowrap">
                      {d.commit_count}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
