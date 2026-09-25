import { vi } from "vitest";

/** Replaces window.fetch with a queue of canned responses. No real network. */
export function mockFetch(
  ...responses: { status?: number; body: unknown; headers?: Record<string, string> }[]
) {
  const fn = vi.fn();
  for (const r of responses) {
    fn.mockResolvedValueOnce(
      new Response(JSON.stringify(r.body), {
        status: r.status ?? 200,
        headers: { "Content-Type": "application/json", ...r.headers },
      }),
    );
  }
  vi.stubGlobal("fetch", fn);
  return fn;
}

export const COMPLAINT = {
  id: "0b8e7a2c-1111-4222-8333-444455556666",
  text: "Burst water main flooding Street 12 since fajr",
  location: "Street 12, G-9/2",
  reporter_contact: null,
  category: "water",
  priority: "high",
  status: "resolved",
  ai_summary: "Burst water main flooding homes on Street 12",
  triaged_by: "llm:groq",
  triage_latency_ms: 412,
  created_at: "2026-09-24T10:00:00Z",
  updated_at: "2026-09-24T10:00:00Z",
};
