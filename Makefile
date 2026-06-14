# DEP-TEST-KIT — common tasks. Everything runs through uv for a locked, reproducible env.

.PHONY: sync test coverage test-int lint deptry audit selftest mutation sbom all review

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

sbom:            ## generate a CycloneDX SBOM
	uvx cyclonedx-py environment "$$(uv python find)" --output-format json -o sbom.cdx.json

all: sync lint deptry test selftest audit

review:          ## pre-push: mechanical gates, then run the MoE audit panel by hand
	$(MAKE) all
	@echo
	@echo "Mechanical gates green. Now run the MoE audit panel: docs/moe-audit.md"
	@echo "Record lens verdicts in the PR's '## Self-audit' section before pushing."
