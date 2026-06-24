"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { ErrorBanner } from "@/components/ErrorBanner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Session {
  id: number;
  candidate: string;
  start_time: string | null;
  end_time: string | null;
  score: number | null;
  notes: string | null;
}

interface InterviewResponse {
  session_id: number;
  candidate: string;
  questions: string[];
  anonymized_code: string;
  complexity: number;
  line_count: number;
  warning: string;
}

export default function InterviewPage() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free"|"pro"|"team"|"enterprise">("free");
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeInterview, setActiveInterview] = useState<InterviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [listLoading, setListLoading] = useState(true);
  const [error, setError] = useState(false);

  // Form state
  const [candidate, setCandidate] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [scoreSessionId, setScoreSessionId] = useState<number | null>(null);
  const [score, setScore] = useState("4.0");
  const [notes, setNotes] = useState("");
  const [scoreSuccess, setScoreSuccess] = useState(false);

  useEffect(() => { setPlan(getCurrentPlan()); }, []);

  const loadSessions = useCallback(async () => {
    setListLoading(true);
    try {
      const r = await fetch(`${API_URL}/interview/sessions`);
      if (r.ok) { const d = await r.json(); setSessions(d.sessions ?? []); }
    } catch { /* silent */ }
    finally { setListLoading(false); }
  }, []);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  const startInterview = async () => {
    if (!candidate) return;
    setLoading(true); setError(false); setActiveInterview(null);
    try {
      const r = await fetch(`${API_URL}/interview/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_name: candidate, difficulty }),
      });
      if (!r.ok) throw new Error();
      const d: InterviewResponse = await r.json();
      setActiveInterview(d);
      setScoreSessionId(d.session_id);
      loadSessions();
    } catch { setError(true); }
    finally { setLoading(false); }
  };

  const saveScore = async () => {
    if (!scoreSessionId) return;
    const p = parseFloat(score);
    if (isNaN(p) || p < 0 || p > 5) return;
    const r = await fetch(`${API_URL}/interview/${scoreSessionId}/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ score: p, evaluator_notes: notes }),
    });
    if (r.ok) {
      setScoreSuccess(true);
      setTimeout(() => setScoreSuccess(false), 2000);
      loadSessions();
    }
  };

  return (
    <FeatureGate feature="interview_tool" plan={plan}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">🎯 {t("interview_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("interview_subtitle")}</p>
        </div>

        <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3">
          <span className="text-amber-400 mt-0.5">⚠️</span>
          <p className="text-xs text-amber-400/80">{t("interview_disclaimer")}</p>
        </div>

        {error && <ErrorBanner />}

        {/* Start interview form */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <span className="text-cyan-400">+</span> {t("interview_start")}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">{t("interview_candidate")}</label>
              <input value={candidate} onChange={(e) => setCandidate(e.target.value)}
                placeholder="Jane D."
                className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">{t("interview_difficulty")}</label>
              <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500">
                <option value="easy">{t("interview_difficulty_easy")}</option>
                <option value="medium">{t("interview_difficulty_medium")}</option>
                <option value="hard">{t("interview_difficulty_hard")}</option>
              </select>
            </div>
          </div>
          <button onClick={startInterview} disabled={loading || !candidate}
            className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-gray-950 font-semibold text-sm px-5 py-2 rounded-lg transition-colors">
            {loading ? "..." : t("interview_start")}
          </button>
        </div>

        {/* Active interview */}
        {activeInterview && (
          <div className="bg-gray-900 border border-cyan-500/30 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-white font-semibold">
                #{activeInterview.session_id} — {activeInterview.candidate}
              </h3>
              <span className="text-xs text-gray-500">
                complexity {activeInterview.complexity.toFixed(0)} · {activeInterview.line_count} lines
              </span>
            </div>

            {/* Anonymized code */}
            <div className="bg-gray-950 rounded-lg p-4 overflow-auto max-h-64">
              <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                {activeInterview.anonymized_code.slice(0, 1200)}
                {activeInterview.anonymized_code.length > 1200 && "\n...(truncated)"}
              </pre>
            </div>

            {/* Questions */}
            <div className="space-y-2">
              {activeInterview.questions.map((q, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-cyan-400 font-bold text-sm">{i + 1}.</span>
                  <p className="text-gray-300 text-sm">{q}</p>
                </div>
              ))}
            </div>

            {/* Score input */}
            <div className="border-t border-gray-800 pt-4">
              <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider">{t("interview_save_score")}</p>
              <div className="flex gap-2 flex-wrap">
                <input type="number" min={0} max={5} step={0.5} value={score}
                  onChange={(e) => setScore(e.target.value)}
                  className="w-24 bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
                  placeholder="4.0" />
                <input value={notes} onChange={(e) => setNotes(e.target.value)}
                  placeholder={t("interview_evaluator_notes")}
                  className="flex-1 bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500" />
                <button onClick={saveScore}
                  className="bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
                  {scoreSuccess ? "✓" : t("interview_save_score")}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Session history */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("interview_session_history")}
          </h2>
          {listLoading ? (
            <div className="space-y-3">{Array.from({length:3}).map((_,i)=><div key={i} className="h-10 bg-gray-800 rounded animate-pulse"/>)}</div>
          ) : sessions.length === 0 ? (
            <p className="text-gray-600 text-sm text-center py-6">{t("interview_no_sessions")}</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-left border-b border-gray-800">
                  <th className="pb-3 font-medium">#</th>
                  <th className="pb-3 font-medium">{t("interview_col_candidate")}</th>
                  <th className="pb-3 font-medium">{t("interview_col_start")}</th>
                  <th className="pb-3 font-medium text-center">{t("interview_col_score")}</th>
                  <th className="pb-3 font-medium">{t("interview_col_notes")}</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((s) => (
                  <tr key={s.id} onClick={() => setScoreSessionId(s.id)}
                    className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 cursor-pointer transition-colors">
                    <td className="py-2.5 text-gray-600 text-xs">{s.id}</td>
                    <td className="py-2.5 text-gray-200">{s.candidate}</td>
                    <td className="py-2.5 text-gray-500 text-xs">{s.start_time ?? "?"}</td>
                    <td className="py-2.5 text-center font-medium">
                      {s.score != null
                        ? <span className={s.score >= 4 ? "text-green-400" : s.score >= 2.5 ? "text-yellow-400" : "text-red-400"}>{s.score.toFixed(1)}/5</span>
                        : <span className="text-gray-700">—</span>}
                    </td>
                    <td className="py-2.5 text-gray-600 text-xs">{(s.notes ?? "").slice(0, 40)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </FeatureGate>
  );
}
