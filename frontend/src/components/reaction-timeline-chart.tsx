"use client";

import {
  Area,
  AreaChart,
  Line,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type TimelinePoint = {
  label: string;
  date: string;
  car: number;
  market?: number;
  total?: number;
};

type ReactionTimelineChartProps = {
  data: TimelinePoint[];
  isLoading?: boolean;
};

type CustomTooltipProps = {
  active?: boolean;
  payload?: Array<{ value: number; payload: TimelinePoint; dataKey?: string }>;
};

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const payloadByKey = payload.reduce((acc: Record<string, any>, p) => {
    if (p && p.dataKey) acc[p.dataKey] = p.value;
    return acc;
  }, {} as Record<string, any>);
  const entry = payload[0].payload;
  const car = payloadByKey.car ?? entry.car;
  const market = payloadByKey.market ?? entry.market;
  const total = payloadByKey.total ?? entry.total;
  const sign = car >= 0 ? "+" : "";
  return (
    <div className="rounded-xl border border-emerald-200 bg-white px-3 py-2 shadow-md text-xs">
      <p className="text-zinc-500">{entry.date}</p>
      <p className="mt-0.5 text-xs text-zinc-600">
        Cumulative Ticker Returns: {total >= 0 ? "+" : ""}{total.toFixed(2)}%
      </p>
      <p className="mt-0.5 text-xs text-zinc-600">
        Cumulative Market Returns: {market >= 0 ? "+" : ""}{market.toFixed(2)}%
      </p>
      <p className={`font-mono font-bold mt-0.5 ${car >= 0 ? "text-positive" : "text-negative"}`}>
        Cumulated actual reaction: {sign}{car.toFixed(2)}%
      </p>
    </div>
  );
}

export default function ReactionTimelineChart({ data, isLoading = false }: ReactionTimelineChartProps) {
  if (isLoading) {
    return <div className="h-56 w-full animate-pulse rounded-2xl bg-surface" />;
  }

  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-zinc-500">
        No reaction timeline data available.
      </div>
    );
  }

  console.log("Rendering ReactionTimelineChart with data:", data);

  const ys = data.flatMap(d => [d.car, d.market, d.total]).filter((v): v is number => typeof v === "number");
  console.log("Extracted y-values for domain calculation:", ys);
  const domainMin = Math.min(...ys, 0);
  const domainMax = Math.max(...ys, 0);

  const gradientId = "carGradient";
  const marketGradientId = "marketGradient";

  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0f766e" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#0f766e" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id={marketGradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1d4ed8" stopOpacity={0.32} />
              <stop offset="100%" stopColor="#1d4ed8" stopOpacity={0.06} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="4 4" stroke="#d8e6df" />
          <XAxis
            dataKey="label"
            stroke="#1f2937"
            tick={{ fontSize: 12 }}
          />
          <YAxis
            stroke="#1f2937"
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => `${v.toFixed(1)}%`}
            domain={[domainMin, domainMax]}
            label={{ value: "Cumulative returns", angle: -90, position: "insideLeft", dy: -10 }}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="4 4" />
          <Area
            type="monotone"
            dataKey="total"
            stroke="#0f766e"
            strokeWidth={2.5}
            fill={`url(#${gradientId})`}
            dot={{ fill: "#0f766e", r: 5, strokeWidth: 2, stroke: "#ffffff" }}
            activeDot={{ r: 7, strokeWidth: 2, stroke: "#ffffff" }}
            name="Total %"
          />
          <Area
            type="monotone"
            dataKey="market"
            stroke="#1d4ed8"
            strokeWidth={2}
            fill={`url(#${marketGradientId})`}
            dot={false}
            activeDot={{ r: 5, strokeWidth: 2, stroke: "#ffffff" }}
            name="Market %"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
