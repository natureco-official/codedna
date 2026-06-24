"use client";

import { useTranslation, Lang } from "@/lib/i18n";

/** Language switcher for the navbar right corner */
export function LanguageSwitcher() {
  const { lang, setLang } = useTranslation();

  const languages: { code: Lang; flag: string; label: string }[] = [
    { code: "en", flag: "🇬🇧", label: "EN" },
    { code: "tr", flag: "🇹🇷", label: "TR" },
  ];

  return (
    <div className="flex items-center gap-1 text-sm">
      {languages.map((d, i) => (
        <span key={d.code} className="flex items-center gap-1">
          {i > 0 && <span className="text-gray-700">|</span>}
          <button
            onClick={() => setLang(d.code)}
            className={`flex items-center gap-1 px-1.5 py-0.5 rounded transition-colors ${
              lang === d.code
                ? "text-cyan-400 font-bold"
                : "text-gray-500 hover:text-gray-300"
            }`}
            aria-label={`Switch to ${d.label}`}
          >
            <span>{d.flag}</span>
            <span>{d.label}</span>
          </button>
        </span>
      ))}
    </div>
  );
}
