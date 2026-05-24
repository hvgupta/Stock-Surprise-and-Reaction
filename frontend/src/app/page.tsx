"use client";

import { useEffect, useMemo, useState } from "react";
import Fuse from "fuse.js";

import SurpriseCard from "@/components/surprise-card";
import SummaryStatsBanner from "@/components/summary-stats-banner";
import SectorSurpriseChart from "@/components/sector-surprise-chart";
import SurpriseHistogram, { type HistogramBucket } from "@/components/surprise-histogram";
import SurpriseReactionScatter from "@/components/surprise-reaction-scatter";
import { fetchSP500SurprisesFresh, type SP500TickerSnapshot } from "@/lib/api";

const HISTOGRAM_BUCKETS: Array<{ label: string; min: number; max: number; isPositive: boolean }> = [
  { label: "< -20%", min: -Infinity, max: -20, isPositive: false },
  { label: "-20→-10%", min: -20, max: -10, isPositive: false },
  { label: "-10→-5%", min: -10, max: -5, isPositive: false },
  { label: "-5→0%", min: -5, max: 0, isPositive: false },
  { label: "0→+5%", min: 0, max: 5, isPositive: true },
  { label: "+5→+10%", min: 5, max: 10, isPositive: true },
  { label: "+10→+20%", min: 10, max: 20, isPositive: true },
  { label: "> +20%", min: 20, max: Infinity, isPositive: true },
];

export default function Home() {
  const [items, setItems] = useState<SP500TickerSnapshot[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const data = await fetchSP500SurprisesFresh();
        setItems(data);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to load surprises";
        setErrorMessage(message);
      } finally {
        setIsLoading(false);
      }
    };

    void run();
  }, []);

  const topTen = useMemo(() => items.slice(0, 12), [items]);
  const fuzzySearch = useMemo(
    () =>
      new Fuse(items, {
        keys: ["ticker", "company_name"],
        threshold: 0.33,
      }),
    [items],
  );

  const summaryStats = useMemo(() => {
    const beats = items.filter((x) => x.surprise > 0);
    const misses = items.filter((x) => x.surprise < 0);
    const avgBeat = beats.length
      ? beats.reduce((s, x) => s + x.surprise, 0) / beats.length
      : 0;
    const avgMiss = misses.length
      ? misses.reduce((s, x) => s + x.surprise, 0) / misses.length
      : 0;
    return { total: items.length, beatCount: beats.length, missCount: misses.length, avgBeat, avgMiss };
  }, [items]);

  const sectorData = useMemo(() => {
    const map = new Map<string, { sum: number; count: number }>();
    for (const item of items) {
      const entry = map.get(item.sector) ?? { sum: 0, count: 0 };
      entry.sum += item.surprise;
      entry.count += 1;
      map.set(item.sector, entry);
    }
    return Array.from(map.entries())
      .map(([sector, { sum, count }]) => ({ sector, avgSurprise: sum / count, count }))
      .sort((a, b) => b.avgSurprise - a.avgSurprise);
  }, [items]);

  const histogramData = useMemo((): HistogramBucket[] => {
    return HISTOGRAM_BUCKETS.map((bucket) => ({
      label: bucket.label,
      isPositive: bucket.isPositive,
      count: items.filter((item) => {
        const pct = item.surprise * 100;
        return pct > bucket.min && pct <= bucket.max;
      }).length,
    }));
  }, [items]);

  const scatterData = useMemo(() => {
    return items
      .filter((x) => x.latest_reaction != null)
      .map((x) => ({
        ticker: x.ticker,
        company_name: x.company_name,
        surprise: x.surprise * 100,
        reaction: (x.latest_reaction as number) * 100,
        sector: x.sector,
      }));
  }, [items]);

  const trimmedQuery = searchQuery.trim();
  const visibleItems =
    trimmedQuery.length > 0
      ? fuzzySearch.search(trimmedQuery).map((result) => result.item)
      : topTen;

  return (
    <div className="pb-10 pt-8">
      <main className="page-shell">
        <section className="mb-6 rounded-3xl border border-emerald-200/80 bg-surface p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-2">
            Market Surprise Reaction
          </p>
          <h1 className="mt-2 text-3xl font-black leading-tight text-foreground sm:text-4xl">
            SP500 Earnings Surprise Board
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-zinc-700 sm:text-base">
            Default view shows the top 10 movers ranked by absolute surprise. Type to switch into fuzzy search mode for any symbol.
          </p>

          <div className="mt-5">
            <label htmlFor="symbol-search" className="mb-1 block text-xs font-semibold uppercase tracking-[0.18em] text-zinc-700">
              Search Ticker or Company
            </label>
            <input
              id="symbol-search"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Try AAPL, MSFT, NVIDIA..."
              className="w-full rounded-xl border border-emerald-200 bg-white px-4 py-3 text-sm outline-none ring-teal-600 transition focus:ring-2"
            />
          </div>

          <div className="mt-3 text-xs text-zinc-600">
            {trimmedQuery.length > 0
              ? `Showing fuzzy matches for "${trimmedQuery}"`
              : "Showing Top 12 by absolute surprise"}
          </div>
        </section>

        {isLoading ? (
          <section className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-20 animate-pulse rounded-2xl bg-surface" />
              ))}
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 10 }).map((_, index) => (
                <div key={index} className="h-24 animate-pulse rounded-2xl bg-surface" />
              ))}
            </div>
          </section>
        ) : null}

        {!isLoading && errorMessage ? (
          <section className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {errorMessage}
          </section>
        ) : null}

        {!isLoading && !errorMessage && items.length > 0 ? (
          <section className="mb-8 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-foreground">Season Analytics</h2>
              <span className="text-xs text-zinc-500">{summaryStats.total} companies loaded</span>
            </div>

            <SummaryStatsBanner stats={summaryStats} />

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <div className="rounded-2xl border border-emerald-200 bg-white p-4">
                <h3 className="mb-1 text-sm font-semibold uppercase tracking-[0.14em] text-zinc-600">
                  Avg Surprise by Sector
                </h3>
                <p className="mb-3 text-xs text-zinc-400">Which sectors are beating or missing analyst expectations</p>
                <SectorSurpriseChart data={sectorData} />
              </div>
              <div className="rounded-2xl border border-emerald-200 bg-white p-4">
                <h3 className="mb-1 text-sm font-semibold uppercase tracking-[0.14em] text-zinc-600">
                  Surprise Distribution
                </h3>
                <p className="mb-3 text-xs text-zinc-400">How surprises are distributed across the S&amp;P 500</p>
                <SurpriseHistogram data={histogramData} />
              </div>
            </div>

            {scatterData.length > 0 ? (
              <div className="rounded-2xl border border-emerald-200 bg-white p-4">
                <h3 className="mb-1 text-sm font-semibold uppercase tracking-[0.14em] text-zinc-600">
                  Surprise vs. Market Reaction
                </h3>
                <p className="mb-3 text-xs text-zinc-400">
                  {scatterData.length} companies with reaction data — each dot is a company, colored by sector
                </p>
                <SurpriseReactionScatter data={scatterData} />
              </div>
            ) : null}
          </section>
        ) : null}

        {!isLoading && !errorMessage ? (
          <>
            <h2 className="mb-3 text-xl font-bold text-foreground">
              {trimmedQuery.length > 0 ? `Results for "${trimmedQuery}"` : "Top Movers"}
            </h2>
            <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {visibleItems.map((item) => (
                <SurpriseCard key={item.ticker} item={item} />
              ))}
            </section>
          </>
        ) : null}

        {!isLoading && !errorMessage && visibleItems.length === 0 ? (
          <section className="rounded-2xl border border-zinc-200 bg-white p-4 text-sm text-zinc-700">
            No matches found.
          </section>
        ) : null}
      </main>
    </div>
  );
}
