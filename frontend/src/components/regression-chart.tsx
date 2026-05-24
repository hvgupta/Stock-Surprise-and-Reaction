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
};

type RegressionPoint = {
  surprise: number;
  expected: number;
};

function getExpectedCar(model: RegressionModelValues, surprise: number): number {
  const z = (surprise - model.surprise_mean) / (model.surprise_sd + 1e-9);
  return model.alpha + model.beta * z;
}

function buildLinePoints(
  model: RegressionModelValues,
  minSurprise: number,
  maxSurprise: number,
): RegressionPoint[] {
  const clampedMinSurprise = Math.min(minSurprise, maxSurprise);
  const clampedMaxSurprise = Math.max(minSurprise, maxSurprise);

  return Array.from({ length: 40 }, (_, index) => {
    const ratio = index / 39;
    const currentSurprise =
      clampedMinSurprise + (clampedMaxSurprise - clampedMinSurprise) * ratio;
    return {
      surprise: currentSurprise,
      expected: getExpectedCar(model, currentSurprise),
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
}: RegressionChartProps) {
  const actualPoint = {
    surprise,
    actual: latestReaction ?? proportionality?.actual_CAR ?? 0,
  };
  const expectedPoint = {
    surprise,
    expected: getExpectedCar(model, surprise),
  };

  const widestModelRange = 4 * (model.surprise_sd + 1e-9);
  const xExtent = Math.max(Math.abs(surprise), Math.abs(model.surprise_mean) + widestModelRange, 0.05);
  const minX = surprise >= 0 ? 0 : -xExtent;
  const maxX = surprise >= 0 ? xExtent : 0;

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
            dataKey="surprise"
            type="number"
            domain={[minX, maxX]}
            tickFormatter={(value: number) => `${(value * 100).toFixed(1)}%`}
            stroke="#1f2937"
          >
            <Label value="Surprise" offset={-4} position="insideBottom" />
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
            labelFormatter={(value: number) => `Surprise ${(value * 100).toFixed(2)}%`}
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
              { x: expectedPoint.surprise, y: expectedPoint.expected },
              { x: actualPoint.surprise, y: actualPoint.actual },
            ]}
            stroke="#6b7280"
            strokeDasharray="4 4"
          />
          <ReferenceDot
            x={expectedPoint.surprise}
            y={expectedPoint.expected}
            r={7}
            fill="#111827"
            stroke="#ffffff"
            strokeWidth={2}
            isFront
            ifOverflow="extendDomain"
          />
          <ReferenceDot
            x={actualPoint.surprise}
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
