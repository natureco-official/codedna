"use client";

import Link from "next/link";
import { Plan } from "@/lib/plan";
import { useTranslation } from "@/lib/i18n";

/** Thin upgrade banner under navbar for free plan users */
export function UpgradeBanner({ plan }: { plan: Plan }) {
  const { t } = useTranslation();

  // Don't show to Pro and above users
  if (plan !== "free") return null;

  return (
    <div className="bg-amber-500/10 border-b border-amber-500/20">
      <div className="max-w-7xl mx-auto px-6 py-2 flex items-center justify-between gap-4">
        <p className="text-amber-400 text-xs flex items-center gap-2">
          <span>⚡</span>
          <span>{t("upgrade_banner")}</span>
        </p>
        <Link
          href="/pricing"
          className="text-xs font-semibold text-amber-300 hover:text-amber-200 transition-colors whitespace-nowrap"
        >
          {t("upgrade_cta")}
        </Link>
      </div>
    </div>
  );
}
