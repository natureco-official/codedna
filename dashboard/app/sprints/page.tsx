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

interface Sprint {
  id: number;
  sprint_name: string;
  start_date: string | null;
  end_date: string | null;
  health_score: number | null;
  status: string;
  avg_understanding: number | null;
  debt_delta_hours: number | null;
  ai_lines: number;
  human_lines: number;
}

interface SprintListResponse {
  total: number;
  sprints: Sprint[];
}

function HealthGauge({ score, status }: { score: number; status: string }) {
  const color =
    status === "HEALTHY" ? "#22c55e"
    : status === "WARNING" ? "#eab308"
    : "#ef4444";

  const r = 54;
  const circumference = 2 * Math.PI * r;
  const filled = (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r={r} fill="none" stroke="#1f2937" strokeWidth="12" />
        <circle
          cx="70" cy="70" r={r}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeDasharray={`${filled} ${circumference - filled}`}
          strokeDashoffset={circumference * 0.25}
          strokeLinecap="round"
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
        <text x="70" y="65" textAnchor="middle" fill="white" fontSize="26" fontWeight="bold">
          {score.toFixed(0)}
        </text>
        <text x="70" y="83" textAnchor="middle" fill="#6b7280" fontSize="11">
          / 100
        </text>
      </svg>
      <span
        className="text-sm font-bold px-3 py-1 rounded-full"
        style={{ background: `${color}20`, color, border: `1px solid ${color}40` }}
      >
        {status}
      </span>
    </div>
  );
}

function TrendTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: { name: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-gray-300 font-medium">{d.payload.name}</p>
      <p className="text-cyan-400 font-bold mt-0.5">{d.value.toFixed(1)} / 100</p>
    </div>
  );
}

function CreateSprintForm({ onCreated, t }: { onCreated: () => void; t: (k: string) => string }) {
  const [name, setName] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const submit = async () => {
    if (!name || !start || !end) {
      setError("All fields are required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/sprints`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sprint_name: name, start_date: start, end_date: end }),
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.detail || "An error occurred.");
        return;
      }
      setSuccess(true);
      setName(""); setStart(""); setEnd("");
      setTimeout(() => { setSuccess(false); onCreated(); }, 1500);
    } catch {
      setError("Could not connect to API.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
        <span className="text-cyan-400">+</span> {t("sprint_create")}
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
        <div>
          <label className="text-xs text-gray-500 mb-1 block">{t("sprint_create_name")}</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Sprint 24"
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">{t("sprint_create_start")}</label>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">{t("sprint_create_end")}</label>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>
      {error && <p className="text-red-400 text-xs mb-2">{error}</p>}
      {success && <p className="text-green-400 text-xs mb-2">✓ {t("sprint_save_success")}</p>}
      <button
        onClick={submit}
        disabled={loading}
        className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-gray-950 font-semibold text-sm px-5 py-2 rounded-lg transition-colors"
      >
        {loading ? "..." : t("sprint_create")}
      </button>
    </div>
  );
}

export default function SprintsPage() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free" | "pro" | "team" | "enterprise">("free");
  const [data, setData] = useState<SprintListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => { setPlan(getCurrentPlan()); }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const res = await fetch(`${API_URL}/sprints/history?limit=10`);
      if (!res.ok) throw new Error();
      setData(await res.json());
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const sprints = data?.sprints ?? [];
  const latest = sprints[0] ?? null;

  const chartData = [...sprints].reverse().map((s) => ({
    name: s.sprint_name,
    score: s.health_score ?? 0,
  }));

  return (
    <FeatureGate feature="sprint_health" plan={plan}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">🏃 {t("sprint_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("sprint_subtitle")}</p>
        </div>

        {error && <ErrorBanner />}

        {!loading && latest && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col items-center justify-center">
              <HealthGauge score={latest.health_score ?? 0} status={latest.status} />
              <p className="text-gray-500 text-xs mt-2 text-center">{latest.sprint_name}</p>
            </div>

            <div className="md:col-span-2 grid grid-cols-2 gap-3">
              {[
                {
                  label: t("sprint_avg_understanding"),
                  value: latest.avg_understanding != null ? `${latest.avg_understanding.toFixed(1)}/5` : "—",
                  color: (latest.avg_understanding ?? 0) >= 4 ? "text-green-400"
                    : (latest.avg_understanding ?? 0) >= 2.5 ? "text-yellow-400" : "text-red-400",
                },
                {
                  label: t("sprint_ai_ratio"),
                  value: `${((latest.ai_lines / Math.max(latest.ai_lines + latest.human_lines, 1)) * 100).toFixed(0)}%`,
                  color: "text-cyan-400",
                },
                {
                  label: t("sprint_debt_trend"),
                  value: `${latest.debt_delta_hours?.toFixed(1) ?? "—"}h`,
                  color: "text-amber-400",
                },
                {
                  label: t("sprint_date_range"),
                  value: `${latest.start_date ?? "?"} → ${latest.end_date ?? "?"}`,
                  color: "text-gray-300",
                },
              ].map((card) => (
                <div key={card.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{card.label}</p>
                  <p className={`text-lg font-bold ${card.color}`}>{card.value}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="h-48 bg-gray-800 rounded-xl animate-pulse" />
            <div className="md:col-span-2 grid grid-cols-2 gap-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-20 bg-gray-800 rounded-xl animate-pulse" />
              ))}
            </div>
          </div>
        )}

        {chartData.length > 1 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span> {t("sprint_history")}
            </h2>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 100]} ticks={[0, 50, 80, 100]} tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} />
                <ReferenceLine y={80} stroke="#22c55e" strokeDasharray="4 2" strokeOpacity={0.4} />
                <ReferenceLine y={50} stroke="#eab308" strokeDasharray="4 2" strokeOpacity={0.4} />
                <Tooltip content={<TrendTooltip />} />
                <Line type="monotone" dataKey="score" stroke="#22d3ee" strokeWidth={2} dot={{ fill: "#22d3ee", r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {sprints.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span> {t("sprint_history")}
              <span className="text-gray-600 text-xs font-normal">— {sprints.length}</span>
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 text-left border-b border-gray-800">
                    <th className="pb-3 font-medium">{t("sprint_create_name")}</th>
                    <th className="pb-3 font-medium">{t("sprint_date_range")}</th>
                    <th className="pb-3 font-medium text-center">{t("sprint_health_score")}</th>
                    <th className="pb-3 font-medium text-right">{t("sprint_avg_understanding")}</th>
                    <th className="pb-3 font-medium text-right">{t("sprint_debt_trend")}</th>
                  </tr>
                </thead>
                <tbody>
                  {sprints.map((s) => {
                    const score = s.health_score ?? 0;
                    const color = s.status === "HEALTHY" ? "text-green-400"
                      : s.status === "WARNING" ? "text-yellow-400" : "text-red-400";
                    return (
                      <tr key={s.id} className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 transition-colors">
                        <td className="py-3 text-gray-200 font-medium">{s.sprint_name}</td>
                        <td className="py-3 text-gray-500 text-xs font-mono">{s.start_date} → {s.end_date}</td>
                        <td className={`py-3 text-center font-bold ${color}`}>{score.toFixed(0)}/100</td>
                        <td className="py-3 text-right text-gray-400">{s.avg_understanding != null ? `${s.avg_understanding.toFixed(1)}/5` : "—"}</td>
                        <td className="py-3 text-right text-gray-400">{s.debt_delta_hours != null ? `${s.debt_delta_hours.toFixed(1)}h` : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!loading && sprints.length === 0 && !error && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <p className="text-gray-600 text-sm">{t("sprint_no_data")}</p>
          </div>
        )}

        <CreateSprintForm onCreated={load} t={t} />
      </div>
    </FeatureGate>
  );
}
