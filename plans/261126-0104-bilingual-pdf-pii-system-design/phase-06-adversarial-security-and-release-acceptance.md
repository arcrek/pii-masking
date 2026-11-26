---
phase: 6
title: "Phase 6: Adversarial Security Suite, Race/Perf Hardening & Release Acceptance"
status: todo
priority: P1
effort: "1.5w"
dependencies: [1, 2, 3, 4, 5]
---

# Phase 6: Adversarial Security Suite, Race/Perf Hardening & Release Acceptance

**Maps to backlog:** `DATA-04`, `DATA-05`, `QA-02..07`, `OPS-02`, `OPS-04`, `OPS-05`
**Primary owners:** `CS2` (adversarial suite, security & release acceptance), `CS1` (race/error/isolation testing), `SE4` (PDF benchmark suite & perf), `SE1` (E2E product tests), `SE2` (HTTPS demo deploy, observability, rollback & retention runbook)

## Goal

Validate the entire system against realistic bilingual PDF fixtures (`DATA-04`), CS2's 13-case adversarial redaction security suite (`DATA-05`), cross-account RBAC & concurrency/deletion race suites (`QA-04/05`), CPU RAM/latency benchmarks (`QA-06`), and operational HTTPS deployment/observability/rollback runbooks (`OPS-02/04/05`, `QA-07`), while keeping `make test` fast and hermetic.

## Requirements

- [ ] **R6.1 (`DATA-04` Synthetic Bilingual PDF Fixture Suite):** Generate deterministic, non-real-PII VI+EN benchmark PDFs covering `NATIVE`, `SCANNED_FLATTENED` (clean + noisy + rotated + skewed), `MIXED` (native text + embedded ID/receipt image), and manual-handwriting regions, with ground-truth text and visual `CropBox` region manifests.
- [ ] **R6.2 (`DATA-05`, `QA-03` 13-Case Adversarial Redaction Security Suite):** Build and run all 13 adversarial traps: <!-- Red-Team Fix: Finding 6 -->
  1. Shared Image XObject across 2 pages (redact Page 1 only; Page 2 raw `pdfimages` stays identical)
  2. Shared transparent PNG with `/SMask` across 2 pages
  3. Same Image XObject placed twice on 1 page (redact only 2nd placement)
  4. Shared indirect `/Resources` dict across 2 pages
  5. Form XObject (nested & shared, plus >10-level nesting fail-closed test)
  6. Invisible `3 Tr` OCR layer (aligned and 2 pt shifted)
  7. Ligatures (`fi`/`fl`/`ffi`) & kerning-split `TJ` arrays (SSN / CCCD split across glyph runs)
  8. Tight line spacing (`10 pt` font, `10.5 pt` leading — assert neighbor line preserved)
  9. Non-zero `/CropBox [50 50 562 742]` + `/Rotate` (`90°`, `180°`, `270°`)
  10. Full hidden-data payload (`/Info`, XMP, `/AcroForm` + widget, comments/StickyNotes/FreeText/Highlight, `/EmbeddedFiles`, `/JavaScript`, `/OpenAction`, `/AA`, `/Outlines`, `/Thumb`, `/PieceInfo`, `/StructTreeRoot` `/ActualText`/`/Alt`, off-by-default hidden `/OCProperties`, plus XObject-level `/Metadata`/`/PieceInfo`, `/URI`, `/DSS`, `/XFA`)
  11. Multi-revision incremental PDF (`>= 2` `%%EOF`) verified via `eof_count == 1` + `qpdf --stream-data=uncompress --object-streams=disable` zero-secret byte sweep
  12. Fake black-box overlay negative self-test (must `FAIL` `VER-01` & `VER-02`)
  13. Vector-outlined text & manual vector signature straddling redaction box boundary (must not survive underneath black rectangle; audited in `VER-03`) <!-- Red-Team Fix: Finding 6 -->
- [ ] **R6.3 (`QA-02`, `QA-04`, `QA-05` Isolated Live-Container E2E, RBAC & Race Suites):** <!-- Red-Team Fix: Finding 12 -->
  - Place live-container tests strictly under `tests/e2e/` marked `@pytest.mark.e2e` and update `Makefile`'s `test` target to `-m "not e2e and not integration"` so unit `make test` remains hermetic without running Docker containers.
  - Full E2E flow across native, scanned, mixed, and 0-PII-detected documents (confirming visual review is still required).
  - Two-account RBAC & CSRF penetration test (expired session, missing CSRF token, forged IDs, direct preview/export URL access, direct `ml-service` call without bearer token).
  - Concurrency & fault suite: edit review during active export, delete document while analyze/export job is running (verifying zero resurrected files and purged PG PII rows), duplicate concurrent export clicks, retry after transient failure, simulated worker `SIGKILL` lease recovery, poison-pill `max_attempts` dead-lettering, and stuck-page timeout.
- [ ] **R6.4 (`QA-06`, `OPS-04` Performance & Observability):** Measure CPU latency/page, peak RAM per container (`api`, `worker`, `ml-service`, `postgres`), and concurrency behavior on the base `lightweight_cpu` deployment (plus optional `docker-compose.opf.yml` benchmark when >=16 GB RAM demo host is provisioned); expose PII-free `/metrics` & `/ready` checks + disk/queue alerts. <!-- Red-Team Fix: Finding 14b -->
- [ ] **R6.5 (`OPS-02`, `OPS-05`, `QA-07` HTTPS Demo Deploy, Retention & Rollback Runbook):** Add reverse-proxy TLS config (`docker/Caddyfile` storing certs in a named Docker volume / out-of-repo path so `scripts/check_secrets.py` never flags cert keys), scheduled retention purge job (`BE-11`), tested release/model rollback drill, and final acceptance report referencing dataset/model/pipeline versions and published limitations. <!-- Red-Team Fix: Finding 12 -->

## Files to Create / Modify

- Create: `tests/fixtures/generate_pdf_suites.py` (deterministic builder for `DATA-04` bilingual suite + `DATA-05` 13 adversarial fixtures)
- Create: `tests/test_phase06_adversarial_redaction.py` (hermetic `QA-03` running all 13 `DATA-05` fixtures + `qpdf --stream-data=uncompress` forensics check)
- Create: `tests/e2e/__init__.py`, `tests/e2e/test_phase06_e2e_rbac_races.py` (`@pytest.mark.e2e` live-container `QA-02`, `QA-04`, `QA-05` tests) <!-- Red-Team Fix: Finding 12 -->
- Create: `scripts/benchmark_e2e_performance.py` (`QA-06` CPU latency/RAM benchmark across 10-page & 50-page native/scanned/mixed PDFs)
- Create: `app/services/retention_service.py` (`OPS-05` TTL cleanup job honoring `deleted_at`, purging PG PII rows & disk artifacts, and backup exclusion policy)
- Create: `docker/Caddyfile` (HTTPS reverse proxy terminating TLS with certs stored in named volume `caddy_data`, setting trusted `X-Forwarded-For`)
- Create: `docs/ops/OPS-05-runbook-rollback-retention.md` (deployment with out-of-repo `--env-file`, health/metrics monitoring, stuck-job recovery, version rollback drill, retention/backup rules)
- Create: `docs/qa/QA-07-release-acceptance-report.md` (traceability matrix from `QA-01` thresholds to live test evidence, model/dataset versions, and known limitations)
- Modify: `Makefile` (keep `make test` hermetic via `-m "not e2e and not integration"`; add `test-security`, `test-e2e`, `benchmark-e2e` targets) <!-- Red-Team Fix: Finding 12 -->

## Implementation Steps

1. Build `tests/fixtures/generate_pdf_suites.py` using synthetic non-sensitive data only (zero real PII) to generate reproducible `DATA-04` and 13-case `DATA-05` suites.
2. Implement and execute `tests/test_phase06_adversarial_redaction.py` (`QA-03`), fixing any edge-case leaks discovered in Phase 5 before proceeding.
3. Implement and execute `tests/e2e/test_phase06_e2e_rbac_races.py` (`QA-02`, `QA-04`, `QA-05`) against live `docker compose up` containers (`make test-e2e`).
4. Run `scripts/benchmark_e2e_performance.py` (`QA-06`) on target host hardware and record exact RAM/latency measurements (and scanned VI CER; trigger RapidOCR contingency only if CER > 5%).
5. Add `docker/Caddyfile`, `app/services/retention_service.py`, `docs/ops/OPS-05-runbook-rollback-retention.md` (including a tested rollback drill), and assemble `docs/qa/QA-07-release-acceptance-report.md`.

## Todo

- [ ] Build `tests/fixtures/generate_pdf_suites.py` (`DATA-04`, `DATA-05` 13 adversarial traps)
- [ ] Run `tests/test_phase06_adversarial_redaction.py` and achieve `0` leaks on all 13 fixtures (`QA-03`)
- [ ] Update `Makefile` (`test` hermetic filter + `test-e2e` / `test-security` / `benchmark-e2e`) and run `tests/e2e/test_phase06_e2e_rbac_races.py` (`QA-02`, `QA-04`, `QA-05`)
- [ ] Run `scripts/benchmark_e2e_performance.py` and verify container RAM stays within configured limits (`QA-06`, `OPS-03`)
- [ ] Configure `docker/Caddyfile` HTTPS termination, retention cleanup, observability `/ready` checks, and complete rollback drill (`OPS-02`, `OPS-04`, `OPS-05`)
- [ ] Publish `docs/qa/QA-07-release-acceptance-report.md` and run `make test && make test-e2e && make lint && make check-secrets`

## Risk Assessment & Load-Bearing Assumptions

| Load-Bearing Assumption | Observable Break Signal | Pre-Decided Response |
|---|---|---|
| 100-page scanned PDF completes within `JOB_TIMEOUT_SECONDS=300` on CPU | Benchmark shows `> 3.0 s/page` OCR latency (exceeding 300s for 100 scanned pages) | Parallelize per-page OCR within a single job across bounded page workers (`OMP_THREAD_LIMIT=1`) or raise `JOB_TIMEOUT_SECONDS` and document scanned-page throughput limit in `QA-01`/`QA-07` |
| Backups do not resurrect deleted documents | OPS-05 review finds volume snapshots retain deleted user PDFs | Exclude `pii_storage` volume from automatic VM backups or enforce matching encrypted retention window, documented explicitly in `OPS-05` |

## Verification & Success Criteria

```bash
make test
make test-security
make test-e2e
make lint
make check-secrets
```

- `make test` runs hermetically with zero Docker dependency and passes 100%.
- All 13 `DATA-05` adversarial redaction fixtures pass with `0` text, vector-path, pixel, embedded-image, hidden-structure, or uncompressed-stream (`qpdf --stream-data=uncompress`) leaks, and the fake-overlay self-test fails verification as expected.
- Cross-account RBAC, CSRF, and concurrency/deletion race tests (`make test-e2e`) pass with `0` failures.
- Rollback drill succeeds cleanly and `docs/qa/QA-07-release-acceptance-report.md` links every `QA-01` gate to passing command evidence.
