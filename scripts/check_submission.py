"""Mechanical pre-submission lint (not a grader).

    python scripts/check_submission.py

Catches the automatic-deduction mistakes: committed secrets, unpinned images,
:latest deploys, loopback service addresses, missing needs:, published DB
ports, a Deployment for Postgres, missing docs. Exit code 1 if anything fails.
If the course provides its own check_submission.py, run that one too.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
results: list[tuple[bool, str]] = []


def check(ok: bool, message: str) -> None:
    results.append((ok, message))


def read(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8") if path.exists() else ""


def code(rel: str) -> str:
    """File content without comments, so explanations don't trigger checks."""
    lines = []
    for line in read(rel).splitlines():
        stripped = re.sub(r"(^|\s)#.*$", "", line)
        if stripped.strip():
            lines.append(stripped)
    return "\n".join(lines)


def tracked_files() -> list[str]:
    try:
        out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    return out.splitlines()


def main() -> int:
    files = tracked_files()

    # --- secrets ---------------------------------------------------------
    env_files = [f for f in files if re.search(r"(^|/)\.env($|\.)", f) and not f.endswith(".example")]
    check(not env_files, f"no .env files tracked by Git {env_files or ''}")
    key_pattern = re.compile(r"(gsk_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{30,})")
    leaks = [
        f for f in files
        if not f.endswith((".png", ".jpg", ".lock", "package-lock.json"))
        and key_pattern.search(read(f))
    ]
    check(not leaks, f"no API keys or tokens in tracked files {leaks or ''}")
    secret = read("k8s/base/secret.yaml")
    check("change-me" in secret and not key_pattern.search(secret),
          "k8s Secret manifest holds placeholders only")

    # --- images pinned ---------------------------------------------------
    for dockerfile in ("backend/Dockerfile", "frontend/Dockerfile"):
        froms = re.findall(r"^FROM\s+(\S+)", read(dockerfile), re.MULTILINE)
        bad = [f for f in froms if ":" not in f or f.endswith(":latest")]
        check(bool(froms) and not bad, f"{dockerfile}: base images pinned {bad or ''}")
        check(bool(re.search(r"^USER\s+\S+", read(dockerfile), re.MULTILINE)),
              f"{dockerfile}: runs as a non-root USER")
    for compose in ("compose.yaml", "compose.prod.yaml"):
        images = re.findall(r"^\s*image:\s*(\S+)", read(compose), re.MULTILINE)
        bad = [i for i in images if ":" not in i or i.endswith(":latest")]
        check(not bad, f"{compose}: every image tag pinned {bad or ''}")

    # --- compose rules ---------------------------------------------------
    prod = code("compose.prod.yaml")
    check("build:" not in prod, "compose.prod.yaml has no build: key")
    check("${IMAGE_TAG" in prod, "compose.prod.yaml uses image: ...:${IMAGE_TAG}")
    for service in ("database", "cache"):
        block = re.search(rf"^  {service}:\n(.*?)(?=^  \S|\Z)", prod, re.MULTILINE | re.DOTALL)
        check(bool(block) and "ports:" not in block.group(1),
              f"compose.prod.yaml: no published port on {service}")
    dev = code("compose.yaml")
    check("internal: true" in dev, "compose.yaml: internal network has internal: true")
    frontend = re.search(r"^  frontend:\n(.*?)(?=^  \S|\Z)", dev, re.MULTILINE | re.DOTALL)
    check(bool(frontend) and "internal" not in frontend.group(1),
          "compose.yaml: frontend is not on the internal network")

    # --- no loopback for service-to-service -------------------------------
    config_files = ["compose.yaml", "compose.prod.yaml", "frontend/nginx/default.conf.template",
                    "backend/app/config.py", *[str(p.relative_to(ROOT)) for p in (ROOT / "k8s").rglob("*.yaml")]]
    # A container probing ITSELF (healthcheck on 127.0.0.1) is fine; talking to
    # another service through a loopback address is the bug.
    loopback = [
        f for f in config_files
        for line in code(f).splitlines()
        if re.search(r"localhost|127\.0\.0\.1", line) and not re.search(r"urlopen|wget|curl", line)
    ]
    check(not loopback, f"no localhost/loopback service addresses {loopback or ''}")

    # --- kubernetes --------------------------------------------------------
    manifests = "\n".join(code(str(p.relative_to(ROOT))) for p in (ROOT / "k8s").rglob("*.yaml"))
    check(":latest" not in manifests, "k8s manifests never reference :latest")
    postgres = read("k8s/base/postgres.yaml")
    check("kind: StatefulSet" in postgres and "volumeClaimTemplates" in postgres,
          "Postgres is a StatefulSet with volumeClaimTemplates")
    check("NodePort" not in manifests and "LoadBalancer" not in manifests,
          "no NodePort/LoadBalancer Services")
    backend = read("k8s/base/backend.yaml")
    for probe in ("startupProbe", "livenessProbe", "readinessProbe", "requests:"):
        check(probe in backend, f"backend Deployment has {probe.rstrip(':')}")

    # --- CI/CD -------------------------------------------------------------
    cd = read(".github/workflows/cd.yml")
    for job in ("build-push", "deploy-k8s"):
        block = re.search(rf"^  {job}:\n(.*?)(?=^  \S|\Z)", cd, re.MULTILINE | re.DOTALL)
        check(bool(block) and "needs:" in block.group(1), f"cd.yml: {job} is gated by needs:")
    check("edit set image" in cd and "github.sha" in cd, "cd.yml deploys by commit SHA")
    for wf in ("ci.yml", "cd.yml", "release.yml"):
        check("permissions:" in read(f".github/workflows/{wf}"), f"{wf} declares permissions:")

    # --- app rules -----------------------------------------------------------
    app_code = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "backend" / "app").rglob("*.py"))
    check("CREATE TABLE" not in app_code.upper(), "no CREATE TABLE in application code")

    # --- docs --------------------------------------------------------------------
    for doc in ("README.md", "docs/RUNBOOK.md", "docs/ENGINEERING-NOTES.md", "docs/AI-USAGE.md",
                "docs/TRIAGE.md", "docs/adr/0001-provider-interface.md",
                "docs/adr/0002-frontend-runtime-config.md", "docs/adr/0003-deploy-by-sha.md",
                "docs/adr/0004-pii-and-data-governance.md"):
        check((ROOT / doc).exists(), f"{doc} exists")

    for ok, message in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {message}")
    failed = sum(1 for ok, _ in results if not ok)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
