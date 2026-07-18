# shepherds-console — Documentation

**Single-pane ops dashboard for Working Animal Infrastructure: pastures, fences, kennel, audit trail.**

> Companion guide to README.md. This document covers the dashboard architecture and programmatic API.

---

## What this package does

`shepherds-console` is the **human operator's window** into a Working Animal Infrastructure deployment. When you have PLATO rooms running, conservation fences active, and FLUX policies registered, the Shepherd's Console shows the operator what's happening in real time.

Four panels:

| Panel | Description |
|-------|-------------|
| **Pastures** | PLATO rooms where working animals operate — status, occupancy, throughput |
| **Fences** | Conservation enforcers — active guardrails, violation counts, enforcement actions |
| **Kennel** | FLUX registry policies — registered working animals, their roles, health |
| **Audit Trail** | Recent events — what happened, when, who did it |

Two surface modes:

- **Terminal UI** — `shepherds-console` (default). Keyboard-driven, 60fps refresh, low-bandwidth friendly. Designed for the boat link.
- **Web UI** — `shepherds-console --web --port 8080`. Browser-based, full graphs and history. Designed for shore-side monitoring.

---

## Architecture context

Sits at Tier 2 of Working Animal Infrastructure, alongside `conservation-enforcer` (fences) and `breed-registry` (kennel).

```
┌─────────────────────────────────────────────────────────┐
│                    shepherds-console                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│   │ Pastures   │  │ Fences     │  │ Kennel     │  Audit  │
│   │ (PLATO)    │  │ (Conserv.) │  │ (FLUX)     │  Trail  │
│   └────────────┘  └────────────┘  └────────────┘         │
└─────────────────────────────────────────────────────────┘
        │                │                │             │
        v                v                v             v
   PLATO rooms      Active fences    Registered     JSONL log
   (status feeds)   (enforcement)    policies       events
```

The console is **read-only by default**. It does not issue commands to fences or kennel — it observes. (A `--write` mode is gated behind an explicit `--confirm-irreversible` flag for the rare case the operator needs to push a command.)

---

## API reference

### `shepherds_console.dashboard.Dashboard`

The main entry point for both UIs.

```python
from shepherds_console import Dashboard
from shepherds_console.sources import FileSource

# Wire the dashboard to data sources
dashboard = Dashboard(
    pastures_source=FileSource("plato_state.jsonl"),
    fences_source=FileSource("enforcement_audit.jsonl"),
    kennel_source=FileSource("policy_registry.json"),
    audit_source=FileSource("audit.jsonl"),
)

# Render to terminal
dashboard.render_terminal(refresh_rate_hz=2)

# Or render to web
dashboard.render_web(port=8080)
```

### `shepherds_console.dashboard.Panel`

A single panel in the dashboard.

```python
from shepherds_console import Panel, PanelSection

pastures = Panel(
    name="Pastures",
    sections=[
        PanelSection("Active rooms", lambda state: state.pastures.active),
        PanelSection("Throughput (ops/sec)", lambda state: state.pastures.ops_per_sec),
        PanelSection("Queue depth", lambda state: state.pastures.queue_depth),
    ],
)
```

### `shepherds_console.web.app` (Web server)

When `render_web()` is called, the dashboard spins up a FastAPI server. Endpoints:

- `GET /` — main dashboard HTML
- `GET /api/pastures` — JSON snapshot of PLATO room state
- `GET /api/fences` — JSON snapshot of conservation fence state
- `GET /api/kennel` — JSON snapshot of registered policies
- `GET /api/audit?limit=100` — recent audit events
- `WebSocket /ws/live` — push channel for live updates

---

## Usage example

```bash
# Install
pip install shepherds-console

# Minimal: terminal dashboard reading from the local audit log
shepherds-console

# Web dashboard
shepherds-console --web --port 8080 \
    --audit-path /var/log/conservation/enforcement.jsonl \
    --kennel-path /etc/flux/registry.json

# In production: read from conservation-enforcer's audit log,
# breed-registry's loaded models, and PLATO rooms' state file.
```

```python
# Custom embedding: feed the dashboard from your own data sources
from shepherds_console import Dashboard
from shepherds_console.sources import CallableSource

dashboard = Dashboard(
    pastures_source=CallableSource(lambda: my_plato_state()),
    fences_source=CallableSource(lambda: my_enforcer_audit()),
)
dashboard.render_terminal(refresh_rate_hz=1)  # 1Hz for low-bandwidth
```

---

## Edge-first operation

The Shepherd's Console is designed for the boat — offline, wattage-constrained, with a low-bandwidth link. The terminal mode does not require a browser, runs at 60fps on a Raspberry Pi, and uses ~1MB of RAM. The web mode is a convenience for shore-side monitoring, not the primary interface.

The `--no-live` flag disables the refresh loop entirely, so the operator can run `shepherds-console --no-live` from a cron job to dump a snapshot once per hour without keeping a process alive.

---

## Ecosystem

- **CLI entry:** `src/shepherds_console/__main__.py`
- **Tests:** `tests/test_console.py`
- **Related:** `conservation-enforcer` (the fences shown), `breed-registry` (the kennel shown), PLATO rooms (the pastures shown)

## License

MIT — see `LICENSE`.
