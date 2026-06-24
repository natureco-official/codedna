"use client";

import { useState } from "react";
import { useTranslation } from "@/lib/i18n";

/**
 * ℹ️ tooltip placed next to dollar amounts.
 * Shows formula explanation on hover or click.
 */
export function CostInfoTooltip() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-flex items-center ml-1">
      <button
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onClick={() => setOpen((v) => !v)}
        className="text-gray-600 hover:text-gray-400 transition-colors text-xs leading-none"
        aria-label="Cost formula information"
      >
        ℹ️
      </button>

      {open && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-72 pointer-events-none">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-3 shadow-xl text-left">
            {/* Formula summary */}
            <p className="text-xs text-cyan-400 font-semibold mb-1">
              {t("debt_formula_summary")}
            </p>
            {/* Warning */}
            <p className="text-xs text-gray-400 leading-relaxed">
              {t("debt_disclaimer")}
            </p>
            {/* Arrow indicator */}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-700" />
          </div>
        </div>
      )}
    </span>
  );
}
