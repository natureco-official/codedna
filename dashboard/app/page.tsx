/**
 * Main dashboard page — fetches data from /repo/summary and /commits endpoints.
 */

import { getRepoSummary, getCommits, getRepoFiles } from "@/lib/api";
import { SummaryCards, SummaryCardsSkeleton } from "@/components/SummaryCards";
import { CommitTable, CommitTableSkeleton } from "@/components/CommitTable";
import { UnderstandingChart } from "@/components/UnderstandingChart";
import { ErrorBanner } from "@/components/ErrorBanner";
import { OverviewTitles } from "@/components/OverviewTitles";
import { QuickInsights } from "@/components/QuickInsights";
import { Suspense } from "react";

async function SummaryCardsData() {
  try {
    const [summary, files] = await Promise.all([
      getRepoSummary(),
      getRepoFiles(),
    ]);
    return <SummaryCards summary={summary} totalFiles={files.total_files} />;
  } catch {
    return <ErrorBanner />;
  }
}

async function CommitsSection() {
  try {
    const { commits } = await getCommits(10);
    return (
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        <div className="xl:col-span-3 bg-gray-900 border border-gray-800 rounded-xl p-6">
          <OverviewTitles section="commits" />
          <CommitTable commits={commits} />
        </div>
        <div className="xl:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-6">
          <OverviewTitles section="chart" />
          <UnderstandingChart commits={commits} />
          <OverviewTitles section="chart_sub" />
        </div>
      </div>
    );
  } catch {
    return <ErrorBanner />;
  }
}

export default function HomePage() {
  return (
    <div className="space-y-8">
      <OverviewTitles section="page" />

      <Suspense fallback={<SummaryCardsSkeleton />}>
        <SummaryCardsData />
      </Suspense>

      {/* Quick insights widget — Bus Factor + Technical Debt summary */}
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
        <CommitsSection />
      </Suspense>
    </div>
  );
}
