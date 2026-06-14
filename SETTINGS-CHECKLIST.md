# Repo Settings Checklist

One-time GitHub settings that the code in this repo cannot enforce on its own. Tick
these in the repository UI; CI enforces the rest.

## Branch protection (`main`)
- [ ] Require a pull request before merging (no direct pushes).
- [ ] Require status checks to pass: `lib`, `supply-chain`, `integration`, `security-scan`.
- [ ] Also require `Dependency Review` once its first run lands (new this batch). CodeQL
      already runs via default setup.
- [ ] Require branches to be up to date before merging.
- [ ] Require linear history (optional but recommended).
- [ ] Restrict who can push / dismiss reviews to the owner.

## Security
- [ ] Secret scanning + push protection: **on**.
- [ ] Dependency graph: **on** (needed for Renovate + advisories).
- [ ] Private vulnerability reporting: **on** (per `SECURITY.md`).
- [ ] Actions → "Allow <owner>, and select non-<owner>, actions" set to pinned SHAs only.
- [ ] Code scanning: keep CodeQL **default setup ON** — it already provides CodeQL. Do NOT
      add an advanced `codeql.yml` (it conflicts: "advanced configurations cannot be
      processed when the default setup is enabled").

## Automation
- [ ] Install/enable **Renovate** (config at `.github/renovate.json`).
- [ ] Workflow permissions default: **read-only**; "Allow GitHub Actions to create and
      approve pull requests": **off**.

## Local dev
- [ ] `uv sync --all-extras` then `uvx pre-commit install`.
- [ ] Docker available if running the integration lane locally.
