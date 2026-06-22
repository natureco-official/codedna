"use client";

import { useState, useEffect } from "react";
import { Commit, CommitDetay, getCommitDetay } from "@/lib/api";
import { useTranslation } from "@/lib/i18n";

/** Anlama skorunu renkli gösterir */
function AnlamaSkoruHucresi({ skor }: { skor: number | null }) {
  if (skor == null) return <span className="text-gray-600 text-sm">—</span>;
  const renk =
    skor >= 4 ? "text-green-400" : skor >= 2.5 ? "text-yellow-400" : "text-red-400";
  const emoji = skor >= 4 ? "✅" : skor >= 2.5 ? "🔶" : "🔴";
  return (
    <span className={`font-medium text-sm ${renk}`}>
      {emoji} {skor.toFixed(1)}/5
    </span>
  );
}

/** Tek commit için detay modalı */
function CommitModal({ commit, onKapat }: { commit: Commit; onKapat: () => void }) {
  const { t } = useTranslation();
  const [detay, setDetay] = useState<CommitDetay | null>(null);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(false);

  useEffect(() => {
    getCommitDetay(commit.commit_hash)
      .then(setDetay)
      .catch(() => setHata(true))
      .finally(() => setYukleniyor(false));
  }, [commit.commit_hash]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={onKapat}
    >
      <div
        className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-2xl max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Başlık */}
        <div className="flex items-center justify-between p-5 border-b border-gray-800">
          <div>
            <h2 className="text-white font-semibold">
              {t("modal_commit_detail")}{" "}
              <code className="text-cyan-400 text-sm bg-gray-800 px-2 py-0.5 rounded">
                {commit.hash_kisa}
              </code>
            </h2>
            <p className="text-gray-500 text-sm mt-0.5">
              {commit.yazar} · {commit.tarih}
            </p>
          </div>
          <button
            onClick={onKapat}
            className="text-gray-500 hover:text-white transition-colors p-1"
            aria-label={t("modal_close")}
          >
            ✕
          </button>
        </div>

        {/* İçerik */}
        <div className="p-5">
          {yukleniyor && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-8 bg-gray-800 rounded animate-pulse" />
              ))}
            </div>
          )}

          {hata && (
            <p className="text-red-400 text-sm">{t("modal_loading_error")}</p>
          )}

          {detay && !yukleniyor && (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 text-left border-b border-gray-800">
                  <th className="pb-2 font-medium">{t("modal_col_file")}</th>
                  <th className="pb-2 font-medium text-right">{t("modal_col_ai")}</th>
                  <th className="pb-2 font-medium text-right">{t("modal_col_complexity")}</th>
                  <th className="pb-2 font-medium text-right">{t("modal_col_understanding")}</th>
                </tr>
              </thead>
              <tbody>
                {detay.dosyalar.map((d) => {
                  const ai = (d.ai_olasıligi ?? 0) * 100;
                  const aiRenk =
                    ai >= 70 ? "text-red-400" : ai >= 40 ? "text-yellow-400" : "text-green-400";
                  return (
                    <tr key={d.dosya_yolu} className="border-b border-gray-800/50 last:border-0">
                      <td className="py-2.5 font-mono text-xs text-gray-300 max-w-[240px] truncate">
                        {d.dosya_yolu.split("/").slice(-2).join("/")}
                      </td>
                      <td className={`py-2.5 text-right font-medium ${aiRenk}`}>
                        %{ai.toFixed(0)}
                      </td>
                      <td className="py-2.5 text-right text-gray-400">
                        {d.karmasiklik_skoru?.toFixed(0) ?? "—"}
                      </td>
                      <td className="py-2.5 text-right">
                        <AnlamaSkoruHucresi skor={d.anlama_skoru} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

/** Commit listesi tablosu */
export function CommitTable({ commitler }: { commitler: Commit[] }) {
  const { t } = useTranslation();
  const [secilenCommit, setSecilenCommit] = useState<Commit | null>(null);

  if (commitler.length === 0) {
    return (
      <p className="text-gray-600 text-sm text-center py-8">
        {t("commits_no_data")}
      </p>
    );
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-left border-b border-gray-800">
              <th className="pb-3 font-medium">{t("commits_col_hash")}</th>
              <th className="pb-3 font-medium">{t("commits_col_author")}</th>
              <th className="pb-3 font-medium">{t("commits_col_date")}</th>
              <th className="pb-3 font-medium text-right">{t("commits_col_files")}</th>
              <th className="pb-3 font-medium text-right">{t("commits_col_understanding")}</th>
            </tr>
          </thead>
          <tbody>
            {commitler.map((c) => (
              <tr
                key={c.commit_hash}
                onClick={() => setSecilenCommit(c)}
                className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/40 cursor-pointer transition-colors"
              >
                <td className="py-3">
                  <code className="text-cyan-400 bg-gray-800 px-2 py-0.5 rounded text-xs">
                    {c.hash_kisa}
                  </code>
                </td>
                <td className="py-3 text-gray-300">{c.yazar ?? "?"}</td>
                <td className="py-3 text-gray-500">{c.tarih ?? "?"}</td>
                <td className="py-3 text-right text-gray-400">{c.degisen_dosya_sayisi}</td>
                <td className="py-3 text-right">
                  <AnlamaSkoruHucresi skor={c.anlama_skoru} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {secilenCommit && (
        <CommitModal commit={secilenCommit} onKapat={() => setSecilenCommit(null)} />
      )}
    </>
  );
}

/** Yükleme iskeleti */
export function CommitTableSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
      ))}
    </div>
  );
}
