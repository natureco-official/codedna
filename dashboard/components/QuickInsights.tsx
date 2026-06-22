"use client";

/**
 * Ana sayfadaki hızlı özet widget'ı.
 * Bus factor kritik sayısı + aylık borç tahmini, tıklanınca ilgili sayfaya yönlendirir.
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface InsightVeri {
  kritikDosya: number | null;
  aylikBorc: number | null;
  dolarGizli: boolean;
  toplamBorc: number | null;
}

export function QuickInsights() {
  const { t } = useTranslation();
  const [veri, setVeri] = useState<InsightVeri | null>(null);
  const [plan, setPlan] = useState("free");

  useEffect(() => {
    setPlan(getCurrentPlan());

    // Bus factor ve borç verilerini paralel çek — hata sessizce görmezden gel
    Promise.allSettled([
      fetch(`${API_URL}/bus-factor/critical`).then((r) =>
        r.ok ? r.json() : Promise.reject()
      ),
      fetch(`${API_URL}/debt/summary?rate=75`).then((r) =>
        r.ok ? r.json() : Promise.reject()
      ),
    ]).then(([bfSonuc, debtSonuc]) => {
      const kritik =
        bfSonuc.status === "fulfilled" ? bfSonuc.value.kritik_sayisi ?? null : null;
      const aylik =
        debtSonuc.status === "fulfilled"
          ? debtSonuc.value.toplam_aylik_maliyet_usd ?? null
          : null;
      const toplam =
        debtSonuc.status === "fulfilled"
          ? debtSonuc.value.toplam_debt_saatleri ?? null
          : null;
      const gizli =
        debtSonuc.status === "fulfilled"
          ? debtSonuc.value.dolar_gizli ?? true
          : true;

      setVeri({ kritikDosya: kritik, aylikBorc: aylik, dolarGizli: gizli, toplamBorc: toplam });
    });
  }, []);

  // Her iki API da cevap vermediyse widget'ı gösterme
  if (!veri) return null;

  const hicVeri = veri.kritikDosya === null && veri.toplamBorc === null;
  if (hicVeri) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {/* Bus Factor kartı */}
      {veri.kritikDosya !== null && (
        <Link
          href="/bus-factor"
          className="group bg-gray-900 border border-red-900/30 hover:border-red-500/40 rounded-xl p-4 flex items-center gap-4 transition-all"
        >
          <div className="text-2xl">🚌</div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-500 uppercase tracking-wider">
              {t("bus_factor_critical_count")}
            </p>
            <p className="text-xl font-bold text-red-400 mt-0.5">
              {veri.kritikDosya}{" "}
              <span className="text-sm font-normal text-gray-500">
                {t("bus_factor_critical").toLowerCase()}
              </span>
            </p>
          </div>
          <span className="text-gray-700 group-hover:text-gray-400 transition-colors text-sm">→</span>
        </Link>
      )}

      {/* Teknik Borç kartı */}
      {veri.toplamBorc !== null && (
        <Link
          href="/debt"
          className="group bg-gray-900 border border-amber-900/30 hover:border-amber-500/40 rounded-xl p-4 flex items-center gap-4 transition-all"
        >
          <div className="text-2xl">💰</div>
          <div className="flex-1 min-w-0">
            <p className="text-xs text-gray-500 uppercase tracking-wider">
              {t("debt_title")}
            </p>
            <p className="text-xl font-bold text-amber-400 mt-0.5">
              {veri.toplamBorc.toFixed(1)}h
              {!veri.dolarGizli && veri.aylikBorc != null && (
                <span className="text-sm font-normal text-gray-500 ml-2">
                  ${veri.aylikBorc.toFixed(0)}/mo
                </span>
              )}
              {veri.dolarGizli && (
                <span className="text-xs font-normal text-gray-600 ml-2">
                  🔒 Pro+
                </span>
              )}
            </p>
          </div>
          <span className="text-gray-700 group-hover:text-gray-400 transition-colors text-sm">→</span>
        </Link>
      )}
    </div>
  );
}
