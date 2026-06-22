# 0008 — Lane taxonomy: fold by execution shape

Status: accepted (2026-06-22). Records how ported (and future) harnesses are assigned to
the `lib` / `ai` lanes, so a security harness that happens to mention an LLM isn't filed by
topic instead of by how it runs.

## Context
The `dep-kit-local-ref` source (ported 2026-06-22; see `HARNESS_ROADMAP.md`, ADR-0001 addendum)
carried a `lib` / `ai` split by **subject matter**: anything AI-adjacent sat under `ai`. But many
of those harnesses are ordinary application-security or dependency-correctness checks that run
in-process and deterministically — they share nothing operationally with the `ai` lane except a
topic. Meanwhile the repo's three lanes (README) are defined by **how a harness runs**:

- `lib` — in-process, needs a pinned library; fast lane.
- `integration` — needs Docker + a real ephemeral service.
- `ai` — in-process *and* deterministic, but specifically a deepeval/Hypothesis evaluation of
  model/agent behavior (no live LLM, no API key).

Filing by topic would put a deterministic AppSec check (e.g. an LDAP-filter escaper) in `ai`
purely because the threat model mentions agents, splitting the fast lane along a meaningless axis
and confusing `make`-lane selection.

## Decision
Assign lanes by **execution shape, not subject** ("Recommendation A — fold").

- **AppSec / dependency-correctness / protocol-correctness → `lib`.** A harness whose oracle is a
  deterministic security or correctness check on a library or protocol goes in `lib`, regardless
  of whether its motivating scenario involves AI. This relabeled the source's AI-topic-but-AppSec
  harnesses into `lib` (37 of the 46 ported).
- **Agent / model behavior → `ai`.** Only harnesses that test an agent's or model's *behavior*
  (tool-use safety, confirmation, memory trust, goal integrity, message auth, capability
  allow-listing, replay/circuit-breaking, sandboxed eval) stay in `ai` — the 9 `agent_*` ported
  harnesses. They remain deterministic and key-free like the rest of the lane.
- **`integration` is unchanged** — the Docker/testcontainers boundary already separates cleanly.

## Consequence
The fast (`-m "not integration"`) lane stays coherent: it runs every in-process harness, and the
`lib` / `ai` divide tracks *what kind of thing is under test* (a library/protocol vs. an agent),
which is the only split that affects how you read and run them. Possible follow-up: if the `lib`
lane's AppSec mass keeps growing, carve an `appsec` sub-grouping (the "B trigger" noted during the
port) — deferred; it is a documentation/grouping change, not a new execution lane. Anti-goal: a
taxonomy that files by buzzword and leaves a reader unable to predict which lane (and which gate) a
harness lives in.
