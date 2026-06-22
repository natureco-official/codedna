"use client";

import Link from "next/link";
import { Plan, PlanLimits, isFeatureAvailable, minimumPlanFor } from "@/lib/plan";
import { useTranslation } from "@/lib/i18n";

interface FeatureGateProps {
  /** Kontrol edilecek özellik anahtarı */
  feature: keyof PlanLimits;
  /** Kullanıcının mevcut planı */
  plan: Plan;
  /** Özellik kullanılabilirse gösterilecek içerik */
  children: React.ReactNode;
}

/**
 * Özellik erişim kapısı.
 *
 * Kullanımı:
 * ```tsx
 * <FeatureGate feature="bus_factor" plan={currentPlan}>
 *   <BusFactorWidget />
 * </FeatureGate>
 * ```
 *
 * Kilitli özelliklerde: 🔒 "Bu özellik X planında mevcut" + "Planı Yükselt" butonu
 */
export function FeatureGate({ feature, plan, children }: FeatureGateProps) {
  const { t } = useTranslation();

  if (isFeatureAvailable(feature, plan)) {
    return <>{children}</>;
  }

  // Hangi plan gerekiyor?
  const gerekliPlan = minimumPlanFor(feature);
  const planAdi =
    gerekliPlan === "pro"
      ? t("plan_pro")
      : gerekliPlan === "team"
      ? t("plan_team")
      : t("plan_enterprise");

  // "{plan}" placeholder'ını gerçek plan adıyla değiştir
  const mesaj = t("feature_gate_locked").replace("{plan}", planAdi);

  return (
    <div className="flex flex-col items-center justify-center gap-3 p-8 bg-gray-900/50 border border-gray-800 border-dashed rounded-xl text-center">
      <span className="text-3xl">🔒</span>
      <p className="text-gray-400 text-sm">{mesaj}</p>
      <Link
        href="/pricing"
        className="inline-block bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold text-sm px-4 py-2 rounded-lg transition-colors"
      >
        {t("feature_gate_upgrade")}
      </Link>
    </div>
  );
}
