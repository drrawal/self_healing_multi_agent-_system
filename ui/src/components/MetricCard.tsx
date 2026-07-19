import type { ReactNode } from "react";

interface Props {
  label: string;
  value: ReactNode;
  sub?: string;
  icon?: ReactNode;
  accent?: string; // tailwind border-l colour class
}

export function MetricCard({ label, value, sub, icon, accent = "border-indigo-500" }: Props) {
  return (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-100 border-l-4 ${accent} p-5 flex gap-4 items-start`}>
      {icon && (
        <div className="p-2 rounded-lg bg-gray-50 text-gray-500 mt-0.5">{icon}</div>
      )}
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</p>
        <p className="mt-1 text-2xl font-bold text-gray-900 truncate">{value}</p>
        {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
      </div>
    </div>
  );
}
