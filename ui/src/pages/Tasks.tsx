import { useQuery } from "@tanstack/react-query";
import { listTasks } from "../api/client";
import { TaskTable } from "../components/TaskTable";
import { TaskSubmitForm } from "../components/TaskSubmitForm";
import { ListTodo } from "lucide-react";

export default function Tasks() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["tasks"],
    queryFn:  () => listTasks(50),
    refetchInterval: 8_000,
  });

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <ListTodo className="w-6 h-6 text-indigo-500" /> Tasks
        </h1>
        <button
          onClick={() => refetch()}
          className="text-sm text-indigo-600 hover:underline"
        >
          Refresh
        </button>
      </div>

      <TaskSubmitForm />

      <div>
        <h2 className="text-sm font-semibold text-gray-700 mb-3">All Executions</h2>
        {isLoading ? (
          <div className="text-gray-400 text-sm py-6 text-center">Loading…</div>
        ) : (
          <TaskTable tasks={data ?? []} />
        )}
      </div>
    </div>
  );
}
