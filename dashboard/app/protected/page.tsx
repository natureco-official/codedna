"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { HataBanner } from "@/components/HataBanner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface KorumaModul {
  dosya_yolu: string;
  etiket: string;
  esik: number;
  mevcut_skor: number | null;
  durum: string;
}

function DurumRozeti({ durum, t }: { durum: string; t: (k: string) => string }) {
  if (durum === "İHLAL" || durum === "VIOLATION")
    return <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-red-500/20 text-red-400">🔴 {t("protect_status_violation")}</span>;
  if (durum === "GÜVENLİ" || durum === "SAFE")
    return <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-green-500/20 text-green-400">✅ {t("protect_status_safe")}</span>;
  return <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-gray-500/20 text-gray-400">⚪ {t("protect_status_unknown")}</span>;
}

function EkleFormu({ onEklendi, t }: { onEklendi: () => void; t: (k: string) => string }) {
  const [yol, setYol] = useState("");
  const [esik, setEsik] = useState(3.5);
  const [etiket, setEtiket] = useState("");
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState("");
  const [basarili, setBasarili] = useState(false);

  const gonder = async () => {
    if (!yol) { setHata("Dosya yolu zorunlu."); return; }
    setYukleniyor(true); setHata("");
    try {
      const r = await fetch(`${API_URL}/protected-modules`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dosya_yolu: yol, esik, etiket: etiket || yol }),
      });
      if (!r.ok) { const e = await r.json(); setHata(e.detail || "Hata."); return; }
      setBasarili(true); setYol(""); setEtiket("");
      setTimeout(() => { setBasarili(false); onEklendi(); }, 1200);
    } catch { setHata("API'ye bağlanılamadı."); }
    finally { setYukleniyor(false); }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
      <h3 className="text-white font-semibold flex items-center gap-2">
        <span className="text-cyan-400">+</span> {t("protect_add")}
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="text-xs text-gray-500 mb-1 block">{t("protect_file_path")}</label>
          <input value={yol} onChange={(e) => setYol(e.target.value)}
            placeholder="src/auth/handler.py"
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500" />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">{t("protect_label")}</label>
          <input value={etiket} onChange={(e) => setEtiket(e.target.value)}
            placeholder="Auth Çekirdeği"
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500" />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">{t("protect_threshold")} ({esik.toFixed(1)}/5)</label>
          <input type="range" min={1} max={5} step={0.5} value={esik} onChange={(e) => setEsik(Number(e.target.value))}
            className="w-full accent-cyan-400 mt-2" />
        </div>
      </div>
      {hata && <p className="text-red-400 text-xs">{hata}</p>}
      {basarili && <p className="text-green-400 text-xs">✓ Eklendi.</p>}
      <button onClick={gonder} disabled={yukleniyor}
        className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-gray-950 font-semibold text-sm px-5 py-2 rounded-lg transition-colors">
        {yukleniyor ? "..." : t("protect_add")}
      </button>
    </div>
  );
}

export default function ProtectedSayfasi() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free"|"pro"|"team"|"enterprise">("free");
  const [moduller, setModuller] = useState<KorumaModul[]>([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(false);

  useEffect(() => { setPlan(getCurrentPlan()); }, []);

  const yukle = useCallback(async () => {
    setYukleniyor(true); setHata(false);
    try {
      const r = await fetch(`${API_URL}/protected-modules`);
      if (!r.ok) throw new Error();
      const d = await r.json();
      setModuller(d.moduller ?? []);
    } catch { setHata(true); }
    finally { setYukleniyor(false); }
  }, []);

  useEffect(() => { yukle(); }, [yukle]);

  const kaldir = async (yol: string) => {
    await fetch(`${API_URL}/protected-modules/${encodeURIComponent(yol)}`, { method: "DELETE" });
    yukle();
  };

  const ihlaller = moduller.filter((m) => m.durum === "İHLAL" || m.durum === "VIOLATION");

  return (
    <FeatureGate feature="bus_factor" plan={plan}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">🛡️ {t("protect_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("protect_subtitle")}</p>
        </div>

        {hata && <HataBanner />}

        {/* İhlal banner'ı */}
        {ihlaller.length > 0 && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 space-y-2">
            <p className="text-red-400 font-semibold text-sm">⚠️ {t("protect_violations_title")} ({ihlaller.length})</p>
            {ihlaller.map((m) => (
              <p key={m.dosya_yolu} className="text-red-300/70 text-xs">
                {m.dosya_yolu.split("/").slice(-2).join("/")} — {t("protect_violation_warning")}
                {" "}(anlama: {m.mevcut_skor?.toFixed(1) ?? "?"} &lt; eşik: {m.esik.toFixed(1)})
              </p>
            ))}
          </div>
        )}
        {!yukleniyor && moduller.length > 0 && ihlaller.length === 0 && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-xl px-4 py-3">
            <p className="text-green-400 text-sm">✅ {t("protect_all_safe")}</p>
          </div>
        )}

        {/* Modül listesi */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("protect_title")}
            <span className="text-gray-600 text-xs font-normal">— {moduller.length}</span>
          </h2>
          {yukleniyor ? (
            <div className="space-y-3">{Array.from({length:3}).map((_,i)=><div key={i} className="h-12 bg-gray-800 rounded animate-pulse"/>)}</div>
          ) : moduller.length === 0 ? (
            <p className="text-gray-600 text-sm text-center py-6">{t("protect_no_data")}</p>
          ) : (
            <div className="space-y-3">
              {moduller.map((m) => (
                <div key={m.dosya_yolu}
                  className={`border rounded-xl p-4 flex items-center gap-4 ${
                    m.durum === "İHLAL" || m.durum === "VIOLATION"
                      ? "border-red-500/30 bg-red-500/5"
                      : "border-gray-800"
                  }`}>
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-sm text-gray-200 truncate"
                      title={m.dosya_yolu}>{m.dosya_yolu.split("/").slice(-2).join("/")}</p>
                    <p className="text-xs text-gray-600 mt-0.5">{m.etiket} · eşik: {m.esik.toFixed(1)}/5</p>
                  </div>
                  <DurumRozeti durum={m.durum} t={t} />
                  <button onClick={() => kaldir(m.dosya_yolu)}
                    className="text-gray-700 hover:text-red-400 transition-colors text-xs ml-2">
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <EkleFormu onEklendi={yukle} t={t} />
      </div>
    </FeatureGate>
  );
}
