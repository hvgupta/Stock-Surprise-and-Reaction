"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type HistogramBucket = {
  label: string;
  count: number;
  isPositive: boolean;
};

type SurpriseHistogramProps = {
  data: HistogramBucket[];
};

type TooltipPayloadEntry = {
  value: number;
  payload: HistogramBucket;
};

type CustomTooltipProps = {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: string;
};

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const entry = payload[0];
  if (!entry) return null;
  return (
    <div className="rounded-xl border border-emerald-200 bg-white px-3 py-2 shadow-md text-xs">
      <p className="font-semibold text-foreground">{label}</p>
      <p className={`font-mono mt-0.5 ${entry.payload.isPositive ? "text-positive" : "text-negative"}`}>
        {entry.value} {entry.value === 1 ? "company" : "companies"}
      </p>
    </div>
  );
}

export default function SurpriseHistogram({ data }: SurpriseHistogramProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-sm text-zinc-500">
        No distribution data available.
      </div>
    );
  }

  return (
    <div className="h-56">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 40, left: 8 }}>
          <CartesianGrid strokeDasharray="4 4" stroke="#d8e6df" vertical={false} />
          <XAxis
            dataKey="label"
            stroke="#1f2937"
            tick={{ fontSize: 10 }}
            angle={-35}
            textAnchor="end"
            interval={0}
          />
          <YAxis
            stroke="#1f2937"
            tick={{ fontSize: 11 }}
            allowDecimals={false}
            label={{ value: "# Companies", angle: -90, position: "insideLeft", offset: 8, style: { fontSize: 10 } }}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f0fdf4", opacity: 0.6 }} />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.isPositive ? "#166534" : "#b91c1c"}
                fillOpacity={0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
