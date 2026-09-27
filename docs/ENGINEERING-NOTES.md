# Engineering notes

File and line references point at this repository. Measured numbers come from two runs
of our evidence workflow ([`.github/workflows/evidence.yml`](../.github/workflows/evidence.yml)) on GitHub
Actions runners; the raw outputs are in [`docs/evidence/run-1-guessed-requests/`](evidence/run-1-guessed-requests/)
and [`docs/evidence/run-2-vpa-requests/`](evidence/run-2-vpa-requests/).

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

## 5. HPA lag

Measured from [`hpa-watch.csv`](evidence/run-1-guessed-requests/hpa-watch.csv) (replicas and CPU every
5 s) and the k6 load curve, same load profile in both runs: 30 s warm-up at 5 users,
ramp to 40 users over 60 s, hold 3 min.

| Seconds after test start | Run 1 (request 100m) | Run 2 (request 275m) |
|---|---|---|
| Offered load starts rising | 32 | 32 |
| HPA sees CPU above the 60 % target and wants more pods | 46 | 71 |
| First new pods exist | 62 | 87 |
| All 10 replicas exist | 108 | 134 |
| Load reaches its peak (40 users) | 91 | 91 |

**Lag from load rising to the first extra pods: 30 s in run 1, 55 s in run 2.** Full
capacity (10 pods) took 76 s and 102 s. Both runs served every request: 0 failed out of
84,768 and 85,282, p95 latency 36 ms and 39 ms
([`08-k6-summary.txt`](evidence/run-2-vpa-requests/08-k6-summary.txt)).

Where the time went:
1. **Metrics delay (about 14 s in run 1).** metrics-server reports averaged CPU and our
   `kubectl get hpa -w` output only changes every ~15 s
   ([`08-kubectl-get-hpa-w.txt`](evidence/run-1-guessed-requests/08-kubectl-get-hpa-w.txt)), so the HPA
   always acts on slightly old numbers.
2. **Utilisation has to cross the target.** In run 2 the same traffic is a smaller
   percentage of a bigger request, so it took longer to reach 60 %: that alone added 25 s.
3. **Pod start-up (about 16 s from decision to new pods, then more until Ready).** The new
   pod runs its init container (migrations + seed,
   [`k8s/base/backend.yaml:42`](../k8s/base/backend.yaml#L42)), then the startup and readiness probes must
   pass ([`k8s/base/backend.yaml:105`](../k8s/base/backend.yaml#L105)) before the Service sends it traffic.
4. **The HPA scales in steps** (2 → 4 → 8 → 10), re-evaluating each time.

What would reduce it: run the seed as a one-off Job instead of in every pod's init
container, scale on request rate rather than CPU, or raise `minReplicas` before a known
peak. This is why autoscaling doesn't replace capacity planning: for the first 30 to 55
seconds of a spike, only the pods already running carry it.

## 6. Why the VPA runs in Off mode

[`k8s/base/vpa.yaml:13`](../k8s/base/vpa.yaml#L13). The HPA scales on CPU utilisation, which is
*usage ÷ request*. A VPA in Auto mode changes that same request. Under load: VPA raises
the CPU request, so computed utilisation drops, so the HPA removes pods, so each
remaining pod gets more load, so VPA raises the request again. The two controllers fight
over one signal and the replica count and pod sizes swing. Recommender mode lets the VPA
suggest numbers and a human applies them, which is common industry practice for exactly
this reason.

Our loop, following the assignment's five steps:

| | CPU request | Memory request | Evidence |
|---|---|---|---|
| 1. Our first guess | 100m | 128Mi | run 1 |
| 3. VPA recommendation after the load test | target **271m** (lower 162m) | target **256Mi** | [`run-1/09-vpa.txt`](evidence/run-1-guessed-requests/09-vpa.txt) |
| 4. What we set ([`k8s/base/backend.yaml:91`](../k8s/base/backend.yaml#L91)) | 275m | 256Mi | commit "set backend requests from the VPA recommendation" |
| VPA recommendation after run 2 | target 410m | target 256Mi | [`run-2/09-vpa.txt`](evidence/run-2-vpa-requests/09-vpa.txt) |

**5. What changed about HPA behaviour.** With the guessed 100m request, the pods ran at
**210 to 344 %** of their request during the hold phase: the HPA hit its maximum of 10
replicas and still showed triple the target, so the number told us nothing except "more".
With 275m, the same traffic settled at **75 %** with 10 replicas: close to the 60 % target,
so the utilisation figure became a real signal of how much headroom we have. The
trade-off is sensitivity: scale-out started 25 s later (section 5), because the same CPU
usage is a smaller share of a bigger request. The total CPU used was about the same in
both runs (roughly 2 cores across 10 pods); what changed is that the scheduler now
reserves what the pods really use instead of overcommitting the node.

The upper bounds (68 and 120 cores) are huge because the recommender had only minutes of
history; they shrink as it watches longer. The target rose again to 410m after run 2 because
the pods now had more room to use CPU. We did not chase it: that loop, request goes up,
usage goes up, recommendation goes up, is exactly why a human reviews the numbers instead of
letting Auto mode apply them.

## 7. The internal network blocks outbound traffic. Where does the LLM call go?

[`compose.yaml:151`](../compose.yaml#L151) means Postgres and Redis can't reach the
internet, which is what we want. The service that calls Groq must reach it, so the
backend joins **both** networks ([`compose.yaml:54`](../compose.yaml#L54)): `internal`
to reach its data, `edge` (a normal bridge with outbound access) for the LLM API. The
frontend is on `edge` only, so it still has no route to the database. The Ollama
container is on `edge` too: it needs internet to pull model weights and holds no citizen
data. Another defensible design would be an egress proxy as the only outbound path,
which gives one place to allow-list `api.groq.com`.

## 8. The failure

**Symptom.** Running `docker compose up --build -d` on my laptop returned
`request returned 500 Internal Server Error for API route and version
…dockerDesktopLinuxEngine/_ping`, and every Docker command failed the same way, even
`docker compose ps`.

**What I wrongly believed first.** At first I thought the issue was in our project or
`compose.yaml`. Then I assumed Docker just needed a restart. Earlier I had even believed
it was a PATH or installation problem, because `docker --version` wasn't recognised.

**What told me the truth.** Opening the Docker Desktop window itself showed
*"Virtualization support not detected"* and *"Engine stopped"*: the `docker` command was
installed, but the engine could never start because CPU virtualization was disabled in the
BIOS.

**What I did next.** I tried GitHub Codespaces. The build worked, but the `migrate`
container failed with `psycopg.errors.ConnectionTimeout` even though Postgres logged
*"database system is ready to accept connections"*. A socket test showed `database`
resolving to `172.19.0.3` but the TCP connection timing out, and loosening the network
(`internal: false`) and the firewall rules didn't help: it was Codespaces' own networking.
The final solution was running every live demo on GitHub Actions runners with
[`evidence.yml`](../.github/workflows/evidence.yml), where Docker worked and everything passed.

**What I learned.** The visible error isn't always the real problem, so debug layer by
layer: CLI, then engine, then virtualization, then BIOS. The same stack passing in CI was
the proof that the problem was the environment, not our code. It was frustrating at first,
but it made me check the environment before blaming the code.

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

**Build context size**, Docker's own `transferring context` figure, measured on a working
copy with `.venv` and `node_modules` present, as on a developer laptop
([`run-2/01-build-context.txt`](evidence/run-2-vpa-requests/01-build-context.txt)):

| Context | Without .dockerignore | With .dockerignore |
|---|---|---|
| backend | 109.63 MB | 68.72 kB |
| frontend | 123.70 MB | 233.56 kB |

Without `.dockerignore`, every build would upload the virtualenv and `node_modules`
(and risk copying a local `.env` into an image layer).

**Image sizes** ([`03-image-sizes.txt`](evidence/run-2-vpa-requests/03-image-sizes.txt)): frontend
**58.6 MB** (under the ~60 MB target: nginx plus static files, no Node), backend 288 MB.

**Triage cache hit rate:** three identical complaints gave 1 miss and 2 hits, a hit rate
of **66.7 %** ([`05-triage-cache.json`](evidence/run-2-vpa-requests/05-triage-cache.json)): nine
neighbours reporting one burst main cost one inference.

**Other results from the evidence runs:**

| Check | Result | File |
|---|---|---|
| Frontend → database | `ping: bad address 'database'` (backend → database OK) | [`04-network-isolation.txt`](evidence/run-2-vpa-requests/04-network-isolation.txt) |
| `docker compose down` then `up` | 35 rows before, 35 after | [`06-compose-persistence.txt`](evidence/run-2-vpa-requests/06-compose-persistence.txt) |
| Delete `postgres-0` | 32 rows before, 32 after, same PVC | [`10-k8s-persistence.txt`](evidence/run-2-vpa-requests/10-k8s-persistence.txt) |
| Rolling update under load (10 users) | 0 failed of 5,881 requests | [`11-zero-downtime-k6.txt`](evidence/run-2-vpa-requests/11-zero-downtime-k6.txt) |
| `kubectl rollout undo` and re-applying the overlay | both returned the backend to `civicpulse-backend:dev` | [`12-rollback.txt`](evidence/run-2-vpa-requests/12-rollback.txt) |
