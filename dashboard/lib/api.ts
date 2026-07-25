/**
 * CodeDNA API client — all fetch calls are centrally managed here.
 */

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Type definitions (match FastAPI responses 1:1)
// ---------------------------------------------------------------------------

export interface RepoSummary {
  total_commits: number;
  avg_ai_score: number | null;
  avg_ai_percentage: number | null;
  risk_level: "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN";
  commits_with_understanding: number;
  avg_understanding_score: number | null;
}

export interface FileScore {
  file_path: string;
  ai_probability: number;
  ai_percentage: number;
  complexity_score: number;
  complexity_label: "Low" | "Medium" | "High";
  comment_ratio: number;
  avg_function_length: number;
  single_commit_ratio: number;
  total_lines: number;
  function_count: number;
}

export interface FilesResponse {
  total_files: number;
  avg_ai_score: number;
  files: FileScore[];
}

export interface Commit {
  commit_hash: string;
  short_hash: string;
  author: string | null;
  timestamp: number | null;
  date: string | null;
  files_changed: number;
  understanding_score: number | null;
  created_at: string | null;
}

export interface CommitListResponse {
  total: number;
  commits: Commit[];
}

export interface CommitFileScore {
  file_path: string;
  ai_probability: number | null;
  complexity_score: number | null;
  comment_ratio: number | null;
  understanding_score: number | null;
}

export interface CommitDetail {
  commit_hash: string;
  author: string | null;
  date: string | null;
  files_changed: number;
  understanding_score: number | null;
  files: CommitFileScore[];
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/** Fetch data from the given endpoint, throw on error */
async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    // Disable cache to always get fresh data
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${path}`);
  }

  return res.json() as Promise<T>;
}

export async function getRepoSummary(): Promise<RepoSummary> {
  return apiFetch<RepoSummary>("/repo/summary");
}

export async function getRepoFiles(minRisk = 0): Promise<FilesResponse> {
  return apiFetch<FilesResponse>(`/repo/files?min_risk=${minRisk}`);
}

export async function getCommits(limit = 20): Promise<CommitListResponse> {
  return apiFetch<CommitListResponse>(`/commits?limit=${limit}`);
}

export async function getCommitDetail(hash: string): Promise<CommitDetail> {
  return apiFetch<CommitDetail>(`/commits/${hash}`);
}
