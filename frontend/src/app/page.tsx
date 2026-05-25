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

  const latestItems = useMemo(() => {
    const byTicker = new Map<string, SP500TickerSnapshot>();
    for (const item of items) {
      const current = byTicker.get(item.ticker);
      if (!current) {
        byTicker.set(item.ticker, item);
        continue;
      }

      const currentTs = Date.parse(current.filing_date);
      const nextTs = Date.parse(item.filing_date);
      if (Number.isNaN(currentTs) || Number.isNaN(nextTs)) {
        if (item.filing_date > current.filing_date) {
          byTicker.set(item.ticker, item);
        }
        continue;
      }

      if (nextTs > currentTs) {
        byTicker.set(item.ticker, item);
      }
    }

    return Array.from(byTicker.values());
  }, [items]);

  const selectedItems = useMemo(() => {
    return latestItems.filter((item) => {
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
  }, [latestItems, selectedBucket, selectedSector]);

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
    const beats = latestItems.filter((x) => x.surprise > 0);
    const misses = latestItems.filter((x) => x.surprise < 0);
    const avgBeat = beats.length
      ? beats.reduce((s, x) => s + x.surprise, 0) / beats.length
      : 0;
    const avgMiss = misses.length
      ? misses.reduce((s, x) => s + x.surprise, 0) / misses.length
      : 0;
    return { total: latestItems.length, beatCount: beats.length, missCount: misses.length, avgBeat, avgMiss };
  }, [latestItems]);

  const sectorData = useMemo(() => {
    const map = new Map<string, { sum: number; count: number }>();
    for (const item of latestItems) {
      const entry = map.get(item.sector) ?? { sum: 0, count: 0 };
      entry.sum += item.surprise;
      entry.count += 1;
      map.set(item.sector, entry);
    }
    return Array.from(map.entries())
      .map(([sector, { sum, count }]) => ({ sector, avgSurprise: sum / count, count }))
      .sort((a, b) => b.avgSurprise - a.avgSurprise);
  }, [latestItems]);

  const sectorOutliers = useMemo(() => {
    const map = new Map<string, Array<{ ticker: string; company_name: string; surprisePct: number; filing_date: string }>>();
    const bySector = new Map<string, number[]>();
    for (const it of latestItems) {
      const pct = it.surprise * 100;
      const arr = bySector.get(it.sector) ?? [];
      arr.push(pct);
      bySector.set(it.sector, arr);
    }

    for (const sector of Array.from(bySector.keys())) {
      const values = bySector.get(sector) ?? [];
      if (values.length < 4) {
        map.set(sector, []);
        continue;
      }
      const sorted = [...values].sort((a, b) => a - b);
      const q1 = sorted[Math.floor((sorted.length - 1) * 0.25)];
      const q3 = sorted[Math.floor((sorted.length - 1) * 0.75)];
      const iqr = q3 - q1;
      const lower = q1 - 1.5 * iqr;
      const upper = q3 + 1.5 * iqr;

      const outliers = latestItems
        .filter((it) => it.sector === sector)
        .map((it) => ({ ticker: it.ticker, company_name: it.company_name, surprisePct: it.surprise * 100, filing_date: it.filing_date }))
        .filter((it) => it.surprisePct < lower || it.surprisePct > upper)
        .sort((a, b) => Math.abs(b.surprisePct) - Math.abs(a.surprisePct));

      map.set(sector, outliers.slice(0, 6));
    }
    return map;
  }, [latestItems]);

  const histogramData = useMemo((): HistogramBucket[] => {
    return HISTOGRAM_BUCKETS.map((bucket) => ({
      label: bucket.label,
      isPositive: bucket.isPositive,
      count: latestItems.filter((item) => {
        const pct = item.surprise * 100;
        return pct > bucket.min && pct <= bucket.max;
      }).length,
    }));
  }, [latestItems]);

  const scatterData = useMemo(() => {
    return latestItems
      .filter((x) => x.latest_reaction != null)
      .map((x) => ({
        ticker: x.ticker,
        company_name: x.company_name,
        surprise: x.surprise * 100,
        reaction: (x.latest_reaction as number) * 100,
        sector: x.sector,
      }));
  }, [latestItems]);

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

        {!isLoading && !errorMessage && latestItems.length > 0 ? (
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
        <div className="mt-4 rounded-2xl border border-emerald-200 p-4">
          <h3 className="mb-1 text-sm font-semibold uppercase tracking-[0.14em] text-zinc-600">Sector Outliers</h3>
          <p className="mb-3 text-xs text-zinc-400">Outlier filings per sector (IQR method). Click a ticker to open details.</p>
          {Array.from(sectorOutliers.entries()).map(([sector, outliers]) => (
            <details key={sector} className="mb-4" open>
              <summary className="flex w-full cursor-pointer items-center justify-between rounded-md px-3 py-2 bg-zinc-50">
                <div className="flex items-center gap-3">
                  <div className="text-sm font-semibold text-foreground">{sector}</div>
                </div>
              </summary>

              {outliers.length === 0 ? (
                <div className="mt-2 mb-2 text-xs text-zinc-500 px-3">No outliers</div>
              ) : (
                <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {outliers.map((it) => {
                    const matched = latestItems.find((x) => x.ticker === it.ticker && x.filing_date === it.filing_date);
                    return matched ? (
                      <SurpriseCard key={it.ticker + it.filing_date} item={matched} />
                    ) : (
                      <div key={it.ticker + it.filing_date} className="flex items-center justify-between rounded-md bg-surface px-3 py-2">
                        <div>
                          <div className="text-sm font-semibold text-foreground">{it.ticker}</div>
                          <div className="text-xs text-zinc-500">{it.company_name}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono text-sm">{it.surprisePct >= 0 ? "+" : ""}{it.surprisePct.toFixed(2)}%</div>
                          <div className="text-xs text-zinc-500">{it.filing_date}</div>
                          <div className="mt-1">
                            <a
                              href={`/ticker/${it.ticker}?filing_date=${encodeURIComponent(it.filing_date)}&company_name=${encodeURIComponent(it.company_name)}&sector=${encodeURIComponent(sector)}&surprise=${encodeURIComponent(it.surprisePct)}`}
                              className="text-xs font-semibold text-brand hover:underline"
                            >
                              Open
                            </a>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </details>
          ))}
        </div>
      </main>
    </div>
  );
}
