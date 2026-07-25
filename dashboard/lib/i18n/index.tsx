"use client";

/**
 * CodeDNA i18n — global language management with React Context.
 * - Stores in localStorage with key 'codedna-lang'
 * - Default: EN, or TR if navigator.language contains 'tr'
 * - useTranslation() hook: { t, lang, setLang }
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { en, TranslationKey } from "./en";
import { tr } from "./tr";

export type Lang = "en" | "tr";

const STORAGE_KEY = "codedna-lang";
const TRANSLATIONS = { en, tr } as const;

/** Read browser language to determine initial language — default EN */
function browserLanguage(): Lang {
  if (typeof window === "undefined") return "en";
  const stored = localStorage.getItem(STORAGE_KEY) as Lang | null;
  if (stored === "en" || stored === "tr") return stored;
  // Default: English (user can switch to TR)
  return "en";
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface I18nContextValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: TranslationKey) => string;
}

const I18nContext = createContext<I18nContextValue>({
  lang: "en",
  setLang: () => {},
  t: (key) => en[key],
});

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  // Load the actual language on the client side
  useEffect(() => {
    setLangState(browserLanguage());
  }, []);

  const setLang = useCallback((newLang: Lang) => {
    setLangState(newLang);
    localStorage.setItem(STORAGE_KEY, newLang);
  }, []);

  const t = useCallback(
    (key: TranslationKey): string => {
      return TRANSLATIONS[lang][key] ?? TRANSLATIONS["en"][key] ?? key;
    },
    [lang]
  );

  return (
    <I18nContext.Provider value={{ lang, setLang, t }}>
      {children}
    </I18nContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/** Translation hook — returns { t, lang, setLang } */
export function useTranslation() {
  return useContext(I18nContext);
}
