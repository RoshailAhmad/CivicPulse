# Engineering notes

File and line references point at this repository. Sections marked **(measure)** need
numbers from our own runs, and section 8 is our own story; fill those in before
submitting. Generic answers score zero, so every claim here points at a line.

## 1. Three things that differ between a laptop and a CI runner

| Difference | What freezes it |
|---|---|
| **Python version and OS libraries.** A laptop has whatever Python was installed; the runner has its own. | The image base, pinned to an exact patch and Debian release: [`backend/Dockerfile:2`](../backend/Dockerfile#L2). Every environment runs the same interpreter. |
| **Dependency versions.** `pip install fastapi` gives a different version next month. | Exact pins in [`backend/requirements.txt:1`](../backend/requirements.txt#L1), installed in the builder stage at [`backend/Dockerfile:10`](../backend/Dockerfile#L10). The frontend uses the lockfile with `npm ci` at [`frontend/Dockerfile:5`](../frontend/Dockerfile#L5). |
| **Node version for the frontend build.** | [`frontend/Dockerfile:2`](../frontend/Dockerfile#L2) pins Node and Alpine. Postgres and Redis are pinned the same way, e.g. [`compose.yaml:92`](../compose.yaml#L92). |

## 2. Where our pipeline sits on the CI/CD maturity ladder

*(Use the rung names from Lecture 03, slide 32.)* We are at **continuous delivery with
automated deployment to an ephemeral environment**. Every PR runs lint, types, unit
tests, a Trivy scan, manifest validation and a Compose integration test
([`.github/workflows/ci.yml:171`](../.github/workflows/ci.yml#L171)). Every merge to `main` re-tests, publishes
images by SHA and deploys them to a fresh k3d cluster with a smoke test through the
Ingress ([`.github/workflows/cd.yml:110`](../.github/workflows/cd.yml#L110)).

We are not at the next rung, **continuous deployment to a long-lived production
environment with automated verification and rollback**: our cluster is thrown away after
each run, and rollback is a human decision (docs/RUNBOOK.md, section 5). That rung would
buy us GitOps (Argo CD reconciling the cluster from Git) and progressive delivery
(canary + automatic rollback when error rate or latency crosses a threshold).

## 3. The line that guarantees build-once-deploy-many

[`.github/workflows/cd.yml:157`](../.github/workflows/cd.yml#L157): the deploy job points the prod
overlay at the image built and tested **in this same run**, by commit SHA. Nothing is
rebuilt for deployment. For the frontend, [`frontend/nginx/default.conf.template:20`](../frontend/nginx/default.conf.template#L20)
makes the image environment-independent: the backend address is read from
`BACKEND_URL` when the container starts, not baked into the JavaScript
([`frontend/src/api/client.ts:54`](../frontend/src/api/client.ts#L54)).

Without it, each environment would build its own image. The image you tested would not
be the image you shipped, a dependency could change between the two builds, and "what is
production running?" would have no exact answer.

## 4. What "correct" means for a probabilistic component, and how CI stays deterministic

With a live LLM the same complaint can get different wording or even a different
priority. So "correct" is not "matches an expected string". It means:

1. **The output is always valid.** Category and priority are in our enums, the summary is
   at most 140 characters ([`backend/app/domain.py:39`](../backend/app/domain.py#L39)). Anything else is
   rejected by [`backend/app/providers/triage/base.py:33`](../backend/app/providers/triage/base.py#L33).
2. **The system never fails because the model failed.** Timeout, 429, 5xx, bad JSON all
   end in a rules answer and `201` ([`backend/app/services/triage_service.py:79`](../backend/app/services/triage_service.py#L79)).
3. **Quality is measured, not asserted:** accuracy is judged over many complaints, and we
   record every outcome with latency and fallback status (`/api/meta/providers`).

CI is deterministic by design: [`.github/workflows/ci.yml:62`](../.github/workflows/ci.yml#L62)
pins the deterministic fake, `SimulatedTriage` injects failures on demand
([`backend/app/providers/triage/simulated.py:11`](../backend/app/providers/triage/simulated.py#L11)), and the retry delay is
injected so tests never sleep ([`backend/tests/conftest.py:62`](../backend/tests/conftest.py#L62)). The
key test is [`backend/tests/test_complaints_api.py:20`](../backend/tests/test_complaints_api.py#L20).

## 5. HPA lag **(measure)**

*(From `kubectl get hpa -w` and docs/evidence/hpa-scaling.png.)*

- Offered load started rising at: **__ s**
- First new replica **Ready** at: **__ s**
- Lag: **__ s**

Where the time goes (confirm with your own timestamps):
1. metrics-server scrapes pod CPU on an interval, and the HPA only sees averaged numbers;
2. the HPA controller re-evaluates every 15 s by default;
3. the new pod is scheduled, then its init container runs migrations and the seed
   ([`k8s/base/backend.yaml:42`](../k8s/base/backend.yaml#L42));
4. the startup probe passes, then the readiness probe must pass before the Service sends
   it traffic ([`k8s/base/backend.yaml:102`](../k8s/base/backend.yaml#L102)).

What would reduce it: a faster start (run the seed as a one-off Job instead of on every
pod start), a lower utilisation target or higher `minReplicas` before a known peak, and
scaling on request rate instead of CPU. The lag is why autoscaling doesn't replace
capacity planning: for the first __ seconds of a spike, only the pods already running
serve it.

## 6. Why the VPA runs in Off mode

[`k8s/base/vpa.yaml:13`](../k8s/base/vpa.yaml#L13). The HPA scales on CPU utilisation, which is
*usage ÷ request*. A VPA in Auto mode changes that same request. Under load: VPA raises
the CPU request, so computed utilisation drops, so the HPA removes pods, so each
remaining pod gets more load, so VPA raises the request again. The two controllers fight
over one signal and the replica count and pod sizes swing. Recommender mode lets the VPA
suggest numbers and a human applies them, which is common industry practice for exactly
this reason.

Our loop **(measure)**:

| | CPU request | Memory request |
|---|---|---|
| Our guess ([`k8s/base/backend.yaml:88`](../k8s/base/backend.yaml#L88)) | 100m | 128Mi |
| VPA target | __ | __ |
| VPA lower / upper bound | __ / __ | __ / __ |
| After updating requests, HPA behaviour changed by | __ | |

## 7. The internal network blocks outbound traffic. Where does the LLM call go?

[`compose.yaml:151`](../compose.yaml#L151) means Postgres and Redis can't reach the
internet, which is what we want. The service that calls Groq must reach it, so the
backend joins **both** networks ([`compose.yaml:54`](../compose.yaml#L54)): `internal`
to reach its data, `edge` (a normal bridge with outbound access) for the LLM API. The
frontend is on `edge` only, so it still has no route to the database. The Ollama
container is on `edge` too: it needs internet to pull model weights and holds no citizen
data. Another defensible design would be an egress proxy as the only outbound path,
which gives one place to allow-list `api.groq.com`.

## 8. The failure **(our own story)**

*(Write this yourselves. Something that cost you more than an hour.)*

- **Symptom:**
- **What we wrongly believed first:**
- **The exact command or log line that told us the truth:**
- **The fix:**

## Other decisions we were asked to justify

**Indexes** ([`backend/alembic/versions/0001_create_complaints.py:65`](../backend/alembic/versions/0001_create_complaints.py#L65)):
`(status, priority)` serves the dashboard filter `WHERE status = 'open' AND priority =
'high'`. `created_at` serves the list ordering `ORDER BY created_at DESC LIMIT 20
OFFSET ...` in [`backend/app/repositories/complaints.py:49`](../backend/app/repositories/complaints.py#L49).

**TTL and invalidation on /api/stats** ([`backend/app/services/stats_service.py:18`](../backend/app/services/stats_service.py#L18)):
invalidation on every write makes a new complaint appear in the stats immediately. The
30 s TTL is the safety net if an invalidation is ever lost (Redis blip during a write, a
future code path that forgets to invalidate): stale data can never live longer than 30 s.

**Why the cache has a volume (AOF)** ([`compose.yaml:155`](../compose.yaml#L155)): the stats cache could
be rebuilt, but Redis also holds the **rate-limit counters** and the **24 h triage
cache**. Losing the counters on restart lets a burst through; losing the triage cache
means paying for inferences again. AOF on a volume keeps both across restarts, at the
cost of a little disk I/O.

**The dev bind mount** ([`compose.yaml:51`](../compose.yaml#L51)): right in
`compose.yaml` because edits on the laptop reload instantly. Wrong in
`compose.prod.yaml`, because production must run exactly the code baked into the tested,
scanned image, never whatever happens to be on a disk.

**Build context size (measure):** from the `transferring context` line of `docker build`.

| Context | Without .dockerignore | With .dockerignore |
|---|---|---|
| backend | __ MB | __ kB |
| frontend | __ MB | __ kB |

**Image sizes (measure):** `docker image ls`. Frontend final image: __ MB (target under
~60 MB). Backend: __ MB.

**Triage cache hit rate (measure):** from `/api/meta/providers` after the demo: __ %.
