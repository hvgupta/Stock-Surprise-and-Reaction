type SummaryStats = {
  total: number;
  beatCount: number;
  missCount: number;
  avgBeat: number;
  avgMiss: number;
};

type SummaryStatsBannerProps = {
  stats: SummaryStats;
};

function formatSignedPercent(value: number): string {
  const percent = (value * 100).toFixed(2);
  return `${value >= 0 ? "+" : ""}${percent}%`;
}

export default function SummaryStatsBanner({ stats }: SummaryStatsBannerProps) {
  const beatPct = stats.total > 0 ? ((stats.beatCount / stats.total) * 100).toFixed(0) : "0";
  const missPct = stats.total > 0 ? ((stats.missCount / stats.total) * 100).toFixed(0) : "0";

  const statItems = [
    {
      label: "Companies Analyzed",
      value: stats.total.toString(),
      sub: null,
      color: "text-foreground",
    },
    {
      label: "Beat Estimates",
      value: stats.beatCount.toString(),
      sub: `${beatPct}% of total`,
      color: "text-positive",
    },
    {
      label: "Missed Estimates",
      value: stats.missCount.toString(),
      sub: `${missPct}% of total`,
      color: "text-negative",
    },
    {
      label: "Avg Beat Magnitude",
      value: formatSignedPercent(stats.avgBeat),
      sub: "positive surprises",
      color: "text-positive",
    },
    {
      label: "Avg Miss Magnitude",
      value: formatSignedPercent(stats.avgMiss),
      sub: "negative surprises",
      color: "text-negative",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {statItems.map((item) => (
        <article key={item.label} className="stat-card rounded-2xl p-4">
          <p className="text-xs uppercase tracking-[0.12em] text-zinc-600">{item.label}</p>
          <p className={`mt-1 font-mono text-xl font-bold ${item.color}`}>{item.value}</p>
          {item.sub ? (
            <p className="mt-0.5 text-xs text-zinc-500">{item.sub}</p>
          ) : null}
        </article>
      ))}
    </div>
  );
}
