"""
The Shepherd's Console — single-pane operations for working animal infrastructure.

Provides a dashboard for monitoring pastures (PLATO rooms), fences (conservation
enforcers), the kennel (flux registry), and an audit trail of recent events.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

try:
    from importlib.metadata import version as _pkg_version, PackageNotFoundError
    try:
        __version__ = _pkg_version("shepherds-console")
    except PackageNotFoundError:
        __version__ = "0.0.0+dev"
except ImportError:
    __version__ = "0.2.0"
__all__ = [
    "ShepherdsConsole",
    "Pasture",
    "Fence",
    "Animal",
    "LogEntry",
    "Health",
    "PastureMode",
    "Severity",
    "FenceReport",
]

__author__ = "SuperInstance"


class Health(str, Enum):
    """Working animal health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    INJURED = "injured"
    OFFLINE = "offline"


class PastureMode(str, Enum):
    """Pasture operational modes."""

    PLOW = "plow"      # Active work
    GRAZE = "graze"    # Idle / consuming
    FALLOW = "fallow"  # Resting / disabled


class Severity(str, Enum):
    """Audit log severity levels."""

    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"


class FenceReport(Protocol):
    """Contract for external conservation enforcers to report state.

    Any enforcer (FLUX bytecode, cocapn spectral, or custom) can implement
    this to feed real fence state into the dashboard instead of the
    dashboard inventing its own model.
    """

    name: str
    limit: float
    consumed: float
    violations: int
    action: str
    enabled: bool

    @property
    def remaining(self) -> float: ...
    @property
    def budget_fraction(self) -> float: ...


@dataclass
class LogEntry:
    """A single audit trail entry."""

    timestamp: float
    message: str
    severity: Severity = Severity.INFO
    source: str = "system"

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
        }


@dataclass
class Pasture:
    """A PLATO room — bounded workspace for working animals."""

    name: str
    mode: PastureMode = PastureMode.FALLOW
    capacity: int = 10
    animals: list[str] = field(default_factory=list)
    tasks_completed: int = 0
    tasks_in_progress: int = 0
    throughput: float = 0.0  # tasks per minute

    @property
    def occupancy(self) -> int:
        return len(self.animals)

    @property
    def utilization(self) -> float:
        """Fraction of capacity in use."""
        return self.occupancy / self.capacity if self.capacity else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mode": self.mode.value,
            "capacity": self.capacity,
            "occupancy": self.occupancy,
            "utilization": round(self.utilization, 4),
            "animals": list(self.animals),
            "tasks_completed": self.tasks_completed,
            "tasks_in_progress": self.tasks_in_progress,
            "throughput": self.throughput,
        }


@dataclass
class Fence:
    """A conservation enforcer — guardrail against overconsumption."""

    name: str
    limit: float
    consumed: float = 0.0
    action: str = "throttle"  # throttle, block, alert
    violations: int = 0
    enabled: bool = True

    @property
    def remaining(self) -> float:
        return max(0.0, self.limit - self.consumed)

    @property
    def budget_fraction(self) -> float:
        """Fraction of budget remaining."""
        return self.remaining / self.limit if self.limit else 0.0

    @property
    def status(self) -> str:
        """Human-readable status."""
        frac = self.budget_fraction
        if not self.enabled:
            return "disabled"
        if frac <= 0:
            return "exhausted"
        if frac < 0.1:
            return "critical"
        if frac < 0.3:
            return "low"
        if frac <= 0.7:
            return "moderate"
        return "healthy"

    def consume(self, amount: float) -> bool:
        """Try to consume from the budget. Returns True if allowed."""
        if amount < 0:
            raise ValueError(f"consume amount must be non-negative, got {amount}")
        if not self.enabled:
            return True
        if self.consumed + amount > self.limit:
            self.violations += 1
            if self.action == "block":
                return False
            # throttle: allow but warn
        self.consumed += amount
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "limit": self.limit,
            "consumed": self.consumed,
            "remaining": round(self.remaining, 2),
            "budget_fraction": round(self.budget_fraction, 4),
            "status": self.status,
            "action": self.action,
            "violations": self.violations,
            "enabled": self.enabled,
        }


@dataclass
class Animal:
    """A working animal registered in the kennel (flux registry)."""

    name: str
    pasture: str | None = None
    role: str = "flux"
    health: Health = Health.HEALTHY
    tasks_completed: int = 0
    last_active: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "pasture": self.pasture,
            "role": self.role,
            "health": self.health.value,
            "tasks_completed": self.tasks_completed,
            "last_active": self.last_active,
            "metadata": dict(self.metadata),
        }


class ShepherdsConsole:
    """Main dashboard class — single-pane view of working animal infrastructure."""

    def __init__(self) -> None:
        self.pastures: dict[str, Pasture] = {}
        self.fences: dict[str, Fence] = {}
        self.kennel: dict[str, Animal] = {}
        self.logs: list[LogEntry] = []
        self._max_logs: int = 500

    # ── Registration ──────────────────────────────────────────

    def add_pasture(
        self,
        name: str,
        mode: str | PastureMode = PastureMode.FALLOW,
        capacity: int = 10,
    ) -> Pasture:
        """Register a new pasture (PLATO room)."""
        if capacity < 0:
            raise ValueError(f"capacity must be non-negative, got {capacity}")
        p = Pasture(
            name=name,
            mode=PastureMode(mode) if isinstance(mode, str) else mode,
            capacity=capacity,
        )
        self.pastures[name] = p
        self.log(f"Pasture '{name}' created (mode={p.mode.value}, capacity={capacity})")
        return p

    def add_fence(
        self,
        name: str,
        limit: float,
        action: str = "throttle",
    ) -> Fence:
        """Register a new fence (conservation enforcer)."""
        if limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")
        f = Fence(name=name, limit=limit, action=action)
        self.fences[name] = f
        self.log(f"Fence '{name}' created (limit={limit}, action={action})")
        return f

    def add_animal(
        self,
        name: str,
        pasture: str | None = None,
        role: str = "flux",
        health: str | Health = Health.HEALTHY,
    ) -> Animal:
        """Register a working animal in the kennel."""
        a = Animal(
            name=name,
            pasture=pasture,
            role=role,
            health=Health(health) if isinstance(health, str) else health,
        )
        self.kennel[name] = a
        if pasture and pasture in self.pastures:
            self.pastures[pasture].animals.append(name)
        self.log(f"Animal '{name}' registered (role={role}, pasture={pasture})")
        return a

    # ── Operations ────────────────────────────────────────────

    def assign(self, animal: str, pasture: str) -> None:
        """Assign an animal to a pasture."""
        if animal not in self.kennel:
            raise KeyError(f"Unknown animal: {animal}")
        if pasture not in self.pastures:
            raise KeyError(f"Unknown pasture: {pasture}")
        a = self.kennel[animal]
        # Remove from old pasture
        if a.pasture and a.pasture in self.pastures:
            try:
                self.pastures[a.pasture].animals.remove(animal)
            except ValueError:
                pass
        a.pasture = pasture
        # Avoid duplicate entries in the pasture's animal list
        if animal not in self.pastures[pasture].animals:
            self.pastures[pasture].animals.append(animal)
        self.log(f"Animal '{animal}' assigned to pasture '{pasture}'")

    def complete_task(self, animal: str, cost: float = 0.0) -> None:
        """Record a completed task, optionally consuming from fences."""
        if cost < 0:
            raise ValueError(f"cost must be non-negative, got {cost}")
        if animal not in self.kennel:
            raise KeyError(f"Unknown animal: {animal}")
        a = self.kennel[animal]
        a.tasks_completed += 1
        a.last_active = time.time()
        if a.pasture and a.pasture in self.pastures:
            self.pastures[a.pasture].tasks_completed += 1
            # decrement in_progress if any
            if self.pastures[a.pasture].tasks_in_progress > 0:
                self.pastures[a.pasture].tasks_in_progress -= 1
        if cost:
            for fence in self.fences.values():
                if not fence.enabled:
                    continue
                if not fence.consume(cost):
                    self.log(
                        f"Fence '{fence.name}' blocked consumption of {cost}",
                        severity=Severity.WARN,
                    )
                elif fence.budget_fraction < 0.1:
                    self.log(
                        f"Fence '{fence.name}' budget critical ({fence.status})",
                        severity=Severity.WARN,
                    )
        self.log(f"Task completed by '{animal}'", source=animal)

    def set_health(self, animal: str, health: str | Health) -> None:
        """Update an animal's health."""
        if animal not in self.kennel:
            raise KeyError(f"Unknown animal: {animal}")
        h = Health(health) if isinstance(health, str) else health
        old = self.kennel[animal].health
        self.kennel[animal].health = h
        sev = Severity.INFO
        if h in (Health.INJURED, Health.OFFLINE):
            sev = Severity.WARN
        self.log(
            f"Animal '{animal}' health: {old.value} → {h.value}",
            severity=sev,
            source=animal,
        )

    # ── Logging ───────────────────────────────────────────────

    def log(
        self,
        message: str,
        severity: Severity = Severity.INFO,
        source: str = "system",
    ) -> LogEntry:
        """Add an entry to the audit trail."""
        entry = LogEntry(
            timestamp=time.time(),
            message=message,
            severity=severity,
            source=source,
        )
        self.logs.append(entry)
        if len(self.logs) > self._max_logs:
            self.logs = self.logs[-self._max_logs:]
        return entry

    # ── Status ────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Return current state of all working animals."""
        return {
            "pastures": {n: p.to_dict() for n, p in self.pastures.items()},
            "fences": {n: f.to_dict() for n, f in self.fences.items()},
            "kennel": {n: a.to_dict() for n, a in self.kennel.items()},
            "logs": [e.to_dict() for e in self.logs[-20:]],
            "summary": self._summary(),
        }

    def _summary(self) -> dict[str, Any]:
        total_animals = len(self.kennel)
        healthy = sum(
            1 for a in self.kennel.values() if a.health == Health.HEALTHY
        )
        active_pastures = sum(
            1 for p in self.pastures.values() if p.mode == PastureMode.PLOW
        )
        exhausted_fences = sum(
            1 for f in self.fences.values() if f.status == "exhausted"
        )
        total_violations = sum(f.violations for f in self.fences.values())
        return {
            "total_animals": total_animals,
            "healthy_animals": healthy,
            "active_pastures": active_pastures,
            "total_pastures": len(self.pastures),
            "exhausted_fences": exhausted_fences,
            "total_fences": len(self.fences),
            "total_violations": total_violations,
            "total_tasks": sum(a.tasks_completed for a in self.kennel.values()),
        }

    # ── Persistence ───────────────────────────────────────────

    def save_state(self, path: str) -> None:
        """Save full state to JSON. Critical for edge: survives restart."""
        import json
        data = {
            "version": __version__,
            "saved_at": time.time(),
            "pastures": {n: p.to_dict() for n, p in self.pastures.items()},
            "fences": {n: f.to_dict() for n, f in self.fences.items()},
            "kennel": {n: a.to_dict() for n, a in self.kennel.items()},
            "logs": [e.to_dict() for e in self.logs],
        }
        with open(path, "w") as fh:
            json.dump(data, fh, indent=2)

    @classmethod
    def load_state(cls, path: str) -> "ShepherdsConsole":
        """Load full state from JSON snapshot."""
        import json
        with open(path) as fh:
            data = json.load(fh)
        c = cls()
        for name, d in data.get("fences", {}).items():
            f = Fence(
                name=d["name"],
                limit=d["limit"],
                consumed=d["consumed"],
                action=d["action"],
                violations=d["violations"],
                enabled=d["enabled"],
            )
            c.fences[name] = f
        for name, d in data.get("pastures", {}).items():
            p = Pasture(
                name=d["name"],
                mode=PastureMode(d["mode"]),
                capacity=d["capacity"],
                animals=list(d.get("animals", [])),
                tasks_completed=d.get("tasks_completed", 0),
                tasks_in_progress=d.get("tasks_in_progress", 0),
                throughput=d.get("throughput", 0.0),
            )
            c.pastures[name] = p
        for name, d in data.get("kennel", {}).items():
            a = Animal(
                name=d["name"],
                pasture=d.get("pasture"),
                role=d.get("role", "flux"),
                health=Health(d.get("health", "healthy")),
                tasks_completed=d.get("tasks_completed", 0),
                last_active=d.get("last_active", time.time()),
                metadata=d.get("metadata", {}),
            )
            c.kennel[name] = a
        for e in data.get("logs", []):
            c.logs.append(LogEntry(
                timestamp=e["timestamp"],
                message=e["message"],
                severity=Severity(e.get("severity", "info")),
                source=e.get("source", "system"),
            ))
        return c

    # ── External Enforcer Integration ─────────────────────────

    def register_external_fence(self, report: FenceReport) -> None:
        """Bind an external conservation enforcer (FLUX bytecode, cocapn, etc.)

        The dashboard becomes a *view* onto real enforcer state rather than
        inventing its own model. Implements Idea 3 from the audit.
        """
        f = Fence(
            name=report.name,
            limit=report.limit,
            consumed=report.consumed,
            action=report.action,
            violations=report.violations,
            enabled=report.enabled,
        )
        self.fences[report.name] = f
        self.log(
            f"External fence '{report.name}' registered "
            f"(limit={report.limit}, consumed={report.consumed})",
            source="external-enforcer",
        )

    # ── Rendering ─────────────────────────────────────────────

    def render_terminal(self) -> str:
        """Render dashboard for terminal output."""
        from shepherds_console.dashboard import render_terminal

        return render_terminal(self)

    def render_html(self) -> str:
        """Render dashboard as a standalone HTML page."""
        from shepherds_console.web import render_html

        return render_html(self)
