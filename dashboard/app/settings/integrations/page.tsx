"use client";

import { useState, useEffect } from "react";
import { useTranslation } from "@/lib/i18n";
import { getCurrentPlan } from "@/lib/plan";
import { FeatureGate } from "@/components/FeatureGate";
import { ErrorBanner } from "@/components/ErrorBanner";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface JiraConfig {
  webhook_url: string;
  secret_exists: boolean;
  secret_length: number;
  supported_events: string[];
}

export default function IntegrationsPage() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const [plan, setPlan] = useState<"free" | "pro" | "team" | "enterprise">("free");
  const [config, setConfig] = useState<JiraConfig | null>(null);
  const [copied, setCopied] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [newSecret, setNewSecret] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setPlan(getCurrentPlan());
    fetch(`${API_URL}/integrations/jira/config`)
      .then((r) => r.ok ? r.json() : Promise.reject())
      .then((d) => {
        // Normalize field names (legacy API may use Turkish keys)
        setConfig({
          webhook_url: d.webhook_url,
          secret_exists: d.secret_exists ?? d.secret_mevcut ?? false,
          secret_length: d.secret_length ?? d.secret_uzunluk ?? 0,
          supported_events: d.supported_events ?? d.desteklenen_eventler ?? [],
        });
      })
      .catch(() => setError(true));
  }, []);

  const webhookUrl = `${API_URL}/integrations/jira/webhook`;

  const copyUrl = () => {
    navigator.clipboard.writeText(webhookUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const rotateSecret = async () => {
    setRotating(true);
    setNewSecret(null);
    try {
      const res = await fetch(`${API_URL}/integrations/jira/rotate-secret`, { method: "POST" });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setNewSecret(data.secret);
      // Refresh config
      const configRes = await fetch(`${API_URL}/integrations/jira/config`);
      if (configRes.ok) {
        const d = await configRes.json();
        setConfig({
          webhook_url: d.webhook_url,
          secret_exists: d.secret_exists ?? d.secret_mevcut ?? false,
          secret_length: d.secret_length ?? d.secret_uzunluk ?? 0,
          supported_events: d.supported_events ?? d.desteklenen_eventler ?? [],
        });
      }
    } catch {
      setError(true);
    } finally {
      setRotating(false);
    }
  };

  return (
    <FeatureGate feature="sprint_health" plan={plan}>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">⚙️ {t("integration_jira_title")}</h1>
          <p className="text-gray-500 text-sm mt-1">{t("integration_jira_subtitle")}</p>
        </div>

        {error && <ErrorBanner />}

        {/* Webhook URL card */}
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
              onClick={copyUrl}
              className={`shrink-0 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${
                copied
                  ? "bg-green-500/20 text-green-400 border border-green-500/30"
                  : "bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700"
              }`}
            >
              {copied ? t("integration_webhook_copied") : t("integration_webhook_copy")}
            </button>
          </div>

          <p className="text-xs text-gray-600">
            Add this URL to the webhook section in your Jira project settings.
            Supported events:{" "}
            <code className="text-cyan-700">
              {config?.supported_events.join(", ") ?? "sprint_started, sprint_closed"}
            </code>
          </p>

          <div className="flex items-start gap-2 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
            <span className="text-amber-400 mt-0.5">⚠️</span>
            <p className="text-xs text-amber-400/80">{t("integration_signature_required")}</p>
          </div>
        </div>

        {/* Secret management */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <span className="text-cyan-400">◈</span> Webhook Secret
          </h2>

          <div className="flex items-center gap-3">
            <div className="flex-1 flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  config?.secret_exists ? "bg-green-500" : "bg-gray-600"
                }`}
              />
              <span className="text-sm text-gray-400">
                {config?.secret_exists
                  ? `${t("integration_status_active")} (${config.secret_length} characters)`
                  : t("integration_status_none")}
              </span>
            </div>
            <button
              onClick={rotateSecret}
              disabled={rotating}
              className="bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-gray-300 border border-gray-700 text-sm font-medium px-4 py-2 rounded-lg transition-colors"
            >
              {rotating ? "..." : t("integration_rotate_secret")}
            </button>
          </div>

          {/* Show new secret once */}
          {newSecret && (
            <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
              <p className="text-amber-400 text-xs font-semibold mb-1">
                ⚠️ Copy this secret now — it will not be shown again.
              </p>
              <code className="text-amber-300 text-xs font-mono break-all">{newSecret}</code>
            </div>
          )}
        </div>

        {/* Connection status */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("integration_status")}
          </h2>
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-gray-600" />
            <span className="text-sm text-gray-500">{t("integration_status_none")}</span>
            <span className="text-xs text-gray-700 ml-2">
              — Will appear here once the first webhook arrives
            </span>
          </div>
        </div>
      </div>
    </FeatureGate>
  );
}
