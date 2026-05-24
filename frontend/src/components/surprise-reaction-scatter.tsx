"use client";

import {
  CartesianGrid,
  Label,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type ScatterDatum = {
  ticker: string;
  company_name: string;
  surprise: number;
  reaction: number;
  sector: string;
};

const SECTOR_COLORS: Record<string, string> = {
  "Information Technology": "#0f766e",
  "Health Care": "#7c3aed",
  "Financials": "#1d4ed8",
  "Consumer Discretionary": "#b45309",
  "Communication Services": "#0891b2",
  "Industrials": "#4d7c0f",
  "Consumer Staples": "#92400e",
  "Energy": "#dc2626",
  "Utilities": "#6b7280",
  "Real Estate": "#9333ea",
  "Materials": "#065f46",
};

const DEFAULT_COLOR = "#64748b";

type CustomDotProps = {
  cx?: number;
  cy?: number;
  payload?: ScatterDatum;
};

function CustomDot({ cx, cy, payload }: CustomDotProps) {
  if (cx === undefined || cy === undefined || !payload) return null;
  const fill = SECTOR_COLORS[payload.sector] ?? DEFAULT_COLOR;
  return <circle cx={cx} cy={cy} r={5} fill={fill} fillOpacity={0.75} stroke={fill} strokeWidth={1} />;
}

type CustomTooltipProps = {
  active?: boolean;
  payload?: Array<{ payload: ScatterDatum }>;
};

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  const sColor = SECTOR_COLORS[d.sector] ?? DEFAULT_COLOR;
  return (
    <div className="rounded-xl border border-emerald-200 bg-white px-3 py-2 shadow-md text-xs max-w-48">
      <p className="font-bold text-foreground">{d.ticker}</p>
      <p className="text-zinc-600 truncate">{d.company_name}</p>
      <p className="mt-0.5 text-xs" style={{ color: sColor }}>{d.sector}</p>
      <div className="mt-1 space-y-0.5">
        <p className={`font-mono ${d.surprise >= 0 ? "text-positive" : "text-negative"}`}>
          Surprise: {d.surprise >= 0 ? "+" : ""}{d.surprise.toFixed(2)}%
        </p>
        <p className={`font-mono ${d.reaction >= 0 ? "text-positive" : "text-negative"}`}>
          CAR: {d.reaction >= 0 ? "+" : ""}{d.reaction.toFixed(2)}%
        </p>
      </div>
    </div>
  );
}

type SurpriseReactionScatterProps = {
  data: ScatterDatum[];
};

export default function SurpriseReactionScatter({ data }: SurpriseReactionScatterProps) {
  if (data.length === 0) {
    return (
      <div className="flex h-80 items-center justify-center text-sm text-zinc-500">
        No companies with reaction data available.
      </div>
    );
  }

  const sectors = Array.from(new Set(data.map((d) => d.sector))).sort();

  return (
    <div>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 16, bottom: 28, left: 16 }}>
            <CartesianGrid strokeDasharray="4 4" stroke="#d8e6df" />
            <XAxis
              type="number"
              dataKey="surprise"
              name="Surprise"
              stroke="#1f2937"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => `${v.toFixed(1)}%`}
            >
              <Label value="EPS Surprise %" offset={-8} position="insideBottom" style={{ fontSize: 11 }} />
            </XAxis>
            <YAxis
              type="number"
              dataKey="reaction"
              name="CAR"
              stroke="#1f2937"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => `${v.toFixed(1)}%`}
            >
              <Label value="Market Reaction (CAR %)" angle={-90} position="insideLeft" style={{ fontSize: 11 }} />
            </YAxis>
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3" }} />
            <ReferenceLine x={0} stroke="#9ca3af" strokeDasharray="3 3" />
            <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="3 3" />
            <Scatter
              data={data}
              shape={(props: unknown) => <CustomDot {...(props as CustomDotProps)} />}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Sector legend */}
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
        {sectors.map((sector) => (
          <div key={sector} className="flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: SECTOR_COLORS[sector] ?? DEFAULT_COLOR }}
            />
            <span className="text-xs text-zinc-600">{sector}</span>
          </div>
        ))}
      </div>

      {/* Quadrant annotations */}
      <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-zinc-500">
        <div className="rounded-lg bg-surface-2 p-2">
          <span className="font-semibold text-positive">↗ Top-right</span>: Beat estimates + market rewarded
        </div>
        <div className="rounded-lg bg-surface-2 p-2">
          <span className="font-semibold text-brand">↘ Bottom-right</span>: Beat estimates + market did NOT reward
        </div>
        <div className="rounded-lg bg-surface-2 p-2">
          <span className="font-semibold" style={{ color: "#b45309" }}>↖ Top-left</span>: Missed + market did NOT punish
        </div>
        <div className="rounded-lg bg-surface-2 p-2">
          <span className="font-semibold text-negative">↙ Bottom-left</span>: Missed + market punished
        </div>
      </div>
    </div>
  );
}
