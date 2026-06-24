"use client";

import Link from "next/link";
import { Plan, PlanLimits, isFeatureAvailable, minimumPlanFor } from "@/lib/plan";
import { useTranslation } from "@/lib/i18n";

interface FeatureGateProps {
  /** Feature key to check */
  feature: keyof PlanLimits;
  /** User's current plan */
  plan: Plan;
  /** Content shown when the feature is available */
  children: React.ReactNode;
}

/**
 * Feature access gate.
 *
 * Usage:
 * ```tsx
 * <FeatureGate feature="bus_factor" plan={currentPlan}>
 *   <BusFactorWidget />
 * </FeatureGate>
 * ```
 *
 * For locked features: 🔒 "Available on X plan" + "Upgrade" button
 */
export function FeatureGate({ feature, plan, children }: FeatureGateProps) {
  const { t } = useTranslation();

  if (isFeatureAvailable(feature, plan)) {
    return <>{children}</>;
  }

  const requiredPlan = minimumPlanFor(feature);
  const planName =
    requiredPlan === "pro"
      ? t("plan_pro")
      : requiredPlan === "team"
      ? t("plan_team")
      : t("plan_enterprise");

  // Replace "{plan}" placeholder with actual plan name
  const message = t("feature_gate_locked").replace("{plan}", planName);

  return (
    <div className="flex flex-col items-center justify-center gap-3 p-8 bg-gray-900/50 border border-gray-800 border-dashed rounded-xl text-center">
      <span className="text-3xl">🔒</span>
      <p className="text-gray-400 text-sm">{message}</p>
      <Link
        href="/pricing"
        className="inline-block bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
      >
        {t("feature_gate_upgrade")}
      </Link>
    </div>
  );
}
