"use client";

import { useEffect, useMemo, useState } from "react";
import Fuse from "fuse.js";

import SurpriseCard from "@/components/surprise-card";
import LoadingSpinner from "@/components/loading-spinner";
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
  const [selectedSector, setSelectedSector] = useState<string | null>(null);
  const [selectedBucket, setSelectedBucket] = useState<string | null>(null);
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

  const selectedItems = useMemo(() => {
    return items.filter((item) => {
      if (selectedSector && item.sector !== selectedSector) {
        return false;
      }

      if (selectedBucket) {
        const bucket = HISTOGRAM_BUCKETS.find((entry) => entry.label === selectedBucket);
        if (!bucket) {
          return true;
        }
        const surprisePct = item.surprise * 100;
        return surprisePct > bucket.min && surprisePct <= bucket.max;
      }

      return true;
    });
  }, [items, selectedBucket, selectedSector]);

  const topTen = useMemo(() => {
    return [...selectedItems]
      .sort((a, b) => Math.abs(b.surprise) - Math.abs(a.surprise))
      .slice(0, 12);
  }, [selectedItems]);

  const fuzzySearch = useMemo(
    () =>
      new Fuse(selectedItems, {
        keys: ["ticker", "company_name"],
        threshold: 0.33,
      }),
    [selectedItems],
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
      : selectedSector || selectedBucket
        ? selectedItems.sort((a, b) => Math.abs(b.surprise) - Math.abs(a.surprise))
        : topTen;

  const hasActiveFilters = Boolean(selectedSector || selectedBucket || trimmedQuery.length > 0);

  const clearFilters = () => {
    setSelectedSector(null);
    setSelectedBucket(null);
    setSearchQuery("");
  };

  return (
    <div className="pb-10 pt-8">
      <main className="page-shell">
        {isLoading ? <LoadingSpinner label="Loading season analytics..." className="min-h-64" /> : null}

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
                <SectorSurpriseChart
                  data={sectorData}
                  selectedSector={selectedSector}
                  onSectorClick={(sector) => setSelectedSector((current) => (current === sector ? null : sector))}
                />
              </div>
              <div className="rounded-2xl border border-emerald-200 bg-white p-4">
                <h3 className="mb-1 text-sm font-semibold uppercase tracking-[0.14em] text-zinc-600">
                  Surprise Distribution
                </h3>
                <p className="mb-3 text-xs text-zinc-400">How surprises are distributed across the S&amp;P 500</p>
                <SurpriseHistogram
                  data={histogramData}
                  selectedBucket={selectedBucket}
                  onBucketClick={(bucketLabel) =>
                    setSelectedBucket((current) => (current === bucketLabel ? null : bucketLabel))
                  }
                />
              </div>
            </div>

            {hasActiveFilters ? (
              <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-emerald-200 bg-white px-4 py-3 text-sm text-zinc-700">
                <span className="font-semibold text-zinc-900">Active filters:</span>
                {selectedSector ? (
                  <button
                    className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800"
                    onClick={() => setSelectedSector(null)}
                  >
                    Sector: {selectedSector} ×
                  </button>
                ) : null}
                {selectedBucket ? (
                  <button
                    className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800"
                    onClick={() => setSelectedBucket(null)}
                  >
                    Surprise: {selectedBucket} ×
                  </button>
                ) : null}
                {trimmedQuery.length > 0 ? (
                  <button
                    className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800"
                    onClick={() => setSearchQuery("")}
                  >
                    Search: {trimmedQuery} ×
                  </button>
                ) : null}
                <button
                  className="ml-auto rounded-full border border-zinc-200 px-3 py-1 text-xs font-semibold text-zinc-700 hover:bg-zinc-50"
                  onClick={clearFilters}
                >
                  Clear all
                </button>
              </div>
            ) : null}

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
        <section className="mb-6 rounded-3xl border border-emerald-200/80 bg-surface p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-2">
            Market Surprise Reaction
          </p>
          <h1 className="mt-2 text-3xl font-black leading-tight text-foreground sm:text-4xl">
            SP500 Earnings Surprise Board
          </h1>
          <p className="mt-3 max-w-2xl text-sm text-zinc-700 sm:text-base">
            Default view shows the top 12 movers ranked by absolute surprise. Type to switch into fuzzy search mode for any symbol.
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
        {!isLoading && !errorMessage ? (
          <>
            <h2 className="mb-3 text-xl font-bold text-foreground">
              {hasActiveFilters ? "Filtered Tickers" : "Top Movers"}
            </h2>
            <p className="mb-3 text-sm text-zinc-600">
              {hasActiveFilters
                ? "The ticker list is filtered by the selected sector, surprise bucket, and search query together."
                : "Showing the top 12 movers by absolute surprise."}
            </p>
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
