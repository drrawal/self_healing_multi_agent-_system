import { Link } from "react-router-dom";
import type { TaskStatusResponse } from "../types";
import { StatusBadge } from "./StatusBadge";

interface Props {
  tasks: TaskStatusResponse[];
}

export function TaskTable({ tasks }: Props) {
  if (tasks.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400 text-sm">
        No tasks yet. Submit one from the Tasks page.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-100 shadow-sm">
      <table className="min-w-full divide-y divide-gray-100 bg-white text-sm">
        <thead className="bg-gray-50">
          <tr>
            {["Objective", "Status", "Repairs", "Failures", "Steps", "Duration"].map((h) => (
              <th
                key={h}
                className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {tasks.map((t) => (
            <tr key={t.task_id} className="hover:bg-gray-50 transition-colors">
              <td className="px-4 py-3 max-w-xs">
                <Link
                  to={`/tasks/${t.task_id}`}
                  className="text-indigo-600 hover:underline font-medium truncate block"
                >
                  {t.objective.length > 60 ? t.objective.slice(0, 57) + "…" : t.objective}
                </Link>
                <span className="text-gray-400 text-xs font-mono">{t.task_id.slice(0, 8)}</span>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={t.status} />
              </td>
              <td className="px-4 py-3 tabular-nums text-gray-700">{t.repair_count}</td>
              <td className="px-4 py-3 tabular-nums text-gray-700">{t.failure_count}</td>
              <td className="px-4 py-3 tabular-nums text-gray-700">{t.step_count}</td>
              <td className="px-4 py-3 tabular-nums text-gray-500">
                {t.duration_ms > 0 ? `${(t.duration_ms / 1000).toFixed(1)}s` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
