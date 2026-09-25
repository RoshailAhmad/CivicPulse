import { useCallback, useEffect, useState } from "react";
import {
  api,
  ApiError,
  CATEGORIES,
  PRIORITIES,
  STATUSES,
  type Category,
  type Complaint,
  type ComplaintPage,
  type Priority,
  type Status,
} from "../api/client";
import { CategoryMark, PriorityTag, StatusText } from "../components/Marks";
import { CATEGORY_LABEL, PRIORITY_LABEL, STATUS_LABEL, providerLabel } from "../labels";

const PAGE_SIZE = 10;

interface Filters {
  category?: Category;
  priority?: Priority;
  status?: Status;
}

export function DashboardPage() {
  const [filters, setFilters] = useState<Filters>({});
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ComplaintPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.listComplaints({ ...filters, page, page_size: PAGE_SIZE }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load complaints.");
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    void load();
  }, [load]);

  function setFilter<K extends keyof Filters>(key: K, value: string) {
    setFilters((f) => ({ ...f, [key]: value === "" ? undefined : (value as Filters[K]) }));
    setPage(1);
  }

  function replace(updated: Complaint) {
    setData((d) =>
      d ? { ...d, items: d.items.map((c) => (c.id === updated.id ? updated : c)) } : d,
    );
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <section className="panel">
      <h1>Operations</h1>
      <div className="filters">
        <label>
          Category
          <select value={filters.category ?? ""} onChange={(e) => setFilter("category", e.target.value)}>
            <option value="">All categories</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {CATEGORY_LABEL[c]}
              </option>
            ))}
          </select>
        </label>
        <label>
          Priority
          <select value={filters.priority ?? ""} onChange={(e) => setFilter("priority", e.target.value)}>
            <option value="">All priorities</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {PRIORITY_LABEL[p]}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select value={filters.status ?? ""} onChange={(e) => setFilter("status", e.target.value)}>
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABEL[s]}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      )}
      {loading && !data && <p className="muted">Loading complaints</p>}
      {data && data.items.length === 0 && (
        <p className="notice">No complaints match these filters. Clear a filter to see more.</p>
      )}

      <ul className="queue">
        {data?.items.map((c) => <ComplaintRow key={c.id} complaint={c} onUpdated={replace} />)}
      </ul>

      {data && data.total > 0 && (
        <nav className="pager" aria-label="Pagination">
          <button type="button" className="btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span>
            Page {page} of {totalPages}, {data.total} complaints
          </span>
          <button
            type="button"
            className="btn"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </nav>
      )}
    </section>
  );
}

function ComplaintRow({
  complaint,
  onUpdated,
}: {
  complaint: Complaint;
  onUpdated: (c: Complaint) => void;
}) {
  // The UI offers every status and lets the SERVER decide if the move is
  // allowed. Valid transitions live only in the backend's transition table.
  const others = STATUSES.filter((s) => s !== complaint.status);
  const [target, setTarget] = useState<Status>(others[0]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateStatus(complaint.id, target);
      onUpdated(updated);
      setTarget(STATUSES.filter((s) => s !== updated.status)[0]);
    } catch (err) {
      // 409 message is shown verbatim, exactly as the server wrote it.
      setError(err instanceof ApiError ? err.message : "Couldn't update the status.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <li className={`row row--${complaint.category}`}>
      <div className="row__main">
        <p className="row__summary">{complaint.ai_summary ?? complaint.text}</p>
        <p className="row__meta">
          <CategoryMark category={complaint.category} />
          <PriorityTag priority={complaint.priority} />
          <span>{complaint.location}</span>
          <span className="muted">{providerLabel(complaint.triaged_by)}</span>
        </p>
      </div>
      <div className="row__status">
        <StatusText status={complaint.status} />
        <div className="row__action">
          <label className="visually-hidden" htmlFor={`move-${complaint.id}`}>
            Change status
          </label>
          <select
            id={`move-${complaint.id}`}
            value={target}
            onChange={(e) => setTarget(e.target.value as Status)}
          >
            {others.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABEL[s]}
              </option>
            ))}
          </select>
          <button type="button" className="btn" onClick={save} disabled={saving}>
            {saving ? "Updating" : "Update status"}
          </button>
        </div>
        {error && (
          <p className="field-error" role="alert">
            {error}
          </p>
        )}
      </div>
    </li>
  );
}
