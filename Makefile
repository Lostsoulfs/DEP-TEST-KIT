# DEP-TEST-KIT — common tasks. Everything runs through uv for a locked, reproducible env.

.PHONY: sync test coverage test-int lint deptry audit selftest mutation canary guard guard-update control-audit vacuity sbom all review

sync:            ## provision the locked environment (all extras)
	uv sync --locked --all-extras

test:            ## fast lib lane (no Docker)
	uv run --frozen pytest -m "not integration" -q

coverage:        ## line coverage on harnesses/ (report-only; no blocking floor yet)
	uv run --frozen pytest -m "not integration" --cov=harnesses --cov-report=term-missing

test-int:        ## real-service lane (needs Docker)
	uv run --frozen pytest -m integration -q

lint:            ## ruff
	uv run ruff check .

deptry:          ## unused/missing dependency scan
	uv run deptry harnesses

audit:           ## OSV vulnerability audit of the locked graph
	uv audit --preview-features audit

selftest:        ## per-harness self-tests (in-process lib + ai harnesses)
	@for h in harnesses/lib/*_test_harness.py harnesses/ai/*_test_harness.py; do \
		echo "--- $$h"; \
		uv run --frozen python "$$h" --self-test || exit 1; \
	done

mutation:        ## mutation-quality check (real mutmut; Linux/WSL only — boxed/mutmut#397)
	uv run --frozen python harnesses/lib/mutation_quality_test_harness.py --self-test

canary:          ## gate-canary: prove the secret scanner + vacuity gate still bite
	uv run --frozen python tools/gate_canary.py

guard:           ## verify the gate machinery matches .fileguard.json
	uv run --frozen python tools/file_guard.py

guard-update:    ## re-baseline .fileguard.json (commit the bump in the diff)
	uv run --frozen python tools/file_guard.py --update

control-audit:   ## validate engineering controls against .github/control-policy.json
	uv run --frozen python tools/control_audit.py

vacuity:         ## vacuous-green meta-gate: neuter each mapped harness's oracle, expect red
	uv run --frozen python tools/vacuity_gate.py

sbom:            ## generate a CycloneDX SBOM
	uvx cyclonedx-py environment "$$(uv python find)" --output-format json -o sbom.cdx.json

all: sync lint deptry test selftest canary guard control-audit vacuity audit

review:          ## pre-push: mechanical gates, then run the MoE audit panel by hand
	$(MAKE) all
	@echo
	@echo "Mechanical gates green. Now run the MoE audit panel: docs/moe-audit.md"
	@echo "Record lens verdicts in the PR's '## Self-audit' section before pushing."
