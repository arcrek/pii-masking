---
phase: 4
title: "Phase 4: Reviewer Web UI & Immutable Revision Locking"
status: todo
priority: P1
effort: "2w"
dependencies: [2, 3]
---

# Phase 4: Reviewer Web UI & Immutable Revision Locking

**Maps to backlog:** `FE-01..12`, `BE-08`, `BE-09`
**Primary owners:** `SE1` (React/Vite/Tailwind UI & viewer), `SE2` (review revision, static SPA mount & snapshot locking endpoints)

## Goal

Replace the static login preview in `frontend/` with the complete authenticated, CSRF-protected reviewer workspace — document upload, per-page analysis progress/error display, safe server-rendered PDF preview with zoom/rotate-invariant PII overlays, accept/reject and manual handwriting box editing, optimistic revision locking, export/verification status UI, document deletion, and production static SPA serving.

## Context & Existing Code Reuse

- Existing frontend starter: [frontend/package.json](../../frontend/package.json) (React `19.3.1`, Vite `8.3.8`, Tailwind CSS `4.3.5`), [frontend/main.jsx](../../frontend/main.jsx), [frontend/index.html](../../frontend/index.html), [frontend/vite.config.js](../../frontend/vite.config.js), [frontend/styles.css](../../frontend/styles.css).
- Safe preview PNGs promoted to `./storage/private/previews/{doc_id}/page_{n}.png` in Phase 3 eliminate browser-side PDF active-content/JavaScript/external-fetch execution (`FE-05`, `BE-05`).

## Requirements

- [ ] **R4.1 (`BE-08` Optimistic Review Revisions):** Implement `GET /api/v1/documents/{id}/review` and `PATCH /api/v1/documents/{id}/review` with `expected_revision_no` optimistic concurrency check (`409 Conflict` on stale concurrent edits) and CSRF enforcement; preserve original `detected_entities` immutably when a reviewer rejects an auto-suggestion; validate every manual region rectangle lies within `[0, visual_width] x [0, visual_height]`.
- [ ] **R4.2 (`BE-09` Immutable Snapshot Lock):** Implement `POST /api/v1/documents/{id}/review/lock` verifying all pages are analyzed without `FAILED` status, all pages are visually reviewed (even when 0 PII detected), and zero unreviewed residual candidates from `VER-06` remain; freezes an immutable `LOCKED` `review_revisions` record. Any subsequent edit marks the prior snapshot `SUPERSEDED`, creates a new `DRAFT` revision (`revision_no + 1`, enforced by `uq_one_draft_per_doc`), and invalidates prior `export_artifacts`.
- [ ] **R4.3 (`FE-01..04` Auth, CSRF, Upload & Document List):** Implement login/logout with CSRF token handling and session-expiry redirect, drag-and-drop PDF upload with server error display/retry, authenticated user document list, and granular per-page progress + error banners (`FAILED` / `NEEDS_ATTENTION` pages block "Complete" badges). <!-- Red-Team Fix: Finding 5 -->
- [ ] **R4.4 (`FE-05..07` Safe Viewer, Overlays & Tailwind v4 Styling):** Refactor [frontend/styles.css](../../frontend/styles.css) to wrap base element styles in `@layer base` so Tailwind v4 utility classes are never overridden. Render authenticated per-page safe preview images with zoom (`50%–300%`), display-only view rotation (`0°/90°/180°/270°`), color-coded SVG overlays for the 6 canonical groups + `MANUAL` regions, synchronized sidebar list with canonical-group filters and jump-to-page, and explicit "uncalibrated score" display. <!-- Red-Team Fix: Finding 11 -->
- [ ] **R4.5 (`FE-08..10` Review Actions, Manual Handwriting Boxes & Lock Gate):** Per-region and bulk-by-group accept/reject toggles, click-and-drag manual rectangle drawing/resizing/deletion using `svgElement.getScreenCTM().inverse()` for missed PII, handwriting, and signatures, per-page reviewed checkboxes with explicit handwriting reminder banner, and Lock Revision button disabled until all preconditions pass.
- [ ] **R4.6 (`FE-11`, `FE-12` Export, Report, Delete & Production SPA Serving):** Trigger export on the locked revision, display structured Verification Report (`PASS`/`FAIL`/`INCONCLUSIVE` checks without raw PII, plus clear re-review guidance when `VER-06` creates a new `DRAFT` revision), download verified PDF bound to the current locked revision, confirm-delete document, and mount built `frontend/dist` + SPA catch-all fallback in `app/main.py` (excluding `/api/*`, `/health`, `/ready`, `/metrics`). <!-- Red-Team Fix: Finding 11 -->

## Architecture & Coordinate Binding (FE)

```text
Stored Region in PG: visual_rect = (x0, y0, x1, y1) relative to (visual_width, visual_height)
Safe Preview Image:  served via GET /api/v1/documents/{id}/pages/{n}/preview (PNG, auth+RBAC checked)
Viewer Transform:
  - Canvas renders PNG at (visual_width * zoom, visual_height * zoom)
  - Overlay SVG maps visual_rect directly via viewBox="0 0 {visual_width} {visual_height}"
  - View rotation (0/90/180/270) rotates composite container; svg.getScreenCTM().inverse()
    projects pointer drag events directly back into exact visual_rect coordinates
```

## Files to Create / Modify

- Create: `app/api/routes/review.py` (`GET/PATCH /review`, `POST /review/lock`, `GET /pages/{n}/preview`)
- Create: `app/services/review_service.py` (optimistic revision mutations, bounds validation, snapshot lock preconditions, `SUPERSEDED` + `revision_no + 1` creation, prior export invalidation)
- Modify: `app/main.py` (register `review` router, mount `/app/frontend/dist` via `StaticFiles` + SPA fallback excluding `/api/*`, `/health`, `/ready`, `/metrics`, configure dev CORS) <!-- Red-Team Fix: Finding 11 -->
- Modify: `frontend/styles.css` (wrap legacy element rules inside `@layer base` or replace with Tailwind v4 theme tokens so utility classes win) <!-- Red-Team Fix: Finding 11 -->
- Modify: `frontend/vite.config.js` (API dev proxy `/api -> http://localhost:8000`)
- Modify: `frontend/main.jsx` (mount full React application router/shell replacing `LoginPreview`)
- Create: `frontend/src/api/client.js` (fetch wrapper attaching `X-CSRF-Token` on `POST`/`PATCH`/`DELETE`, session-expiry redirect, `409 Conflict` handling) <!-- Red-Team Fix: Finding 5 -->
- Create: `frontend/src/pages/LoginPage.jsx`
- Create: `frontend/src/pages/DocumentsPage.jsx` (upload dropzone, document table, status badges, delete confirmation)
- Create: `frontend/src/pages/ReviewWorkspacePage.jsx` (split layout: safe page viewer + overlay + sidebar + lock/export bar)
- Create: `frontend/src/components/PageViewerCanvas.jsx` (zoom, display-only rotation, SVG overlay in `viewBox` space, manual box draw/edit/delete via `getScreenCTM().inverse()`)
- Create: `frontend/src/components/EntitySidebar.jsx` (6-group filter chips, provenance `native`/`ocr`/`manual` badges, accept/reject single & bulk actions)
- Create: `frontend/src/components/ExportVerificationPanel.jsx` (export trigger, PASS/FAIL/INCONCLUSIVE report viewer, residual-candidate re-review banner, download link)
- Create: `tests/test_phase04_review_revisions.py` (optimistic `409` conflict, CSRF check, out-of-bounds manual box `422`, lock blocked on failed/unreviewed pages, edit creating `revision_no + 1` and invalidating prior export, SPA fallback test)

## Implementation Steps

1. Implement `app/services/review_service.py` and `app/api/routes/review.py` enforcing owner RBAC, CSRF, coordinate bounds, optimistic `expected_revision_no`, and snapshot locking (`BE-08`, `BE-09`).
2. Fix `frontend/styles.css` (`@layer base` scoping), configure `frontend/vite.config.js` proxy, and mount built `frontend/dist` + SPA catch-all route in `app/main.py`.
3. Build `frontend/src/api/client.js`, `LoginPage.jsx`, and `DocumentsPage.jsx` (`FE-01..04`, `FE-12`).
4. Build `PageViewerCanvas.jsx` (`viewBox` + `getScreenCTM().inverse()`), `EntitySidebar.jsx`, `ReviewWorkspacePage.jsx`, and `ExportVerificationPanel.jsx` (`FE-05..11`).
5. Verify production frontend bundle builds cleanly (`npm --prefix frontend run build`) and run `tests/test_phase04_review_revisions.py`.

## Todo

- [ ] Implement `app/services/review_service.py` and `app/api/routes/review.py` (`BE-08`, `BE-09`)
- [ ] Fix `frontend/styles.css` Tailwind v4 layering and wire `frontend/dist` static + SPA serving in `app/main.py`
- [ ] Implement `frontend/src/api/client.js` (with CSRF header), `LoginPage.jsx`, and `DocumentsPage.jsx` (`FE-01..04`, `FE-12`)
- [ ] Implement `PageViewerCanvas.jsx`, `EntitySidebar.jsx`, `ReviewWorkspacePage.jsx`, and `ExportVerificationPanel.jsx` (`FE-05..11`)
- [ ] Run backend revision tests and `npm --prefix frontend run build`

## Security Considerations

- Serving server-rendered preview PNGs with `Content-Security-Policy: default-src 'none'; img-src 'self'` completely blocks PDF JavaScript, launch actions, and external resource callbacks in the reviewer's browser.
- Every preview image URL requires authenticated session cookies and owner RBAC (no unsigned public static paths), and all mutating calls require valid CSRF tokens.

## Risk Assessment & Load-Bearing Assumptions

| Load-Bearing Assumption | Observable Break Signal | Pre-Decided Response |
|---|---|---|
| 150 DPI server-rendered preview PNGs provide legible text for dense small-font contracts | Reviewers report blurred 7–8 pt table text at 200% zoom | Increase preview render DPI from 150 to 200 DPI in `app/ocr/normalizer.py`; `viewBox` coordinates stay unchanged |
| `getScreenCTM().inverse()` stays accurate under CSS view rotation (90°/180°/270°) | Manual box drawn on a rotated page jumps to wrong quadrant after save & reload | Add automated coordinate-mapping tests across all 4 rotations before Phase 6 |

## Verification & Success Criteria

```bash
python3 -m pytest tests/test_phase04_review_revisions.py -v
npm --prefix frontend run build
```

- `npm --prefix frontend run build` succeeds with zero errors and Tailwind utility classes render cleanly without `frontend/styles.css` override.
- `GET /` and deep SPA routes serve `frontend/dist/index.html` while `/api/*` returns JSON.
- Concurrent `PATCH /review` with stale `expected_revision_no` returns `409 Conflict`; out-of-bounds manual box returns `422`.
- `POST /review/lock` rejects locking when any page is `FAILED`, unreviewed, or has unaddressed residual candidates; editing after lock creates `revision_no + 1` and marks prior exports invalid.
