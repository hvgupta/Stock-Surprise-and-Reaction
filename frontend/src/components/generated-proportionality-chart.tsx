"use client";

import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { GeneratedProportionalityPlotResponse } from "@/lib/api";

type GeneratedProportionalityChartProps = {
  data: GeneratedProportionalityPlotResponse;
  xDomain?: [number, number];
};

function formatPercent(value: number): string {
  const percent = value * 100;
  const abs = Math.abs(percent);
  if (abs >= 1000) return `${(percent / 1000).toFixed(1)}K%`;
  if (abs >= 100) return `${percent.toFixed(0)}%`;
  if (abs >= 1) return `${percent.toFixed(1)}%`;
  return `${percent.toFixed(2)}%`;
}

export default function GeneratedProportionalityChart({ data, xDomain }: GeneratedProportionalityChartProps) {
  const outliers = data.outliers ?? [];

  // compute full z-range across line_points, points and outliers so the X axis (and
  // regression line) spans the entire plotted domain
  const allZs = [
    ...(data.line_points?.map((p) => p.z_score) ?? []),
    ...(data.points?.map((p) => p.z_score) ?? []),
    ...(outliers?.map((p) => p.z_score) ?? []),
  ];
  const minZ = allZs.length ? Math.min(...allZs) : -3;
  const maxZ = allZs.length ? Math.max(...allZs) : 3;
  const domain = xDomain ?? [minZ, maxZ];

  return (
    <div className="rounded-2xl border border-emerald-200 bg-white p-3">
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            margin={{ top: 16, right: 24, bottom: 32, left: 36 }}
            data={data.line_points}
          >
            <CartesianGrid strokeDasharray="4 4" stroke="#d8e6df" />
            <XAxis
              dataKey="z_score"
              type="number"
              domain={domain}
              allowDataOverflow={true}
              tickFormatter={(value: number) => value.toFixed(2)}
              tickMargin={10}
              height={48}
              label={{ value: "Surprise z-score", position: "bottom" }}
            />
            <YAxis
              type="number"
              tickFormatter={(value: number) => formatPercent(value)}
              tickMargin={10}
              width={90}
              label={{ value: "Reaction / CAR", angle: -90, position: "left" }}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload || payload.length === 0) return null;

                // dedupe by reaction value (prefer model data points over outliers)
                const seen = new Set<number>();
                const items = [] as any[];
                for (const p of payload) {
                  const val = p?.payload?.reaction ?? p?.value;
                  if (val == null) continue;
                  const rounded = Math.round(val * 1e9) / 1e9;
                  if (seen.has(rounded)) continue;
                  seen.add(rounded);
                  items.push(p);
                }

                return (
                  <div className="rounded border bg-white p-2 text-xs text-zinc-800">
                    <div className="mb-1 font-medium">z-score {Number(label).toFixed(3)}</div>
                    {items.map((it: any, idx: number) => (
                      <div key={idx} className="flex justify-between">
                        <div className="text-zinc-600">{it.name}</div>
                        <div className="font-mono">{formatPercent(it.payload?.reaction ?? it.value)}</div>
                      </div>
                    ))}
                  </div>
                );
              }}
            />
            <Line
              dataKey="expected_reaction"
              name="Regression line"
              type="monotone"
              stroke="#dc2626"
              strokeWidth={2.5}
              dot={false}
            />
            <Scatter
              data={data.points}
              dataKey="reaction"
              name="Model data points"
              fill="#111827"
            />
            <Scatter
              data={outliers}
              dataKey="reaction"
              name="Excluded outliers"
              fill="#9ca3af"
              shape="cross"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-700">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="inline-flex items-center gap-2">
            <span className="h-0.5 w-5 bg-red-600" /> Regression line
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-black" /> Model data points
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="text-sm leading-none text-zinc-500">✕</span> Excluded outliers
          </span>
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-mono text-zinc-700">
        alpha: {data.alpha.toFixed(6)} | beta: {data.beta.toFixed(6)} | mean: {data.x_mean.toFixed(6)} | sd: {data.x_sd.toFixed(6)}
      </div>
    </div>
  );
}
