"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslation } from "@/lib/i18n";
import { useAuth } from "@/components/AuthProvider";
import { PLAN_LIMITS, Plan } from "@/lib/plan";

interface SubscriptionData {
  plan: string;
  subscription_status: string;
  lemonsqueezy_customer_id: string | null;
}

function PlanCard({
  plan, price, currentPlan, featured, onUpgrade, loading, t,
}: {
  plan: Plan; price: string; currentPlan: string; featured: boolean;
  onUpgrade: (p: Plan) => void; loading: boolean; t: (k: string) => string;
}) {
  const active = plan === currentPlan;
  const planName = { free: t("plan_free"), pro: t("plan_pro"), team: t("plan_team"), enterprise: t("plan_enterprise") }[plan];

  return (
    <div className={`relative bg-gray-900 rounded-2xl p-5 border flex flex-col gap-3 ${
      featured ? "border-cyan-500 shadow-lg shadow-cyan-500/10" : active ? "border-green-500/40" : "border-gray-800"
    }`}>
      {featured && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-cyan-500 text-gray-950 text-xs font-bold px-3 py-0.5 rounded-full">
            {t("pricing_most_popular")}
          </span>
        </div>
      )}
      <div>
        <h3 className="text-white font-bold text-lg">{planName}</h3>
        <div className="flex items-end gap-1">
          {price === "?" ? (
            <span className="text-2xl font-bold text-white">{t("pricing_contact_sales").split(" ")[0]}</span>
          ) : (
            <>
              <span className="text-2xl font-bold text-white">${price}</span>
              {price !== "0" && (
                <span className="text-gray-500 text-sm mb-0.5">{t("pricing_per_month")}</span>
              )}
            </>
          )}
        </div>
      </div>

      {active ? (
        <div className="w-full text-center py-2 px-3 rounded-xl border border-green-500/30 text-green-400 text-sm font-medium">
          ✓ {t("pricing_current_plan")}
        </div>
      ) : plan === "free" ? (
        <div className="w-full text-center py-2 px-3 rounded-xl border border-gray-700 text-gray-600 text-sm">—</div>
      ) : plan === "enterprise" ? (
        <a href="mailto:hello@natureco.me" className="w-full text-center py-2 px-3 rounded-xl border border-cyan-500 text-cyan-400 hover:bg-cyan-500/10 transition-colors text-sm font-medium">
          {t("pricing_contact_sales")}
        </a>
      ) : (
        <button
          onClick={() => onUpgrade(plan)} disabled={loading}
          className={`w-full py-2 px-3 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 ${
            featured ? "bg-cyan-500 hover:bg-cyan-400 text-gray-950" : "bg-gray-800 hover:bg-gray-700 text-white"
          }`}
        >
          {loading ? "..." : `💳 ${t("billing_upgrade")}`}
        </button>
      )}
    </div>
  );
}

function SubscriptionStatusBadge({ status, t }: { status: string; t: (k: string) => string }) {
  const styleMap: Record<string, string> = {
    active: "bg-green-500/20 text-green-400",
    cancelled: "bg-yellow-500/20 text-yellow-400",
    past_due: "bg-red-500/20 text-red-400",
    none: "bg-gray-500/20 text-gray-500",
  };
  const labelMap: Record<string, string> = {
    active: t("billing_status_active"),
    cancelled: t("billing_status_cancelled"),
    past_due: t("billing_status_past_due"),
    none: t("billing_status_none"),
  };
  return (
    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${styleMap[status] ?? styleMap.none}`}>
      {labelMap[status] ?? status}
    </span>
  );
}

export default function BillingPage() {
  const { t: tRaw } = useTranslation();
  const t = (k: string) => tRaw(k as Parameters<typeof tRaw>[0]);
  const { user, loading: authLoading } = useAuth();
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [checkoutError, setCheckoutError] = useState("");
  const [cancelLoading, setCancelLoading] = useState(false);

  useEffect(() => {
    fetch("/api/auth/me", { credentials: "include" })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => {
        if (d) setSubscription({ plan: d.plan, subscription_status: d.subscription_status, lemonsqueezy_customer_id: null });
      })
      .catch(() => {});
  }, [user]);

  const handleUpgrade = async (plan: Plan) => {
    setCheckoutError("");
    setCheckoutLoading(true);
    try {
      const chRes = await fetch(`/api/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ plan }),
      });
      if (!chRes.ok) {
        const err = await chRes.json();
        throw new Error(err.detail || "Could not get checkout URL.");
      }
      const data = await chRes.json();
      if (data.checkout_url) window.location.href = data.checkout_url;
    } catch (e: unknown) {
      setCheckoutError(e instanceof Error ? e.message : "Unknown error.");
    } finally {
      setCheckoutLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to cancel your subscription? You will be redirected to the Lemon Squeezy portal.")) return;
    setCancelLoading(true);
    try {
      const res = await fetch("/api/billing/customer-portal", { method: "POST", credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        if (data.url) window.location.href = data.url;
        else alert("Customer portal unavailable. Please try again later.");
      } else {
        alert("Customer portal coming soon. For now, use: codedna plan demo");
      }
    } catch (e) {
      alert("Error: " + (e instanceof Error ? e.message : "Unknown"));
    } finally {
      setCancelLoading(false);
    }
  };

  const currentPlan = subscription?.plan ?? user?.plan ?? "free";
  const subscriptionStatus = subscription?.subscription_status ?? "none";

  if (!authLoading && !user) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4">
        <p className="text-gray-500">You need to be logged in.</p>
        <Link href="/login" className="bg-cyan-500 hover:bg-cyan-400 text-gray-950 font-semibold px-5 py-2 rounded-lg transition-colors">
          {t("auth_login")}
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">💳 {t("billing_title")}</h1>
        <p className="text-gray-500 text-sm mt-1">
          {t("billing_current_plan")}: <span className="text-cyan-400 font-semibold uppercase">{currentPlan}</span>
        </p>
      </div>

      {subscriptionStatus === "cancelled" && (
        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl px-4 py-3 flex gap-2">
          <span className="text-yellow-400">⚠️</span>
          <p className="text-yellow-400/80 text-sm">{t("billing_cancelled_notice")}</p>
        </div>
      )}
      {subscriptionStatus === "past_due" && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 flex gap-2">
          <span className="text-red-400">🔴</span>
          <p className="text-red-400/80 text-sm">{t("billing_past_due_warning")}</p>
        </div>
      )}

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{t("billing_subscription_status")}</p>
          <div className="flex items-center gap-3">
            <span className="text-white font-bold text-lg uppercase">{currentPlan}</span>
            <SubscriptionStatusBadge status={subscriptionStatus} t={t} />
          </div>
        </div>
        {user && <p className="text-sm text-gray-600">{user.email}</p>}
      </div>

      {checkoutError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
          <p className="text-red-400 text-sm">⚠️ {checkoutError}</p>
          <p className="text-red-400/60 text-xs mt-1">A real Lemon Squeezy API key is required. See .env.example.</p>
        </div>
      )}

      <div>
        <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
          <span className="text-cyan-400">◈</span> {t("billing_upgrade")}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <PlanCard plan="free"       price="0"    currentPlan={currentPlan} featured={false} onUpgrade={handleUpgrade} loading={checkoutLoading} t={t} />
          <PlanCard plan="pro"        price="15"   currentPlan={currentPlan} featured={false} onUpgrade={handleUpgrade} loading={checkoutLoading} t={t} />
          <PlanCard plan="team"       price="49"   currentPlan={currentPlan} featured={true}  onUpgrade={handleUpgrade} loading={checkoutLoading} t={t} />
          <PlanCard plan="enterprise" price="?"    currentPlan={currentPlan} featured={false} onUpgrade={handleUpgrade} loading={checkoutLoading} t={t} />
        </div>
      </div>

      {subscription && subscriptionStatus === "active" && currentPlan !== "free" && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <span className="text-cyan-400">◈</span> Subscription Details
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wider">Plan</p>
              <p className="text-white font-semibold uppercase mt-0.5">{currentPlan}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs uppercase tracking-wider">Status</p>
              <div className="mt-0.5"><SubscriptionStatusBadge status={subscriptionStatus} t={t} /></div>
            </div>
            {subscription?.lemonsqueezy_customer_id && (
              <div className="sm:col-span-2">
                <p className="text-gray-500 text-xs uppercase tracking-wider">Customer ID</p>
                <p className="text-white font-mono text-xs mt-0.5">{subscription.lemonsqueezy_customer_id}</p>
              </div>
            )}
          </div>
          <div className="pt-2 border-t border-gray-800 flex items-center justify-between">
            <p className="text-xs text-gray-500">You can cancel at any time. The current month has already been paid.</p>
            <button
              onClick={handleCancel} disabled={cancelLoading}
              className="bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 text-sm font-semibold px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
            >
              {cancelLoading ? "..." : "Cancel Subscription"}
            </button>
          </div>
        </div>
      )}

      <p className="text-center text-sm text-gray-600">
        To compare all features,{" "}
        <Link href="/pricing" className="text-cyan-400 hover:text-cyan-300 transition-colors">view the pricing page</Link>.
      </p>
    </div>
  );
}
