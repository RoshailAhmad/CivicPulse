import { validateComplaint } from "../src/validation";

test("client validation mirrors the server's length rules", () => {
  const errors = validateComplaint({ text: "too short", location: "G9", reporter_contact: "" });
  expect(errors.text).toMatch(/at least 10/);
  expect(errors.location).toMatch(/at least 3/);
  expect(validateComplaint({ text: "Water pipe burst in street", location: "G-9/2" })).toEqual({});
});
