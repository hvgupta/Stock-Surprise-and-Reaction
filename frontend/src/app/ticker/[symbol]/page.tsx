"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import GeneratedProportionalityChart from "@/components/generated-proportionality-chart";
import LoadingSpinner from "@/components/loading-spinner";
import ProportionalityComparisonChart from "@/components/proportionality-comparison-chart";
import ReactionTimelineChart from "@/components/reaction-timeline-chart";
import RegressionChart from "@/components/regression-chart";
import {
  getGeneratedProportionalityPlotData,
  getTickerProportionality,
  getTickerReaction,
  type GeneratedProportionalityPlotResponse,
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
  const [generatedPlotLoading, setGeneratedPlotLoading] = useState(true);
  const [generatedPlotData, setGeneratedPlotData] = useState<GeneratedProportionalityPlotResponse | null>(null);
  const [generatedPlotError, setGeneratedPlotError] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [zRange, setZRange] = useState<number>(2);
  const searchParams = useSearchParams();

  function computeXDomain(model: RegressionModelValues | null, surpriseVal: number | null, halfRange: number) {
    if (!model || surpriseVal === null) return undefined;
    const sd = model.surprise_sd || 1e-9;
    const z = (surpriseVal - model.surprise_mean) / sd;
    return [z - halfRange, z + halfRange] as [number, number];
  }

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
        setGeneratedPlotLoading(false);
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

      const currentSector = searchParams.get("sector") ?? "";
      if (!currentSector) {
        setGeneratedPlotLoading(false);
      } else {
        void (async () => {
          try {
            const payload = await getGeneratedProportionalityPlotData(currentSector, currentFilingDate);
            setGeneratedPlotData(payload);
          } catch (error) {
            const message = error instanceof Error ? error.message : "Failed to load generated plot";
            setGeneratedPlotError(message);
          } finally {
            setGeneratedPlotLoading(false);
          }
        })();
      }
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

    const timelineData = useMemo(() => {
        return reactionRows.map(([date, car], i) => ({
        label: `Day ${i + 1}`,
        date,
        car: car * 100,
        }));
    }, [reactionRows]);

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
  const actualCAR = proportionalityEntry?.actual_CAR ?? null;
  const expectedCAR = proportionalityEntry?.expected_CAR ?? null;
  const pctDiffFromExpected = proportionalityEntry?.pct_diff_from_expected ?? null;

  return (
    <div className="pb-10 pt-8">
      <main className="page-shell">
        <Link href="/" className="text-sm font-semibold text-brand hover:underline">
          ← Back to Top 10 / Search
        </Link>

        {reactionLoading || proportionalityLoading ? (
          <section className="mt-4 grid gap-3 md:grid-cols-2">
            <LoadingSpinner label="Loading reaction data..." className="min-h-28" />
            <LoadingSpinner label="Loading proportionality data..." className="min-h-72" />
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

            {actualCAR !== null && expectedCAR !== null && pctDiffFromExpected !== null ? (
              <section className="mt-5">
                <ProportionalityComparisonChart
                  actualCAR={actualCAR}
                  expectedCAR={expectedCAR}
                  pctDiffFromExpected={pctDiffFromExpected}
                />
              </section>
            ) : null}

            <section className="mt-5 rounded-2xl border border-emerald-200 bg-white p-4">
              <h2 className="text-lg font-bold">Reaction and Proportionality Model</h2>
              {regressionModel ? (
                <div className="mt-3">
                  <div className="mb-3 flex items-center gap-3">
                    <label className="text-sm text-zinc-700">z-range ±</label>
                    <input
                      type="range"
                      min={0.5}
                      max={6}
                      step={0.25}
                      defaultValue={2}
                      onChange={(e) => {
                        const val = Number(e.target.value);
                        setZRange(val);
                      }}
                    />
                    <div className="ml-2 w-12 font-mono">±{zRange.toFixed(2)}</div>
                    <div className="ml-4 flex gap-2">
                      {[1, 2, 3].map((p) => (
                        <button
                          key={p}
                          className="rounded bg-zinc-100 px-2 text-xs"
                          onClick={() => setZRange(p)}
                        >
                          ±{p}
                        </button>
                      ))}
                    </div>
                  </div>
                  <RegressionChart
                    model={regressionModel}
                    proportionality={proportionalityEntry ?? null}
                    surprise={surprise ?? 0}
                    latestReaction={latestReaction}
                    isLoading={reactionLoading || proportionalityLoading}
                    xDomain={computeXDomain(regressionModel, surprise, zRange)}
                  />
                </div>
              ) : proportionalityLoading ? (
                <div className="mt-3 h-72 animate-pulse rounded-2xl bg-surface" />
              ) : (
                <p className="mt-3 text-sm text-zinc-700">
                  Regression model is unavailable for {symbol} and this filing date.
                </p>
              )}
            </section>
            {/* CAR Timeline Chart */}
            <section className="mt-5 rounded-2xl border border-emerald-200 bg-white p-4">
              <h2 className="text-lg font-bold">Reaction Timeline (CAR %)</h2>
              <p className="mt-1 text-xs text-zinc-500">
                Cumulative Abnormal Return accumulating day-by-day after the filing date
              </p>
              <div className="mt-3">
                <ReactionTimelineChart data={timelineData} isLoading={reactionLoading} />
              </div>
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

            <section className="mt-5 rounded-2xl border border-emerald-200 bg-white p-4">
              <h2 className="text-lg font-bold">Generated Proportionality Plot (Interactive)</h2>
              {generatedPlotLoading ? <LoadingSpinner label="Loading generated plot..." className="mt-3 min-h-72" /> : null}
              {!generatedPlotLoading && generatedPlotError ? (
                <p className="mt-3 text-sm text-zinc-700">{generatedPlotError}</p>
              ) : null}
              {!generatedPlotLoading && !generatedPlotError && generatedPlotData ? (
                <div className="mt-3">
                  <GeneratedProportionalityChart data={generatedPlotData} />
                </div>
              ) : null}
              {!generatedPlotLoading && !generatedPlotError && !generatedPlotData ? (
                <p className="mt-3 text-sm text-zinc-700">No generated proportionality plot data available.</p>
              ) : null}
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
