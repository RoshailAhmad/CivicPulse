import { render, screen } from "@testing-library/react";
import { StatsPage } from "../src/pages/StatsPage";
import { mockFetch } from "./helpers";

test("shows the cache state from the X-Cache header", async () => {
  mockFetch(
    {
      body: {
        total: 3,
        by_category: { water: 2, electricity: 1, sanitation: 0, roads: 0, streetlights: 0, other: 0 },
        by_priority: { high: 2, normal: 1, low: 0 },
        by_status: { open: 3, in_progress: 0, resolved: 0, rejected: 0 },
      },
      headers: { "X-Cache": "HIT" },
    },
    {
      body: {
        active_provider: "llm:groq",
        recent: [],
        triage_cache: { hits: 1, misses: 3, hit_rate: 0.25 },
      },
    },
  );
  render(<StatsPage />);
  expect(await screen.findByTestId("cache-state")).toHaveTextContent("X-Cache: HIT");
  expect(screen.getByText("25%")).toBeInTheDocument();
});
