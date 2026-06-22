"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { HataBanner } from "@/components/HataBanner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Oturum {
  id: number;
  aday: string;
  baslangic: string | null;
  bitis: string | null;
  skor: number | null;
  notlar: string | null;
}

interface MulakatYanit {
  session_id: number;
  aday: string;
  sorular: string[];
  anonimlestirilmis_kod: string;
  karmasiklik: number;
  satir_sayisi: number;
  uyari: string;
}

export default function InterviewSayfasi() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free"|"pro"|"team"|"enterprise">("free");
  const [oturumlar, setOturumlar] = useState<Oturum[]>([]);
  const [aktifMulakat, setAktifMulakat] = useState<MulakatYanit | null>(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [listYukleniyor, setListYukleniyor] = useState(true);
  const [hata, setHata] = useState(false);

  // Form state
  const [aday, setAday] = useState("");
  const [zorluk, setZorluk] = useState("medium");
  const [puanSessId, setPuanSessId] = useState<number | null>(null);
  const [puan, setPuan] = useState("4.0");
  const [notlar, setNotlar] = useState("");
  const [puanBasarili, setPuanBasarili] = useState(false);

  useEffect(() => { setPlan(getCurrentPlan()); }, []);

  const oturumYukle = useCallback(async () => {
    setListYukleniyor(true);
    try {
      const r = await fetch(`${API_URL}/interview/sessions`);
      if (r.ok) { const d = await r.json(); setOturumlar(d.oturumlar ?? []); }
    } catch { /* sessiz */ }
    finally { setListYukleniyor(false); }
  }, []);

  useEffect(() => { oturumYukle(); }, [oturumYukle]);

  const mulakatBaslat = async () => {
    if (!aday) return;
    setYukleniyor(true); setHata(false); setAktifMulakat(null);
    try {
      const r = await fetch(`${API_URL}/interview/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_name: aday, difficulty: zorluk }),
      });
      if (!r.ok) throw new Error();
      const d: MulakatYanit = await r.json();
      setAktifMulakat(d);
      setPuanSessId(d.session_id);
      oturumYukle();
    } catch { setHata(true); }
    finally { setYukleniyor(false); }
  };

  const puanKaydet = async () => {
    if (!puanSessId) return;
    const p = parseFloat(puan);
    if (isNaN(p) || p < 0 || p > 5) return;
    const r = await fetch(`${API_URL}/interview/${puanSessId}/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ score: p, evaluator_notes: notlar }),
    });
    if (r.ok) { setPuanBasarili(true); setTimeout(() => setPuanBasarili(false), 2000); oturumYukle(); }
  };

  return (
    <FeatureGate feature="interview_tool" plan={plan}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">🎯 {t("interview_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("interview_subtitle")}</p>
        </div>

        {/* Disclaimer */}
        <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-3">
          <span className="text-amber-400 mt-0.5">⚠️</span>
          <p className="text-xs text-amber-400/80">{t("interview_disclaimer")}</p>
        </div>

        {hata && <HataBanner />}

        {/* Mülakat başlatma formu */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <span className="text-cyan-400">+</span> {t("interview_start")}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">{t("interview_candidate")}</label>
              <input value={aday} onChange={(e) => setAday(e.target.value)}
                placeholder="Ayşe Y."
                className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">{t("interview_difficulty")}</label>
              <select value={zorluk} onChange={(e) => setZorluk(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500">
                <option value="easy">{t("interview_difficulty_easy")}</option>
                <option value="medium">{t("interview_difficulty_medium")}</option>
                <option value="hard">{t("interview_difficulty_hard")}</option>
              </select>
            </div>
          </div>
          <button onClick={mulakatBaslat} disabled={yukleniyor || !aday}
            className="bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-gray-950 font-semibold text-sm px-5 py-2 rounded-lg transition-colors">
            {yukleniyor ? "..." : t("interview_start")}
          </button>
        </div>

        {/* Aktif mülakat */}
        {aktifMulakat && (
          <div className="space-y-4">
            <div className="bg-gray-900 border border-cyan-500/30 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-white font-semibold">#{aktifMulakat.session_id} — {aktifMulakat.aday}</h3>
                <span className="text-xs text-gray-500">{aktifMulakat.karmasiklik.toFixed(0)} karmaşıklık · {aktifMulakat.satir_sayisi} satır</span>
              </div>

              {/* Anonimleştirilmiş kod */}
              <div className="bg-gray-950 rounded-lg p-4 mb-4 overflow-auto max-h-64">
                <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">
                  {aktifMulakat.anonimlestirilmis_kod.slice(0, 1200)}
                  {aktifMulakat.anonimlestirilmis_kod.length > 1200 && "\n...(kısaltıldı)"}
                </pre>
              </div>

              {/* Sorular */}
              <div className="space-y-2 mb-4">
                {aktifMulakat.sorular.map((s, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-cyan-400 font-bold text-sm">{i + 1}.</span>
                    <p className="text-gray-300 text-sm">{s}</p>
                  </div>
                ))}
              </div>

              {/* Puan girme */}
              <div className="border-t border-gray-800 pt-4">
                <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider">{t("interview_save_score")}</p>
                <div className="flex gap-2 flex-wrap">
                  <input type="number" min={0} max={5} step={0.5} value={puan}
                    onChange={(e) => setPuan(e.target.value)}
                    className="w-24 bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
                    placeholder="4.0" />
                  <input value={notlar} onChange={(e) => setNotlar(e.target.value)}
                    placeholder={t("interview_evaluator_notes")}
                    className="flex-1 bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500" />
                  <button onClick={puanKaydet}
                    className="bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
                    {puanBasarili ? "✓" : t("interview_save_score")}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Geçmiş oturumlar */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("interview_session_history")}
          </h2>
          {listYukleniyor ? (
            <div className="space-y-3">{Array.from({length:3}).map((_,i)=><div key={i} className="h-10 bg-gray-800 rounded animate-pulse"/>)}</div>
          ) : oturumlar.length === 0 ? (
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
                {oturumlar.map((o) => (
                  <tr key={o.id} onClick={() => setPuanSessId(o.id)}
                    className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 cursor-pointer transition-colors">
                    <td className="py-2.5 text-gray-600 text-xs">{o.id}</td>
                    <td className="py-2.5 text-gray-200">{o.aday}</td>
                    <td className="py-2.5 text-gray-500 text-xs">{o.baslangic ?? "?"}</td>
                    <td className="py-2.5 text-center font-medium">
                      {o.skor != null
                        ? <span className={o.skor >= 4 ? "text-green-400" : o.skor >= 2.5 ? "text-yellow-400" : "text-red-400"}>{o.skor.toFixed(1)}/5</span>
                        : <span className="text-gray-700">—</span>}
                    </td>
                    <td className="py-2.5 text-gray-600 text-xs">{(o.notlar ?? "").slice(0, 40)}</td>
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
