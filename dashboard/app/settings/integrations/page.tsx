"use client";

import { useState, useEffect } from "react";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { HataBanner } from "@/components/HataBanner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface JiraKonfig {
  webhook_url: string;
  secret_mevcut: boolean;
  secret_uzunluk: number;
  desteklenen_eventler: string[];
}

export default function EntegrasyonlarSayfasi() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free" | "pro" | "team" | "enterprise">("free");
  const [konfig, setKonfig] = useState<JiraKonfig | null>(null);
  const [kopyalandi, setKopyalandi] = useState(false);
  const [yenileniyor, setYenileniyor] = useState(false);
  const [yeniSecret, setYeniSecret] = useState<string | null>(null);
  const [hata, setHata] = useState(false);

  useEffect(() => {
    setPlan(getCurrentPlan());
    fetch(`${API_URL}/integrations/jira/config`)
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then(setKonfig)
      .catch(() => setHata(true));
  }, []);

  const webhookUrl = `${API_URL}/integrations/jira/webhook`;

  const kopyala = () => {
    navigator.clipboard.writeText(webhookUrl).then(() => {
      setKopyalandi(true);
      setTimeout(() => setKopyalandi(false), 2000);
    });
  };

  const secretYenile = async () => {
    setYenileniyor(true);
    setYeniSecret(null);
    try {
      const res = await fetch(`${API_URL}/integrations/jira/rotate-secret`, { method: "POST" });
      if (!res.ok) throw new Error();
      const veri = await res.json();
      setYeniSecret(veri.secret);
      // Konfigi yenile
      const konfRes = await fetch(`${API_URL}/integrations/jira/config`);
      if (konfRes.ok) setKonfig(await konfRes.json());
    } catch {
      setHata(true);
    } finally {
      setYenileniyor(false);
    }
  };

  return (
    <FeatureGate feature="sprint_health" plan={plan}>
      <div className="space-y-6">
        {/* Başlık */}
        <div>
          <h1 className="text-2xl font-bold text-white">⚙️ {t("integration_jira_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("integration_jira_subtitle")}</p>
        </div>

        {hata && <HataBanner />}

        {/* Webhook URL kartı */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("integration_webhook_url")}
          </h2>

          <div className="flex gap-2">
            <input
              readOnly
              value={webhookUrl}
              className="flex-1 bg-gray-800 border border-gray-700 text-gray-300 text-sm font-mono rounded-lg px-3 py-2 focus:outline-none"
            />
            <button
              onClick={kopyala}
              className={`shrink-0 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                kopyalandi
                  ? "bg-green-500/20 text-green-400 border border-green-500/30"
                  : "bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700"
              }`}
            >
              {kopyalandi ? t("integration_webhook_copied") : t("integration_webhook_copy")}
            </button>
          </div>

          <p className="text-xs text-gray-600">
            Bu URL&apos;yi Jira proje ayarlarındaki webhook bölümüne ekleyin.
            Desteklenen event&apos;ler:{" "}
            <code className="text-cyan-700">
              {konfig?.desteklenen_eventler.join(", ") ?? "sprint_started, sprint_closed"}
            </code>
          </p>
          {/* Güvenlik uyarısı */}
          <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
            <span className="text-amber-400 mt-0.5">⚠️</span>
            <p className="text-xs text-amber-400/80">{t("integration_signature_required")}</p>
          </div>
        </div>

        {/* Secret yönetimi */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <span className="text-cyan-400">◈</span> Webhook Secret
          </h2>

          <div className="flex items-center gap-3">
            <div className="flex-1 flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  konfig?.secret_mevcut ? "bg-green-500" : "bg-gray-600"
                }`}
              />
              <span className="text-sm text-gray-400">
                {konfig?.secret_mevcut
                  ? `${t("integration_status_active")} (${konfig.secret_uzunluk} karakter)`
                  : t("integration_status_none")}
              </span>
            </div>
            <button
              onClick={secretYenile}
              disabled={yenileniyor}
              className="bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-gray-300 border border-gray-700 text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              {yenileniyor ? "..." : t("integration_rotate_secret")}
            </button>
          </div>

          {/* Yeni secret bir kez göster */}
          {yeniSecret && (
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
              <p className="text-amber-400 text-xs font-semibold mb-1">
                ⚠️ Bu secret&apos;ı şimdi kopyalayın — bir daha gösterilmeyecek.
              </p>
              <code className="text-amber-300 text-xs font-mono break-all">{yeniSecret}</code>
            </div>
          )}
        </div>

        {/* Bağlantı durumu */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("integration_status")}
          </h2>
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-gray-600" />
            <span className="text-sm text-gray-500">{t("integration_status_none")}</span>
            <span className="text-xs text-gray-700 ml-2">
              — İlk webhook geldiğinde burada görünecek
            </span>
          </div>
        </div>
      </div>
    </FeatureGate>
  );
}
