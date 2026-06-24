"use client";

import { useState, useEffect, useCallback } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { ErrorBanner } from "@/components/ErrorBanner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AuthorSummary {
  author: string;
  total_commits: number;
  commits_with_understanding: number;
  ramp_up_weeks: number | null;
  latest_avg_understanding: number | null;
  sufficient_data: boolean;
}

interface DataPoint {
  commit_number: number;
  week_number: number;
  date: string;
  understanding_score: number | null;
}

interface AuthorCurveResponse {
  author: string;
  total_commits: number;
  commits_with_understanding: number;
  ramp_up_weeks: number | null;
  latest_avg_understanding: number | null;
  sufficient_data: boolean;
  data_points: DataPoint[];
}

function CurveTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: DataPoint }>;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-gray-400">#{d.payload.commit_number} · {d.payload.date}</p>
      <p className="text-cyan-400 font-bold mt-0.5">{d.value.toFixed(1)} / 5</p>
    </div>
  );
}

function AuthorSelector({
  authors,
  selected,
  onChange,
  t,
}: {
  authors: AuthorSummary[];
  selected: string;
  onChange: (a: string) => void;
  t: (k: string) => string;
}) {
  return (
    <select
      value={selected}
      onChange={(e) => onChange(e.target.value)}
      className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
    >
      <option value="">{t("onboarding_select_author")}</option>
      {authors.map((a) => (
        <option key={a.author} value={a.author}>
          {a.author} ({a.total_commits} commits)
        </option>
      ))}
    </select>
  );
}

export default function OnboardingPage() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);

  const [plan, setPlan] = useState<"free" | "pro" | "team" | "enterprise">("free");
  const [authors, setAuthors] = useState<AuthorSummary[]>([]);
  const [selectedAuthor, setSelectedAuthor] = useState("");
  const [curve, setCurve] = useState<AuthorCurveResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [curveLoading, setCurveLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => { setPlan(getCurrentPlan()); }, []);

  // Load team summary
  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/onboarding/team`)
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((d) => {
        setAuthors(d.authors ?? []);
        if (d.authors?.length > 0) {
          setSelectedAuthor(d.authors[0].author);
        }
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  // Load curve when selected author changes
  const loadCurve = useCallback(async (author: string) => {
    if (!author) return;
    setCurveLoading(true);
    setCurve(null);
    try {
      const r = await fetch(`${API_URL}/onboarding/${encodeURIComponent(author)}`);
      if (!r.ok) throw new Error();
      setCurve(await r.json());
    } catch {
      // Silent error — author may have no data
    } finally {
      setCurveLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedAuthor) loadCurve(selectedAuthor);
  }, [selectedAuthor, loadCurve]);

  // Chart data — only points with understanding scores
  const chartData = (curve?.data_points ?? [])
    .filter((p) => p.understanding_score != null)
    .map((p) => ({ ...p, score: p.understanding_score! }));

  const rampUpWeeks = curve?.ramp_up_weeks;
  const sufficientData = curve?.sufficient_data ?? false;
  const latestAvg = curve?.latest_avg_understanding;

  return (
    <FeatureGate feature="sprint_health" plan={plan}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">🚀 {t("onboarding_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("onboarding_subtitle")}</p>
        </div>

        {error && <ErrorBanner />}

        {/* Author selector + summary metrics */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div>
              <label className="text-xs text-gray-500 mb-1.5 block uppercase tracking-wider">
                {t("onboarding_select_author")}
              </label>
              {loading ? (
                <div className="h-9 w-48 bg-gray-800 rounded-lg animate-pulse" />
              ) : (
                <AuthorSelector
                  authors={authors}
                  selected={selectedAuthor}
                  onChange={setSelectedAuthor}
                  t={t}
                />
              )}
            </div>

            {curve && (
              <div className="sm:ml-auto flex gap-4">
                <div className="bg-gray-800 rounded-xl px-4 py-3 text-center min-w-[100px]">
                  <p className="text-xs text-gray-500 mb-1">{t("onboarding_ramp_up")}</p>
                  {rampUpWeeks != null ? (
                    <p className="text-xl font-bold text-green-400">
                      {rampUpWeeks} <span className="text-sm font-normal text-gray-500">{t("onboarding_ramp_up_weeks")}</span>
                    </p>
                  ) : sufficientData ? (
                    <p className="text-sm text-yellow-400">{t("onboarding_threshold_not_reached")}</p>
                  ) : (
                    <p className="text-xs text-gray-600">{t("onboarding_insufficient_data")}</p>
                  )}
                </div>

                <div className="bg-gray-800 rounded-xl px-4 py-3 text-center min-w-[100px]">
                  <p className="text-xs text-gray-500 mb-1">{t("onboarding_last_understanding")}</p>
                  <p className={`text-xl font-bold ${
                    latestAvg == null ? "text-gray-600"
                    : latestAvg >= 4 ? "text-green-400"
                    : latestAvg >= 2.5 ? "text-yellow-400"
                    : "text-red-400"
                  }`}>
                    {latestAvg != null ? `${latestAvg.toFixed(1)}/5` : "—"}
                  </p>
                </div>

                <div className="bg-gray-800 rounded-xl px-4 py-3 text-center min-w-[100px]">
                  <p className="text-xs text-gray-500 mb-1">{t("onboarding_surveyed_commits")}</p>
                  <p className="text-xl font-bold text-cyan-400">
                    {curve.commits_with_understanding}
                    <span className="text-sm font-normal text-gray-500"> / {curve.total_commits}</span>
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {curveLoading && <div className="h-64 bg-gray-800 rounded-xl animate-pulse" />}

        {!curveLoading && chartData.length >= 2 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span>
              {selectedAuthor} — {t("onboarding_title")}
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis
                  dataKey="commit_number"
                  tick={{ fill: "#6b7280", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  label={{ value: "Commit #", position: "insideBottomRight", fill: "#4b5563", fontSize: 10 }}
                />
                <YAxis
                  domain={[0, 5]}
                  ticks={[0, 1, 2, 3, 3.5, 4, 5]}
                  tick={{ fill: "#6b7280", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <ReferenceLine
                  y={3.5}
                  stroke="#22c55e"
                  strokeDasharray="5 3"
                  strokeOpacity={0.5}
                  label={{ value: t("onboarding_chart_threshold"), fill: "#22c55e", fontSize: 10, position: "right" }}
                />
                <Tooltip content={<CurveTooltip />} />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#22d3ee"
                  strokeWidth={2.5}
                  dot={{ fill: "#22d3ee", r: 4, strokeWidth: 0 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {!curveLoading && curve && chartData.length < 2 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <p className="text-gray-600 text-sm">{t("onboarding_insufficient_data")}</p>
          </div>
        )}

        {/* Team summary table */}
        {authors.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span> Team Summary
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 text-left border-b border-gray-800">
                    <th className="pb-3 font-medium">{t("onboarding_select_author")}</th>
                    <th className="pb-3 font-medium text-right">{t("onboarding_total_commits")}</th>
                    <th className="pb-3 font-medium text-right">{t("onboarding_surveyed_commits")}</th>
                    <th className="pb-3 font-medium text-center">{t("onboarding_ramp_up")}</th>
                    <th className="pb-3 font-medium text-right">{t("onboarding_last_understanding")}</th>
                  </tr>
                </thead>
                <tbody>
                  {authors.map((a) => {
                    const understandingColor =
                      (a.latest_avg_understanding ?? 0) >= 4 ? "text-green-400"
                      : (a.latest_avg_understanding ?? 0) >= 2.5 ? "text-yellow-400"
                      : "text-gray-600";
                    return (
                      <tr
                        key={a.author}
                        onClick={() => setSelectedAuthor(a.author)}
                        className={`border-b border-gray-800/50 last:border-0 cursor-pointer transition-colors ${
                          selectedAuthor === a.author ? "bg-cyan-500/5" : "hover:bg-gray-800/30"
                        }`}
                      >
                        <td className="py-3 font-medium text-gray-200">{a.author}</td>
                        <td className="py-3 text-right text-gray-400">{a.total_commits}</td>
                        <td className="py-3 text-right text-gray-400">{a.commits_with_understanding}</td>
                        <td className="py-3 text-center">
                          {a.ramp_up_weeks != null ? (
                            <span className="text-green-400 font-medium">
                              {a.ramp_up_weeks} {t("onboarding_ramp_up_weeks")}
                            </span>
                          ) : a.sufficient_data ? (
                            <span className="text-yellow-400 text-xs">{t("onboarding_threshold_not_reached")}</span>
                          ) : (
                            <span className="text-gray-700 text-xs">{t("onboarding_insufficient_data")}</span>
                          )}
                        </td>
                        <td className={`py-3 text-right font-medium ${understandingColor}`}>
                          {a.latest_avg_understanding != null ? `${a.latest_avg_understanding.toFixed(1)}/5` : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!loading && authors.length === 0 && !error && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <p className="text-gray-600 text-sm">{t("onboarding_no_authors")}</p>
          </div>
        )}
      </div>
    </FeatureGate>
  );
}
