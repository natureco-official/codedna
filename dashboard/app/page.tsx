/**
 * Ana pano sayfası — /repo/summary ve /commits endpoint'lerinden veri alır.
 */

import { getRepoSummary, getCommitler, getRepoDosyalar } from "@/lib/api";
import { SummaryCards, SummaryCardsSkeleton } from "@/components/SummaryCards";
import { CommitTable, CommitTableSkeleton } from "@/components/CommitTable";
import { AnlamaGrafigi } from "@/components/AnlamaGrafigi";
import { HataBanner } from "@/components/HataBanner";
import { OverviewTitles } from "@/components/OverviewTitles";
import { QuickInsights } from "@/components/QuickInsights";
import { Suspense } from "react";

async function OzetKartlarVeri() {
  try {
    const [ozet, dosyalar] = await Promise.all([
      getRepoSummary(),
      getRepoDosyalar(),
    ]);
    return <SummaryCards ozet={ozet} toplamDosya={dosyalar.toplam_dosya} />;
  } catch {
    return <HataBanner />;
  }
}

async function CommitBolumu() {
  try {
    const { commitler } = await getCommitler(10);
    return (
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        <div className="xl:col-span-3 bg-gray-900 border border-gray-800 rounded-xl p-6">
          <OverviewTitles section="commits" />
          <CommitTable commitler={commitler} />
        </div>
        <div className="xl:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-6">
          <OverviewTitles section="chart" />
          <AnlamaGrafigi commitler={commitler} />
          <OverviewTitles section="chart_sub" />
        </div>
      </div>
    );
  } catch {
    return <HataBanner />;
  }
}

export default function AnaSayfa() {
  return (
    <div className="space-y-8">
      <OverviewTitles section="page" />

      <Suspense fallback={<SummaryCardsSkeleton />}>
        <OzetKartlarVeri />
      </Suspense>

      {/* Hızlı içgörü widget'ı — Bus Factor + Teknik Borç özeti */}
      <QuickInsights />

      <Suspense
        fallback={
          <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
            <div className="xl:col-span-3 bg-gray-900 border border-gray-800 rounded-xl p-6">
              <CommitTableSkeleton />
            </div>
            <div className="xl:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-6">
              <div className="h-48 bg-gray-800 rounded animate-pulse" />
            </div>
          </div>
        }
      >
        <CommitBolumu />
      </Suspense>
    </div>
  );
}
