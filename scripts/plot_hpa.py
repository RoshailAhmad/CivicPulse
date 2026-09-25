"""Chart replicas against offered load over time.

    pip install matplotlib
    python scripts/plot_hpa.py

Reads load/hpa-watch.csv (scripts/record_hpa.py) and load/k6-results.csv
(k6 --out csv=...), writes docs/evidence/hpa-scaling.png.
"""

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
HPA_CSV = ROOT / "load" / "hpa-watch.csv"
K6_CSV = ROOT / "load" / "k6-results.csv"
OUT = ROOT / "docs" / "evidence" / "hpa-scaling.png"


def main() -> None:
    hpa = list(csv.DictReader(HPA_CSV.open(encoding="utf-8")))
    vus: dict[int, float] = defaultdict(float)
    for row in csv.DictReader(K6_CSV.open(encoding="utf-8")):
        if row["metric_name"] == "vus":
            vus[int(float(row["timestamp"]))] = float(row["metric_value"])

    start = min([int(r["unix_time"]) for r in hpa] + list(vus))
    fig, ax_load = plt.subplots(figsize=(10, 5))
    ax_load.plot([t - start for t in sorted(vus)], [vus[t] for t in sorted(vus)],
                 color="tab:gray", label="Offered load (k6 virtual users)")
    ax_load.set_xlabel("Seconds since test start")
    ax_load.set_ylabel("Virtual users")

    ax_rep = ax_load.twinx()
    ax_rep.step([int(r["unix_time"]) - start for r in hpa],
                [int(r["current_replicas"]) for r in hpa],
                where="post", color="tab:blue", linewidth=2, label="Backend replicas")
    ax_rep.set_ylabel("Replicas")
    ax_rep.set_ylim(0, 11)

    handles = ax_load.get_legend_handles_labels()[0] + ax_rep.get_legend_handles_labels()[0]
    labels = ax_load.get_legend_handles_labels()[1] + ax_rep.get_legend_handles_labels()[1]
    ax_load.legend(handles, labels, loc="upper left")
    ax_load.set_title("HPA scale-out: replicas vs offered load")
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
