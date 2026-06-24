"use client";

import { FileScore } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

function shortPath(path: string): string {
  const parts = path.split("/");
  return parts.length > 2 ? parts.slice(-2).join("/") : path;
}

function AIProgressBar({ percentage }: { percentage: number }) {
  const color = percentage >= 70 ? "bg-red-500" : percentage >= 40 ? "bg-yellow-500" : "bg-green-500";
  const emoji = percentage >= 70 ? "🔴" : percentage >= 40 ? "🟡" : "🟢";
  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <span className="text-sm">{emoji}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-2">
        <div
          className={`${color} h-2 rounded-full transition-all`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      <span className="text-xs text-gray-400 w-10 text-right">{percentage.toFixed(0)}%</span>
    </div>
  );
}

function ComplexityBadge({ label }: { label: string }) {
  const { t } = useTranslation();

  // Normalize API value (TR or EN) → translate with t()
  const normalize = (e: string): string => {
    const map: Record<string, string> = {
      Yüksek: "complexity_high", High: "complexity_high",
      Orta: "complexity_medium", Medium: "complexity_medium",
      Düşük: "complexity_low", Low: "complexity_low",
    };
    return map[e] ?? e;
  };

  const colorMap: Record<string, string> = {
    complexity_high: "bg-red-500/20 text-red-400",
    complexity_medium: "bg-yellow-500/20 text-yellow-400",
    complexity_low: "bg-green-500/20 text-green-400",
  };

  const key = normalize(label);
  const color = colorMap[key] ?? "bg-gray-500/20 text-gray-400";
  const displayLabel = t(key as Parameters<typeof t>[0]) ?? label;

  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
      {displayLabel}
    </span>
  );
}

export function FileHeatmap({ files }: { files: FileScore[] }) {
  const { t } = useTranslation();

  if (files.length === 0) {
    return (
      <p className="text-gray-600 text-sm text-center py-8">{t("files_no_data")}</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 text-left border-b border-gray-800">
            <th className="pb-3 font-medium">{t("files_col_path")}</th>
            <th className="pb-3 font-medium">{t("files_col_ai")}</th>
            <th className="pb-3 font-medium">{t("files_col_complexity")}</th>
            <th className="pb-3 font-medium text-right">{t("files_col_lines")}</th>
            <th className="pb-3 font-medium text-right">{t("files_col_functions")}</th>
          </tr>
        </thead>
        <tbody>
          {files.map((f) => (
            <tr
              key={f.file_path}
              className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30 transition-colors"
            >
              <td className="py-3 font-mono text-xs text-gray-300 max-w-[240px]">
                <span title={f.file_path}>{shortPath(f.file_path)}</span>
              </td>
              <td className="py-3 min-w-[160px]">
                <AIProgressBar percentage={f.ai_percentage} />
              </td>
              <td className="py-3">
                <ComplexityBadge label={f.complexity_label} />
              </td>
              <td className="py-3 text-right text-gray-400">{f.total_lines}</td>
              <td className="py-3 text-right text-gray-400">{f.function_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function FileHeatmapSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
      ))}
    </div>
  );
}
