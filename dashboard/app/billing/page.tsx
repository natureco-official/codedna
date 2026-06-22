"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslation } from "@/lib/i18n";
import { useAuth } from "@/components/AuthProvider";
import { PLAN_LIMITS, Plan } from "@/lib/plan";
import { RiskBadge } from "@/components/RiskBadge";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AbonelikVeri {
  plan: string;
  subscription_status: string;
  lemonsqueezy_customer_id: string | null;
}

/** Plan kartı */
function PlanKarti({
  plan,
  fiyat,
  mevcutPlan,
  vurgulu,
  onYukselt,
  yukleniyor,
  t,
}: {
  plan: Plan;
  fiyat: string;
  mevcutPlan: string;
  vurgulu: boolean;
  onYukselt: (p: Plan) => void;
  yukleniyor: boolean;
  t: (k: string) => string;
}) {
  const aktif = plan === mevcutPlan;
  const planAdi = { free: t("plan_free"), pro: t("plan_pro"), team: t("plan_team"), enterprise: t("plan_enterprise") }[plan];

  return (
    <div className={`relative bg-gray-900 rounded-2xl p-5 border flex flex-col gap-3 ${
      vurgulu ? "border-cyan-500 shadow-lg shadow-cyan-500/10" : aktif ? "border-green-500/40" : "border-gray-800"
    }`}>
      {vurgulu && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-cyan-500 text-gray-950 text-xs font-bold px-3 py-0.5 rounded-full">
            {t("pricing_most_popular")}
          </span>
        </div>
      )}
      <div>
        <h3 className="text-white font-bold text-lg">{planAdi}</h3>
        <div className="mt-1 flex items-end gap-1">
          <span className="text-2xl font-bold text-white">${fiyat}</span>
          {fiyat !== "0" && fiyat !== "?" && (
            <span className="text-gray-500 text-sm mb-0.5">{t("pricing_per_month")}</span>
          )}
        </div>
      </div>

      {aktif ? (
        <div className="w-full text-center py-2 px-3 rounded-xl border border-green-500/30 text-green-400 text-sm font-medium">
          ✓ {t("pricing_current_plan")}
        </div>
      ) : plan === "free" ? (
        <div className="w-full text-center py-2 px-3 rounded-xl border border-gray-700 text-gray-600 text-sm">
          —
        </div>
      ) : plan === "enterprise" ? (
        <a
          href="mailto:hello@codedna.dev"
          className="w-full text-center py-2 px-3 rounded-xl border border-cyan-500 text-cyan-400 hover:bg-cyan-500/10 transition-colors text-sm font-medium"
        >
          {t("pricing_contact_sales")}
        </a>
      ) : (
        <button
          onClick={() => onYukselt(plan)}
          disabled={yukleniyor}
          className={`w-full py-2 px-3 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 ${
            vurgulu
              ? "bg-cyan-500 hover:bg-cyan-400 text-gray-950"
              : "bg-gray-800 hover:bg-gray-700 text-white"
          }`}
        >
          {yukleniyor ? "..." : t("billing_upgrade")}
        </button>
      )}
    </div>
  );
}

/** Abonelik durum badge'i */
function AbonelikDurum({ durum, t }: { durum: string; t: (k: string) => string }) {
  const stilMap: Record<string, string> = {
    active: "bg-green-500/20 text-green-400",
    cancelled: "bg-yellow-500/20 text-yellow-400",
    past_due: "bg-red-500/20 text-red-400",
    none: "bg-gray-500/20 text-gray-500",
  };
  const etiketMap: Record<string, string> = {
    active: t("billing_status_active"),
    cancelled: t("billing_status_cancelled"),
    past_due: t("billing_status_past_due"),
    none: t("billing_status_none"),
  };
  const stil = stilMap[durum] ?? stilMap.none;
  const etiket = etiketMap[durum] ?? durum;
  return (
    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${stil}`}>{etiket}</span>
  );
}

export default function BillingSayfasi() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const { kullanici, yukleniyor: authYukleniyor } = useAuth();
  const [abonelik, setAbonelik] = useState<AbonelikVeri | null>(null);
  const [checkoutYukleniyor, setCheckoutYukleniyor] = useState(false);
  const [checkoutHata, setCheckoutHata] = useState("");

  useEffect(() => {
    // Cookie üzerinden abonelik bilgisi al
    fetch("/api/auth/me", { credentials: "include" })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => {
        if (d) {
          setAbonelik({
            plan: d.plan,
            subscription_status: d.subscription_status,
            lemonsqueezy_customer_id: null,
          });
        }
      })
      .catch(() => {});
  }, [kullanici]);

  const handleYukselt = async (plan: Plan) => {
    setCheckoutHata("");
    setCheckoutYukleniyor(true);

    try {
      // Cookie'den token okumak için /api/auth route'unu kullan
      const meRes = await fetch("/api/auth/me", { credentials: "include" });
      if (!meRes.ok) throw new Error("Giriş yapınız.");

      // FastAPI'den checkout URL al (token cookie'de, ama burada API proxy kullanıyoruz)
      const chRes = await fetch(`/api/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ plan }),
      });

      if (!chRes.ok) {
        const err = await chRes.json();
        throw new Error(err.detail || "Checkout URL alınamadı.");
      }

      const veri = await chRes.json();
      if (veri.checkout_url) {
        window.location.href = veri.checkout_url;
      }
    } catch (e: unknown) {
      setCheckoutHata(e instanceof Error ? e.message : "Bilinmeyen hata.");
    } finally {
      setCheckoutYukleniyor(false);
    }
  };

  const mevcutPlan = abonelik?.plan ?? kullanici?.plan ?? "free";
  const abonelikDurum = abonelik?.subscription_status ?? "none";

  if (!authYukleniyor && !kullanici) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4">
        <p className="text-gray-500">{t("auth_login")} yapmanız gerekiyor.</p>
        <Link href="/login" className="bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold px-5 py-2 rounded-lg transition-colors">
          {t("auth_login")}
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Başlık */}
      <div>
        <h1 className="text-2xl font-bold text-white">💳 {t("billing_title")}</h1>
        <p className="text-gray-500 text-sm mt-1">{t("billing_current_plan")}: <span className="text-cyan-400 font-semibold uppercase">{mevcutPlan}</span></p>
      </div>

      {/* Abonelik durum uyarıları */}
      {abonelikDurum === "cancelled" && (
        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl px-4 py-3 flex gap-2">
          <span className="text-yellow-400">⚠️</span>
          <p className="text-yellow-400/80 text-sm">{t("billing_cancelled_notice")}</p>
        </div>
      )}
      {abonelikDurum === "past_due" && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 flex gap-2">
          <span className="text-red-400">🔴</span>
          <p className="text-red-400/80 text-sm">{t("billing_past_due_warning")}</p>
        </div>
      )}

      {/* Mevcut durum kartı */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{t("billing_subscription_status")}</p>
          <div className="flex items-center gap-3">
            <span className="text-white font-bold text-lg uppercase">{mevcutPlan}</span>
            <AbonelikDurum durum={abonelikDurum} t={t} />
          </div>
        </div>
        {kullanici && (
          <p className="text-sm text-gray-600">{kullanici.email}</p>
        )}
      </div>

      {/* Checkout hatası */}
      {checkoutHata && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
          <p className="text-red-400 text-sm">⚠️ {checkoutHata}</p>
          <p className="text-red-400/60 text-xs mt-1">
            Gerçek Lemon Squeezy API anahtarı gereklidir. .env.example dosyasına bakın.
          </p>
        </div>
      )}

      {/* Plan kartları */}
      <div>
        <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
          <span className="text-cyan-400">◈</span> {t("billing_upgrade")}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <PlanKarti plan="free"       fiyat="0"  mevcutPlan={mevcutPlan} vurgulu={false} onYukselt={handleYukselt} yukleniyor={checkoutYukleniyor} t={t} />
          <PlanKarti plan="pro"        fiyat="19" mevcutPlan={mevcutPlan} vurgulu={false} onYukselt={handleYukselt} yukleniyor={checkoutYukleniyor} t={t} />
          <PlanKarti plan="team"       fiyat="49" mevcutPlan={mevcutPlan} vurgulu={true}  onYukselt={handleYukselt} yukleniyor={checkoutYukleniyor} t={t} />
          <PlanKarti plan="enterprise" fiyat="?"  mevcutPlan={mevcutPlan} vurgulu={false} onYukselt={handleYukselt} yukleniyor={checkoutYukleniyor} t={t} />
        </div>
      </div>

      {/* Pricing karşılaştırması linki */}
      <p className="text-center text-sm text-gray-600">
        Tüm özellikleri karşılaştırmak için{" "}
        <Link href="/pricing" className="text-cyan-400 hover:text-cyan-300 transition-colors">
          fiyatlandırma sayfasına
        </Link>{" "}
        bakın.
      </p>
    </div>
  );
}
