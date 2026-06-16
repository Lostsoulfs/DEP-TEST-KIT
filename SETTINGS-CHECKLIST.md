# Repo Settings Checklist

One-time GitHub settings that the code in this repo cannot enforce on its own. **All items are
applied** — branch protection and the Actions allow-list were re-verified via `gh api` on
2026-06-16; the rest were applied during earlier provisioning (see `docs/LEARNINGS.md`). Kept
here as the record and for re-provisioning. CI enforces the rest.

## Branch protection (`main`)
- [x] Require a pull request before merging (no direct pushes; force-pushes off).
- [x] Require status checks to pass — **6 required contexts**, `strict` (up-to-date) on:
      `Lib lane + lint + dep-prune`, `Audit + SBOM`, `Integration lane (Docker)`,
      `Secret + workflow scan`, `review` (Dependency Review), `Vacuous-green meta-gate`.
- [x] Require branches to be up to date before merging (`strict`).
- [x] Require linear history (squash-only merges).
- [x] Enforce for administrators; 0 approvals required (solo owner).

## Security
- [x] Secret scanning + push protection: **on**.
- [x] Dependency graph: **on** (public repo default; Renovate is active against it).
- [x] Private vulnerability reporting: **on** (per `SECURITY.md`).
- [x] Actions → allowed actions set to **selected** (owner actions + pinned-SHA third-party only).
- [x] Code scanning: CodeQL **default setup ON** (the `Analyze (python)/(actions)` checks). Do NOT
      add an advanced `codeql.yml` — it conflicts ("advanced configurations cannot be processed when
      the default setup is enabled").
- Note: **Dependabot vulnerability alerts are intentionally OFF.** The repo's vuln mechanism is
  `uv audit` (OSV-based, **blocking** in the `Audit + SBOM` CI lane) plus Renovate updates — see
  `SECURITY.md`. Enable Dependabot alerts only if a redundant passive-alert layer is wanted.

## Automation
- [x] **Renovate** enabled (config at `.github/renovate.json`; merged Renovate PRs confirm it runs).
- [x] Workflow permissions default: **read-only**; "Allow GitHub Actions to create and approve
      pull requests": **off**.

## Local dev (per-clone / per-machine, not a repo setting)
- [ ] `uv sync --all-extras` then `uvx pre-commit install`.
- [ ] Docker available if running the integration lane locally.
