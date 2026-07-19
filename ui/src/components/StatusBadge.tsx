import type { TaskStatus } from "../types";

const MAP: Record<TaskStatus, { bg: string; text: string; dot: string }> = {
  completed: { bg: "bg-emerald-100", text: "text-emerald-800", dot: "bg-emerald-500" },
  failed:    { bg: "bg-red-100",     text: "text-red-800",     dot: "bg-red-500"     },
  healing:   { bg: "bg-amber-100",   text: "text-amber-800",   dot: "bg-amber-500"   },
  running:   { bg: "bg-blue-100",    text: "text-blue-800",    dot: "bg-blue-500"    },
  unknown:   { bg: "bg-gray-100",    text: "text-gray-700",    dot: "bg-gray-400"    },
};

export function StatusBadge({ status }: { status: string }) {
  const s = (status as TaskStatus) in MAP ? (status as TaskStatus) : "unknown";
  const { bg, text, dot } = MAP[s];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${bg} ${text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {status}
    </span>
  );
}
