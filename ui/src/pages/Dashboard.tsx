import { useQuery } from "@tanstack/react-query";
import { getHealth, getHealingStats, getKnowledgeStats, listTasks } from "../api/client";
import { MetricCard } from "../components/MetricCard";
import { TaskTable } from "../components/TaskTable";
import { StatusBadge } from "../components/StatusBadge";
import {
  Activity, AlertTriangle, CheckCircle, GitBranch,
  Network, RefreshCw, Zap,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

const COLORS: Record<string, string> = {
  network:    "#6366f1",
  data:       "#f59e0b",
  tool:       "#10b981",
  resource:   "#ef4444",
  logic:      "#8b5cf6",
  dependency: "#06b6d4",
  unknown:    "#9ca3af",
};

export default function Dashboard() {
  const health   = useQuery({ queryKey: ["health"],    queryFn: getHealth,         refetchInterval: 10_000 });
  const healing  = useQuery({ queryKey: ["healing"],   queryFn: getHealingStats,   refetchInterval: 15_000 });
  const kg       = useQuery({ queryKey: ["kg"],        queryFn: getKnowledgeStats, refetchInterval: 30_000 });
  const tasks    = useQuery({ queryKey: ["tasks"],     queryFn: () => listTasks(5), refetchInterval: 10_000 });

  const hStats = healing.data;
  const chartData = hStats
    ? Object.entries(hStats.by_failure_type).map(([type, v]) => ({
        type,
        count:    v.count,
        resolved: v.resolved,
      }))
    : [];

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Self-healing multi-agent system overview</p>
        </div>
        {health.data && (
          <div className="flex items-center gap-2">
            {health.data.status === "ok"
              ? <CheckCircle className="w-4 h-4 text-emerald-500" />
              : <AlertTriangle className="w-4 h-4 text-amber-500" />}
            <StatusBadge status={health.data.status} />
          </div>
        )}
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <MetricCard
          label="Total Tasks"
          value={hStats?.total ?? "—"}
          sub="all time"
          icon={<Activity className="w-4 h-4" />}
          accent="border-indigo-500"
        />
        <MetricCard
          label="Resolution Rate"
          value={hStats ? `${(hStats.resolution_rate * 100).toFixed(1)}%` : "—"}
          sub={`${hStats?.resolved ?? 0} resolved`}
          icon={<CheckCircle className="w-4 h-4" />}
          accent="border-emerald-500"
        />
        <MetricCard
          label="KG Nodes"
          value={kg.data?.nodes ?? "—"}
          sub={`${kg.data?.edges ?? 0} edges`}
          icon={<Network className="w-4 h-4" />}
          accent="border-violet-500"
        />
        <MetricCard
          label="KG Edge Types"
          value={kg.data ? Object.keys(kg.data.node_types).length : "—"}
          sub="distinct node types"
          icon={<GitBranch className="w-4 h-4" />}
          accent="border-cyan-500"
        />
      </div>

      {/* Charts + component health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Failure type chart */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" /> Failures by Type
          </h2>
          {chartData.length === 0 ? (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
              No failure data yet
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} barGap={4}>
                <XAxis dataKey="type" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8 }}
                  cursor={{ fill: "#f3f4f6" }}
                />
                <Bar dataKey="count" name="Total" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry) => (
                    <Cell key={entry.type} fill={COLORS[entry.type] ?? "#9ca3af"} />
                  ))}
                </Bar>
                <Bar dataKey="resolved" name="Resolved" fill="#10b981" radius={[4, 4, 0, 0]} opacity={0.6} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Component health */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-indigo-500" /> Component Health
          </h2>
          {health.data ? (
            <ul className="space-y-2">
              {Object.entries(health.data.components).map(([name, status]) => (
                <li key={name} className="flex items-center justify-between text-sm">
                  <span className="capitalize text-gray-700">{name}</span>
                  <StatusBadge status={status} />
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-gray-400 text-sm">Loading…</div>
          )}
          {health.data?.version && (
            <p className="mt-4 text-xs text-gray-400">v{health.data.version}</p>
          )}
        </div>
      </div>

      {/* Recent tasks */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <RefreshCw className="w-4 h-4 text-gray-400" /> Recent Tasks
          </h2>
        </div>
        {tasks.isLoading ? (
          <div className="text-gray-400 text-sm py-6 text-center">Loading…</div>
        ) : (
          <TaskTable tasks={tasks.data ?? []} />
        )}
      </div>
    </div>
  );
}
