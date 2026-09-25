# AI usage log

We used Claude (Anthropic) as a coding assistant for this assignment. This file records
where, honestly, because the viva tests whether we understand everything we submit.

| Area | What the AI produced |
|---|---|
| Project plan | Split of the assignment into three parts and the order of work |
| Backend (Part 1) | Initial code for the API, services, repositories, Alembic migration, seed data, triage providers and tests |
| Frontend and Docker (Part 2) | Initial React views, typed API client, component tests, Dockerfiles, nginx config, Compose files |
| Kubernetes and CI/CD (Part 3) | Manifests, overlays, CI/CD/release workflows, load-test and HPA scripts, evidence workflow, submission checker |
| Documentation | First drafts of README, ADRs, runbook, engineering notes and this file; we supplied the failure story and our own account below |
| Git and GitHub | Step-by-step instructions for branches, PRs, reviews, branch protection and debugging help from our screenshots |

## What we did ourselves, and how we checked the AI's work

We didn't just copy the AI output: we ran every step ourselves, from installing Git and
Python to cloning the repo, adding files and verifying the tests locally ("3 passed",
"38 passed"). We split the work (Part 1: Roshail, Part 2: Mehak, Part 3 shared), created
Issues and PRs, reviewed each other's PRs, and fixed mistakes like wrong base branches
(`main` instead of `dev`), messy titles and missing issue links.

We also handled all the GitHub setup ourselves, including branch protection, required
checks, secrets (`LLM_API_KEY`) and making the packages public. We debugged several real
problems: Git not on PATH, incorrect file paths, Docker's virtualization failure and
Codespaces networking. We confirmed correctness by checking the evidence outputs and
running the red-to-green gate demo, and we resolved the merge conflict ourselves and made
sure everything passed on GitHub Actions.

## What we understand, and what we're still studying

Honestly, we understand the high-level flow and structure of the code, but we still need
to study some implementation details, especially Docker, Kubernetes and the workflows,
more deeply before the viva.
