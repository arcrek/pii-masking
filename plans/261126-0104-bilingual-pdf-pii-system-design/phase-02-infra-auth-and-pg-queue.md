---
phase: 2
title: "Phase 2: Infrastructure, Auth/RBAC & PostgreSQL Job Queue"
status: todo
priority: P1
effort: "1.5w"
dependencies: [1]
---

# Phase 2: Infrastructure, Auth/RBAC & PostgreSQL Job Queue

**Maps to backlog:** `OPS-01`, `OPS-03`, `BE-01`, `BE-02`, `BE-03`, `BE-04`, `BE-05`, `BE-07`, `BE-11`, `BE-12`
**Primary owners:** `SE2` (Docker/API/queue/storage), `CS1` (RBAC, CSRF, audit log, subprocess & network isolation)

## Goal

Stand up the hardened 4-container self-hosted CPU stack (`api`, `postgres`, `worker`, `ml-service`) with zero runtime internet egress, pin all runtime & ML dependencies offline, and implement authenticated/CSRF-protected/RBAC-enforced PDF upload, immutable private storage, PDF-bomb-hardened intake in isolated subprocesses, PostgreSQL `SKIP LOCKED` job orchestration with non-blocking RSS/heartbeat monitoring, full tombstone deletion, and global PII-free logging.

## Context & Existing Code Reuse

- Existing config/logging/health: [config/system_config.py](../../config/system_config.py), [config/logger.py](../../config/logger.py), [config/health.py](../../config/health.py).
- Existing container & test contracts: [docker/Dockerfile](../../docker/Dockerfile), [docker-compose.yml](../../docker-compose.yml), [requirements.txt](../../requirements.txt), [pyproject.toml](../../pyproject.toml), [.env.example](../../.env.example), [.dockerignore](../../.dockerignore), [scripts/check_secrets.py](../../scripts/check_secrets.py), [tests/test_ops01_environment.py](../../tests/test_ops01_environment.py).

## Requirements

- [ ] **R2.1 (Offline Multi-Target Docker & Pinned Deps):** <!-- Red-Team Fix: Finding 1, Finding 4, Finding 11 -->
  - Standardize Python `3.12-slim-bookworm` across multi-stage targets in `docker/Dockerfile`: (a) `frontend-builder` (`node:22-slim` compiling `frontend/dist`), (b) `app-runtime` (`api` + `worker` with `poppler-utils`, `qpdf`, `libgl1`, `libglib2.0-0`, `libgomp1`, `tesseract-ocr`, `tesseract-ocr-vie`, `tesseract-ocr-eng`, and commit-pinned + `sha256sum -c` verified `tessdata_best` `vie`/`eng` traineddata), and (c) `ml-runtime` (`ml-service` installing `requirements-ml.txt`: `presidio-analyzer` + exact pinned `en_core_web_lg` wheel baked into the image so zero runtime downloads occur).
  - Sync `pymupdf>=1.25.0,<2.0` in **both** `requirements.txt` and `pyproject.toml`.
  - Keep `lightweight_cpu` (`spacy_vn_19_ner` + `en_core_web_lg` + Presidio + rules, ~2 GB RAM) as the confirmed self-contained base Compose build; provide `docker-compose.opf.yml` as the optional mounted-weights override (`ML_MODEL_PROFILE=opf_high_ram`, `12G` RAM) for >=16 GB demo hosts. PyMuPDF AGPL-3.0 licensing is confirmed acceptable for this deployment (`pymupdf>=1.25.0,<2.0`). <!-- Updated: Validation Session 1 - Confirmed lightweight_cpu base + optional docker-compose.opf.yml override and PyMuPDF AGPL-3.0 acceptability -->
- [ ] **R2.2 (Hardened 4-Service Compose Topology & Isolation):** <!-- Red-Team Fix: Finding 4, Finding 11 -->
  - Define two Docker networks in `docker-compose.yml`: `frontend_net` (only `api` / Phase 6 reverse proxy) and `backend_internal` (`internal: true`, zero internet egress — holding `api`, `postgres`, `worker`, and `ml-service`).
  - Make `/app` root-owned read-only (`root:root`, `0755`/`0644`), set `read_only: true` with `tmpfs: [/tmp:size=512m,noexec,nosuid]`, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]` on `api`, `worker`, and `ml-service`, and use a named Docker volume `pii_storage:/app/storage` initialized to `10001:10001` (preventing host UID bind-mount `PermissionError`).
  - Fix `API_PORT` -> `APP_PORT`; move `HEALTHCHECK` out of shared `Dockerfile` into per-service `docker-compose.yml` definitions (`api` HTTP `/health`, `worker` PG-heartbeat probe, `ml-service` HTTP `/health` with `start_period: 60s`).
  - Require a shared internal bearer token (`ML_SERVICE_TOKEN`) on all `ml-service` inference calls.
- [ ] **R2.3 (`BE-01`, `BE-02`, `BE-03` Auth, CSRF, Startup Security Gate & RBAC):** <!-- Red-Team Fix: Finding 5 -->
  - Extend `SystemConfig.validate_security(strict_runtime: bool = False)` and call `validate_security(strict_runtime=True)` fail-fast in startup lifespan of `api`, `worker`, and `ml-service`, enforcing non-default `JWT_SECRET_KEY`, non-default `DATABASE_URL` password, `ML_SERVICE_TOKEN`, and `cookie_secure=True` in both `production` and `staging` (while default `strict_runtime=False` keeps `tests/test_ops01_environment.py::TestSystemConfig::test_security_validation_valid_configuration` green).
  - Demo account CLI seeder (Argon2id password hashing), DB-backed login rate-limiting keyed by `(username, trusted_client_ip)` (honoring `X-Forwarded-For` only from configured trusted reverse-proxy CIDRs), HttpOnly session cookies with `SameSite=Lax` + double-submit CSRF (`csrf_token` readable cookie matched against `X-CSRF-Token` header) + `Origin`/`Sec-Fetch-Site` check on all `POST`/`PATCH`/`DELETE` routes, server-side revocation (`sessions`), and strict `owner_id == current_user.id` RBAC on every document/page/preview/revision/export/delete endpoint.
- [ ] **R2.4 (`BE-04`, `OPS-03` Zero-Egress PDF-Bomb-Hardened Intake & Safe Subprocess Isolation):** <!-- Red-Team Fix: Finding 4, Finding 7, Finding 10 -->
  - Keep `api` upload handling strictly native-parser-free: stream upload to `/app/storage/temp/quarantine_{uuid}.pdf` enforcing size `<= 25 MB` and `%PDF-` magic-byte header only, then enqueue an `ANALYZE` job whose first step runs deep PDF validation inside the zero-egress `worker` container (`backend_internal`, `internal: true`).
  - Launch all untrusted PDF tasks (deep intake validation, OCR, redaction, verification) inside `worker` via clean `subprocess.Popen([sys.executable, "-m", ...], start_new_session=True)` (never `fork()`), passing a scrubbed `env` (`MALLOC_ARENA_MAX=2`, `OPENBLAS_NUM_THREADS=1`, `OMP_THREAD_LIMIT=1`, `PATH` — **zero** `DATABASE_URL`, `JWT_SECRET_KEY`, or `ML_SERVICE_TOKEN`) and per-job staging paths (guaranteeing secret scrubbing, path hygiene, OOM/timeout containment, read-only `/app`, and zero network egress; distinct-UID cross-tenant FS sandboxing is explicitly documented as a post-MVP hardening boundary).
  - Monitor child process group in a 2–5s non-blocking parent loop using `psutil` RSS watchdog (kill on physical RSS cap), wall-clock timeout (`os.killpg(..., SIGKILL)`), 30s PG `lease_expires_at` heartbeat renewal, and 5s `documents.deleted_at` cancellation check (reserving `RLIMIT_AS` only at a safe >=4 GB guard).
  - Deep intake checks (in `worker`): pages `<= 100`, non-encrypted, valid xref, max xref object count (`<= 50,000`), max uncompressed stream inflation check, and max embedded image pixel cap (`PIL.Image.MAX_IMAGE_PIXELS` + `page.get_image_info` check); rejected files are immediately purged from quarantine and marked `REJECTED` with structured error codes (`PDF_ENCRYPTED`, `PDF_CORRUPTED`, `PDF_LIMIT_EXCEEDED`, `PDF_BOMB_DETECTED`).
- [ ] **R2.5 (`BE-05`, `BE-07`, `BE-11` Private Storage, PG Queue & Full Tombstone Deletion):** <!-- Red-Team Fix: Finding 7, Finding 9 -->
  - UUID-scoped private store (`originals/`, `previews/`, `exports/`, `temp/`) with `SHA-256` checksums, `X-Content-Type-Options: nosniff`, `Cache-Control: no-store`, `Content-Disposition: attachment`.
  - PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED` job queue with stale-lease reaper, retryable partial-unique `idempotency_key`, and `max_attempts=3` dead-lettering to `FAILED`.
  - Stage **all** worker outputs in `./storage/temp/{job_id}/`; move into `./storage/private/` only inside a PG transaction holding `SELECT id FROM documents WHERE id = :id FOR UPDATE` confirming `deleted_at IS NULL`.
  - On `DELETE /api/v1/documents/{id}`, atomically set `deleted_at`, **delete/purge PII-bearing PG child rows** (`document_pages`, `detected_entities`, `review_regions`, `original_filename` — retaining only PII-free `audit_logs` and tombstone ID), cancel active jobs, and wipe all disk artifacts.
- [ ] **R2.6 (`BE-12` Global Safe Logging & Secret-Scanner Hygiene):** <!-- Red-Team Fix: Finding 12, Finding 13 -->
  - Add `configure_global_safe_logging()` in [config/logger.py](../../config/logger.py) attaching `SafeFormatter` to root, `uvicorn.*`, `sqlalchemy.*`, and `httpx` at startup; extend `SECRET_PATTERNS` (unquoted credentials, `postgresql://user:pass@`, `Cookie`/`Set-Cookie`) and `PII_LOG_PATTERNS` (US SSN, US/intl phone, CMND, MST, Amex); add payload-free global FastAPI exception handler.
  - Update [scripts/check_secrets.py](../../scripts/check_secrets.py) to prune runtime directories (`storage`, `frontend/dist`, `logs`), narrow its `config/system_config.py` whitelist to the exact dev placeholder constant instead of skipping the whole file, and document an out-of-repo `--env-file` path so local Docker runs never break `make check-secrets` or `tests/test_ops01_environment.py`.

## Architecture & Subprocess Isolation Flow

```text
HTTP POST /api/v1/documents (authenticated + CSRF verified on `api`)
  -> Stream to /app/storage/temp/quarantine_{doc_id}.pdf (abort if > MAX_FILE_SIZE_MB or missing %PDF- header; NO native PDF parser in `api`)
  -> PG transaction: INSERT documents(status='PENDING_INTAKE') + INSERT jobs(type='ANALYZE', status='QUEUED') + INSERT audit_logs
  -> Return 202 Accepted {document_id, job_id, status}
Zero-Egress `worker` (`internal: true`):
  -> Spawn clean subprocess.Popen (scrubbed env={}, no DB/JWT/ML secrets, psutil RSS watchdog, 15s timeout):
       validate unencrypted, pages <= 100, xref <= 50k, inflation & image pixel caps
  -> If rejected -> purge quarantine file, mark documents.status='REJECTED' + structured error code
  -> If valid -> atomic move to /app/storage/private/originals/{doc_id}.pdf (chmod 0640) + proceed to Phase 3 analysis
```

## Files to Create / Modify

- Modify: `requirements.txt` (bump `pymupdf>=1.25.0,<2.0`; add `sqlalchemy>=2.0.35`, `alembic>=1.13.0`, `psycopg[binary]>=3.2.0`, `pikepdf>=9.4.0`, `Pillow>=11.0.0`, `numpy>=2.1.0`, `opencv-python-headless>=4.10.0`, `pytesseract>=0.3.13`, `deskew>=0.10.29`, `argon2-cffi>=23.1.0`, `PyJWT>=2.9.0`, `httpx>=0.27.0`, `langid>=1.1.6`)
- Create: `requirements-ml.txt` (`presidio-analyzer>=2.2.355`, exact pinned `en_core_web_lg` wheel URL, `spacy>=3.8.0,<3.9.0`, `torch>=2.2.0,<3.0.0`, `safetensors>=0.4.5`) <!-- Red-Team Fix: Finding 1 -->
- Modify: `pyproject.toml` (bump `pymupdf>=1.25.0,<2.0`; register `e2e` and `integration` pytest markers) <!-- Red-Team Fix: Finding 1, Finding 12 -->
- Modify: `docker/Dockerfile` (multi-stage: `frontend-builder` `node:22-slim`, `app-runtime` with SHA-256-verified `tessdata_best` + `poppler-utils` + `qpdf` + root-owned RO `/app`, `ml-runtime` with baked `en_core_web_lg`; remove baked single-port `HEALTHCHECK`) <!-- Red-Team Fix: Finding 1, Finding 4, Finding 11 -->
- Modify: `docker-compose.yml` (add `postgres:16-alpine`, `ml-service`, `backend_internal` `internal: true` network, named volume `pii_storage`, `read_only: true`, `cap_drop: [ALL]`, `APP_PORT`, per-service healthchecks) <!-- Red-Team Fix: Finding 4, Finding 11 -->
- Create: `docker-compose.opf.yml` (optional mounted-weights + 12G RAM override for `ML_MODEL_PROFILE=opf_high_ram`) <!-- Red-Team Fix: Finding 14b -->
- Modify: `.dockerignore` (add `**/node_modules`, `frontend/dist`) <!-- Red-Team Fix: Finding 11 -->
- Modify: `config/system_config.py` (add `database_url`, `ml_service_url`, `ml_service_token`, `ml_model_profile`, `subprocess_rss_limit_mb`, `cookie_secure`, `trusted_proxy_cidrs`; harden `validate_security()` for `production`/`staging` while preserving `tests/test_ops01_environment.py`) <!-- Red-Team Fix: Finding 5, Finding 14a -->
- Modify: `config/logger.py` (add `configure_global_safe_logging()`, expand secret & bilingual PII patterns) <!-- Red-Team Fix: Finding 13 -->
- Modify: `scripts/check_secrets.py` (prune runtime dirs `storage`/`frontend/dist`/`logs`, narrow `config/system_config.py` placeholder allowlist) <!-- Red-Team Fix: Finding 12 -->
- Modify: `.env.example` (document PG, `ML_SERVICE_TOKEN`, `APP_PORT`, `TRUSTED_PROXY_CIDRS`, out-of-repo `--env-file` usage)
- Create: `app/db/session.py`, `app/security/auth.py`, `app/security/csrf.py`, `app/security/rbac.py`, `app/security/audit.py`
- Create: `app/storage/local_store.py`, `app/worker/isolation.py`, `app/worker/queue.py`, `app/worker/runner.py`
- Create: `app/api/routes/auth.py`, `app/api/routes/documents.py`, `app/api/routes/health.py`, `app/main.py`
- Create: `scripts/seed_demo_users.py`
- Create: `tests/test_phase02_auth_intake_queue.py` (unit/mocked tests for auth, CSRF, startup security gate, safe global logging, PDF-bomb intake, `SKIP LOCKED` queue, dead-lettering, and tombstone purge)

## Implementation Steps

1. Update `requirements.txt`, `requirements-ml.txt`, `pyproject.toml`, `.dockerignore`, `docker/Dockerfile`, `docker-compose.yml`, `docker-compose.opf.yml`, `.env.example`, `config/system_config.py`, `config/logger.py`, and `scripts/check_secrets.py`; verify `tests/test_ops01_environment.py` stays green.
2. Implement `app/db/session.py`, `app/security/auth.py` (Argon2id, revocable sessions, DB rate limiter), `app/security/csrf.py`, `app/security/rbac.py`, and `app/security/audit.py`.
3. Implement `app/worker/isolation.py` (clean `subprocess.Popen` with scrubbed `env`, staging-dir isolation, `psutil` RSS watchdog, non-blocking heartbeat + cancellation polling) and `app/storage/local_store.py` (atomic move under PG row lock, full purge).
4. Implement `app/worker/queue.py` and `app/worker/runner.py` (`SKIP LOCKED`, 30s lease heartbeat, stale-lease reaper, `max_attempts=3` dead-lettering).
5. Implement `app/api/routes/auth.py`, `documents.py`, `health.py`, and `app/main.py` (startup `validate_security()`, `configure_global_safe_logging()`, payload-free exception handler, `/health`, `/ready`).
6. Add `scripts/seed_demo_users.py` and `tests/test_phase02_auth_intake_queue.py`.

## Todo

- [ ] Update dependencies, multi-stage `docker/Dockerfile`, hardened `docker-compose.yml`, `docker-compose.opf.yml`, `.dockerignore`, and `pyproject.toml`
- [ ] Harden `config/system_config.py`, `config/logger.py` (global framework scrubbing), and `scripts/check_secrets.py`
- [ ] Implement auth, CSRF protection, trusted-proxy DB login throttling, owner RBAC, and PII-free audit logger
- [ ] Implement scrubbed-env `subprocess.Popen` isolation with `psutil` RSS watchdog + PDF-bomb intake gate
- [ ] Implement PostgreSQL `SKIP LOCKED` queue, non-blocking heartbeat/cancel loop, dead-lettering, and full PII-row + file tombstone deletion
- [ ] Wire FastAPI endpoints (`/api/v1/auth/*`, `/api/v1/documents/*`, `/health`, `/ready`) and run `tests/test_phase02_auth_intake_queue.py`, `tests/test_ops01_environment.py`, and `make check-secrets`

## Security Considerations

- Zero outbound internet egress for `worker`, `postgres`, and `ml-service` via Docker `internal: true` network; native PDF parsing never runs inside the external-network `api` container.
- Untrusted PDF parser/OCR/redaction subprocesses never receive `DATABASE_URL`, `JWT_SECRET_KEY`, or `ML_SERVICE_TOKEN`, and receive only per-job staging paths (with `/app` root-owned read-only). *(Same-UID cross-tenant OS filesystem sandboxing via separate parser UIDs/containers is noted as a post-MVP hardening step.)*
- All mutating cookie-authenticated routes enforce `SameSite=Lax` + CSRF token + `Origin`/`Sec-Fetch-Site` validation.
- Keep `scripts/check_secrets.py` clean (`make check-secrets` exit `0`). <!-- Red-Team Fix: Finding 12 -->

## Risk Assessment & Load-Bearing Assumptions

| Load-Bearing Assumption | Observable Break Signal | Pre-Decided Response |
|---|---|---|
| Named volume `pii_storage` + `read_only: true` rootfs works with `tesseract`, `poppler`, and `pymupdf` temp needs | Subprocess fails with `Read-only file system` writing to `/tmp` | Mount container `tmpfs: [/tmp:size=512m,noexec,nosuid]` in `docker-compose.yml` while keeping `/app` read-only |
| `psutil` RSS watchdog catches memory spikes fast enough before Linux OOM-killer hits container | Crafted PDF spikes RSS faster than 2s poll interval | Tighten poll interval to 0.5s during intake/OCR and keep container `memory` limit + high `RLIMIT_AS` (4 GB) safety net |

## Verification & Success Criteria

```bash
python3 -m pytest tests/test_phase02_auth_intake_queue.py tests/test_ops01_environment.py -v
make check-secrets
docker compose config --quiet
```

- `docker compose config --quiet` validates all 4 services, `internal: true` network, and named `pii_storage` volume cleanly.
- Startup with default `JWT_SECRET_KEY` under `APP_ENV=production` or `staging` fails closed immediately; mutating cookie requests without valid CSRF token return `403`.
- Cross-account access returns `403`/`404`; encrypted, non-PDF, oversized, and PDF-bomb uploads are rejected with zero orphaned files.
- Deleting a document during an active job kills the subprocess, deletes PII child rows in PG, and leaves zero artifacts on disk.
- Framework error logs (`uvicorn`, `sqlalchemy`, `httpx`) scrub `DATABASE_URL`, `Cookie`, US SSN, and VN PII completely.
