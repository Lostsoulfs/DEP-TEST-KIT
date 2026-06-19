# Reviewer Dashboard

The reviewer dashboard is a local, generated review aid for DEP-TEST-KIT.

It is meant to help a human reviewer or AI assistant answer four questions quickly:

1. Which harnesses exist?
2. Which flavor owns each harness: `lib`, `integration`, or `ai`?
3. Which source and proof files should be inspected?
4. Which command should be run to verify the harness locally?

## What it is

A static HTML view generated from repo-owned status data.

The dashboard may show:

- harness counts;
- flavor counts;
- proof-source presence;
- TEETH eligibility;
- source files;
- local verification commands;
- next test paths.

## What it is not

The dashboard is not a governance source. It does not override `AGENTS.md`, `SECURITY.md`, `.github/control-policy.json`, or branch-protection rules.

The dashboard does not claim total correctness, production safety, or future-code guarantees. Its claim scope is limited to the current proof baseline and fixture-defined proof under the current tooling.

## Generation policy

Preferred local commands:

```bash
make report
make dashboard
make dashboard-check
```

`make report` should generate the status data used by the dashboard.

`make dashboard` should generate the local static page.

`make dashboard-check` should verify that the dashboard generator can render from current status data. If generated HTML is committed later, this check should also fail when the committed page is stale.

## Generated artifact policy

For the first dashboard PR, keep the generated HTML local unless a freshness check is also committed.

If `dashboard/site/index.html` is committed later for GitHub Pages or reviewer convenience, CI should run a dashboard freshness check.

## Security boundary

All dynamic dashboard text must be HTML-escaped before rendering. Harness names, descriptions, commands, source paths, warnings, and status text are data, not trusted markup.

The page should avoid external JavaScript, external CSS, tracking, analytics, and remote CDNs unless a later PR explicitly scopes and reviews that change.

## Review path

1. Generate the report.
2. Generate the dashboard.
3. Open the local HTML file.
4. Pick a harness by flavor, topic, or failure class.
5. Inspect the listed source and proof files.
6. Run the listed command.
7. Treat skips or environment failures as environment results, not green proof.
