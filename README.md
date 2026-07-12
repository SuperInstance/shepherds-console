# 🐑 The Shepherd's Console

**Single-pane operations for working animal infrastructure.**

The Shepherd's Console is the operations dashboard for a human operator managing working animal infrastructure — what your working animals are doing, what fences are active, what pastures are running, conservation budget status.

## What It Shows

| Panel | Description |
|-------|-------------|
| **Pastures** | PLATO rooms where working animals operate — status, occupancy, throughput |
| **Fences** | Conservation enforcers — active guardrails, violation counts, enforcement actions |
| **Kennel** | Flux registry policies — registered working animals, their roles, health |
| **Audit Trail** | Recent events — what happened, when, who did it |

## Quick Start

```bash
pip install shepherds-console

# Terminal dashboard
shepherds-console

# Web dashboard
shepherds-console --web --port 8080
```

## Programmatic Use

```python
from shepherds_console import ShepherdsConsole

console = ShepherdsConsole()

# Register a pasture
console.add_pasture("translation-farm", mode="PLATO", capacity=10)

# Register a fence (conservation enforcer)
console.add_fence("token-budget", limit=50000, action="throttle")

# Register a working animal
console.add_animal("translator-7", pasture="translation-farm", role="flux")

# Get status
print(console.status())

# Render
print(console.render_terminal())
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              The Shepherd's Console                  │
├─────────────┬───────────────┬───────────┬───────────┤
│   Pastures  │    Fences     │  Kennel   │  Audit    │
│  (PLATO)    │ (Enforcers)   │ (Flux)    │  Trail    │
├─────────────┼───────────────┼───────────┼───────────┤
│ Room status │ Guardrails    │ Registry  │ Events    │
│ Occupancy   │ Violations    │ Policies  │ Timeline  │
│ Throughput  │ Budget left   │ Health    │ Severity  │
└─────────────┴───────────────┴───────────┴───────────┘
```

## Conceptual Model

This is part of **Working Animal Architecture** — a system where AI workers are treated as working animals that need pastures (workspaces), fences (guardrails), and a kennel (registry).

- **Pasture** — A bounded workspace (PLATO room) where animals graze on tasks
- **Fence** — A conservation enforcer that prevents overconsumption
- **Kennel** — The registry where animals are tracked, vetted, and dispatched
- **Shepherd** — The human operator who watches the console

## License

MIT
