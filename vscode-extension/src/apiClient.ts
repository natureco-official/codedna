/**
 * CodeDNA API client — sends requests to FastAPI (codedna serve).
 * Returns null silently when the server is down, no popup spam.
 */

import * as https from "https";
import * as http from "http";
import { URL } from "url";

export interface FileAnalysisResult {
  file_path: string;
  ai_percentage: number;
  complexity_label: string;
  total_lines: number;
}

export interface RepoSummary {
  total_files: number;
  avg_ai_percentage: number | null;
  risk_level: string;
}

/**
 * Fetch JSON data from the specified endpoint.
 * Returns null on error — does not throw.
 */
async function apiFetch<T>(baseUrl: string, path: string): Promise<T | null> {
  return new Promise((resolve) => {
    try {
      const url = new URL(path, baseUrl);
      const lib = url.protocol === "https:" ? https : http;

      const req = lib.get(
        url.toString(),
        { timeout: 3000 },
        (res) => {
          let data = "";
          res.on("data", (chunk) => (data += chunk));
          res.on("end", () => {
            try {
              resolve(JSON.parse(data) as T);
            } catch {
              resolve(null);
            }
          });
        }
      );

      req.on("error", () => resolve(null));
      req.on("timeout", () => {
        req.destroy();
        resolve(null);
      });
    } catch {
      resolve(null);
    }
  });
}

/** Check whether the server is up. */
export async function checkHealth(apiUrl: string): Promise<boolean> {
  const result = await apiFetch<{ status: string }>(apiUrl, "/health");
  return result?.status === "running";
}

/** Get a general repo summary. */
export async function getRepoSummary(apiUrl: string): Promise<RepoSummary | null> {
  return apiFetch<RepoSummary>(apiUrl, "/repo/summary");
}

/**
 * Get analysis result for a specific file.
 * Filters by file path from the /repo/files endpoint.
 */
export async function getFileAnalysis(
  apiUrl: string,
  filePath: string
): Promise<FileAnalysisResult | null> {
  const result = await apiFetch<{ files: FileAnalysisResult[] }>(
    apiUrl,
    "/repo/files?max_files=500"
  );

  if (!result?.files) return null;

  // Match by full path or last two path segments
  const parts = filePath.replace(/\\/g, "/").split("/");
  const tail2 = parts.slice(-2).join("/");
  const tail1 = parts.slice(-1)[0];

  return (
    result.files.find(
      (f) =>
        f.file_path === filePath ||
        f.file_path.endsWith(tail2) ||
        f.file_path.endsWith(tail1)
    ) ?? null
  );
}
