"use client";

/**
 * Quick summary widget on the main page.
 * Shows critical bus factor count + monthly debt estimate,
 * clicking navigates to the relevant page.
 */

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface InsightData {
  criticalFiles: number | null;
  monthlyDebt: number | null;
  dollarsHidden: boolean;
  totalDebt: number | null;
}

export function QuickInsights() {
  const { t } = useTranslation();
  const [data, setData] = useState<InsightData | null>(null);
  const [plan, setPlan] = useState("free");

  useEffect(() => {
    setPlan(getCurrentPlan());

    // Fetch bus factor and debt data in parallel — silently ignore errors
    Promise.allSettled([
      fetch(`${API_URL}/bus-factor/critical`).then((r) =>
        r.ok ? r.json() : Promise.reject()
      ),
      fetch(`${API_URL}/debt/summary?rate=75`).then((r) =>
        r.ok ? r.json() : Promise.reject()
      ),
    ]).then(([bfResult, debtResult]) => {
      const critical =
        bfResult.status === "fulfilled" ? bfResult.value.critical_count ?? null : null;
      const monthly =
        debtResult.status === "fulfilled"
          ? debtResult.value.total_monthly_cost_usd ?? null
          : null;
      const total =
        debtResult.status === "fulfilled"
          ? debtResult.value.total_debt_hours ?? null
          : null;
      const hidden =
        debtResult.status === "fulfilled"
          ? debtResult.value.dollars_hidden ?? true
          : true;

      setData({ criticalFiles: critical, monthlyDebt: monthly, dollarsHidden: hidden, totalDebt: total });
    });
  }, []);

  // Don't show widget until both APIs respond
  if (!data) return null;

  const noData = data.criticalFiles === null && data.totalDebt === null;
  if (noData) return null;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {/* Bus Factor card */}
      {data.criticalFiles !== null && (
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
              {data.criticalFiles}{" "}
              <span className="text-sm font-normal text-gray-500">
                {t("bus_factor_critical").toLowerCase()}
              </span>
            </p>
          </div>
          <span className="text-gray-700 group-hover:text-gray-400 transition-colors text-sm">→</span>
        </Link>
      )}

      {/* Technical Debt card */}
      {data.totalDebt !== null && (
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
              {data.totalDebt.toFixed(1)}h
              {!data.dollarsHidden && data.monthlyDebt != null && (
                <span className="text-sm font-normal text-gray-500 ml-2">
                  ${data.monthlyDebt.toFixed(0)}/mo
                </span>
              )}
              {data.dollarsHidden && (
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
