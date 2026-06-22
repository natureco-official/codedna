"use client";

import { useTranslation, Lang } from "@/lib/i18n";

/** Navbar sağ köşesine giden dil değiştirici */
export function LanguageSwitcher() {
  const { lang, setLang } = useTranslation();

  const diller: { kod: Lang; bayrak: string; etiket: string }[] = [
    { kod: "en", bayrak: "🇬🇧", etiket: "EN" },
    { kod: "tr", bayrak: "🇹🇷", etiket: "TR" },
  ];

  return (
    <div className="flex items-center gap-1 text-sm">
      {diller.map((d, i) => (
        <span key={d.kod} className="flex items-center gap-1">
          {i > 0 && <span className="text-gray-700">|</span>}
          <button
            onClick={() => setLang(d.kod)}
            className={`flex items-center gap-1 px-1.5 py-0.5 rounded transition-colors ${
              lang === d.kod
                ? "text-cyan-400 font-bold"
                : "text-gray-500 hover:text-gray-300"
            }`}
            aria-label={`Switch to ${d.etiket}`}
          >
            <span>{d.bayrak}</span>
            <span>{d.etiket}</span>
          </button>
        </span>
      ))}
    </div>
  );
}
