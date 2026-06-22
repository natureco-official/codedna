"use client";

import Link from "next/link";
import { useTranslation } from "@/lib/i18n";
import { PLAN_LIMITS, Plan, getCurrentPlan } from "@/lib/plan";
import { useState, useEffect } from "react";

// Fiyatlar (statik — ödeme sistemi Faz 9'da)
const PRICES: Record<Plan, string> = {
  free: "0",
  pro: "19",
  team: "49",
  enterprise: "?",
};

const CHECK = "✓";
const CROSS = "✗";
const LOCK = "🔒";

/** Özellik değerini okunabilir string'e çevir */
function limitGoster(
  value: number | boolean,
  t: (k: string) => string,
  unit?: string
): string {
  if (typeof value === "boolean") return value ? CHECK : CROSS;
  if (value === -1) return t("pricing_unlimited");
  if (unit) return `${value} ${t(unit)}`;
  return String(value);
}

interface PlanKarti {
  plan: Plan;
  vurgulu: boolean;
  fiyat: string;
  buton: "started" | "sales" | "current";
}

export default function PricingSayfasi() {
  const { t: tRaw } = useTranslation();
  // limitGoster string parametresi alabilsin diye sarmala
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [mevcutPlan, setMevcutPlan] = useState<Plan>("free");

  useEffect(() => {
    setMevcutPlan(getCurrentPlan());
  }, []);

  const planlar: PlanKarti[] = [
    { plan: "free",       vurgulu: false, fiyat: PRICES.free,       buton: "started" },
    { plan: "pro",        vurgulu: false, fiyat: PRICES.pro,        buton: "started" },
    { plan: "team",       vurgulu: true,  fiyat: PRICES.team,       buton: "started" },
    { plan: "enterprise", vurgulu: false, fiyat: PRICES.enterprise, buton: "sales"   },
  ];

  const planAdi = (p: Plan) =>
    ({ free: t("plan_free"), pro: t("plan_pro"), team: t("plan_team"), enterprise: t("plan_enterprise") })[p];

  // Özellik satırları
  type OzellikSatiri = {
    label: string;
    values: (string | React.ReactNode)[];
    kilitli?: boolean[];
  };

  const ozellikler: OzellikSatiri[] = [
    {
      label: t("pricing_feature_repos"),
      values: planlar.map((k) =>
        limitGoster(PLAN_LIMITS[k.plan].max_repos, t)
      ),
    },
    {
      label: t("pricing_feature_files"),
      values: planlar.map((k) =>
        limitGoster(PLAN_LIMITS[k.plan].max_files_scan, t)
      ),
    },
    {
      label: t("pricing_feature_history"),
      values: planlar.map((k) => {
        const v = PLAN_LIMITS[k.plan].history_days;
        if (v === -1) return t("pricing_unlimited");
        return `${v} ${t("pricing_days")}`;
      }),
    },
    {
      label: t("pricing_feature_dashboard"),
      values: planlar.map((k) =>
        limitGoster(PLAN_LIMITS[k.plan].dashboard_access, t)
      ),
    },
    {
      label: t("pricing_feature_github"),
      values: planlar.map((k) =>
        limitGoster(PLAN_LIMITS[k.plan].github_actions, t)
      ),
    },
    {
      label: t("pricing_feature_slack"),
      values: planlar.map((k) =>
        limitGoster(PLAN_LIMITS[k.plan].slack_notify, t)
      ),
      kilitli: planlar.map((k) => !PLAN_LIMITS[k.plan].slack_notify),
    },
    {
      label: `${t("pricing_feature_bus_factor")} ${LOCK}`,
      values: planlar.map((k) =>
        limitGoster(PLAN_LIMITS[k.plan].bus_factor, t)
      ),
      kilitli: planlar.map((k) => !PLAN_LIMITS[k.plan].bus_factor),
    },
    {
      label: `${t("pricing_feature_sprint")} ${LOCK}`,
      values: planlar.map((k) =>
        limitGoster(PLAN_LIMITS[k.plan].sprint_health, t)
      ),
      kilitli: planlar.map((k) => !PLAN_LIMITS[k.plan].sprint_health),
    },
    {
      label: `${t("pricing_feature_ai_comparison")} ${LOCK}`,
      values: planlar.map((k) =>
        limitGoster(PLAN_LIMITS[k.plan].ai_comparison, t)
      ),
      kilitli: planlar.map((k) => !PLAN_LIMITS[k.plan].ai_comparison),
    },
    {
      label: t("pricing_feature_team_members"),
      values: planlar.map((k) =>
        limitGoster(PLAN_LIMITS[k.plan].team_members, t)
      ),
    },
    {
      label: t("pricing_feature_support"),
      values: [
        t("pricing_support_community"),
        t("pricing_support_email"),
        t("pricing_support_priority"),
        t("pricing_support_sla"),
      ],
    },
  ];

  return (
    <div className="space-y-10">
      {/* Başlık */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-white">💎 {t("pricing_title")}</h1>
        <p className="text-gray-500 mt-2">{t("pricing_subtitle")}</p>
      </div>

      {/* Plan kartları */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {planlar.map((k) => {
          const isCurrent = k.plan === mevcutPlan;
          return (
            <div
              key={k.plan}
              className={`relative bg-gray-900 rounded-2xl p-6 flex flex-col gap-4 border transition-all ${
                k.vurgulu
                  ? "border-cyan-500 shadow-lg shadow-cyan-500/10"
                  : "border-gray-800"
              }`}
            >
              {/* Most Popular badge */}
              {k.vurgulu && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-cyan-500 text-gray-950 text-xs font-bold px-3 py-1 rounded-full">
                    {t("pricing_most_popular")}
                  </span>
                </div>
              )}

              <div>
                <h2 className="text-lg font-bold text-white">{planAdi(k.plan)}</h2>
                <div className="flex items-end gap-1 mt-2">
                  {k.fiyat === "?" ? (
                    <span className="text-3xl font-bold text-white">
                      {t("pricing_contact_sales").split(" ")[0]}
                    </span>
                  ) : (
                    <>
                      <span className="text-3xl font-bold text-white">${k.fiyat}</span>
                      {k.fiyat !== "0" && (
                        <span className="text-gray-500 text-sm mb-1">
                          {t("pricing_per_month")}
                        </span>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* CTA butonu */}
              {isCurrent ? (
                <div className="w-full text-center py-2 px-4 rounded-xl border border-gray-700 text-gray-500 text-sm font-medium">
                  {t("pricing_current_plan")}
                </div>
              ) : k.buton === "sales" ? (
                <Link
                  href="mailto:hello@codedna.dev"
                  className="w-full text-center py-2 px-4 rounded-xl border border-cyan-500 text-cyan-400 hover:bg-cyan-500/10 transition-colors text-sm font-medium"
                >
                  {t("pricing_contact_sales")}
                </Link>
              ) : (
                <Link
                  href="#"
                  className={`w-full text-center py-2 px-4 rounded-xl text-sm font-semibold transition-colors ${
                    k.vurgulu
                      ? "bg-cyan-500 hover:bg-cyan-400 text-gray-950"
                      : "bg-gray-800 hover:bg-gray-700 text-white"
                  }`}
                >
                  {t("pricing_get_started")}
                </Link>
              )}
            </div>
          );
        })}
      </div>

      {/* Özellik karşılaştırma tablosu */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left p-4 text-gray-500 font-medium w-1/3">
                {t("pricing_title")}
              </th>
              {planlar.map((k) => (
                <th
                  key={k.plan}
                  className={`p-4 font-bold text-center ${
                    k.vurgulu ? "text-cyan-400" : "text-white"
                  }`}
                >
                  {planAdi(k.plan)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ozellikler.map((satir, si) => (
              <tr
                key={satir.label}
                className={`border-b border-gray-800/50 last:border-0 ${
                  si % 2 === 0 ? "" : "bg-gray-800/20"
                }`}
              >
                <td className="p-4 text-gray-400">{satir.label}</td>
                {satir.values.map((v, vi) => {
                  const kilitli = satir.kilitli?.[vi] ?? false;
                  const isCheck = v === CHECK;
                  const isCross = v === CROSS;
                  return (
                    <td
                      key={vi}
                      className={`p-4 text-center font-medium ${
                        isCheck
                          ? "text-green-400"
                          : isCross || kilitli
                          ? "text-gray-700"
                          : planlar[vi].vurgulu
                          ? "text-cyan-300"
                          : "text-gray-300"
                      }`}
                    >
                      {v}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-center text-xs text-gray-700">
        {t("pricing_footer_note")}
      </p>
    </div>
  );
}
