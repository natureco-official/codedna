"use client";

import { useTranslation } from "@/lib/i18n";

/** Risk seviyesini renkli badge olarak gösterir */
export function RiskBadge({
  risk,
  size = "md",
}: {
  risk: string | null | undefined;
  size?: "sm" | "md" | "lg";
}) {
  const { t } = useTranslation();

  // API'den gelen değer (TR veya EN) → normalize et → t() ile çevir
  const renkMap: Record<string, string> = {
    HIGH:    "bg-red-500/20 text-red-400 border border-red-500/30",
    MEDIUM:  "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
    LOW:     "bg-green-500/20 text-green-400 border border-green-500/30",
    UNKNOWN: "bg-gray-500/20 text-gray-400 border border-gray-500/30",
    // API Türkçe döndürüyor — her ikisini destekle
    YÜKSEK:    "bg-red-500/20 text-red-400 border border-red-500/30",
    ORTA:      "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
    DÜŞÜK:     "bg-green-500/20 text-green-400 border border-green-500/30",
    BİLİNMİYOR: "bg-gray-500/20 text-gray-400 border border-gray-500/30",
  };

  const boyutMap = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-3 py-1 text-sm",
    lg: "px-4 py-1.5 text-base",
  };

  const normalize = (r: string): string => {
    const map: Record<string, string> = {
      YÜKSEK: "risk_high", ORTA: "risk_medium",
      DÜŞÜK: "risk_low", BİLİNMİYOR: "risk_unknown",
      HIGH: "risk_high", MEDIUM: "risk_medium",
      LOW: "risk_low", UNKNOWN: "risk_unknown",
    };
    return map[r.toUpperCase()] ?? "risk_unknown";
  };

  const upper = risk?.toUpperCase() ?? "BİLİNMİYOR";
  const renk = renkMap[upper] ?? renkMap["BİLİNMİYOR"];
  const label = t(normalize(upper) as Parameters<typeof t>[0]);

  return (
    <span className={`inline-block font-semibold rounded-full ${renk} ${boyutMap[size]}`}>
      {label}
    </span>
  );
}
