/**
 * CodeDNA plan system — feature restrictions and plan management.
 */

export type Plan = "free" | "pro" | "team" | "enterprise";

export interface PlanLimits {
  max_repos: number;
  max_files_scan: number;
  history_days: number;
  dashboard_access: boolean;
  github_actions: boolean;
  slack_notify: boolean;
  bus_factor: boolean;
  sprint_health: boolean;
  ai_comparison: boolean;
  team_members: number;
  interview_tool: boolean;
  protect_modules: boolean;
}

export const PLAN_LIMITS: Record<Plan, PlanLimits> = {
  free: {
    max_repos: 1,
    max_files_scan: 50,
    history_days: 7,
    dashboard_access: true,
    github_actions: false,
    slack_notify: false,
    bus_factor: false,
    sprint_health: false,
    ai_comparison: false,
    team_members: 1,
    interview_tool: false,
    protect_modules: false,
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
    protect_modules: false,
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
    protect_modules: true,
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
    protect_modules: true,
  },
};

const STORAGE_KEY = "codedna-plan";

/** Read current plan from localStorage (default: free) */
export function getCurrentPlan(): Plan {
  if (typeof window === "undefined") return "free";
  const stored = localStorage.getItem(STORAGE_KEY) as Plan | null;
  if (stored && stored in PLAN_LIMITS) return stored;
  return "free";
}

/** Save plan (for development/demo) */
export function setPlan(plan: Plan): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, plan);
  }
}

/** Check whether a feature is active on the current plan */
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

/** Check whether a plan upgrade is required */
export function needsUpgrade(
  feature: keyof PlanLimits,
  plan: Plan = getCurrentPlan()
): boolean {
  return !isFeatureAvailable(feature, plan);
}

/** Return the minimum plan required for a feature */
export function minimumPlanFor(feature: keyof PlanLimits): Plan {
  const ordered: Plan[] = ["free", "pro", "team", "enterprise"];
  for (const plan of ordered) {
    const value = PLAN_LIMITS[plan][feature];
    if (typeof value === "boolean" && value) return plan;
    if (typeof value === "number" && value !== 0) return plan;
  }
  return "enterprise";
}
