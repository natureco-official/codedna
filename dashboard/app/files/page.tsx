"use client";

import { useState, useEffect } from "react";
import { getRepoDosyalar, DosyalarYanit } from "@/lib/api";
import { FileHeatmap, FileHeatmapSkeleton } from "@/components/FileHeatmap";
import { HataBanner } from "@/components/HataBanner";
import { useTranslation } from "@/lib/i18n";

export default function DosyalarSayfasi() {
  const { t } = useTranslation();
  const [minRisk, setMinRisk] = useState(0);
  const [veri, setVeri] = useState<DosyalarYanit | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(false);

  useEffect(() => {
    setYukleniyor(true);
    setHata(false);
    getRepoDosyalar(minRisk / 100)
      .then(setVeri)
      .catch(() => setHata(true))
      .finally(() => setYukleniyor(false));
  }, [minRisk]);

  return (
    <div className="space-y-6">
      {/* Başlık */}
      <div>
        <h1 className="text-2xl font-bold text-white">📁 {t("files_title")}</h1>
        <p className="text-gray-500 text-sm mt-1">{t("files_subtitle")}</p>
      </div>

      {/* Filtre kartı */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex-1">
            <label className="text-sm text-gray-400 mb-2 block">
              {t("files_filter")}:{" "}
              <span className="text-cyan-400 font-semibold">%{minRisk}</span>
            </label>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={minRisk}
              onChange={(e) => setMinRisk(Number(e.target.value))}
              className="w-full accent-cyan-400"
            />
            <div className="flex justify-between text-xs text-gray-700 mt-1">
              <span>{t("files_filter_all")}</span>
              <span>{t("files_filter_medium")}</span>
              <span>{t("files_filter_high")}</span>
              <span>%100</span>
            </div>
          </div>

          {veri && (
            <div className="sm:text-right">
              <p className="text-2xl font-bold text-cyan-400">{veri.toplam_dosya}</p>
              <p className="text-xs text-gray-500">
                {t("files_results")} · {t("files_avg_ai")}:{" "}
                <span className="text-gray-300">
                  %{(veri.ortalama_ai_skoru * 100).toFixed(0)}
                </span>
              </p>
            </div>
          )}
        </div>
      </div>

      {hata && <HataBanner />}

      {/* Tablo */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-white font-semibold mb-4 flex items-center gap-2">
          <span className="text-cyan-400">◈</span> {t("files_section")}
          {veri && (
            <span className="text-gray-600 text-xs font-normal">
              — {veri.toplam_dosya} {t("files_results")}
            </span>
          )}
        </h2>
        {yukleniyor ? (
          <FileHeatmapSkeleton />
        ) : veri ? (
          <FileHeatmap dosyalar={veri.dosyalar} />
        ) : null}
      </div>
    </div>
  );
}
