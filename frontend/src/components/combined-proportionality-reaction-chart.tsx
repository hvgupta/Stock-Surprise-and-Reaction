"use client";

import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Scatter,
  ReferenceDot,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
  Label,
} from "recharts";

import type {
  GeneratedProportionalityPlotResponse,
  RegressionModelValues,
  ProportionalityValues,
} from "@/lib/api";
import type { ContentType } from "recharts/types/component/Label";

type Props = {
  generated: GeneratedProportionalityPlotResponse;
  model: RegressionModelValues;
  proportionality: ProportionalityValues | null;
  surprise: number;
  latestReaction: number | null;
  sector?: string | null;
  isLoading?: boolean;
  xDomain?: [number, number];
};

function formatPercent(value: number) {
  const pct = value * 100;
  if (Math.abs(pct) >= 100) return `${pct.toFixed(0)}%`;
  if (Math.abs(pct) >= 1) return `${pct.toFixed(1)}%`;
  return `${pct.toFixed(2)}%`;
}

function surpriseToZ(model: RegressionModelValues, surprise: number) {
  return (surprise - model.surprise_mean) / (model.surprise_sd + 1e-9);
}

const renderDotLabel: Exclude<ContentType, React.ReactElement> = (props) => {
  const { x, y, value, fill = "#111827", fontSize = 12, viewBox, position } = props ?? {};
  const resolvedX = typeof x === "number" ? x : Number(x ?? 0);
  const resolvedY = typeof y === "number" ? y : Number(y ?? 0);
  const resolvedFontSize = typeof fontSize === "number" ? fontSize : Number(fontSize);
  const cartesianViewBox = viewBox as { x?: number; y?: number } | undefined;

  if (!Number.isFinite(resolvedFontSize) || value === undefined) {
    return null;
  }

  const resolvedViewBoxX = typeof cartesianViewBox?.x === "number" ? cartesianViewBox.x : NaN;
  const resolvedViewBoxY = typeof cartesianViewBox?.y === "number" ? cartesianViewBox.y : NaN;

  const text = String(value);
  const paddingX = 6;
  const paddingY = 3;
  const estimatedWidth = Math.max(text.length * 7, 54);
  const width = estimatedWidth + paddingX * 2;
  const height = resolvedFontSize + paddingY * 2 + 2;
  const centerX = Number.isFinite(resolvedViewBoxX) ? resolvedViewBoxX : resolvedX;
  const centerY = Number.isFinite(resolvedViewBoxY) ? resolvedViewBoxY : resolvedY;
  const positionName = typeof position === "string" ? position : "top";
  const dotGap = 12;
  const labelCenterY = positionName === "bottom"
    ? centerY + dotGap + height / 2
    : centerY - dotGap - height / 2;

  if (!Number.isFinite(centerX) || !Number.isFinite(centerY)) {
    return null;
  }

  return (
    <g transform={`translate(${centerX - width / 2}, ${labelCenterY - height / 2})`}>
      <rect width={width} height={height} rx={8} ry={8} fill="#ffffff" stroke="#e5e7eb" strokeWidth={1} />
      <text
        x={width / 2}
        y={height / 2 + resolvedFontSize / 3 - 1}
        textAnchor="middle"
        fill={fill}
        fontSize={resolvedFontSize}
        fontWeight={600}
      >
        {text}
      </text>
    </g>
  );
};

export default function CombinedProportionalityReactionChart({
  generated,
  model,
  proportionality,
  surprise,
  latestReaction,
  sector = null,
  isLoading = false,
  xDomain,
}: Props) {

  if (isLoading) {
    return (
      <div className="flex h-80 w-full items-center justify-center rounded-2xl border border-teal-200 bg-white p-3 shadow-sm">
        <div className="w-full space-y-3">
          <div className="h-5 w-40 animate-pulse rounded bg-surface" />
          <div className="h-64 animate-pulse rounded-2xl bg-surface" />
          <p className="text-center text-sm text-zinc-600">Loading graph...</p>
        </div>
      </div>
    );
  }

  const z = surpriseToZ(model, surprise);
  const actual = latestReaction ?? proportionality?.actual_CAR ?? 0;
  const expected = model.alpha + model.beta * z;

  const domainMin = xDomain ? xDomain[0] : Math.min(z - 0.5, 0);
  const domainMax = xDomain ? xDomain[1] : Math.max(z + 0.5, 0);

  const linePoints = generated.line_points ?? [];
  if (!linePoints.map(p => p.expected_reaction).find(r => r === expected)) {
    linePoints.push({ z_score: z, expected_reaction: expected });
  }

  const yVals = [
    ...linePoints.map((p) => p.expected_reaction),
    actual,
    expected,
  ];
  const minY = Math.min(...yVals);
  const maxY = Math.max(...yVals);
  const spread = Math.max(maxY - minY, 1e-3);
  const padding = spread * 0.25;
  const expectedIsLower = expected < actual;
  const actualIsLower = actual < expected;
  const expectedLabelPosition = expectedIsLower ? "bottom" : "top";
  const actualLabelPosition = actualIsLower ? "bottom" : "top";
  const expectedLabelDx = 0;
  const actualLabelDx = 0;
  const expectedLabelDy = expectedIsLower ? 16 : -12;
  const actualLabelDy = actualIsLower ? 16 : -12;

  return (
    <div className="rounded-2xl border border-teal-200 bg-white p-3 shadow-sm">
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            margin={{ top: 18, right: 28, bottom: 36, left: 34 }}
            data={linePoints}
          >
            <CartesianGrid strokeDasharray="4 4" stroke="#d8e6df" />
            <XAxis
              dataKey="z_score"
              type="number"
              domain={[domainMin, domainMax]}
              tickFormatter={(v: number) => v.toFixed(2)}
              stroke="#1f2937"
              tickMargin={10}
              height={50}
            >
              <Label value="Surprise z-score" position="bottom" />
            </XAxis>
            <YAxis
              type="number"
              domain={[minY - padding, maxY + padding]}
              tickFormatter={(v: number) => formatPercent(v)}
              stroke="#1f2937"
              tickMargin={10}
              width={90}
            >
              <Label value="Reaction / CAR" angle={-90} position="left" />
            </YAxis>

            <Tooltip
              formatter={(v: number) => formatPercent(v)}
              labelFormatter={(v: number) => `z-score ${Number(v).toFixed(3)}`}
            />

            {/* regression line */}
            <Line
              dataKey="expected_reaction"
              name="Regression line"
              type="monotone"
              stroke="#dc2626"
              strokeWidth={3}
              dot={false}
            />

            {/* model points and outliers */}
            <Scatter data={generated.points} dataKey="reaction" name="Model data points" fill="#111827" />
            {generated.outliers && generated.outliers.length > 0 ? (
              <Scatter data={generated.outliers} dataKey="reaction" name="Excluded outliers" fill="#9ca3af" shape="cross" />
            ) : null}

            {/* guide between expected and actual for this test point */}
            <ReferenceLine
              segment={[{ x: z, y: expected }, { x: z, y: actual }]}
              stroke="#6b7280"
              strokeDasharray="4 4"
            />

            <ReferenceDot
              x={z}
              y={expected}
              r={7}
              fill="#065f46"
              stroke="#ffffff"
              strokeWidth={2}
              isFront
              ifOverflow="extendDomain"
              label={{ value: `Expected ${formatPercent(expected)}`, position: expectedLabelPosition, fill: "#065f46", fontSize: 12, dx: expectedLabelDx, dy: expectedLabelDy, content: renderDotLabel }}
              style={{ cursor: "pointer" }}
            />

            <ReferenceDot
              x={z}
              y={actual}
              r={7}
              fill="#2563eb"
              stroke="#ffffff"
              strokeWidth={2}
              isFront
              ifOverflow="extendDomain"
              label={{ value: `Actual ${formatPercent(actual)}`, position: actualLabelPosition, fill: "#2563eb", fontSize: 12, dx: actualLabelDx, dy: actualLabelDy, content: renderDotLabel }}
              style={{ cursor: "pointer" }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-3 text-sm text-zinc-700">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="text-xs text-zinc-500">Model</div>
            <div className="mt-1 font-mono text-sm text-zinc-900">
              CAR = {model.alpha.toFixed(4)} + {model.beta.toFixed(4)} × z
            </div>
            <div className="mt-1 text-xs text-zinc-500">(z is surprise z-score; CAR reported as decimal)</div>
          </div>

          <div className="flex items-start gap-3">
            <div className="text-right">
              <div className="text-xs text-zinc-500">Expected</div>
              <div className="font-mono text-sm text-emerald-700">{formatPercent(model.alpha + model.beta * ((surprise - model.surprise_mean) / (model.surprise_sd + 1e-9)))}</div>
            </div>
            <div className="text-right">
              <div className="text-xs text-zinc-500">Actual</div>
              <div className="font-mono text-sm text-sky-700">{formatPercent(latestReaction ?? proportionality?.actual_CAR ?? 0)}</div>
            </div>
            {sector ? (
              <div className="ml-2 rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-800">{sector}</div>
            ) : null}
          </div>
        </div>

        <div className="mt-3">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-zinc-700">
            <span className="inline-flex items-center gap-2">
              <span className="inline-block h-1 w-5 rounded bg-red-600" aria-hidden /> Regression line
            </span>
            <span className="inline-flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded-full bg-black" aria-hidden /> Sector data points
            </span>
            <span className="inline-flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded-full bg-[#065f46]" aria-hidden /> Expected point
            </span>
            <span className="inline-flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded-full bg-blue-600" aria-hidden /> Actual point
            </span>
            <span className="inline-flex items-center gap-2">
              <svg className="w-3 h-3 text-gray-500" viewBox="0 0 8 8" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
                <path d="M1 4 L7 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <path d="M4 1 L4 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              Rejected Outliers
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
