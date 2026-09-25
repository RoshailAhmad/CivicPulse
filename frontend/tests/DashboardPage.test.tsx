import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DashboardPage } from "../src/pages/DashboardPage";
import { COMPLAINT, mockFetch } from "./helpers";

test("surfaces the server's 409 message verbatim on an invalid transition", async () => {
  const serverMessage =
    "Invalid status transition: resolved -> open. Allowed from resolved: none (terminal state)";
  mockFetch(
    { body: { items: [COMPLAINT], total: 1, page: 1, page_size: 10 } },
    { status: 409, body: { detail: serverMessage } },
  );
  render(<DashboardPage />);
  expect(await screen.findByText(COMPLAINT.ai_summary)).toBeInTheDocument();

  const user = userEvent.setup();
  await user.selectOptions(screen.getByLabelText("Change status"), "open");
  await user.click(screen.getByRole("button", { name: "Update status" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(serverMessage);
});
