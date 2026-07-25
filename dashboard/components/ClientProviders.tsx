"use client";

import { I18nProvider } from "@/lib/i18n";
import { UpgradeBanner } from "./UpgradeBanner";
import { AuthProvider } from "./AuthProvider";
import { getCurrentPlan } from "@/lib/plan";
import { useState, useEffect } from "react";
import type { Plan } from "@/lib/plan";

export function ClientProviders({ children }: { children: React.ReactNode }) {
  const [plan, setPlanState] = useState<Plan>("free");

  useEffect(() => {
    setPlanState(getCurrentPlan());
  }, []);

  return (
    <I18nProvider>
      <AuthProvider>
        <UpgradeBanner plan={plan} />
        {children}
      </AuthProvider>
    </I18nProvider>
  );
}
