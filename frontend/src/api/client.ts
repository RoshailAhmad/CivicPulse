/**
 * Typed API client. Every type comes from src/api/schema.ts, which is
 * GENERATED from the backend's OpenAPI schema (npm run gen:api), so if the
 * backend contract changes, `tsc` fails here instead of in production.
 *
 * All calls use the relative path /api: nginx (or the Vite dev proxy)
 * forwards it to the backend. No backend URL is baked into the bundle.
 */
import type { components } from "./schema";

export type Complaint = components["schemas"]["ComplaintOut"];
export type ComplaintCreate = components["schemas"]["ComplaintCreate"];
export type ComplaintPage = components["schemas"]["ComplaintPage"];
export type Stats = components["schemas"]["StatsOut"];
export type ProvidersMeta = components["schemas"]["ProvidersMeta"];
export type Category = Complaint["category"];
export type Priority = Complaint["priority"];
export type Status = Complaint["status"];

// Enum values for filter dropdowns. `satisfies` + the Exclude checks below make
// the compiler fail if the backend adds a value we don't list.
export const CATEGORIES = [
  "water",
  "electricity",
  "sanitation",
  "roads",
  "streetlights",
  "other",
] as const satisfies readonly Category[];
export const PRIORITIES = ["high", "normal", "low"] as const satisfies readonly Priority[];
export const STATUSES = [
  "open",
  "in_progress",
  "resolved",
  "rejected",
] as const satisfies readonly Status[];

type AssertNever<T extends never> = T;
export type _AllCategoriesListed = AssertNever<Exclude<Category, (typeof CATEGORIES)[number]>>;
export type _AllPrioritiesListed = AssertNever<Exclude<Priority, (typeof PRIORITIES)[number]>>;
export type _AllStatusesListed = AssertNever<Exclude<Status, (typeof STATUSES)[number]>>;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly fieldErrors: Record<string, string> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<{ data: T; headers: Headers }> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your connection and try again.");
  }

  if (!response.ok) {
    let body: { detail?: unknown; errors?: { field: string; message: string }[] } = {};
    try {
      body = await response.json();
    } catch {
      /* non-JSON error body */
    }
    const fieldErrors: Record<string, string> = {};
    for (const err of body.errors ?? []) fieldErrors[err.field] = err.message;
    let message =
      typeof body.detail === "string" ? body.detail : `Request failed (HTTP ${response.status})`;
    const retryAfter = response.headers.get("Retry-After");
    if (response.status === 429 && retryAfter) message += ` Try again in ${retryAfter} seconds.`;
    throw new ApiError(response.status, message, fieldErrors);
  }
  return { data: (await response.json()) as T, headers: response.headers };
}

export interface ListParams {
  category?: Category;
  priority?: Priority;
  status?: Status;
  page: number;
  page_size: number;
}

export type CacheState = "HIT" | "MISS" | null;

export const api = {
  async createComplaint(body: ComplaintCreate): Promise<Complaint> {
    return (await request<Complaint>("/complaints", { method: "POST", body: JSON.stringify(body) }))
      .data;
  },

  async listComplaints(params: ListParams): Promise<ComplaintPage> {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") query.set(key, String(value));
    }
    return (await request<ComplaintPage>(`/complaints?${query}`)).data;
  },

  async updateStatus(id: string, status: Status): Promise<Complaint> {
    return (
      await request<Complaint>(`/complaints/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      })
    ).data;
  },

  async getStats(): Promise<{ stats: Stats; cache: CacheState }> {
    const { data, headers } = await request<Stats>("/stats");
    const header = headers.get("X-Cache");
    return { stats: data, cache: header === "HIT" || header === "MISS" ? header : null };
  },

  async getProviders(): Promise<ProvidersMeta> {
    return (await request<ProvidersMeta>("/meta/providers")).data;
  },
};
