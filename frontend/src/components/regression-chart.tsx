"use client";

import { useState } from "react";

import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  ReferenceDot,
  ReferenceLine,
  Label,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ProportionalityValues, RegressionModelValues } from "@/lib/api";

type RegressionChartProps = {
  model: RegressionModelValues;
  proportionality: ProportionalityValues | null;
  surprise: number;
  latestReaction: number | null;
  isLoading?: boolean;
  xDomain?: [number, number];
};

type RegressionPoint = {
  zScore: number;
  expected: number;
};

function formatPercentValue(value: number): string {
  const percent = value * 100;
  const absPercent = Math.abs(percent);

  if (absPercent >= 1_000_000) {
    return `${(percent / 1_000_000).toFixed(1)}M%`;
  }
  if (absPercent >= 1_000) {
    return `${(percent / 1_000).toFixed(1)}K%`;
  }
  if (absPercent >= 100) {
    return `${percent.toFixed(0)}%`;
  }
  if (absPercent >= 1) {
    return `${percent.toFixed(1)}%`;
  }
  return `${percent.toFixed(2)}%`;
}

function getExpectedCar(model: RegressionModelValues, surprise: number): number {
  const z = (surprise - model.surprise_mean) / (model.surprise_sd + 1e-9);
  return model.alpha + model.beta * z;
}

function getSurpriseZScore(model: RegressionModelValues, surprise: number): number {
  return (surprise - model.surprise_mean) / (model.surprise_sd + 1e-9);
}

function buildLinePoints(
  model: RegressionModelValues,
  minZScore: number,
  maxZScore: number,
): RegressionPoint[] {
  const clampedMinZScore = Math.min(minZScore, maxZScore);
  const clampedMaxZScore = Math.max(minZScore, maxZScore);

  return Array.from({ length: 40 }, (_, index) => {
    const ratio = index / 39;
    const currentZScore = clampedMinZScore + (clampedMaxZScore - clampedMinZScore) * ratio;
    return {
      zScore: currentZScore,
      expected: model.alpha + model.beta * currentZScore,
    };
  });
}

function addPadding(minValue: number, maxValue: number): [number, number] {
  const spread = Math.max(maxValue - minValue, 0.01);
  const padding = spread * 0.35;
  return [minValue - padding, maxValue + padding];
}

export default function RegressionChart({
  model,
  proportionality,
  surprise,
  latestReaction,
  isLoading = false,
  xDomain,
}: RegressionChartProps) {
  const [activePoint, setActivePoint] = useState<"expected" | "actual" | null>(null);

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

  const surpriseZScore = getSurpriseZScore(model, surprise);
  const actualPoint = {
    zScore: surpriseZScore,
    actual: latestReaction ?? proportionality?.actual_CAR ?? 0,
  };
  const expectedPoint = {
    zScore: surpriseZScore,
    expected: getExpectedCar(model, surprise),
  };

  const halfRangeFromZScore = 0.5;
  const minX: number = Math.min(surpriseZScore - halfRangeFromZScore, 0);
  const maxX: number = Math.max(surpriseZScore + halfRangeFromZScore, 0);

  const domainMin = xDomain ? xDomain[0] : minX;
  const domainMax = xDomain ? xDomain[1] : maxX;

  const linePoints = buildLinePoints(model, domainMin, domainMax);

  const yValues = [
    ...linePoints.map((point) => point.expected),
    actualPoint.actual,
    expectedPoint.expected,
  ];
  const [minY, maxY] = addPadding(Math.min(...yValues), Math.max(...yValues));

  const pointInfo =
    activePoint === "expected"
      ? {
          title: "Expected Reaction (Black Dot)",
          zScore: expectedPoint.zScore,
          yValue: expectedPoint.expected,
        }
      : activePoint === "actual"
        ? {
            title: "Actual Reaction (Blue Dot)",
            zScore: actualPoint.zScore,
            yValue: actualPoint.actual,
          }
        : null;

  return (
    <div className="rounded-2xl border border-teal-200 bg-white p-3 shadow-sm">
      <div className="h-80 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart margin={{ top: 18, right: 28, bottom: 36, left: 34 }} data={linePoints}>
          <CartesianGrid strokeDasharray="4 4" stroke="#d8e6df" />
          <XAxis
            dataKey="zScore"
            type="number"
            domain={[domainMin, domainMax]}
            tickFormatter={(value: number) => value.toFixed(2)}
            stroke="#1f2937"
            tickMargin={10}
            height={50}
          >
            <Label value="Surprise z-score" position="bottom" />
          </XAxis>
          <YAxis
            type="number"
            domain={[minY, maxY]}
            tickFormatter={(value: number) => formatPercentValue(value)}
            stroke="#1f2937"
            tickMargin={10}
            width={90}
          >
            <Label value="Reaction / CAR" angle={-90} position="left" />
          </YAxis>
          <Tooltip
            formatter={(value: number) => formatPercentValue(value)}
            labelFormatter={(value: number) => `z-score ${value.toFixed(3)}`}
          />
          <Line
            dataKey="expected"
            type="monotone"
            stroke="#dc2626"
            strokeWidth={3}
            dot={false}
            name="Linear Regression Model"
          />
          <ReferenceLine
            segment={[
              { x: expectedPoint.zScore, y: expectedPoint.expected },
              { x: actualPoint.zScore, y: actualPoint.actual },
            ]}
            stroke="#6b7280"
            strokeDasharray="4 4"
          />
            <ReferenceLine
              segment={[
                { x: 0, y: expectedPoint.expected },
                { x: expectedPoint.zScore, y: expectedPoint.expected },
              ]}
              stroke="#111827"
              strokeDasharray="3 3"
            />
            <ReferenceLine
              segment={[
                { x: 0, y: actualPoint.actual },
                { x: actualPoint.zScore, y: actualPoint.actual },
              ]}
              stroke="#2563eb"
              strokeDasharray="3 3"
            />
            <ReferenceDot
              x={expectedPoint.zScore}
              y={expectedPoint.expected}
              r={7}
              fill="#111827"
              stroke="#ffffff"
              strokeWidth={2}
              isFront
              ifOverflow="extendDomain"
              onMouseEnter={() => setActivePoint("expected")}
              onClick={() => setActivePoint("expected")}
              label={{ value: `Expected ${formatPercentValue(expectedPoint.expected)}`, position: 'top', fill: '#111827', fontSize: 12 }}
              style={{ cursor: "pointer" }}
            />
            <ReferenceDot
              x={actualPoint.zScore}
              y={actualPoint.actual}
              r={7}
              fill="#2563eb"
              stroke="#ffffff"
              strokeWidth={2}
              isFront
              ifOverflow="extendDomain"
              onMouseEnter={() => setActivePoint("actual")}
              onClick={() => setActivePoint("actual")}
              label={{ value: `Actual ${formatPercentValue(actualPoint.actual)}`, position: 'top', fill: '#2563eb', fontSize: 12 }}
              style={{ cursor: "pointer" }}
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
            <span className="h-3 w-3 rounded-full bg-black" /> Expected point
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-blue-600" /> Actual point
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="h-0.5 w-5 border-t border-dashed border-zinc-500" /> Dot-to-axis guide
          </span>
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-700">
        <p className="font-semibold text-zinc-800">Model Parameters</p>
        <p className="mt-1 font-mono">alpha: {model.alpha.toFixed(6)} | beta: {model.beta.toFixed(6)}</p>
      </div>

      <div className="mt-3 rounded-xl border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-700">
        {pointInfo ? (
          <p>
            <span className="font-semibold">{pointInfo.title}</span>
            {` | z-score ${pointInfo.zScore.toFixed(3)} | y ${formatPercentValue(pointInfo.yValue)}`}
          </p>
        ) : (
          <p>
            Hover or click the <span className="font-semibold text-black">black dot</span> (expected)
            {","} and <span className="font-semibold text-blue-600">blue dot</span> (actual) to inspect values.
          </p>
        )}
      </div>
    </div>
  );
}
