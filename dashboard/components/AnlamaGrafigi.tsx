"use client";

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { Commit } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

interface GrafikVeri {
  hash: string;
  anlama: number;
  tarih: string;
}

function OzelTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: GrafikVeri }>;
}) {
  const { t } = useTranslation();
  if (!active || !payload?.length) return null;
  const veri = payload[0];
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs">
      <p className="text-cyan-400 font-mono">{veri.payload.hash}</p>
      <p className="text-gray-300">{veri.payload.tarih}</p>
      <p className="text-white font-semibold mt-1">
        {t("chart_tooltip_understanding")}: {veri.value.toFixed(1)}/5
      </p>
    </div>
  );
}

export function AnlamaGrafigi({ commitler }: { commitler: Commit[] }) {
  const { t } = useTranslation();

  const veri: GrafikVeri[] = commitler
    .filter((c) => c.anlama_skoru != null)
    .reverse()
    .map((c) => ({
      hash: c.hash_kisa,
      anlama: c.anlama_skoru!,
      tarih: c.tarih ?? "",
    }));

  if (veri.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-600 text-sm text-center px-4">
        {t("chart_no_data")}
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={veri} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
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
        <Tooltip content={<OzelTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
        <Bar dataKey="anlama" radius={[4, 4, 0, 0]}>
          {veri.map((entry) => (
            <Cell
              key={entry.hash}
              fill={entry.anlama >= 4 ? "#22c55e" : entry.anlama >= 2.5 ? "#eab308" : "#ef4444"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
