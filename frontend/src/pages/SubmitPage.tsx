import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, type Complaint, type ComplaintCreate } from "../api/client";
import { CategoryMark, PriorityTag } from "../components/Marks";
import { providerLabel } from "../labels";
import { LIMITS, validateComplaint, type FormErrors } from "../validation";

const EMPTY: ComplaintCreate = { text: "", location: "", reporter_contact: "" };

export function SubmitPage() {
  const [form, setForm] = useState<ComplaintCreate>(EMPTY);
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [result, setResult] = useState<Complaint | null>(null);

  // Honest loading state: AI triage takes seconds, so show real elapsed time.
  useEffect(() => {
    if (!submitting) return;
    setElapsed(0);
    const timer = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [submitting]);

  function update(field: keyof ComplaintCreate, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => ({ ...e, [field]: undefined }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setServerError(null);
    const found = validateComplaint(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      const created = await api.createComplaint({
        text: form.text.trim(),
        location: form.location.trim(),
        reporter_contact: form.reporter_contact?.trim() || null,
      });
      setResult(created);
      setForm(EMPTY);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fieldErrors as FormErrors);
        setServerError(err.message);
      } else {
        setServerError("Something unexpected went wrong. Try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="submit">
      <form className="panel form" onSubmit={onSubmit} noValidate>
        <h1>Report a problem</h1>
        <p className="lede">
          Describe what's wrong in your own words, in English or Roman Urdu. The system reads it,
          sorts it and sends it to the right team.
        </p>

        <label htmlFor="text">What's the problem?</label>
        <textarea
          id="text"
          rows={6}
          value={form.text}
          maxLength={LIMITS.text.max}
          onChange={(e) => update("text", e.target.value)}
          aria-invalid={Boolean(errors.text)}
          aria-describedby="text-help"
          placeholder="Burst water main flooding Street 12 since fajr, water entering ground floors"
        />
        <p id="text-help" className={errors.text ? "field-error" : "hint"}>
          {errors.text ?? `${form.text.trim().length} / ${LIMITS.text.max} characters`}
        </p>

        <label htmlFor="location">Where is it?</label>
        <input
          id="location"
          value={form.location}
          onChange={(e) => update("location", e.target.value)}
          aria-invalid={Boolean(errors.location)}
          aria-describedby="location-help"
          placeholder="Street 12, G-9/2, Islamabad"
        />
        <p id="location-help" className={errors.location ? "field-error" : "hint"}>
          {errors.location ?? "Street, sector or a nearby landmark"}
        </p>

        <label htmlFor="contact">
          Phone or email <span className="optional">(optional)</span>
        </label>
        <input
          id="contact"
          value={form.reporter_contact ?? ""}
          onChange={(e) => update("reporter_contact", e.target.value)}
          aria-invalid={Boolean(errors.reporter_contact)}
          aria-describedby="contact-help"
        />
        <p id="contact-help" className={errors.reporter_contact ? "field-error" : "hint"}>
          {errors.reporter_contact ?? "Only the operations team sees this"}
        </p>

        {serverError && (
          <p className="notice notice--error" role="alert">
            {serverError}
          </p>
        )}

        <button type="submit" className="btn btn--primary" disabled={submitting}>
          {submitting ? "Sending report" : "Send report"}
        </button>
        {submitting && (
          <p className="loading" role="status" aria-live="polite">
            Reading and sorting your report, {elapsed}s elapsed. AI triage usually takes a few
            seconds.
          </p>
        )}
      </form>

      <aside className="ticket-slot" aria-live="polite">
        {result ? (
          <article className={`ticket ticket--${result.category}`} data-testid="result">
            <h2>Report received</h2>
            <dl>
              <dt>Category</dt>
              <dd>
                <CategoryMark category={result.category} />
              </dd>
              <dt>Priority</dt>
              <dd>
                <PriorityTag priority={result.priority} />
              </dd>
              <dt>Summary</dt>
              <dd>{result.ai_summary ?? "No summary"}</dd>
              <dt>Sorted by</dt>
              <dd>
                {providerLabel(result.triaged_by)}{" "}
                <span className="muted">in {result.triage_latency_ms} ms</span>
              </dd>
              <dt>Reference</dt>
              <dd className="ref">{result.id.slice(0, 8)}</dd>
            </dl>
          </article>
        ) : (
          <div className="ticket ticket--empty">
            <h2>Your report ticket appears here</h2>
            <p>After you send a report, you'll see its category, priority and a one-line summary.</p>
          </div>
        )}
      </aside>
    </div>
  );
}
