import type {
  HealthResponse,
  HealingStats,
  KnowledgeGraphStats,
  RunTaskRequest,
  RunTaskResponse,
  TaskStatusResponse,
} from "../types";

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) || "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

// ── Tasks ──────────────────────────────────────────────────────────────────

export const submitTask = (body: RunTaskRequest) =>
  request<RunTaskResponse>("/tasks/", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const getTask = (taskId: string) =>
  request<TaskStatusResponse>(`/tasks/${taskId}`);

export const listTasks = (limit = 20) =>
  request<TaskStatusResponse[]>(`/tasks/?limit=${limit}`);

// ── Health & Stats ────────────────────────────────────────────────────────

export const getHealth = () => request<HealthResponse>("/health");

export const getHealingStats = () => request<HealingStats>("/healing/stats");

export const getKnowledgeStats = () =>
  request<KnowledgeGraphStats>("/knowledge/stats");
