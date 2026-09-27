# Evidence

| Rubric item | Evidence |
|---|---|
| A: `main` protected | `branch-protection-01`, `branch-protection-02` |
| A: deliberate merge conflict | [`merge-conflict.md`](merge-conflict.md), `merge-conflict.png` |
| I: red pipeline blocks the merge, then green | `red-check.png`, `blocked-merge.png`, `green-check.png` (release PR #12) |
| G: frontend can't reach the database | [`network-isolation.txt`](network-isolation.txt) |
| H: `kubectl get hpa -w` during load | [`run-1-guessed-requests/08-kubectl-get-hpa-w.txt`](run-1-guessed-requests/08-kubectl-get-hpa-w.txt), [`run-2-vpa-requests/08-kubectl-get-hpa-w.txt`](run-2-vpa-requests/08-kubectl-get-hpa-w.txt) |
| H: replicas vs offered load chart | `hpa-scaling-run1.png` (requests 100m), `hpa-scaling-run2.png` (requests 275m) |
| H: VPA recommendations | `run-1-guessed-requests/09-vpa.txt`, `run-2-vpa-requests/09-vpa.txt` |
| Bonus: zero-downtime rolling update | `run-2-vpa-requests/11-zero-downtime-k6.txt` (0 failed of 5,881) |
| Rollback, both ways | `run-2-vpa-requests/12-rollback.txt` |
| Persistence (Compose and Kubernetes) | `06-compose-persistence.txt`, `10-k8s-persistence.txt` |

## How these were produced

Our laptops couldn't run Docker (CPU virtualization disabled in the BIOS; see
ENGINEERING-NOTES.md, section 8), so every live demo runs in
[`.github/workflows/evidence.yml`](../../.github/workflows/evidence.yml) on a GitHub Actions runner:
Docker Compose, then a k3d cluster with metrics-server and the VPA recommender, a k6 load
test, pod deletion, a rolling update under load and both rollbacks. Each run uploads its
outputs as an artifact; the two runs are saved here.

- **Run 1:** backend requests at our first guess (cpu 100m, memory 128Mi).
- **Run 2:** requests updated to the VPA recommendation (cpu 275m, memory 256Mi).

The raw per-request k6 output (over 100 MB) is not committed; `k6-vus.csv` keeps the
offered-load curve used for the charts.
