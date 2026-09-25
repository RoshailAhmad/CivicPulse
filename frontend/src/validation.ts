/**
 * Client-side checks that MIRROR the server's rules so citizens get instant
 * feedback. They do not replace the server: the backend (and the database)
 * validate again, and any server error is shown as-is.
 */
import type { ComplaintCreate } from "./api/client";

export const LIMITS = {
  text: { min: 10, max: 2000 },
  location: { min: 3, max: 200 },
  contact: { max: 200 },
} as const;

export type FormErrors = Partial<Record<"text" | "location" | "reporter_contact", string>>;

export function validateComplaint(form: ComplaintCreate): FormErrors {
  const errors: FormErrors = {};
  const text = form.text.trim();
  const location = form.location.trim();
  const contact = (form.reporter_contact ?? "").trim();

  if (text.length < LIMITS.text.min)
    errors.text = `Describe the problem in at least ${LIMITS.text.min} characters.`;
  else if (text.length > LIMITS.text.max)
    errors.text = `Keep the description under ${LIMITS.text.max} characters.`;

  if (location.length < LIMITS.location.min)
    errors.location = `Enter a location of at least ${LIMITS.location.min} characters.`;
  else if (location.length > LIMITS.location.max)
    errors.location = `Keep the location under ${LIMITS.location.max} characters.`;

  if (contact.length > LIMITS.contact.max)
    errors.reporter_contact = `Keep contact details under ${LIMITS.contact.max} characters.`;

  return errors;
}
