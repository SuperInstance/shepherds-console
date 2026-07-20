# Changelog

All notable changes to `shepherds-console` are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v0.1.4 — 2026-07-20

### Fixed
- **`complete_task` now skips inactive fences.** When a fence has `limit <= 0` (indicating it should be inactive/skipped), `complete_task` no longer attempts to process it. Previously, inactive fences could interfere with task completion logic by trying to evaluate constraints on a fence that was never activated.

## v0.1.3 — 2026-07-20

### Fixed
- **Fence `limit=0` raises `ValueError` instead of `ZeroDivisionError`.** Creating a fence with `limit=0` previously caused a cryptic `ZeroDivisionError` when the fence tried to compute utilization ratios. Now raises an explicit `ValueError` with a clear message explaining that `limit` must be positive.

## v0.1.2 — 2026-07-19

### Fixed
- **Input validation for API endpoints.** Added strict type checking and bounds validation for all user-facing inputs to prevent injection of malformed data.
- **Duplicate animal prevention.** The fleet registry now prevents registering the same animal ID more than once, raising a clear error instead of silently overwriting.
- Added 7 regression tests covering validation edge cases.

## v0.1.1 — 2026-07-18

### Fixed
- Removed deprecated License classifier (PEP 639 compliance)
- Using SPDX license expression `license = "MIT"` instead

## v0.1.0 — 2026-07-17

### Initial Release
- Single-pane operations dashboard for working animal infrastructure
- Fleet status, model lineage, breeding records
- Web UI + CLI entry point
- 33 tests passing
