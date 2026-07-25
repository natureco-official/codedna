"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslation } from "@/lib/i18n";
import { useAuth } from "@/components/AuthProvider";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const { t } = useTranslation();
  const { refresh } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(""); setLoading(true);
    const result = await login(email, password);
    setLoading(false);
    if (result.success) {
      await refresh();
      router.push("/");
    } else {
      setError(result.error || t("auth_login_error"));
    }
  };

  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="text-3xl">🧬</span>
          <h1 className="text-2xl font-bold text-white mt-2">{t("auth_login")}</h1>
        </div>

        <form onSubmit={submit} className="bg-gray-900 border border-gray-800 rounded-2xl p-7 space-y-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2.5">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          <div>
            <label className="text-xs text-gray-500 mb-1.5 block">{t("auth_email")}</label>
            <input
              type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2.5 focus:outline-none focus:border-cyan-500"
              placeholder="you@company.com"
            />
          </div>

          <div>
            <label className="text-xs text-gray-500 mb-1.5 block">{t("auth_password")}</label>
            <input
              type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2.5 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <button
            type="submit" disabled={loading}
            className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-gray-950 font-semibold py-2.5 rounded-lg transition-colors"
          >
            {loading ? "..." : t("auth_login")}
          </button>
        </form>

        <p className="text-center text-sm text-gray-600 mt-4">
          {t("auth_no_account")}{" "}
          <Link href="/register" className="text-cyan-400 hover:text-cyan-300 transition-colors">
            {t("auth_register")}
          </Link>
        </p>
      </div>
    </div>
  );
}
