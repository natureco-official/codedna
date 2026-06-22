"use client";

import Link from "next/link";
import { useTranslation } from "@/lib/i18n";
import { useAuth } from "./AuthProvider";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { useRouter } from "next/navigation";

export function NavClient() {
  const { t } = useTranslation();
  const { kullanici, cikis } = useAuth();
  const router = useRouter();

  const handleCikis = async () => {
    await cikis();
    router.push("/login");
  };

  return (
    <div className="flex items-center gap-4">
      <Link href="/" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">{t("nav_dashboard")}</Link>
      <Link href="/files" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">{t("nav_files")}</Link>
      <Link href="/commits" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">{t("nav_commits")}</Link>
      <Link href="/bus-factor" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">🚌</Link>
      <Link href="/debt" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">💰</Link>
      <Link href="/sprints" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">🏃</Link>
      <Link href="/ai-compare" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">🤖</Link>
      <Link href="/onboarding" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">🚀</Link>
      <Link href="/settings/integrations" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">⚙️</Link>
      <Link href="/protected" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">🛡️</Link>
      <Link href="/interview" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">🎯</Link>
      <Link href="/pricing" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm font-medium">{t("nav_pricing")}</Link>
      <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer" className="text-gray-600 hover:text-gray-400 transition-colors text-xs">API ↗</a>

      {/* Auth durumu */}
      {kullanici ? (
        <div className="flex items-center gap-3 border-l border-gray-800 pl-4 ml-1">
          <Link href="/billing" className="flex items-center gap-1.5">
            <span className="text-xs text-gray-500">{kullanici.email.split("@")[0]}</span>
            <span className="text-xs bg-cyan-500/20 text-cyan-400 px-1.5 py-0.5 rounded font-medium uppercase">
              {kullanici.plan}
            </span>
          </Link>
          <button onClick={handleCikis} className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
            {t("auth_logout")}
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-3 border-l border-gray-800 pl-4 ml-1">
          <Link href="/login" className="text-gray-400 hover:text-cyan-400 transition-colors text-sm">{t("auth_login")}</Link>
          <Link href="/register" className="bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold text-xs px-3 py-1.5 rounded-lg transition-colors">
            {t("auth_register")}
          </Link>
        </div>
      )}

      <LanguageSwitcher />
    </div>
  );
}
