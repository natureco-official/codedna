"use client";

import { useState, useEffect } from "react";
import { getCommitler, CommitListYanit } from "@/lib/api";
import { CommitTable, CommitTableSkeleton } from "@/components/CommitTable";
import { HataBanner } from "@/components/HataBanner";
import { useTranslation } from "@/lib/i18n";

export default function CommitlerSayfasi() {
  const { t } = useTranslation();
  const [limit, setLimit] = useState(20);
  const [veri, setVeri] = useState<CommitListYanit | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(false);

  useEffect(() => {
    setYukleniyor(true);
    setHata(false);
    getCommitler(limit)
      .then(setVeri)
      .catch(() => setHata(true))
      .finally(() => setYukleniyor(false));
  }, [limit]);

  const anketliCommit = veri?.commitler.filter((c) => c.anlama_skoru != null) ?? [];
  const ortAnlama =
    anketliCommit.length > 0
      ? anketliCommit.reduce((s, c) => s + c.anlama_skoru!, 0) / anketliCommit.length
      : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">🕒 {t("commits_title")}</h1>
        <p className="text-gray-500 text-sm mt-1">{t("commits_subtitle")}</p>
      </div>

      {veri && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: t("commits_total"), value: veri.toplam, renk: "text-cyan-400" },
            { label: t("commits_surveyed"), value: anketliCommit.length, renk: "text-white" },
            {
              label: t("commits_avg_understanding"),
              value: ortAnlama != null ? `${ortAnlama.toFixed(1)}/5` : "—",
              renk: ortAnlama == null
                ? "text-gray-600"
                : ortAnlama >= 4 ? "text-green-400"
                : ortAnlama >= 2.5 ? "text-yellow-400"
                : "text-red-400",
            },
          ].map((k) => (
            <div key={k.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{k.label}</p>
              <p className={`text-2xl font-bold ${k.renk}`}>{k.value}</p>
            </div>
          ))}
        </div>
      )}

      {hata && <HataBanner />}

      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <span className="text-cyan-400">◈</span> {t("commits_section")}
          </h2>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500"
          >
            {[10, 20, 50, 100].map((n) => (
              <option key={n} value={n}>
                {t("commits_last")} {n}
              </option>
            ))}
          </select>
        </div>

        {yukleniyor ? (
          <CommitTableSkeleton />
        ) : veri ? (
          <CommitTable commitler={veri.commitler} />
        ) : null}
      </div>
    </div>
  );
}
