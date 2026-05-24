"use client";

import { useEffect, useMemo, useState } from "react";
import Fuse from "fuse.js";

import SurpriseCard from "@/components/surprise-card";
import { fetchSP500SurprisesFresh, readLocalSurprisesCache, type SP500TickerSnapshot } from "@/lib/api";

export default function Home() {
  const [items, setItems] = useState<SP500TickerSnapshot[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    const cached = readLocalSurprisesCache();
    if (cached) {
      setItems(cached);
      setIsLoading(false);
      setIsRefreshing(true);
      void fetchSP500SurprisesFresh()
        .then((fresh) => {
          setItems(fresh);
        })
        .catch((err) => {
          const message = err instanceof Error ? err.message : "Failed to refresh surprises";
          setErrorMessage(message);
        })
        .finally(() => setIsRefreshing(false));
      return;
    }

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
            {isRefreshing ? <span className="ml-3 inline-block text-xs text-zinc-500">Refreshing…</span> : null}
          </div>
        </section>

        {isLoading ? (
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 10 }).map((_, index) => (
              <div key={index} className="h-24 animate-pulse rounded-2xl bg-surface" />
            ))}
          </section>
        ) : null}

        {!isLoading && errorMessage ? (
          <section className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {errorMessage}
          </section>
        ) : null}

        {!isLoading && !errorMessage ? (
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {visibleItems.map((item) => (
              <SurpriseCard key={item.ticker} item={item} />
            ))}
          </section>
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
