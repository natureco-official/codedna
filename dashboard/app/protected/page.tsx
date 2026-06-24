"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { ErrorBanner } from "@/components/ErrorBanner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ProtectedModule {
  file_path: string;
  label: string;
  threshold: number;
  current_score: number | null;
  status: string;
}

function StatusBadge({ status, t }: { status: string; t: (k: string) => string }) {
  if (status === "VIOLATION")
    return <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-red-500/20 text-red-400">🔴 {t("protect_status_violation")}</span>;
  if (status === "SAFE")
    return <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">✅ {t("protect_status_safe")}</span>;
  return <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-gray-500/20 text-gray-400">⚪ {t("protect_status_unknown")}</span>;
}

function AddModuleForm({ onAdded, t }: { onAdded: () => void; t: (k: string) => string }) {
  const [path, setPath] = useState("");
  const [threshold, setThreshold] = useState(3.5);
  const [label, setLabel] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const submit = async () => {
    if (!path) { setError("File path is required."); return; }
    setLoading(true); setError("");
    try {
      const r = await fetch(`${API_URL}/protected-modules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: path, threshold, label: label || path }),
      });
      if (!r.ok) { const e = await r.json(); setError(e.detail || "Error."); return; }
      setSuccess(true); setPath(""); setLabel("");
      setTimeout(() => { setSuccess(false); onAdded(); }, 1200);
    } catch { setError("Could not connect to API."); }
    finally { setLoading(false); }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
      <h3 className="text-white font-semibold flex items-center gap-2">
        <span className="text-cyan-400">+</span> {t("protect_add")}
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="text-xs text-gray-500 mb-1 block">{t("protect_file_path")}</label>
          <input value={path} onChange={(e) => setPath(e.target.value)}
            placeholder="src/auth/handler.py"
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500" />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">{t("protect_label")}</label>
          <input value={label} onChange={(e) => setLabel(e.target.value)}
            placeholder="Auth Core"
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500" />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">{t("protect_threshold")} ({threshold.toFixed(1)}/5)</label>
          <input type="range" min={1} max={5} step={0.5} value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
            className="w-full accent-cyan-400 mt-2" />
        </div>
      </div>
      {error && <p className="text-red-400 text-xs">{error}</p>}
      {success && <p className="text-green-400 text-xs">✓ Added.</p>}
      <button onClick={submit} disabled={loading}
        className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-gray-950 font-semibold text-sm px-5 py-2 rounded-lg transition-colors">
        {loading ? "..." : t("protect_add")}
      </button>
    </div>
  );
}

export default function ProtectedPage() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free"|"pro"|"team"|"enterprise">("free");
  const [modules, setModules] = useState<ProtectedModule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => { setPlan(getCurrentPlan()); }, []);

  const load = useCallback(async () => {
    setLoading(true); setError(false);
    try {
      const r = await fetch(`${API_URL}/protected-modules`);
      if (!r.ok) throw new Error();
      const d = await r.json();
      setModules(d.modules ?? []);
    } catch { setError(true); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const remove = async (path: string) => {
    await fetch(`${API_URL}/protected-modules/${encodeURIComponent(path)}`, { method: "DELETE" });
    load();
  };

  const violations = modules.filter((m) => m.status === "VIOLATION");

  return (
    <FeatureGate feature="bus_factor" plan={plan}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">🛡️ {t("protect_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("protect_subtitle")}</p>
        </div>

        {error && <ErrorBanner />}

        {violations.length > 0 && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 space-y-2">
            <p className="text-red-400 font-semibold text-sm">⚠️ {t("protect_violations_title")} ({violations.length})</p>
            {violations.map((m) => (
              <p key={m.file_path} className="text-red-300/70 text-xs">
                {m.file_path.split("/").slice(-2).join("/")} — {t("protect_violation_warning")}
                {" "}(score: {m.current_score?.toFixed(1) ?? "?"} &lt; threshold: {m.threshold.toFixed(1)})
              </p>
            ))}
          </div>
        )}

        {!loading && modules.length > 0 && violations.length === 0 && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-xl px-4 py-3">
            <p className="text-green-400 text-sm">✅ {t("protect_all_safe")}</p>
          </div>
        )}

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("protect_title")}
            <span className="text-gray-600 text-xs font-normal">— {modules.length}</span>
          </h2>
          {loading ? (
            <div className="space-y-3">{Array.from({length:3}).map((_,i)=><div key={i} className="h-12 bg-gray-800 rounded animate-pulse"/>)}</div>
          ) : modules.length === 0 ? (
            <p className="text-gray-600 text-sm text-center py-6">{t("protect_no_data")}</p>
          ) : (
            <div className="space-y-3">
              {modules.map((m) => (
                <div key={m.file_path}
                  className={`border rounded-xl p-4 flex items-center gap-4 ${
                    m.status === "VIOLATION" ? "border-red-500/30 bg-red-500/5" : "border-gray-800"
                  }`}>
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-sm text-gray-200 truncate" title={m.file_path}>
                      {m.file_path.split("/").slice(-2).join("/")}
                    </p>
                    <p className="text-xs text-gray-600 mt-0.5">
                      {m.label} · threshold: {m.threshold.toFixed(1)}/5
                    </p>
                  </div>
                  <StatusBadge status={m.status} t={t} />
                  <button onClick={() => remove(m.file_path)}
                    className="text-gray-700 hover:text-red-400 transition-colors text-xs ml-2">
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <AddModuleForm onAdded={load} t={t} />
      </div>
    </FeatureGate>
  );
}
