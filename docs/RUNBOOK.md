# Runbook

Commands are for Windows PowerShell unless marked. Run them from the repository root.

## 1. Run locally with Docker Compose

```powershell
copy .env.example .env
docker compose up --build            # first run: 5-10 minutes
```

- App: http://127.0.0.1:8080, API docs: http://127.0.0.1:8000/docs
- Stop, keeping data: `docker compose down`. Start again: `docker compose up`.
- Stop and delete all data: `docker compose down -v`.

**Persistence check (demo):** submit a complaint, run `docker compose down` then
`docker compose up -d`, and the complaint is still there.

**Network isolation check (demo):** this must FAIL with `bad address 'database'`:

```powershell
docker compose exec frontend ping -c 1 database
```

**Offline AI (optional):**

```powershell
docker compose --profile ollama up -d
docker compose exec ollama ollama pull llama3.2:1b
# then set TRIAGE_PROVIDER=ollama in .env and: docker compose up -d backend
```

## 2. Deploy to Kubernetes (local k3d cluster)

### One-time tools

`kubectl` comes with Docker Desktop. Install k3d and k6:

```powershell
mkdir $HOME\bin -Force
curl.exe -L -o $HOME\bin\k3d.exe https://github.com/k3d-io/k3d/releases/download/v5.7.5/k3d-windows-amd64.exe
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path","User") + ";$HOME\bin", "User")
winget install k6 --source winget
```

Close and reopen PowerShell, then check: `k3d version`, `kubectl version --client`, `k6 version`.

### Create the cluster and deploy

```powershell
k3d cluster create civicpulse --agents 1 -p "8081:80@loadbalancer"
docker build -t civicpulse-backend:dev backend
docker build -t civicpulse-frontend:dev frontend
k3d image import civicpulse-backend:dev civicpulse-frontend:dev -c civicpulse
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/vertical-pod-autoscaler-1.2.1/vertical-pod-autoscaler/deploy/vpa-v1-crd-gen.yaml
kubectl apply -k k8s/overlays/dev
kubectl -n civicpulse rollout status deployment/backend --timeout=300s
kubectl -n civicpulse get pods,svc,ingress,hpa,pvc
```

Open **http://127.0.0.1:8081**. The dev overlay uses placeholder secrets and keyword
triage. To use Groq on the cluster:

```powershell
kubectl -n civicpulse create secret generic civicpulse-secrets --from-literal=POSTGRES_USER=civicpulse --from-literal=POSTGRES_PASSWORD=change-me --from-literal=LLM_API_KEY=YOUR_KEY --dry-run=client -o yaml | kubectl apply -f -
kubectl -n civicpulse patch configmap civicpulse-config -p '{\"data\":{\"TRIAGE_PROVIDER\":\"llm\"}}'
kubectl -n civicpulse rollout restart deployment/backend
```

**Persistence check (demo):** note the complaint count on the Statistics page, then
`kubectl -n civicpulse delete pod postgres-0`. The StatefulSet recreates the pod on the
same PersistentVolumeClaim, and the count is unchanged.

### Production deploys

Production deploys happen only through `cd.yml` on a push to `main`: tests, build, push to
GHCR as `:<commit-sha>`, deploy that SHA. Nobody applies `overlays/prod` by hand.

## 3. Autoscaling

### HPA load test

Needs three PowerShell windows:

```powershell
# Window 1: watch the HPA (screenshot this for the evidence)
kubectl -n civicpulse get hpa backend-hpa -w
# Window 2: record replicas every 5 s to load/hpa-watch.csv
python scripts/record_hpa.py
# Window 3: offered load (about 5.5 minutes)
k6 run --out csv=load/k6-results.csv load/k6-script.js
```

Then stop the recorder (Ctrl+C) and draw the chart:

```powershell
pip install matplotlib
python scripts/plot_hpa.py          # writes docs/evidence/hpa-scaling.png
```

If the HPA shows `<unknown>/60%`, metrics-server isn't ready yet (wait a minute) or a pod
has no CPU request.

### VPA in recommender mode

```powershell
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/vertical-pod-autoscaler-1.2.1/vertical-pod-autoscaler/deploy/vpa-rbac.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/vertical-pod-autoscaler-1.2.1/vertical-pod-autoscaler/deploy/recommender-deployment.yaml
# run the load test again, wait a few minutes, then:
kubectl -n civicpulse describe vpa backend-vpa
```

Copy Target, Lower Bound and Upper Bound into docs/ENGINEERING-NOTES.md, update the
requests in `k8s/base/backend.yaml`, re-apply, re-run the load test and note what changed.

## 4. Zero-downtime rollout (demo)

```powershell
# Window 1: steady traffic; fails if even ONE request fails
k6 run load/rollout-check.js
# Window 2, while it runs: build a new image and roll it out
docker build -t civicpulse-backend:dev2 backend
k3d image import civicpulse-backend:dev2 -c civicpulse
kubectl -n civicpulse set image deployment/backend backend=civicpulse-backend:dev2
kubectl -n civicpulse rollout status deployment/backend
```

k6 should finish with `http_req_failed: 0.00%`. This works because of `maxUnavailable: 0`,
the readiness probe, the 5 s `preStop` sleep and uvicorn's graceful drain on SIGTERM.

## 5. Roll back

| Situation | Command |
|---|---|
| Something broke just now (fast, imperative) | `kubectl -n civicpulse rollout undo deployment/backend` |
| See what versions exist | `kubectl -n civicpulse rollout history deployment/backend` |
| Fire is out: make Git match reality (declarative, auditable) | Put the previous SHA back in the overlay and apply it, see below |

```powershell
cd k8s/overlays/prod
kustomize edit set image civicpulse-backend=ghcr.io/roshailahmad/civicpulse-backend:<previous-sha>
cd ../../..
kubectl apply -k k8s/overlays/prod
```

On the real pipeline, the declarative rollback is `git revert <bad-commit>` on `main`
through a PR; CD then redeploys the previous code by its SHA.

## 6. Read logs

Every log line is JSON on stdout with a `request_id`.

```powershell
docker compose logs -f backend                                  # Compose
kubectl -n civicpulse logs deploy/backend -f                     # Kubernetes
kubectl -n civicpulse logs deploy/backend | Select-String "abc123"   # follow one request by id
kubectl -n civicpulse logs deploy/backend -c migrate             # migration + seed output
```

Send `X-Request-ID: abc123` on a request (or read it from any response header) and search
for it: nginx, backend and triage lines all carry the same id.

## 7. When triage starts failing

Symptoms: new complaints show "Keyword rules (AI unavailable, used fallback)".
Citizens are **not** affected: every complaint is still accepted and sorted by rules.

1. **Confirm:** open `/api/meta/providers`. Look at `recent`: `fallback: true` and the
   `error` class tell you what's happening.
2. **Find the error class** in the logs: search for `triage fallback`. Each has
   `complaint_id`, `provider` and `error_class`.
3. **By error class:**
   - `RetryableTriageError` with `rate_limited_429`: free-tier quota used up. Wait for the
     window to reset; check the rate limiter isn't disabled (`RATE_LIMIT_PER_MINUTE`).
   - `RetryableTriageError` with `timeout` or `connection_error`: the provider is slow or
     down. Check its status page.
   - `TriageError` with `http_401`: the API key is wrong or revoked. Rotate it (below).
   - `MalformedTriageOutputError`: the model is returning bad JSON. Try another model
     (`LLM_MODEL`) or switch provider.
4. **Switch provider without a rebuild:**
   `kubectl -n civicpulse patch configmap civicpulse-config -p '{\"data\":{\"TRIAGE_PROVIDER\":\"rules\"}}'`
   then `kubectl -n civicpulse rollout restart deployment/backend`.
5. **Rotate a leaked or revoked key:** create a new key at the provider, update the
   GitHub secret `LLM_API_KEY` and the cluster Secret (section 2), restart the backend,
   then revoke the old key.
6. **Metrics:** `civicpulse_triage_fallbacks_total` on `/metrics` counts fallbacks by
   provider and error. A rising line is the alert signal.
