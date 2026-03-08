/**
 * API client — all fetch calls go through here.
 * No fetch() calls in components directly.
 */

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "/api/backend";

let _token: string | null = null;
let _tokenPromise: Promise<string | null> | null = null;

async function getAuthToken() {
  if (_token) return _token;
  if (_tokenPromise) return _tokenPromise;

  _tokenPromise = fetch(`${BACKEND}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sub: "dev_user" }),
  })
    .then((res) => {
      if (res.ok) {
        return res.json().then((data) => {
          _token = data.access_token;
          return _token;
        });
      }
      return null;
    })
    .catch((e) => {
      console.error("Failed to get auth token", e);
      return null;
    });

  return _tokenPromise;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...init?.headers,
  };
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${BACKEND}${path}`, {
      headers,
      cache: "no-store",
      ...init,
    });
    if (!res.ok) {
      const body = await res.text();
      let parsedBody;
      try {
        parsedBody = JSON.parse(body);
      } catch (e) {
        parsedBody = body;
      }
      console.error(`API Error ${res.status}: ${path}`, parsedBody);
      throw new Error(
        `[Backend Error ${res.status}] ${path}: ${
          typeof parsedBody === "string"
            ? parsedBody
            : JSON.stringify(parsedBody)
        }`,
      );
    }
    return res.json() as Promise<T>;
  } catch (error) {
    console.error(`Fetch failed: ${path}`, error);
    throw error;
  }
}

export interface RunTaskPayload {
  task: string;
  context_docs?: string[];
  actor?: string;
}

export interface RunTaskResponse {
  task_id: string;
  status: string;
}

export async function runTask(
  payload: RunTaskPayload,
): Promise<RunTaskResponse> {
  return apiFetch<RunTaskResponse>("/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getMCPStatus(): Promise<
  Record<string, Record<string, unknown>>
> {
  return apiFetch("/mcp/status");
}

export async function getAuditLog(page = 1, pageSize = 20, taskId?: string) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (taskId) params.set("task_id", taskId);
  return apiFetch(`/audit?${params.toString()}`);
}

export async function approveHITL(taskId: string, actor = "user", reason = "") {
  return apiFetch(`/hitl/${taskId}/approve`, {
    method: "POST",
    body: JSON.stringify({ actor, reason }),
  });
}

export async function rejectHITL(taskId: string, actor = "user", reason = "") {
  return apiFetch(`/hitl/${taskId}/reject`, {
    method: "POST",
    body: JSON.stringify({ actor, reason }),
  });
}

export async function getTasks(page = 1, pageSize = 50, status?: string) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status) params.set("status", status);
  return apiFetch<{ tasks: any[]; count: number }>(
    `/tasks?${params.toString()}`,
  );
}
export async function deleteTask(taskId: string) {
  return apiFetch(`/tasks/${taskId}`, { method: "DELETE" });
}

export async function clearTasks() {
  return apiFetch("/tasks", { method: "DELETE" });
}
