"use client";

type LoadingSpinnerProps = {
  label?: string;
  className?: string;
};

export default function LoadingSpinner({ label = "Loading...", className = "" }: LoadingSpinnerProps) {
  return (
    <div className={`flex flex-col items-center justify-center gap-3 rounded-2xl border border-emerald-200 bg-white p-6 ${className}`.trim()}>
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-emerald-200 border-t-emerald-600" />
      <p className="text-sm text-zinc-600">{label}</p>
    </div>
  );
}
