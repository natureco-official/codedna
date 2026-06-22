"use client";

import { useTranslation } from "@/lib/i18n";

type Section = "page" | "commits" | "chart" | "chart_sub";

/** Ana sayfadaki çevrilebilir başlık/alt başlık bileşeni */
export function OverviewTitles({ section }: { section: Section }) {
  const { t } = useTranslation();

  if (section === "page") {
    return (
      <div>
        <h1 className="text-2xl font-bold text-white">
          🧬 {t("overview_title")}
        </h1>
        <p className="text-gray-500 text-sm mt-1">{t("overview_subtitle")}</p>
      </div>
    );
  }

  if (section === "commits") {
    return (
      <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
        <span className="text-cyan-400">◈</span> {t("overview_recent_commits")}
        <span className="text-gray-600 text-xs font-normal ml-auto">
          {t("overview_click_hint")}
        </span>
      </h2>
    );
  }

  if (section === "chart") {
    return (
      <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
        <span className="text-cyan-400">◈</span> {t("chart_title")}
      </h2>
    );
  }

  // chart_sub
  return (
    <p className="text-xs text-gray-600 mt-3 text-center">
      {t("chart_subtitle")}
    </p>
  );
}
