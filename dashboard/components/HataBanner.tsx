"use client";

import { useTranslation } from "@/lib/i18n";

/** API bağlantı hatası durumunda gösterilen banner */
export function HataBanner({ mesaj }: { mesaj?: string }) {
  const { t } = useTranslation();

  return (
    <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-4 flex items-start gap-3">
      <span className="text-red-400 text-lg mt-0.5">⚠️</span>
      <div>
        <p className="text-red-400 font-semibold text-sm">
          {t("error_api").split("—")[0].trim()}
        </p>
        <p className="text-red-300/70 text-xs mt-0.5">
          {mesaj ?? t("error_api")}
        </p>
      </div>
    </div>
  );
}
