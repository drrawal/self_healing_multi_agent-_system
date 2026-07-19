import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { submitTask } from "../api/client";
import type { RunTaskResponse } from "../types";
import { StatusBadge } from "./StatusBadge";
import { Loader2, Send } from "lucide-react";

export function TaskSubmitForm() {
  const qc = useQueryClient();
  const [objective, setObjective] = useState("");
  const [maxRepairs, setMaxRepairs] = useState(3);
  const [result, setResult] = useState<RunTaskResponse | null>(null);

  const mutation = useMutation({
    mutationFn: submitTask,
    onSuccess: (data) => {
      setResult(data);
      setObjective("");
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!objective.trim()) return;
    setResult(null);
    mutation.mutate({ objective: objective.trim(), max_repairs: maxRepairs });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-4">Submit New Task</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Objective
          </label>
          <textarea
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="e.g. Fetch latest sales data and generate a summary report"
            rows={3}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm
                       focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                       resize-none placeholder:text-gray-400"
          />
        </div>

        <div className="flex items-center gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max Repairs
            </label>
            <select
              value={maxRepairs}
              onChange={(e) => setMaxRepairs(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {[0, 1, 2, 3, 5, 10].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={mutation.isPending || !objective.trim()}
            className="ml-auto inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5
                       text-sm font-medium text-white shadow-sm
                       hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors"
          >
            {mutation.isPending ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Running…</>
            ) : (
              <><Send className="w-4 h-4" /> Run Task</>
            )}
          </button>
        </div>

        {mutation.isError && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {(mutation.error as Error).message}
          </div>
        )}
      </form>

      {result && (
        <div className="mt-6 border-t border-gray-100 pt-5 space-y-3">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-gray-700">Result:</span>
            <StatusBadge status={result.status} />
            <span className="text-xs text-gray-400 font-mono">{result.task_id.slice(0, 8)}</span>
          </div>

          <dl className="grid grid-cols-3 gap-3">
            {[
              { label: "Repairs", value: result.repair_count },
              { label: "Failures", value: result.failure_count },
              { label: "Steps", value: result.metrics?.step_count ?? "—" },
            ].map(({ label, value }) => (
              <div key={label} className="bg-gray-50 rounded-lg p-3 text-center">
                <dt className="text-xs text-gray-500">{label}</dt>
                <dd className="text-lg font-bold text-gray-800">{value}</dd>
              </div>
            ))}
          </dl>

          {result.messages.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Last messages</p>
              <ul className="space-y-1">
                {result.messages.map((m, i) => (
                  <li key={i} className="text-xs text-gray-600 bg-gray-50 rounded px-2 py-1">
                    {m}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
