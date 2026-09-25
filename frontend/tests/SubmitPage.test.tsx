import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SubmitPage } from "../src/pages/SubmitPage";
import { COMPLAINT, mockFetch } from "./helpers";

async function fillAndSend(text: string, location: string) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("What's the problem?"), text);
  await user.type(screen.getByLabelText("Where is it?"), location);
  await user.click(screen.getByRole("button", { name: "Send report" }));
}

test("blocks a too-short report without calling the server", async () => {
  const fetchMock = mockFetch();
  render(<SubmitPage />);
  await fillAndSend("short", "G-9/2");
  expect(screen.getByText(/at least 10 characters/)).toBeInTheDocument();
  expect(fetchMock).not.toHaveBeenCalled();
});

test("shows the category, priority, summary and provider returned by the server", async () => {
  mockFetch({ status: 201, body: COMPLAINT });
  render(<SubmitPage />);
  await fillAndSend("Burst water main flooding Street 12", "Street 12, G-9/2");
  const ticket = await screen.findByTestId("result");
  expect(ticket).toHaveTextContent("Water");
  expect(ticket).toHaveTextContent("High priority");
  expect(ticket).toHaveTextContent("Burst water main flooding homes on Street 12");
  expect(ticket).toHaveTextContent("AI model (Groq)");
});

test("shows the server's field error and rate-limit message", async () => {
  mockFetch({
    status: 429,
    body: { detail: "Too many complaints from this address." },
    headers: { "Retry-After": "42" },
  });
  render(<SubmitPage />);
  await fillAndSend("Burst water main flooding Street 12", "Street 12, G-9/2");
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Too many complaints from this address. Try again in 42 seconds.",
  );
});
