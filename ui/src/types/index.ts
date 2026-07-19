// Shared TypeScript types mirroring the FastAPI schemas

export type TaskStatus = "completed" | "failed" | "healing" | "running" | "unknown";

export interface RunTaskRequest {
  objective: string;
  max_repairs?: number;
}

export interface RunTaskResponse {
  task_id: string;
  status: TaskStatus;
  repair_count: number;
  failure_count: number;
  metrics: Record<string, number>;
  messages: string[];
}

export interface TaskStatusResponse {
  task_id: string;
  objective: string;
  status: TaskStatus;
  repair_count: number;
  step_count: number;
  failure_count: number;
  duration_ms: number;
  metrics: Record<string, number>;
}

export interface HealingStats {
  total: number;
  resolved: number;
  resolution_rate: number;
  by_failure_type: Record<string, { count: number; resolved: number }>;
}

export interface KnowledgeGraphStats {
  nodes: number;
  edges: number;
  node_types: Record<string, number>;
}

export interface HealthResponse {
  status: string;
  version: string;
  components: Record<string, string>;
}
