import Link from "next/link";

import type { SP500TickerSnapshot } from "@/lib/api";

type SurpriseCardProps = {
  item: SP500TickerSnapshot;
};

function formatSignedPercent(value: number): string {
  const percent = (value * 100).toFixed(2);
  return `${value >= 0 ? "+" : ""}${percent}%`;
}

export default function SurpriseCard({ item }: SurpriseCardProps) {
  const isPositive = item.surprise >= 0;
  const query = new URLSearchParams({
    company_name: item.company_name,
    sector: item.sector,
    filing_date: item.filing_date,
    surprise: String(item.surprise),
  });

  return (
    <Link
      href={`/ticker/${item.ticker}?${query.toString()}`}
      className="stat-card group rounded-2xl p-4 transition-transform duration-200 hover:-translate-y-0.5"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-lg font-bold tracking-wide">{item.ticker}</div>
          <div className="text-xs text-zinc-700">{item.company_name}</div>
        </div>
        <span
          className={`font-mono text-sm font-semibold ${
            isPositive ? "text-positive" : "text-negative"
          }`}
        >
          {formatSignedPercent(item.surprise)}
        </span>
      </div>
    </Link>
  );
}
