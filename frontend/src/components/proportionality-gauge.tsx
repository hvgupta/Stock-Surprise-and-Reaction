"use client";

import React from "react";

type ProportionalityGaugeProps = {
  value: number | null;
  label?: string;
};

export default function ProportionalityGauge({ value, label = "Proportionality" }: ProportionalityGaugeProps) {
  const display = value === null ? "N/A" : `${(value * 100).toFixed(2)}%`;
  return (
    <div className="rounded-2xl border border-zinc-200 bg-white p-4 text-center">
      <div className="text-xs uppercase text-zinc-600">{label}</div>
      <div className="mt-3 text-2xl font-mono font-semibold text-zinc-900">{display}</div>
    </div>
  );
}
