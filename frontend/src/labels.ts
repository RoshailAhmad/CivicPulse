import type { Category, Priority, Status } from "./api/client";

export const CATEGORY_LABEL: Record<Category, string> = {
  water: "Water",
  electricity: "Electricity",
  sanitation: "Sanitation",
  roads: "Roads",
  streetlights: "Streetlights",
  other: "Other",
};

export const PRIORITY_LABEL: Record<Priority, string> = {
  high: "High priority",
  normal: "Normal priority",
  low: "Low priority",
};

export const STATUS_LABEL: Record<Status, string> = {
  open: "Open",
  in_progress: "In progress",
  resolved: "Resolved",
  rejected: "Rejected",
};

export function providerLabel(triagedBy: string): string {
  switch (triagedBy) {
    case "llm:groq":
      return "AI model (Groq)";
    case "llm:ollama":
      return "AI model (local Ollama)";
    case "rules":
      return "Keyword rules";
    case "rules:fallback":
      return "Keyword rules (AI unavailable, used fallback)";
    case "simulated":
      return "Simulated AI (test mode)";
    default:
      return triagedBy;
  }
}
