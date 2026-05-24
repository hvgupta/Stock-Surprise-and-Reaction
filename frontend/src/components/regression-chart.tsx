"use client";

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
};

type RegressionPoint = {
  zScore: number;
  expected: number;
};

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
}: RegressionChartProps) {
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

  const halfRangeFromZScore = Math.max(Math.abs(surpriseZScore) * 0.5, 0.5);
  const minX: number = surpriseZScore - halfRangeFromZScore;
  const maxX: number = surpriseZScore + halfRangeFromZScore;

  const linePoints = buildLinePoints(model, minX, maxX);

  const yValues = [
    ...linePoints.map((point) => point.expected),
    actualPoint.actual,
    expectedPoint.expected,
  ];
  const [minY, maxY] = addPadding(Math.min(...yValues), Math.max(...yValues));

  return (
    <div className="h-80 w-full rounded-2xl border border-teal-200 bg-white p-3 shadow-sm">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart margin={{ top: 16, right: 16, bottom: 16, left: 4 }} data={linePoints}>
          <CartesianGrid strokeDasharray="4 4" stroke="#d8e6df" />
          <XAxis
            dataKey="zScore"
            type="number"
            domain={[minX, maxX]}
            tickFormatter={(value: number) => value.toFixed(2)}
            stroke="#1f2937"
          >
            <Label value="Surprise z-score" offset={-4} position="insideBottom" />
          </XAxis>
          <YAxis
            type="number"
            domain={[minY, maxY]}
            tickFormatter={(value: number) => `${(value * 100).toFixed(1)}%`}
            stroke="#1f2937"
          >
            <Label value="Reaction / CAR" angle={-90} position="insideLeft" />
          </YAxis>
          <Tooltip
            formatter={(value: number) => `${(value * 100).toFixed(2)}%`}
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
          <ReferenceDot
            x={expectedPoint.zScore}
            y={expectedPoint.expected}
            r={7}
            fill="#111827"
            stroke="#ffffff"
            strokeWidth={2}
            isFront
            ifOverflow="extendDomain"
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
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
