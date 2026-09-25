"""Record HPA replicas and CPU every 5 s while a load test runs.

    python scripts/record_hpa.py          (Ctrl+C to stop)

Writes load/hpa-watch.csv: unix_time, current_replicas, desired_replicas, cpu_percent.
Pair it with `k6 run --out csv=load/k6-results.csv load/k6-script.js`,
then draw the chart with scripts/plot_hpa.py.
"""

import csv
import json
import subprocess
import time
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "load" / "hpa-watch.csv"
CMD = ["kubectl", "-n", "civicpulse", "get", "hpa", "backend-hpa", "-o", "json"]


def sample() -> tuple[int, int, int | None]:
    status = json.loads(subprocess.check_output(CMD, text=True)).get("status", {})
    cpu = None
    for metric in status.get("currentMetrics") or []:
        resource = metric.get("resource", {})
        if resource.get("name") == "cpu":
            cpu = resource.get("current", {}).get("averageUtilization")
    return status.get("currentReplicas", 0), status.get("desiredReplicas", 0), cpu


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["unix_time", "current_replicas", "desired_replicas", "cpu_percent"])
        print(f"recording to {OUT} - press Ctrl+C to stop")
        try:
            while True:
                current, desired, cpu = sample()
                now = int(time.time())
                writer.writerow([now, current, desired, "" if cpu is None else cpu])
                fh.flush()
                print(f"{time.strftime('%H:%M:%S')}  replicas={current} desired={desired} cpu={cpu}%")
                time.sleep(5)
        except KeyboardInterrupt:
            print("stopped")


if __name__ == "__main__":
    main()
