# ADR 0003: Deploy by immutable commit SHA

**Status:** Accepted

## Context

"What is production running?" needs a one-word answer we can paste into `git show`.
Mutable tags like `:latest` can't give that: the same tag points at different images over
time, two pods can pull different versions during a rollout, and a rollback to
"the previous latest" is impossible.

## Decision

- `cd.yml` builds each image once, after the tests pass on the merged result, and pushes
  it to GHCR as `:<commit-sha>`. It also pushes `:latest` for convenience, but
  `:latest` is **never deployed** anywhere.
- The deploy job runs `kustomize edit set image civicpulse-backend=...:<sha>` and applies
  the prod overlay. The committed overlay carries the placeholder tag `set-by-cd`, so a
  hand-applied overlay fails loudly instead of running something unknown.
- `compose.prod.yaml` takes `${IMAGE_TAG}` and refuses to start without it.
- Every publishing or deploying job is gated with `needs:`: `build-push` needs `test`,
  and `deploy-k8s` needs `build-push`.

## Rollback

- **Fast (the 3 a.m. answer):** `kubectl rollout undo deployment/backend -n civicpulse`.
  Seconds, no Git involved. Use it while the incident is live.
- **Declarative (once the fire is out):** set the overlay back to the previous SHA
  (`kustomize edit set image ...:<previous-sha>`) and apply it, or revert the commit on
  `main` so CD redeploys. The repository again describes what is running, and the change
  is reviewed and auditable. See docs/RUNBOOK.md.

## Consequences

- Any running pod's image maps to exactly one commit.
- Digests (`@sha256:...`) would be stronger still, since a tag can technically be
  re-pushed; `build-push` already exposes both digests as job outputs, so moving to
  digest-based deploys plus Cosign signing is the next step.
