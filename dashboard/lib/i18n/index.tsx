"use client";

/**
 * CodeDNA i18n — React Context ile global dil yönetimi.
 * - localStorage'da 'codedna-lang' anahtarı ile saklar
 * - Varsayılan: navigator.language 'tr' içeriyorsa TR, diğer her şey EN
 * - useTranslation() hook'u: { t, lang, setLang }
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

/** Tarayıcı dilini okuyarak başlangıç dilini belirle */
function tarayiciDili(): Lang {
  if (typeof window === "undefined") return "en";
  const kayitli = localStorage.getItem(STORAGE_KEY) as Lang | null;
  if (kayitli === "en" || kayitli === "tr") return kayitli;
  return navigator.language.toLowerCase().startsWith("tr") ? "tr" : "en";
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

  // İstemci tarafında gerçek dili yükle
  useEffect(() => {
    setLangState(tarayiciDili());
  }, []);

  const setLang = useCallback((yeniDil: Lang) => {
    setLangState(yeniDil);
    localStorage.setItem(STORAGE_KEY, yeniDil);
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

/** Çeviri hook'u — { t, lang, setLang } döndürür */
export function useTranslation() {
  return useContext(I18nContext);
}
