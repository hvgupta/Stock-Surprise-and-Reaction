"use client";

type SectionNavItem = {
  href: string;
  label: string;
  description?: string;
};

type SectionNavProps = {
  title: string;
  items: SectionNavItem[];
  className?: string;
};

export default function SectionNav({ title, items, className = "" }: SectionNavProps) {
  return (
    <aside
      className={`rounded-3xl border border-emerald-200/80 bg-white/85 p-4 shadow-sm backdrop-blur ${className}`.trim()}
    >
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-2">Jump to</p>
      <h2 className="mt-2 text-lg font-black text-foreground">{title}</h2>
      <nav className="mt-4 space-y-2">
        {items.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="group flex items-start justify-between gap-3 rounded-2xl border border-transparent px-3 py-2 text-left transition hover:border-emerald-200 hover:bg-emerald-50"
          >
            <span>
              <span className="block text-sm font-semibold text-foreground">{item.label}</span>
              {item.description ? (
                <span className="mt-0.5 block text-xs leading-5 text-zinc-500">{item.description}</span>
              ) : null}
            </span>
            <span className="mt-0.5 text-xs font-semibold text-brand transition group-hover:translate-x-0.5">↗</span>
          </a>
        ))}
      </nav>
    </aside>
  );
}