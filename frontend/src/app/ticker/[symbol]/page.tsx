"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import RegressionChart from "@/components/regression-chart";
import {
  getTickerProportionality,
  getTickerReaction,
  type ProportionalityEndpointResponse,
  type RegressionModelValues,
  type ReactionEndpointResponse,
} from "@/lib/api";

type TickerDetailsPageProps = {
  params: Promise<{ symbol: string }>;
};

function formatSignedPercent(value: number | null): string {
  if (value === null) {
    return "N/A";
  }
  const percent = (value * 100).toFixed(2);
  return `${value >= 0 ? "+" : ""}${percent}%`;
}

export default function TickerDetailsPage({ params }: TickerDetailsPageProps) {
  const [symbol, setSymbol] = useState<string>("");
  const [companyName, setCompanyName] = useState<string>("");
  const [sector, setSector] = useState<string>("");
  const [filingDate, setFilingDate] = useState<string>("");
  const [surprise, setSurprise] = useState<number | null>(null);
  const [reactionData, setReactionData] = useState<ReactionEndpointResponse | null>(null);
  const [proportionalityData, setProportionalityData] = useState<ProportionalityEndpointResponse | null>(null);
  const [reactionLoading, setReactionLoading] = useState(true);
  const [proportionalityLoading, setProportionalityLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const searchParams = useSearchParams();

  useEffect(() => {
    const run = async () => {
      const resolvedParams = await params;
      setSymbol(resolvedParams.symbol.toUpperCase());

      setCompanyName(searchParams.get("company_name") ?? resolvedParams.symbol.toUpperCase());
      setSector(searchParams.get("sector") ?? "");
      setFilingDate(searchParams.get("filing_date") ?? "");

      const surpriseParam = searchParams.get("surprise");
      setSurprise(surpriseParam === null ? null : Number(surpriseParam));

      const currentFilingDate = searchParams.get("filing_date") ?? "";
      if (!currentFilingDate) {
        setErrorMessage("Missing filing date for this ticker.");
        setReactionLoading(false);
        setProportionalityLoading(false);
        return;
      }

      void (async () => {
        try {
          const payload = await getTickerReaction(resolvedParams.symbol, currentFilingDate);
          setReactionData(payload);
        } catch (error) {
          const message = error instanceof Error ? error.message : "Failed to load reaction";
          setErrorMessage(message);
        } finally {
          setReactionLoading(false);
        }
      })();

      void (async () => {
        try {
          const payload = await getTickerProportionality(resolvedParams.symbol, currentFilingDate);
          setProportionalityData(payload);
        } catch (error) {
          const message = error instanceof Error ? error.message : "Failed to load proportionality";
          setErrorMessage(message);
        } finally {
          setProportionalityLoading(false);
        }
      })();
    };

    void run();
  }, [params, searchParams]);

  const reactionRows = useMemo(() => {
    if (!reactionData) {
      return [] as Array<[string, number]>;
    }

    const firstEntry = Object.values(reactionData.reaction_data)[0];
    if (!firstEntry || typeof firstEntry.reaction === "string") {
      return [] as Array<[string, number]>;
    }

    return Object.entries(firstEntry.reaction).sort((a, b) => a[0].localeCompare(b[0]));
  }, [reactionData]);

  const latestReaction = useMemo(() => {
    if (reactionRows.length === 0) {
      return null;
    }

    return reactionRows[reactionRows.length - 1]?.[1] ?? null;
  }, [reactionRows]);

  const proportionalityEntry = useMemo(() => {
    if (!proportionalityData) {
      return null;
    }

    const firstEntry = Object.values(proportionalityData)[0];
    return firstEntry ?? null;
  }, [proportionalityData]);

  const regressionModel: RegressionModelValues | null = proportionalityEntry?.regression_model ?? null;

  return (
    <div className="pb-10 pt-8">
      <main className="page-shell">
        <Link href="/" className="text-sm font-semibold text-brand hover:underline">
          Back to Top 10 / Search
        </Link>

        {reactionLoading || proportionalityLoading ? (
          <section className="mt-4 space-y-3">
            <div className="h-28 animate-pulse rounded-2xl bg-surface" />
            <div className="h-72 animate-pulse rounded-2xl bg-surface" />
          </section>
        ) : null}

        {errorMessage ? (
          <section className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {errorMessage}
          </section>
        ) : null}

        {companyName ? (
          <>
            <section className="stat-card mt-4 rounded-2xl p-6">
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div>
                  <h1 className="text-3xl font-black">{symbol}</h1>
                  <p className="text-sm text-zinc-700">{companyName}</p>
                  <p className="text-xs uppercase tracking-[0.14em] text-zinc-600">
                    {sector} · Filing {filingDate}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs uppercase tracking-[0.12em] text-zinc-600">Surprise</p>
                  <p className="font-mono text-2xl font-bold text-brand">
                    {formatSignedPercent(surprise)}
                  </p>
                </div>
              </div>
            </section>

            <section className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
              <article className="stat-card rounded-2xl p-4">
                <p className="text-xs uppercase tracking-[0.12em] text-zinc-600">Latest Reaction</p>
                <p className="mt-2 font-mono text-xl font-semibold">
                  {reactionLoading ? "Loading..." : formatSignedPercent(latestReaction)}
                </p>
              </article>
              <article className="stat-card rounded-2xl p-4">
                <p className="text-xs uppercase tracking-[0.12em] text-zinc-600">Expected CAR</p>
                <p className="mt-2 font-mono text-xl font-semibold">
                  {proportionalityLoading
                    ? "Loading..."
                    : formatSignedPercent(proportionalityEntry?.expected_CAR ?? null)}
                </p>
              </article>
              <article className="stat-card rounded-2xl p-4">
                <p className="text-xs uppercase tracking-[0.12em] text-zinc-600">% Diff From Expected</p>
                <p className="mt-2 font-mono text-xl font-semibold">
                  {proportionalityLoading
                    ? "Loading..."
                    : formatSignedPercent(proportionalityEntry?.pct_diff_from_expected ?? null)}
                </p>
              </article>
            </section>

            <section className="mt-5 rounded-2xl border border-emerald-200 bg-white p-4">
              <h2 className="text-lg font-bold">Reaction and Proportionality Model</h2>
              {proportionalityLoading ? (
                <div className="mt-3 h-72 animate-pulse rounded-2xl bg-surface" />
              ) : regressionModel ? (
                <div className="mt-3">
                  <RegressionChart
                    model={regressionModel}
                    proportionality={proportionalityEntry ?? null}
                    surprise={surprise ?? 0}
                    latestReaction={latestReaction}
                  />
                </div>
              ) : (
                <p className="mt-3 text-sm text-zinc-700">
                  Regression model is unavailable for {symbol} and this filing date.
                </p>
              )}
            </section>

            <section className="mt-5 rounded-2xl border border-emerald-200 bg-white p-4">
              <h2 className="text-lg font-bold">Reaction Timeline</h2>
              {reactionLoading ? (
                <div className="mt-3 h-20 animate-pulse rounded-2xl bg-surface" />
              ) : reactionRows.length > 0 ? (
                <div className="mt-3 overflow-auto">
                  <table className="min-w-[320px] text-sm">
                    <thead>
                      <tr className="border-b border-zinc-200 text-left">
                        <th className="px-2 py-2">Date</th>
                        <th className="px-2 py-2">Reaction</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reactionRows.map(([date, value]) => (
                        <tr key={date} className="border-b border-zinc-100">
                          <td className="px-2 py-2 font-mono">{date}</td>
                          <td className="px-2 py-2 font-mono">{formatSignedPercent(value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
              {!reactionLoading && reactionRows.length === 0 ? (
                <p className="mt-2 text-sm text-zinc-700">No reaction timeline data available.</p>
              ) : null}
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
