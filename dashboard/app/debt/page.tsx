"use client";

import { useState, useEffect, useCallback } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { HataBanner } from "@/components/HataBanner";
import { CostInfoTooltip } from "@/components/CostInfoTooltip";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface DebtDosya {
  dosya_yolu: string;
  debt_saatleri: number;
  aylik_maliyet_usd: number | null;
  risk_seviyesi: string;
  ai_olasiligi: number;
  karmasiklik: number;
  toplam_satir: number;
}

interface DebtOzet {
  toplam_debt_saatleri: number;
  toplam_aylik_maliyet_usd: number | null;
  dolar_gizli: boolean;
  saatlik_ucret: number;
  toplam_dosya: number;
  en_pahali_5: { dosya_yolu: string; debt_saatleri: number; aylik_maliyet_usd: number | null; risk_seviyesi: string }[];
}

interface DebtDosyaYanit {
  toplam_dosya: number;
  dolar_gizli: boolean;
  saatlik_ucret: number;
  dosyalar: DebtDosya[];
}

/** Risk rengini döndür */
function riskRenk(risk: string): string {
  if (risk === "KRİTİK" || risk === "CRITICAL") return "#ef4444";
  if (risk === "YÜKSEK" || risk === "HIGH") return "#f97316";
  if (risk === "ORTA" || risk === "MEDIUM") return "#eab308";
  return "#22c55e";
}

function riskTailwind(risk: string): string {
  if (risk === "KRİTİK" || risk === "CRITICAL") return "text-red-400";
  if (risk === "YÜKSEK" || risk === "HIGH") return "text-orange-400";
  if (risk === "ORTA" || risk === "MEDIUM") return "text-yellow-400";
  return "text-green-400";
}

/** Kısaltılmış dosya yolu */
function kisaYol(yol: string): string {
  const p = yol.split("/");
  return p.length > 2 ? p.slice(-2).join("/") : yol;
}

/** Recharts özel tooltip */
function DebtTooltip({
  active,
  payload,
  dolarGizli,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: { yol: string; aylik: number | null } }>;
  dolarGizli: boolean;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-gray-300 font-mono">{d.payload.yol}</p>
      <p className="text-cyan-400 font-semibold mt-1">{d.value.toFixed(1)} saat</p>
      {!dolarGizli && d.payload.aylik != null && (
        <p className="text-green-400">${d.payload.aylik.toFixed(2)}/ay</p>
      )}
    </div>
  );
}

export default function DebtSayfasi() {
  const { t } = useTranslation();
  const [rate, setRate] = useState(75);
  const [inputRate, setInputRate] = useState("75");
  const [ozet, setOzet] = useState<DebtOzet | null>(null);
  const [dosyalar, setDosyalar] = useState<DebtDosya[]>([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(false);
  const [plan, setPlan] = useState<string>("free");

  useEffect(() => {
    setPlan(getCurrentPlan());
  }, []);

  const veriYukle = useCallback(async (r: number) => {
    setYukleniyor(true);
    setHata(false);
    try {
      const [ozetRes, dosyaRes] = await Promise.all([
        fetch(`${API_URL}/debt/summary?rate=${r}`),
        fetch(`${API_URL}/debt/files?rate=${r}&limit=10`),
      ]);
      if (!ozetRes.ok || !dosyaRes.ok) throw new Error("api_error");
      const [ozetVeri, dosyaVeri]: [DebtOzet, DebtDosyaYanit] = await Promise.all([
        ozetRes.json(),
        dosyaRes.json(),
      ]);
      setOzet(ozetVeri);
      setDosyalar(dosyaVeri.dosyalar);
    } catch {
      setHata(true);
    } finally {
      setYukleniyor(false);
    }
  }, []);

  useEffect(() => {
    veriYukle(rate);
  }, [rate, veriYukle]);

  const handleRateChange = () => {
    const yeni = parseFloat(inputRate);
    if (!isNaN(yeni) && yeni > 0) setRate(yeni);
  };

  const dolarGizli = ozet?.dolar_gizli ?? plan === "free";

  // Bar chart verisi
  const grafikVeri = dosyalar.slice(0, 8).map((d) => ({
    yol: kisaYol(d.dosya_yolu),
    saat: d.debt_saatleri,
    aylik: d.aylik_maliyet_usd,
    risk: d.risk_seviyesi,
  }));

  return (
    <div className="space-y-6">
      {/* Başlık */}
      <div>
        <h1 className="text-2xl font-bold text-white">💰 {t("debt_title")}</h1>
        <p className="text-gray-500 text-sm mt-1">{t("debt_subtitle")}</p>
      </div>

      {/* Saatlik ücret kontrolü */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex-1">
            <label className="text-sm text-gray-400 mb-2 block">
              {t("debt_rate_label")}:{" "}
              <span className="text-cyan-400 font-semibold">${rate}/h</span>
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                min={1}
                max={1000}
                value={inputRate}
                onChange={(e) => setInputRate(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleRateChange()}
                className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 w-28 focus:outline-none focus:border-cyan-500"
              />
              <button
                onClick={handleRateChange}
                className="bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
              >
                ↵
              </button>
            </div>
          </div>

          {/* Free plan kısıtlama notu */}
          {dolarGizli && (
            <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
              <span>🔒</span>
              <span>{t("debt_free_hint")}</span>
            </div>
          )}
        </div>
      </div>

      {hata && <HataBanner />}

      {/* Özet kartlar */}
      {ozet && !yukleniyor && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
              {t("debt_total_hours")}
            </p>
            <p className="text-2xl font-bold text-cyan-400">
              {ozet.toplam_debt_saatleri.toFixed(1)}h
            </p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
              {t("debt_monthly_cost")}
            </p>
            {dolarGizli ? (
              <p className="text-2xl font-bold text-gray-700 select-none blur-sm">
                $999/mo
              </p>
            ) : (
              <p className="text-2xl font-bold text-green-400 flex items-center">
                ${ozet.toplam_aylik_maliyet_usd?.toFixed(0) ?? "—"}/mo
                <CostInfoTooltip />
              </p>
            )}
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
              {t("debt_hourly_rate")}
            </p>
            <p className="text-2xl font-bold text-white">${rate}/h</p>
          </div>
        </div>
      )}

      {/* Yükleniyor */}
      {yukleniyor && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 bg-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {/* Bar chart */}
      {grafikVeri.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("debt_top_files")}
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={grafikVeri}
              margin={{ top: 4, right: 8, left: -8, bottom: 40 }}
            >
              <XAxis
                dataKey="yol"
                tick={{ fill: "#6b7280", fontSize: 10, fontFamily: "monospace" }}
                axisLine={false}
                tickLine={false}
                angle={-30}
                textAnchor="end"
                interval={0}
              />
              <YAxis
                tick={{ fill: "#6b7280", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                unit="h"
              />
              <Tooltip
                content={<DebtTooltip dolarGizli={dolarGizli} />}
                cursor={{ fill: "rgba(255,255,255,0.04)" }}
              />
              <Bar dataKey="saat" radius={[4, 4, 0, 0]}>
                {grafikVeri.map((entry, i) => (
                  <Cell key={i} fill={riskRenk(entry.risk)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Dosya tablosu */}
      {dosyalar.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("debt_col_file")}
            <span className="text-gray-600 text-xs font-normal">
              — {dosyalar.length} {t("files_results")}
            </span>
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-left border-b border-gray-800">
                  <th className="pb-3 font-medium">{t("debt_col_file")}</th>
                  <th className="pb-3 font-medium text-right">{t("debt_col_hours")}</th>
                  <th className="pb-3 font-medium text-right">{t("debt_col_monthly")}</th>
                  <th className="pb-3 font-medium text-center">{t("debt_col_risk")}</th>
                </tr>
              </thead>
              <tbody>
                {dosyalar.map((d) => (
                  <tr
                    key={d.dosya_yolu}
                    className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 transition-colors"
                  >
                    <td
                      className="py-2.5 font-mono text-xs text-gray-300 max-w-[240px] truncate"
                      title={d.dosya_yolu}
                    >
                      {kisaYol(d.dosya_yolu)}
                    </td>
                    <td className="py-2.5 text-right text-gray-300">
                      {d.debt_saatleri.toFixed(1)}h
                    </td>
                    <td className="py-2.5 text-right">
                      {dolarGizli ? (
                        <span className="text-gray-700 blur-sm select-none">$99</span>
                      ) : d.aylik_maliyet_usd != null ? (
                        <span className={riskTailwind(d.risk_seviyesi)}>
                          ${d.aylik_maliyet_usd.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-gray-600">—</span>
                      )}
                    </td>
                    <td className="py-2.5 text-center">
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                          d.risk_seviyesi === "KRİTİK"
                            ? "bg-red-500/20 text-red-400"
                            : d.risk_seviyesi === "YÜKSEK"
                            ? "bg-orange-500/20 text-orange-400"
                            : d.risk_seviyesi === "ORTA"
                            ? "bg-yellow-500/20 text-yellow-400"
                            : "bg-green-500/20 text-green-400"
                        }`}
                      >
                        {d.risk_seviyesi}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {dolarGizli && (
            <p className="mt-4 text-xs text-amber-400/70 text-center">
              🔒 {t("debt_locked_pro")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
