"use client";

import { useTranslation } from "@/lib/i18n";
import { PLAN_LIMITS, Plan, getCurrentPlan } from "@/lib/plan";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

const CHECK = "✓";
const CROSS = "✗";
const LOCK = "🔒";

// Prices TRY - via Lemon Squeezy
const PRICES: Record<Plan, string> = {
  free: "0",
  pro: "400",
  team: "800",
  enterprise: "1650",
};

const PLAN_VARIANT: Record<Exclude<Plan, "free">, string> = {
  pro: "pro",
  team: "team",
  enterprise: "enterprise",
};

function showLimit(
  value: number | boolean,
  t: (k: string) => string,
  unit?: string
): string {
  if (typeof value === "boolean") return value ? CHECK : CROSS;
  if (value === -1) return t("pricing_unlimited");
  if (unit) return `${value} ${t(unit)}`;
  return String(value);
}

interface PlanCard {
  plan: Plan;
  highlighted: boolean;
  price: string;
}

export default function PricingPage() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const router = useRouter();
  const [currentPlan, setCurrentPlan] = useState<Plan>("free");
  const [loading, setLoading] = useState<Plan | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    setCurrentPlan(getCurrentPlan());
  }, []);

  const plans: PlanCard[] = [
    { plan: "free",       highlighted: false, price: PRICES.free },
    { plan: "pro",        highlighted: false, price: PRICES.pro },
    { plan: "team",       highlighted: true,  price: PRICES.team },
    { plan: "enterprise", highlighted: false, price: PRICES.enterprise },
  ];

  const planName = (p: Plan) =>
    ({ free: t("plan_free"), pro: t("plan_pro"), team: t("plan_team"), enterprise: t("plan_enterprise") })[p];

  // Redirect to Lemon Squeezy checkout
  const handleBuy = async (plan: Exclude<Plan, "free">) => {
    if (loading) return;
    setLoading(plan);
    setError("");

    try {
      // First check login - /api/auth/me works via cookie
      const meRes = await fetch("/api/auth/me", { credentials: "include" });
      if (!meRes.ok) {
        // Redirect to login if not logged in
        router.push(`/login?redirect=/pricing&plan=${plan}`);
        return;
      }

      // Checkout request - cookie sent automatically
      const response = await fetch("/api/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan }),
        credentials: "include",
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      if (data.checkout_url) {
        // Redirect to Lemon Squeezy checkout page
        window.location.href = data.checkout_url;
      } else {
        throw new Error("Could not get checkout URL");
      }
    } catch (e: any) {
      setError(e.message || "Could not open payment page");
      setLoading(null);
    }
  };

  // Feature rows
  const features = [
    {
      label: t("pricing_feature_repos"),
      values: plans.map((k) => showLimit(PLAN_LIMITS[k.plan].max_repos, t)),
    },
    {
      label: t("pricing_feature_files"),
      values: plans.map((k) => showLimit(PLAN_LIMITS[k.plan].max_files_scan, t)),
    },
    {
      label: t("pricing_feature_history"),
      values: plans.map((k) => {
        const v = PLAN_LIMITS[k.plan].history_days;
        if (v === -1) return t("pricing_unlimited");
        return `${v} ${t("pricing_days")}`;
      }),
    },
    {
      label: t("pricing_feature_dashboard"),
      values: plans.map((k) => showLimit(PLAN_LIMITS[k.plan].dashboard_access, t)),
    },
    {
      label: t("pricing_feature_github"),
      values: plans.map((k) => showLimit(PLAN_LIMITS[k.plan].github_actions, t)),
    },
    {
      label: t("pricing_feature_slack"),
      values: plans.map((k) => showLimit(PLAN_LIMITS[k.plan].slack_notify, t)),
      locked: plans.map((k) => !PLAN_LIMITS[k.plan].slack_notify),
    },
    {
      label: `${t("pricing_feature_bus_factor")} ${LOCK}`,
      values: plans.map((k) => showLimit(PLAN_LIMITS[k.plan].bus_factor, t)),
      locked: plans.map((k) => !PLAN_LIMITS[k.plan].bus_factor),
    },
    {
      label: `${t("pricing_feature_sprint")} ${LOCK}`,
      values: plans.map((k) => showLimit(PLAN_LIMITS[k.plan].sprint_health, t)),
      locked: plans.map((k) => !PLAN_LIMITS[k.plan].sprint_health),
    },
    {
      label: `${t("pricing_feature_ai_comparison")} ${LOCK}`,
      values: plans.map((k) => showLimit(PLAN_LIMITS[k.plan].ai_comparison, t)),
      locked: plans.map((k) => !PLAN_LIMITS[k.plan].ai_comparison),
    },
    {
      label: t("pricing_feature_team_members"),
      values: plans.map((k) => showLimit(PLAN_LIMITS[k.plan].team_members, t)),
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
      {/* Title */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-white">💎 {t("pricing_title")}</h1>
        <p className="text-gray-500 mt-2">{t("pricing_subtitle")}</p>
      </div>

      {/* Error message */}
      {error && (
        <div className="max-w-2xl mx-auto bg-red-500/10 border border-red-500/30 text-red-300 px-4 py-3 rounded-xl text-sm text-center">
          {error}
        </div>
      )}

      {/* Plan cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {plans.map((k) => {
          const isCurrent = k.plan === currentPlan;
          const isLoading = loading === k.plan;
          const isPaid = k.plan !== "free";
          return (
            <div
              key={k.plan}
              className={`relative bg-gray-900 rounded-2xl p-6 flex flex-col gap-4 border transition-all ${
                k.highlighted
                  ? "border-cyan-500 shadow-lg shadow-cyan-500/10"
                  : "border-gray-800"
              }`}
            >
              {k.highlighted && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-cyan-500 text-gray-950 text-xs font-bold px-3 py-1 rounded-full">
                    {t("pricing_most_popular")}
                  </span>
                </div>
              )}

              <div>
                <h2 className="text-lg font-bold text-white">{planName(k.plan)}</h2>
                <div className="flex items-end gap-1 mt-2">
                  {k.price === "?" ? (
                    <span className="text-3xl font-bold text-white">
                      {t("pricing_contact_sales").split(" ")[0]}
                    </span>
                  ) : (
                    <>
                      <span className="text-3xl font-bold text-white">₺{k.price}</span>
                      {k.price !== "0" && (
                        <span className="text-gray-500 text-sm mb-1">
                          {t("pricing_per_month")}
                        </span>
                      )}
                    </>
                  )}
                </div>
              </div>

              {/* CTA button */}
              {isCurrent ? (
                <div className="w-full text-center py-2 px-4 rounded-xl border border-gray-700 text-gray-500 text-sm font-medium">
                  {t("pricing_current_plan")}
                </div>
              ) : k.plan === "enterprise" ? (
                <a
                  href="mailto:hello@natureco.me"
                  className="w-full text-center py-2 px-4 rounded-xl border border-cyan-500 text-cyan-400 hover:bg-cyan-500/10 transition-colors text-sm font-medium"
                >
                  {t("pricing_contact_sales")}
                </a>
              ) : isPaid ? (
                <button
                  onClick={() => handleBuy(k.plan as Exclude<Plan, "free">)}
                  disabled={isLoading}
                  className={`w-full py-2 px-4 rounded-xl text-sm font-semibold transition-colors ${
                    k.highlighted
                      ? "bg-cyan-500 hover:bg-cyan-400 text-gray-950"
                      : "bg-gray-800 hover:bg-gray-700 text-white"
                  } ${isLoading ? "opacity-50 cursor-wait" : ""}`}
                >
                  {isLoading ? (
                    <span>Loading...</span>
                  ) : (
                    <>💳 {t("pricing_get_started_paid")}</>
                  )}
                </button>
              ) : (
                <button
                  onClick={() => router.push("/login?redirect=/pricing")}
                  className={`w-full py-2 px-4 rounded-xl text-sm font-semibold transition-colors ${
                    k.highlighted
                      ? "bg-cyan-500 hover:bg-cyan-400 text-gray-950"
                      : "bg-gray-800 hover:bg-gray-700 text-white"
                  }`}
                >
                  {t("pricing_get_started")}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Feature comparison table */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800">
              <th className="text-left p-4 text-gray-500 font-medium w-1/3">
                {t("pricing_title")}
              </th>
              {plans.map((k) => (
                <th
                  key={k.plan}
                  className={`p-4 font-bold text-center ${
                    k.highlighted ? "text-cyan-400" : "text-white"
                  }`}
                >
                  {planName(k.plan)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {features.map((row, ri) => (
              <tr
                key={row.label}
                className={`border-b border-gray-800/50 last:border-0 ${
                  ri % 2 === 0 ? "" : "bg-gray-800/20"
                }`}
              >
                <td className="p-4 text-gray-400">{row.label}</td>
                {row.values.map((v, vi) => {
                  const locked = row.locked?.[vi] ?? false;
                  const isCheck = v === CHECK;
                  const isCross = v === CROSS;
                  return (
                    <td
                      key={vi}
                      className={`p-4 text-center font-medium ${
                        isCheck
                          ? "text-green-400"
                          : isCross || locked
                          ? "text-gray-700"
                          : plans[vi].highlighted
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
