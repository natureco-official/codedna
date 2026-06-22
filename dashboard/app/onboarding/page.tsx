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

interface YazarOzet {
  yazar: string;
  toplam_commit: number;
  anlama_skoru_olan: number;
  ramp_up_hafta: number | null;
  son_ort_anlama: number | null;
  yeterli_veri: boolean;
}

interface Nokta {
  commit_no: number;
  hafta_no: number;
  tarih: string;
  understanding_score: number | null;
}

interface YazarEgriYanit {
  yazar: string;
  toplam_commit: number;
  anlama_skoru_olan: number;
  ramp_up_hafta: number | null;
  son_ort_anlama: number | null;
  yeterli_veri: boolean;
  noktalar: Nokta[];
}

/** Recharts özel tooltip */
function EgriTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: Nokta }>;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-gray-400">#{d.payload.commit_no} · {d.payload.tarih}</p>
      <p className="text-cyan-400 font-bold mt-0.5">{d.value.toFixed(1)} / 5</p>
    </div>
  );
}

/** Yazar seçici dropdown */
function YazarSecici({
  yazarlar,
  secili,
  onChange,
  t,
}: {
  yazarlar: YazarOzet[];
  secili: string;
  onChange: (y: string) => void;
  t: (k: string) => string;
}) {
  return (
    <select
      value={secili}
      onChange={(e) => onChange(e.target.value)}
      className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
    >
      <option value="">{t("onboarding_select_author")}</option>
      {yazarlar.map((y) => (
        <option key={y.yazar} value={y.yazar}>
          {y.yazar} ({y.toplam_commit} commit)
        </option>
      ))}
    </select>
  );
}

export default function OnboardingSayfasi() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);

  const [plan, setPlan] = useState<"free" | "pro" | "team" | "enterprise">("free");
  const [yazarlar, setYazarlar] = useState<YazarOzet[]>([]);
  const [seciliYazar, setSeciliYazar] = useState("");
  const [egri, setEgri] = useState<YazarEgriYanit | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [egriYukleniyor, setEgriYukleniyor] = useState(false);
  const [hata, setHata] = useState(false);

  useEffect(() => { setPlan(getCurrentPlan()); }, []);

  // Takım özeti yükle
  useEffect(() => {
    setYukleniyor(true);
    fetch(`${API_URL}/onboarding/team`)
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((d) => {
        setYazarlar(d.yazarlar ?? []);
        // İlk yazarı otomatik seç
        if (d.yazarlar?.length > 0) {
          setSeciliYazar(d.yazarlar[0].yazar);
        }
      })
      .catch(() => setHata(true))
      .finally(() => setYukleniyor(false));
  }, []);

  // Seçili yazar değiştiğinde eğriyi yükle
  const yukleEgri = useCallback(async (yazar: string) => {
    if (!yazar) return;
    setEgriYukleniyor(true);
    setEgri(null);
    try {
      const r = await fetch(`${API_URL}/onboarding/${encodeURIComponent(yazar)}`);
      if (!r.ok) throw new Error();
      setEgri(await r.json());
    } catch {
      // sessiz hata — yazar verisi olmayabilir
    } finally {
      setEgriYukleniyor(false);
    }
  }, []);

  useEffect(() => {
    if (seciliYazar) yukleEgri(seciliYazar);
  }, [seciliYazar, yukleEgri]);

  // Grafik verisi — sadece anlama skoru olan noktalar
  const grafikVeri = (egri?.noktalar ?? [])
    .filter((n) => n.understanding_score != null)
    .map((n) => ({
      ...n,
      skor: n.understanding_score!,
    }));

  const rampUpHafta = egri?.ramp_up_hafta;
  const yeterliVeri = egri?.yeterli_veri ?? false;
  const sonOrt = egri?.son_ort_anlama;

  return (
    <FeatureGate feature="sprint_health" plan={plan}>
      <div className="space-y-6">
        {/* Başlık */}
        <div>
          <h1 className="text-2xl font-bold text-white">🚀 {t("onboarding_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("onboarding_subtitle")}</p>
        </div>

        {hata && <HataBanner />}

        {/* Yazar seçici + özet metrikler */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div>
              <label className="text-xs text-gray-500 mb-1.5 block uppercase tracking-wider">
                {t("onboarding_select_author")}
              </label>
              {yukleniyor ? (
                <div className="h-9 w-48 bg-gray-800 rounded-lg animate-pulse" />
              ) : (
                <YazarSecici
                  yazarlar={yazarlar}
                  secili={seciliYazar}
                  onChange={setSeciliYazar}
                  t={t}
                />
              )}
            </div>

            {/* Ramp-up özet kartı */}
            {egri && (
              <div className="sm:ml-auto flex gap-4">
                <div className="bg-gray-800 rounded-xl px-4 py-3 text-center min-w-[100px]">
                  <p className="text-xs text-gray-500 mb-1">{t("onboarding_ramp_up")}</p>
                  {rampUpHafta != null ? (
                    <p className="text-xl font-bold text-green-400">
                      {rampUpHafta} <span className="text-sm font-normal text-gray-500">{t("onboarding_ramp_up_weeks")}</span>
                    </p>
                  ) : yeterliVeri ? (
                    <p className="text-sm text-yellow-400">{t("onboarding_threshold_not_reached")}</p>
                  ) : (
                    <p className="text-xs text-gray-600">{t("onboarding_insufficient_data")}</p>
                  )}
                </div>

                <div className="bg-gray-800 rounded-xl px-4 py-3 text-center min-w-[100px]">
                  <p className="text-xs text-gray-500 mb-1">{t("onboarding_last_understanding")}</p>
                  <p className={`text-xl font-bold ${
                    sonOrt == null ? "text-gray-600"
                    : sonOrt >= 4 ? "text-green-400"
                    : sonOrt >= 2.5 ? "text-yellow-400"
                    : "text-red-400"
                  }`}>
                    {sonOrt != null ? `${sonOrt.toFixed(1)}/5` : "—"}
                  </p>
                </div>

                <div className="bg-gray-800 rounded-xl px-4 py-3 text-center min-w-[100px]">
                  <p className="text-xs text-gray-500 mb-1">{t("onboarding_surveyed_commits")}</p>
                  <p className="text-xl font-bold text-cyan-400">
                    {egri.anlama_skoru_olan}
                    <span className="text-sm font-normal text-gray-500"> / {egri.toplam_commit}</span>
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Anlama eğrisi grafiği */}
        {egriYukleniyor && (
          <div className="h-64 bg-gray-800 rounded-xl animate-pulse" />
        )}

        {!egriYukleniyor && grafikVeri.length >= 2 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span>
              {seciliYazar} — {t("onboarding_title")}
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart
                data={grafikVeri}
                margin={{ top: 4, right: 8, left: -8, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis
                  dataKey="commit_no"
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
                {/* Üretkenlik eşiği çizgisi */}
                <ReferenceLine
                  y={3.5}
                  stroke="#22c55e"
                  strokeDasharray="5 3"
                  strokeOpacity={0.5}
                  label={{ value: t("onboarding_chart_threshold"), fill: "#22c55e", fontSize: 10, position: "right" }}
                />
                <Tooltip content={<EgriTooltip />} />
                <Line
                  type="monotone"
                  dataKey="skor"
                  stroke="#22d3ee"
                  strokeWidth={2.5}
                  dot={{ fill: "#22d3ee", r: 4, strokeWidth: 0 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Yetersiz veri durumu */}
        {!egriYukleniyor && egri && grafikVeri.length < 2 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <p className="text-gray-600 text-sm">{t("onboarding_insufficient_data")}</p>
          </div>
        )}

        {/* Takım özet tablosu */}
        {yazarlar.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
            <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
              <span className="text-cyan-400">◈</span> Takım Özeti
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
                  {yazarlar.map((y) => {
                    const anlamaRenk =
                      (y.son_ort_anlama ?? 0) >= 4 ? "text-green-400"
                      : (y.son_ort_anlama ?? 0) >= 2.5 ? "text-yellow-400"
                      : "text-gray-600";
                    return (
                      <tr
                        key={y.yazar}
                        onClick={() => setSeciliYazar(y.yazar)}
                        className={`border-b border-gray-800/50 last:border-0 cursor-pointer transition-colors ${
                          seciliYazar === y.yazar
                            ? "bg-cyan-500/5"
                            : "hover:bg-gray-800/30"
                        }`}
                      >
                        <td className="py-3 font-medium text-gray-200">{y.yazar}</td>
                        <td className="py-3 text-right text-gray-400">{y.toplam_commit}</td>
                        <td className="py-3 text-right text-gray-400">{y.anlama_skoru_olan}</td>
                        <td className="py-3 text-center">
                          {y.ramp_up_hafta != null ? (
                            <span className="text-green-400 font-medium">
                              {y.ramp_up_hafta} {t("onboarding_ramp_up_weeks")}
                            </span>
                          ) : y.yeterli_veri ? (
                            <span className="text-yellow-400 text-xs">{t("onboarding_threshold_not_reached")}</span>
                          ) : (
                            <span className="text-gray-700 text-xs">{t("onboarding_insufficient_data")}</span>
                          )}
                        </td>
                        <td className={`py-3 text-right font-medium ${anlamaRenk}`}>
                          {y.son_ort_anlama != null ? `${y.son_ort_anlama.toFixed(1)}/5` : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Yazar yok */}
        {!yukleniyor && yazarlar.length === 0 && !hata && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <p className="text-gray-600 text-sm">{t("onboarding_no_authors")}</p>
          </div>
        )}
      </div>
    </FeatureGate>
  );
}
