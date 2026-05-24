"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type SectorBarDatum = {
  sector: string;
  avgSurprise: number;
  count: number;
};

type SectorSurpriseChartProps = {
  data: SectorBarDatum[];
};

type TooltipPayloadEntry = {
  value: number;
  payload: SectorBarDatum;
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
  const pct = (entry.value * 100).toFixed(2);
  const sign = entry.value >= 0 ? "+" : "";
  return (
    <div className="rounded-xl border border-emerald-200 bg-white px-3 py-2 shadow-md text-xs">
      <p className="font-semibold text-foreground">{label}</p>
      <p className={`font-mono mt-0.5 ${entry.value >= 0 ? "text-positive" : "text-negative"}`}>
        Avg Surprise: {sign}{pct}%
      </p>
      <p className="text-zinc-500 mt-0.5">{entry.payload.count} companies</p>
    </div>
  );
}

export default function SectorSurpriseChart({ data }: SectorSurpriseChartProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-zinc-500">
        No sector data available.
      </div>
    );
  }

  const chartHeight = Math.max(data.length * 42, 280);

  return (
    <div style={{ height: chartHeight }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          layout="vertical"
          data={data}
          margin={{ top: 4, right: 48, bottom: 4, left: 4 }}
        >
          <CartesianGrid strokeDasharray="4 4" stroke="#d8e6df" horizontal={false} />
          <XAxis
            type="number"
            tickFormatter={(v: number) => `${(v * 100).toFixed(1)}%`}
            stroke="#1f2937"
            tick={{ fontSize: 11 }}
          />
          <YAxis
            type="category"
            dataKey="sector"
            width={148}
            stroke="#1f2937"
            tick={{ fontSize: 11 }}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "#f0fdf4", opacity: 0.6 }} />
          <ReferenceLine x={0} stroke="#9ca3af" strokeDasharray="3 3" />
          <Bar dataKey="avgSurprise" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.avgSurprise >= 0 ? "#166534" : "#b91c1c"}
                fillOpacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
