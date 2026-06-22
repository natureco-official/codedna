"use client";

import { useState } from "react";
import { useTranslation } from "@/lib/i18n";

/**
 * Dolar rakamlarının yanına konan ℹ️ tooltip'i.
 * Hover veya tıklamada formül açıklamasını gösterir.
 */
export function CostInfoTooltip() {
  const { t } = useTranslation();
  const [acik, setAcik] = useState(false);

  return (
    <span className="relative inline-flex items-center ml-1">
      <button
        onMouseEnter={() => setAcik(true)}
        onMouseLeave={() => setAcik(false)}
        onClick={() => setAcik((v) => !v)}
        className="text-gray-600 hover:text-gray-400 transition-colors text-xs leading-none"
        aria-label="Maliyet formülü hakkında bilgi"
      >
        ℹ️
      </button>

      {acik && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-72 pointer-events-none">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-3 shadow-xl text-left">
            {/* Formül özeti */}
            <p className="text-xs text-cyan-400 font-semibold mb-1">
              {t("debt_formula_summary")}
            </p>
            {/* Uyarı */}
            <p className="text-xs text-gray-400 leading-relaxed">
              {t("debt_disclaimer")}
            </p>
            {/* Ok işareti */}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-700" />
          </div>
        </div>
      )}
    </span>
  );
}
