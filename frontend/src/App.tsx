import { useState } from "react";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { DashboardPage } from "./pages/DashboardPage";
import { StatsPage } from "./pages/StatsPage";
import { SubmitPage } from "./pages/SubmitPage";

type View = "submit" | "dashboard" | "stats";

const VIEWS: { id: View; label: string }[] = [
  { id: "submit", label: "Report a problem" },
  { id: "dashboard", label: "Operations" },
  { id: "stats", label: "Statistics" },
];

export default function App() {
  const [view, setView] = useState<View>("submit");

  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <p className="brand">
            <span className="brand__marks" aria-hidden="true">
              <i /> <i /> <i /> <i />
            </span>
            CivicPulse
          </p>
          <nav aria-label="Main">
            {VIEWS.map((v) => (
              <button
                key={v.id}
                type="button"
                className="nav-link"
                aria-current={view === v.id ? "page" : undefined}
                onClick={() => setView(v.id)}
              >
                {v.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="page">
        <ErrorBoundary key={view}>
          {view === "submit" && <SubmitPage />}
          {view === "dashboard" && <DashboardPage />}
          {view === "stats" && <StatsPage />}
        </ErrorBoundary>
      </main>
    </>
  );
}
