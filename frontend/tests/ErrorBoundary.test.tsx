import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ErrorBoundary } from "../src/components/ErrorBoundary";

function Broken(): never {
  throw new Error("boom");
}

test("error boundary shows a recovery message instead of a blank page", () => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  render(
    <ErrorBoundary>
      <Broken />
    </ErrorBoundary>,
  );
  expect(screen.getByRole("alert")).toHaveTextContent("This view stopped working");
});
