import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getTask } from "../api/client";
import { StatusBadge } from "../components/StatusBadge";
import { ArrowLeft, Clock, Wrench, AlertTriangle, BarChart2 } from "lucide-react";

export default function TaskDetail() {
  const { taskId } = useParams<{ taskId: string }>();
  const { data, isLoading, error } = useQuery({
    queryKey: ["task", taskId],
    queryFn:  () => getTask(taskId!),
    enabled:  !!taskId,
  });

  if (isLoading) {
    return (
      <div className="p-8 text-gray-400 text-sm">Loading task…</div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 space-y-4">
        <Link to="/tasks" className="text-indigo-600 text-sm flex items-center gap-1 hover:underline">
          <ArrowLeft className="w-4 h-4" /> Back to Tasks
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          {(error as Error)?.message ?? "Task not found"}
        </div>
      </div>
    );
  }

  const metrics = data.metrics ?? {};

  return (
    <div className="p-8 space-y-6 max-w-3xl">
      <Link to="/tasks" className="text-indigo-600 text-sm flex items-center gap-1 hover:underline">
        <ArrowLeft className="w-4 h-4" /> Back to Tasks
      </Link>

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 space-y-3">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-lg font-bold text-gray-900 leading-snug">{data.objective}</h1>
          <StatusBadge status={data.status} />
        </div>
        <p className="text-xs text-gray-400 font-mono">{data.task_id}</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: "Duration",  value: `${(data.duration_ms / 1000).toFixed(2)}s`, icon: <Clock className="w-4 h-4" /> },
          { label: "Repairs",   value: data.repair_count,   icon: <Wrench className="w-4 h-4" /> },
          { label: "Failures",  value: data.failure_count,  icon: <AlertTriangle className="w-4 h-4" /> },
          { label: "Steps",     value: data.step_count,     icon: <BarChart2 className="w-4 h-4" /> },
        ].map(({ label, value, icon }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 flex gap-3 items-start">
            <div className="text-gray-400 mt-0.5">{icon}</div>
            <div>
              <p className="text-xs text-gray-500">{label}</p>
              <p className="text-xl font-bold text-gray-900">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Metrics table */}
      {Object.keys(metrics).length > 0 && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Metrics</h2>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2">
            {Object.entries(metrics).map(([key, val]) => (
              <div key={key} className="flex justify-between text-sm border-b border-gray-50 pb-1">
                <dt className="text-gray-500 capitalize">{key.replace(/_/g, " ")}</dt>
                <dd className="font-medium text-gray-800 tabular-nums">
                  {typeof val === "number" ? val.toFixed(3) : String(val)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
}
