# Evidence

Screenshots and captures the rubric asks for. File names used in the docs:

| File | Rubric item | How to get it |
|---|---|---|
| `branch-protection.png` | A: main protected | Settings → Branches → edit the `main` rule |
| `merge-conflict.md` + `merge-conflict.png` | A: deliberate merge conflict | See merge-conflict.md |
| `red-check.png`, `blocked-merge.png`, `green-check.png` | I: gate works | The release PR, with a failing test and then the fix |
| `hpa-watch.png` | H: `kubectl get hpa -w` | Screenshot of window 1 during the load test |
| `hpa-scaling.png` | H: replicas vs load chart | `python scripts/plot_hpa.py` |
| `vpa-recommendation.png` | H: VPA recommendations | `kubectl -n civicpulse describe vpa backend-vpa` |
| `network-isolation.png` | G: frontend can't reach DB | `docker compose exec frontend ping -c 1 database` failing |
| `zero-downtime.png` | Bonus: rollout under load | k6 `rollout-check.js` summary with 0% failed |
