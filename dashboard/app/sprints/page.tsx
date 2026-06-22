"use client";

import { useState, useEffect, useCallback } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { HataBanner } from "@/components/HataBanner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Sprint {
  id: number;
  sprint_adi: string;
  baslangic: string | null;
  bitis: string | null;
  health_score: number | null;
  durum: string;
  avg_understanding: number | null;
  debt_delta_saati: number | null;
  ai_satir: number;
  insan_satir: number;
}

interface SprintListYanit {
  toplam: number;
  sprintler: Sprint[];
}

/** Dairesel sağlık göstergesi */
function SaglikGostergesi({ skor, durum }: { skor: number; durum: string }) {
  const renk =
    durum === "SAĞLIKLI" || durum === "HEALTHY" ? "#22c55e"
    : durum === "DİKKAT" || durum === "WARNING" ? "#eab308"
    : "#ef4444";

  const r = 54;
  const cevres = 2 * Math.PI * r;
  const dolu = (skor / 100) * cevres;

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width="140" height="140" viewBox="0 0 140 140">
        {/* Arka plan çemberi */}
        <circle cx="70" cy="70" r={r} fill="none" stroke="#1f2937" strokeWidth="12" />
        {/* Skor yayı */}
        <circle
          cx="70" cy="70" r={r}
          fill="none"
          stroke={renk}
          strokeWidth="12"
          strokeDasharray={`${dolu} ${cevres - dolu}`}
          strokeDashoffset={cevres * 0.25}
          strokeLinecap="round"
          style={{ transition: "stroke-dasharray 0.6s ease" }}
        />
        {/* Skor metni */}
        <text x="70" y="65" textAnchor="middle" fill="white" fontSize="26" fontWeight="bold">
          {skor.toFixed(0)}
        </text>
        <text x="70" y="83" textAnchor="middle" fill="#6b7280" fontSize="11">
          / 100
        </text>
      </svg>
      <span
        className="text-sm font-bold px-3 py-1 rounded-full"
        style={{ background: `${renk}20`, color: renk, border: `1px solid ${renk}40` }}
      >
        {durum}
      </span>
    </div>
  );
}

/** Recharts trend tooltip */
function TrendTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: { ad: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-gray-300 font-medium">{d.payload.ad}</p>
      <p className="text-cyan-400 font-bold mt-0.5">{d.value.toFixed(1)} / 100</p>
    </div>
  );
}

/** Sprint oluşturma formu */
function SprintOlusturFormu({
  onOlusturuldu,
  t,
}: {
  onOlusturuldu: () => void;
  t: (k: string) => string;
}) {
  const [ad, setAd] = useState("");
  const [bas, setBas] = useState("");
  const [bit, setBit] = useState("");
  const [yukleniyor, setYukleniyor] = useState(false);
  const [hata, setHata] = useState("");
  const [basarili, setBasarili] = useState(false);

  const gonder = async () => {
    if (!ad || !bas || !bit) {
      setHata("Tüm alanlar zorunludur.");
      return;
    }
    setYukleniyor(true);
    setHata("");
    try {
      const res = await fetch(`${API_URL}/sprints`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sprint_adi: ad, baslangic: bas, bitis: bit }),
      });
      if (!res.ok) {
        const err = await res.json();
        setHata(err.detail || "Hata oluştu.");
        return;
      }
      setBasarili(true);
      setAd(""); setBas(""); setBit("");
      setTimeout(() => { setBasarili(false); onOlusturuldu(); }, 1500);
    } catch {
      setHata("API'ye bağlanılamadı.");
    } finally {
      setYukleniyor(false);
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
            value={ad}
            onChange={(e) => setAd(e.target.value)}
            placeholder="Sprint 24"
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">{t("sprint_create_start")}</label>
          <input
            type="date"
            value={bas}
            onChange={(e) => setBas(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 mb-1 block">{t("sprint_create_end")}</label>
          <input
            type="date"
            value={bit}
            onChange={(e) => setBit(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>
      {hata && <p className="text-red-400 text-xs mb-2">{hata}</p>}
      {basarili && <p className="text-green-400 text-xs mb-2">✓ {t("sprint_save_success")}</p>}
      <button
        onClick={gonder}
        disabled={yukleniyor}
        className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-gray-950 font-semibold text-sm px-5 py-2 rounded-lg transition-colors"
      >
        {yukleniyor ? "..." : t("sprint_create")}
      </button>
    </div>
  );
}

export default function SprintSayfasi() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free" | "pro" | "team" | "enterprise">("free");
  const [veri, setVeri] = useState<SprintListYanit | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(false);

  useEffect(() => {
    setPlan(getCurrentPlan());
  }, []);

  const yukle = useCallback(async () => {
    setYukleniyor(true);
    setHata(false);
    try {
      const res = await fetch(`${API_URL}/sprints/history?limit=10`);
      if (!res.ok) throw new Error();
      setVeri(await res.json());
    } catch {
      setHata(true);
    } finally {
      setYukleniyor(false);
    }
  }, []);

  useEffect(() => { yukle(); }, [yukle]);

  const sprintler = veri?.sprintler ?? [];
  const sonSprint = sprintler[0] ?? null;

  // Trend grafiği verisi — en eskiden en yeniye
  const grafikVeri = [...sprintler].reverse().map((s) => ({
    ad: s.sprint_adi,
    skor: s.health_score ?? 0,
  }));

  return (
    <FeatureGate feature="sprint_health" plan={plan}>
      <div className="space-y-6">
        {/* Başlık */}
        <div>
          <h1 className="text-2xl font-bold text-white">🏃 {t("sprint_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("sprint_subtitle")}</p>
        </div>

        {hata && <HataBanner />}

        {/* Üst bölüm: gösterge + son sprint bilgisi */}
        {!yukleniyor && sonSprint && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Dairesel gösterge */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col items-center justify-center">
              <SaglikGostergesi
                skor={sonSprint.health_score ?? 0}
                durum={sonSprint.durum}
              />
              <p className="text-gray-500 text-xs mt-2 text-center">{sonSprint.sprint_adi}</p>
            </div>

            {/* Metrik kartları */}
            <div className="md:col-span-2 grid grid-cols-2 gap-3">
              {[
                {
                  label: t("sprint_avg_understanding"),
                  value: sonSprint.avg_understanding != null
                    ? `${sonSprint.avg_understanding.toFixed(1)}/5`
                    : "—",
                  renk: (sonSprint.avg_understanding ?? 0) >= 4
                    ? "text-green-400"
                    : (sonSprint.avg_understanding ?? 0) >= 2.5
                    ? "text-yellow-400"
                    : "text-red-400",
                },
                {
                  label: t("sprint_ai_ratio"),
                  value: `%${((sonSprint.ai_satir / Math.max(sonSprint.ai_satir + sonSprint.insan_satir, 1)) * 100).toFixed(0)}`,
                  renk: "text-cyan-400",
                },
                {
                  label: t("sprint_debt_trend"),
                  value: `${sonSprint.debt_delta_saati?.toFixed(1) ?? "—"}h`,
                  renk: "text-amber-400",
                },
                {
                  label: t("sprint_date_range"),
                  value: `${sonSprint.baslangic ?? "?"} → ${sonSprint.bitis ?? "?"}`,
                  renk: "text-gray-300",
                },
              ].map((k) => (
                <div key={k.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{k.label}</p>
                  <p className={`text-lg font-bold ${k.renk}`}>{k.value}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Yükleniyor iskeleti */}
        {yukleniyor && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="h-48 bg-gray-800 rounded-xl animate-pulse" />
            <div className="md:col-span-2 grid grid-cols-2 gap-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-20 bg-gray-800 rounded-xl animate-pulse" />
              ))}
            </div>
          </div>
        )}

        {/* Trend grafiği */}
        {grafikVeri.length > 1 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span> {t("sprint_history")}
            </h2>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={grafikVeri} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis
                  dataKey="ad"
                  tick={{ fill: "#6b7280", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  ticks={[0, 50, 80, 100]}
                  tick={{ fill: "#6b7280", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <ReferenceLine y={80} stroke="#22c55e" strokeDasharray="4 2" strokeOpacity={0.4} />
                <ReferenceLine y={50} stroke="#eab308" strokeDasharray="4 2" strokeOpacity={0.4} />
                <Tooltip content={<TrendTooltip />} />
                <Line
                  type="monotone"
                  dataKey="skor"
                  stroke="#22d3ee"
                  strokeWidth={2}
                  dot={{ fill: "#22d3ee", r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Geçmiş tablo */}
        {sprintler.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span> {t("sprint_history")}
              <span className="text-gray-600 text-xs font-normal">— {sprintler.length}</span>
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
                  {sprintler.map((s) => {
                    const skor = s.health_score ?? 0;
                    const renk =
                      s.durum === "SAĞLIKLI" || s.durum === "HEALTHY" ? "text-green-400"
                      : s.durum === "DİKKAT" || s.durum === "WARNING" ? "text-yellow-400"
                      : "text-red-400";
                    return (
                      <tr key={s.id} className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 transition-colors">
                        <td className="py-3 text-gray-200 font-medium">{s.sprint_adi}</td>
                        <td className="py-3 text-gray-500 text-xs font-mono">
                          {s.baslangic} → {s.bitis}
                        </td>
                        <td className={`py-3 text-center font-bold ${renk}`}>
                          {skor.toFixed(0)}/100
                        </td>
                        <td className="py-3 text-right text-gray-400">
                          {s.avg_understanding != null ? `${s.avg_understanding.toFixed(1)}/5` : "—"}
                        </td>
                        <td className="py-3 text-right text-gray-400">
                          {s.debt_delta_saati != null ? `${s.debt_delta_saati.toFixed(1)}h` : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Veri yok */}
        {!yukleniyor && sprintler.length === 0 && !hata && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <p className="text-gray-600 text-sm">{t("sprint_no_data")}</p>
          </div>
        )}

        {/* Sprint oluşturma formu */}
        <SprintOlusturFormu onOlusturuldu={yukle} t={t} />
      </div>
    </FeatureGate>
  );
}
