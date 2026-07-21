# Changelog

All notable changes to `shepherds-console` are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-07-21

### Fixed
- **Failing test shipped in 0.1.4**: `test_add_fence_negative_limit` expected "limit must be non-negative" but the code correctly raises "limit must be positive". A zero-limit fence is silently permissive (budget_fraction returns 0.0, status reads "exhausted", but consume() still returns True on throttle), so rejecting limit<=0 is the correct, safe behavior. The test was wrong; the code was right. Test fixed + `test_add_fence_zero_limit_rejected` added.
- **Version desync**: `__version__` was hardcoded as "0.1.1" while pyproject said 0.1.4. Now derived from package metadata via `importlib.metadata`.
- **Dead code in `complete_task`**: was checking `if fence.limit <= 0: continue` but `add_fence` already rejects limit<=0 at construction. Changed to check `fence.enabled` instead — the actual skip condition.

### Added
- **CI gate** (`.github/workflows/ci.yml`): pytest on Python 3.10–3.13 with version-sync verification. Root cause fix — prevents shipping red releases.
- **State persistence** (`save_state` / `load_state`): full JSON round-trip of pastures, fences, kennel, and audit trail. Edge-critical: the console can now survive a restart and restore its watch state.
- **External enforcer integration** (`register_external_fence` + `FenceReport` Protocol): the dashboard can now consume real fence state from FLUX bytecode, cocapn spectral, or any enforcer that implements the protocol. The dashboard becomes a *view* onto real conservation state, not a duplicate model.
- **5 new tests**: state persistence round-trip, load error handling, external fence registration, zero-limit rejection, version sync verification. 47/47 passing.

### Changed
- Minor version bump (0.1.x → 0.2.0): the test fix and new features are a meaningful contract change. The `FenceReport` protocol and `register_external_fence` are new public API surface.

## v0.1.4 — 2026-07-20

### Fixed
- `complete_task` now skips inactive fences (limit<=0) instead of crashing

## v0.1.3 — 2026-07-20

### Fixed
- Fence `limit=0` raises `ValueError` instead of `ZeroDivisionError`

## v0.1.2 — 2026-07-19

### Fixed
- Input validation: negative capacity, negative cost, negative consume amounts
- Duplicate animal prevention in pasture lists
- Fence status gap at budget_fraction=0.7

## v0.1.1 — 2026-07-18

### Fixed
- Removed deprecated License classifier (PEP 639 compliance)
- Using SPDX license expression `license = "MIT"` instead

## v0.1.0 — 2026-07-13

### Initial Release
- Single-pane operations dashboard for working animal infrastructure
- Pastures (PLATO rooms), Fences (conservation enforcers), Kennel (flux registry)
- Terminal + web renderers, JSON export
- 33 tests passing
