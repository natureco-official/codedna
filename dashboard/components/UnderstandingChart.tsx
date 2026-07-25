"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { Commit } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

interface ChartDataPoint {
  hash: string;
  score: number;
  date: string;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: ChartDataPoint }>;
}) {
  const { t } = useTranslation();
  if (!active || !payload?.length) return null;
  const item = payload[0];
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-cyan-400 font-mono">{item.payload.hash}</p>
      <p className="text-gray-300">{item.payload.date}</p>
      <p className="text-white font-semibold mt-1">
        {t("chart_tooltip_understanding")}: {item.value.toFixed(1)}/5
      </p>
    </div>
  );
}

export function UnderstandingChart({ commits }: { commits: Commit[] }) {
  const { t } = useTranslation();

  const data: ChartDataPoint[] = commits
    .filter((c) => c.understanding_score != null)
    .reverse()
    .map((c) => ({
      hash: c.short_hash,
      score: c.understanding_score!,
      date: c.date ?? "",
    }));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-600 text-sm text-center px-4">
        {t("chart_no_data")}
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
        <XAxis
          dataKey="hash"
          tick={{ fill: "#6b7280", fontSize: 11, fontFamily: "monospace" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 5]}
          ticks={[0, 1, 2, 3, 4, 5]}
          tick={{ fill: "#6b7280", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
        <Bar dataKey="score" radius={[4, 4, 0, 0]}>
          {data.map((entry) => (
            <Cell
              key={entry.hash}
              fill={entry.score >= 4 ? "#22c55e" : entry.score >= 2.5 ? "#eab308" : "#ef4444"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

