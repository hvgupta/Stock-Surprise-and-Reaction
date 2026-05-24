"use client";

import {
  Area,
  AreaChart,
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
};

type ReactionTimelineChartProps = {
  data: TimelinePoint[];
  isLoading?: boolean;
};

type CustomTooltipProps = {
  active?: boolean;
  payload?: Array<{ value: number; payload: TimelinePoint }>;
};

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const entry = payload[0];
  if (!entry) return null;
  const car = entry.value;
  const sign = car >= 0 ? "+" : "";
  return (
    <div className="rounded-xl border border-emerald-200 bg-white px-3 py-2 shadow-md text-xs">
      <p className="text-zinc-500">{entry.payload.date}</p>
      <p className={`font-mono font-bold mt-0.5 ${car >= 0 ? "text-positive" : "text-negative"}`}>
        CAR: {sign}{car.toFixed(2)}%
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

  const cars = data.map((d) => d.car);
  const maxCar = Math.max(...cars, 0);
  const minCar = Math.min(...cars, 0);
  const range = maxCar - minCar;
  const yPadding = Math.max(range * 0.2, 0.1);

  // Compute where Y=0 falls as a percentage from top (for gradient stop)
  const domainMax = maxCar + yPadding;
  const domainMin = minCar - yPadding;
  const zeroPct = Math.max(0, Math.min(100, (domainMax / (domainMax - domainMin)) * 100));

  const gradientId = "carGradient";

  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset={`${zeroPct}%`} stopColor="#166534" stopOpacity={0.35} />
              <stop offset={`${zeroPct}%`} stopColor="#b91c1c" stopOpacity={0.25} />
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
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="4 4" />
          <Area
            type="monotone"
            dataKey="car"
            stroke="#0f766e"
            strokeWidth={2.5}
            fill={`url(#${gradientId})`}
            dot={{ fill: "#0f766e", r: 5, strokeWidth: 2, stroke: "#ffffff" }}
            activeDot={{ r: 7, strokeWidth: 2, stroke: "#ffffff" }}
            name="CAR %"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
