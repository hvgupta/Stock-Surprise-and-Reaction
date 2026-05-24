"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ProportionalityComparisonChartProps = {
  actualCAR: number;
  expectedCAR: number;
  pctDiffFromExpected: number;
  proportionateThreshold?: number;
};

type ChartDatum = {
  label: "Expected" | "Actual";
  value: number;
};

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function formatSignedPercent(value: number): string {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

function formatPercentDiff(value: number): string {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}% vs expected`;
}

export default function ProportionalityComparisonChart({
  actualCAR,
  expectedCAR,
  pctDiffFromExpected,
  proportionateThreshold = 0.1,
}: ProportionalityComparisonChartProps) {
  const isAboveProportionate = pctDiffFromExpected > proportionateThreshold;
  const isBelowProportionate = pctDiffFromExpected < -proportionateThreshold;
  const isProportionate = !isAboveProportionate && !isBelowProportionate;
  const data: ChartDatum[] = [
    { label: "Expected", value: expectedCAR },
    { label: "Actual", value: actualCAR },
  ];

  const minValue = Math.min(0, expectedCAR, actualCAR);
  const maxValue = Math.max(0, expectedCAR, actualCAR);
  const spread = Math.max(maxValue - minValue, 0.01);
  const padding = spread * 0.25;

  return (
    <div className="rounded-2xl border border-emerald-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-zinc-600">
            Actual vs Expected Reaction
          </h3>
          <p className="mt-1 text-xs text-zinc-500">
            {formatPercentDiff(pctDiffFromExpected)}
          </p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            isAboveProportionate
              ? "bg-amber-100 text-amber-800"
              : isBelowProportionate
                ? "bg-red-100 text-red-800"
                : "bg-emerald-100 text-emerald-800"
          }`}
        >
          {isAboveProportionate
            ? "Above proportionate"
            : isBelowProportionate
              ? "Below proportionate"
              : "Proportionate"}
        </span>
      </div>

      <div className="mt-4 h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 20, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="4 4" stroke="#d8e6df" vertical={false} />
            <XAxis dataKey="label" stroke="#1f2937" tick={{ fontSize: 12 }} />
            <YAxis
              type="number"
              domain={[minValue - padding, maxValue + padding]}
              tickFormatter={(value: number) => formatPercent(value)}
              stroke="#1f2937"
              tick={{ fontSize: 11 }}
            />
            <Tooltip
              formatter={(value: number) => formatPercent(value)}
              labelFormatter={(label) => `${label} reaction`}
            />
            <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="3 3" />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {data.map((entry) => (
                <Cell
                  key={entry.label}
                  fill={entry.label === "Actual" ? "#2563eb" : "#111827"}
                  fillOpacity={entry.label === "Actual" ? 0.9 : 0.75}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-zinc-700 sm:grid-cols-3">
        <div className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2">
          <span className="block text-zinc-500">Expected reaction</span>
          <span className="font-mono font-semibold">{formatSignedPercent(expectedCAR)}</span>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2">
          <span className="block text-zinc-500">Actual reaction</span>
          <span className="font-mono font-semibold">{formatSignedPercent(actualCAR)}</span>
        </div>
        <div className="rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2">
          <span className="block text-zinc-500">Difference from expected</span>
          <span className="font-mono font-semibold">{formatSignedPercent(pctDiffFromExpected)}</span>
        </div>
      </div>
    </div>
  );
}
