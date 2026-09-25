import { useCallback, useEffect, useState } from "react";
import {
  api,
  ApiError,
  CATEGORIES,
  PRIORITIES,
  type CacheState,
  type ProvidersMeta,
  type Stats,
} from "../api/client";
import { CATEGORY_LABEL, PRIORITY_LABEL, providerLabel } from "../labels";

export function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [cache, setCache] = useState<CacheState>(null);
  const [meta, setMeta] = useState<ProvidersMeta | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [statsResult, providers] = await Promise.all([api.getStats(), api.getProviders()]);
      setStats(statsResult.stats);
      setCache(statsResult.cache);
      setMeta(providers);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't load statistics.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const max = stats ? Math.max(1, ...Object.values(stats.by_category)) : 1;

  return (
    <section className="panel stats">
      <div className="stats__head">
        <h1>Statistics</h1>
        <div className="stats__cache">
          {cache && (
            <span className={`cache cache--${cache.toLowerCase()}`} data-testid="cache-state">
              {cache === "HIT"
                ? "Served from Redis cache (X-Cache: HIT)"
                : "Computed fresh from the database (X-Cache: MISS)"}
            </span>
          )}
          <button type="button" className="btn" onClick={() => void load()}>
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <p className="notice notice--error" role="alert">
          {error}
        </p>
      )}

      {stats && (
        <>
          <p className="total">
            <strong>{stats.total}</strong> complaints received
          </p>
          <h2>By category</h2>
          <ul className="bars">
            {CATEGORIES.map((c) => (
              <li key={c} className={`bar bar--${c}`}>
                <span className="bar__label">{CATEGORY_LABEL[c]}</span>
                <span className="bar__track">
                  <span
                    className="bar__fill"
                    style={{ width: `${((stats.by_category[c] ?? 0) / max) * 100}%` }}
                  />
                </span>
                <span className="bar__value">{stats.by_category[c] ?? 0}</span>
              </li>
            ))}
          </ul>
          <h2>By priority</h2>
          <dl className="priority-counts">
            {PRIORITIES.map((p) => (
              <div key={p} className={`priority-count priority-count--${p}`}>
                <dt>{PRIORITY_LABEL[p]}</dt>
                <dd>{stats.by_priority[p] ?? 0}</dd>
              </div>
            ))}
          </dl>
        </>
      )}

      {meta && (
        <>
          <h2>Triage engine</h2>
          <p>
            Active: <strong>{providerLabel(meta.active_provider)}</strong>. Duplicate reports
            answered from cache: <strong>{Math.round(meta.triage_cache.hit_rate * 100)}%</strong>{" "}
            ({meta.triage_cache.hits} of {meta.triage_cache.hits + meta.triage_cache.misses}).
          </p>
          {meta.recent.length > 0 && (
            <div className="table-wrap">
              <table>
                <caption>Last {meta.recent.length} triage calls</caption>
                <thead>
                  <tr>
                    <th scope="col">Sorted by</th>
                    <th scope="col">Time</th>
                    <th scope="col">Fallback</th>
                    <th scope="col">Cache</th>
                  </tr>
                </thead>
                <tbody>
                  {meta.recent.map((r, i) => (
                    <tr key={i}>
                      <td>{providerLabel(String(r.provider))}</td>
                      <td>{String(r.latency_ms)} ms</td>
                      <td>{r.fallback ? "Yes" : "No"}</td>
                      <td>{r.cache_hit ? "Hit" : "Miss"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
