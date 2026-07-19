import { useQuery } from "@tanstack/react-query";
import { getKnowledgeStats } from "../api/client";
import { MetricCard } from "../components/MetricCard";
import { BookOpen, GitBranch, Network } from "lucide-react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

const PALETTE = [
  "#6366f1", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#06b6d4", "#f97316", "#84cc16",
];

export default function Knowledge() {
  const { data, isLoading } = useQuery({
    queryKey:        ["kg"],
    queryFn:         getKnowledgeStats,
    refetchInterval: 30_000,
  });

  const pieData = data
    ? Object.entries(data.node_types).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div className="p-8 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
        <BookOpen className="w-6 h-6 text-violet-500" /> Knowledge Graph
      </h1>

      {isLoading ? (
        <div className="text-gray-400 text-sm">Loading…</div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <MetricCard
              label="Total Nodes"
              value={data?.nodes ?? 0}
              icon={<Network className="w-4 h-4" />}
              accent="border-violet-500"
            />
            <MetricCard
              label="Total Edges"
              value={data?.edges ?? 0}
              icon={<GitBranch className="w-4 h-4" />}
              accent="border-indigo-500"
            />
            <MetricCard
              label="Node Types"
              value={Object.keys(data?.node_types ?? {}).length}
              sub="distinct categories"
              icon={<BookOpen className="w-4 h-4" />}
              accent="border-cyan-500"
            />
          </div>

          {pieData.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
              <h2 className="text-sm font-semibold text-gray-700 mb-4">Node Distribution</h2>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={({ name, percent }) =>
                      `${name} ${(percent * 100).toFixed(0)}%`
                    }
                    labelLine={false}
                  >
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Node Types Breakdown</h2>
            <table className="min-w-full text-sm divide-y divide-gray-100">
              <thead>
                <tr>
                  <th className="text-left py-2 pr-4 text-xs text-gray-500 font-semibold uppercase">Type</th>
                  <th className="text-right py-2 text-xs text-gray-500 font-semibold uppercase">Count</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {Object.entries(data?.node_types ?? {}).map(([type, count]) => (
                  <tr key={type}>
                    <td className="py-2 pr-4 capitalize text-gray-700">{type}</td>
                    <td className="py-2 text-right font-mono text-gray-800">{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
