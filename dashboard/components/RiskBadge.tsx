"use client";

import { useTranslation } from "@/lib/i18n";

/** Displays risk level as a colored badge */
export function RiskBadge({
  risk,
  size = "md",
}: {
  risk: string | null | undefined;
  size?: "sm" | "md" | "lg";
}) {
  const { t } = useTranslation();

  const colorMap: Record<string, string> = {
    HIGH:    "bg-red-500/20 text-red-400 border border-red-500/30",
    MEDIUM:  "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
    LOW:     "bg-green-500/20 text-green-400 border border-green-500/30",
    UNKNOWN: "bg-gray-500/20 text-gray-400 border border-gray-500/30",
  };

  const sizeMap = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-3 py-1 text-sm",
    lg: "px-4 py-1.5 text-base",
  };

  const normalize = (r: string): string => {
    const map: Record<string, string> = {
      // English keys
      HIGH: "risk_high", MEDIUM: "risk_medium",
      LOW: "risk_low", UNKNOWN: "risk_unknown",
      // Turkish legacy keys (in case old API response slips through)
      YÜKSEK: "risk_high", ORTA: "risk_medium",
      DÜŞÜK: "risk_low", BİLİNMİYOR: "risk_unknown",
    };
    return map[r.toUpperCase()] ?? "risk_unknown";
  };

  const upper = risk?.toUpperCase() ?? "UNKNOWN";
  const color = colorMap[upper] ?? colorMap["UNKNOWN"];
  const label = t(normalize(upper) as Parameters<typeof t>[0]);

  return (
    <span className={`inline-block font-semibold rounded-full ${color} ${sizeMap[size]}`}>
      {label}
    </span>
  );
}
