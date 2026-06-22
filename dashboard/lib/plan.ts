/**
 * CodeDNA plan sistemi — özellik kısıtları ve plan yönetimi.
 */

export type Plan = "free" | "pro" | "team" | "enterprise";

export interface PlanLimits {
  max_repos: number;        // -1 = sınırsız
  max_files_scan: number;   // -1 = sınırsız
  history_days: number;     // -1 = sınırsız
  dashboard_access: boolean;
  github_actions: boolean;
  slack_notify: boolean;
  bus_factor: boolean;      // Faz 5
  sprint_health: boolean;   // Faz 6
  ai_comparison: boolean;   // Faz 7
  team_members: number;     // -1 = sınırsız
  interview_tool: boolean;  // Faz 8
}

export const PLAN_LIMITS: Record<Plan, PlanLimits> = {
  free: {
    max_repos: 1,
    max_files_scan: 50,
    history_days: 7,
    dashboard_access: false,
    github_actions: false,
    slack_notify: false,
    bus_factor: false,
    sprint_health: false,
    ai_comparison: false,
    team_members: 1,
    interview_tool: false,
  },
  pro: {
    max_repos: -1,
    max_files_scan: -1,
    history_days: 90,
    dashboard_access: true,
    github_actions: true,
    slack_notify: false,
    bus_factor: false,
    sprint_health: false,
    ai_comparison: false,
    team_members: 1,
    interview_tool: false,
  },
  team: {
    max_repos: -1,
    max_files_scan: -1,
    history_days: 365,
    dashboard_access: true,
    github_actions: true,
    slack_notify: true,
    bus_factor: true,
    sprint_health: true,
    ai_comparison: false,
    team_members: 10,
    interview_tool: false,
  },
  enterprise: {
    max_repos: -1,
    max_files_scan: -1,
    history_days: -1,
    dashboard_access: true,
    github_actions: true,
    slack_notify: true,
    bus_factor: true,
    sprint_health: true,
    ai_comparison: true,
    team_members: -1,
    interview_tool: true,
  },
};

const STORAGE_KEY = "codedna-plan";

/** Mevcut planı localStorage'dan oku (varsayılan: free) */
export function getCurrentPlan(): Plan {
  if (typeof window === "undefined") return "free";
  const stored = localStorage.getItem(STORAGE_KEY) as Plan | null;
  if (stored && stored in PLAN_LIMITS) return stored;
  return "free";
}

/** Planı kaydet (geliştirme/demo için) */
export function setPlan(plan: Plan): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, plan);
  }
}

/** Belirli bir özelliğin mevcut planda aktif olup olmadığını kontrol et */
export function isFeatureAvailable(
  feature: keyof PlanLimits,
  plan: Plan = getCurrentPlan()
): boolean {
  const limits = PLAN_LIMITS[plan];
  const value = limits[feature];
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  return false;
}

/** Planın yükseltme gerektirip gerektirmediğini kontrol et */
export function needsUpgrade(
  feature: keyof PlanLimits,
  plan: Plan = getCurrentPlan()
): boolean {
  return !isFeatureAvailable(feature, plan);
}

/** Bir özellik için minimum gereken planı döndür */
export function minimumPlanFor(feature: keyof PlanLimits): Plan {
  const sirali: Plan[] = ["free", "pro", "team", "enterprise"];
  for (const plan of sirali) {
    const value = PLAN_LIMITS[plan][feature];
    if (typeof value === "boolean" && value) return plan;
    if (typeof value === "number" && value !== 0) return plan;
  }
  return "enterprise";
}
