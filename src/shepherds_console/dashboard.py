"""Terminal dashboard renderer for The Shepherd's Console.

Uses ANSI escape codes for a clean terminal dashboard. Falls back to plain text.
Works with or without `rich` — gracefully degrades.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shepherds_console import ShepherdsConsole

# ANSI colors
_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_MAGENTA = "\033[35m"
_CYAN = "\033[36m"

# Status colors
_STATUS_COLOR = {
    "healthy": _GREEN,
    "moderate": _GREEN,
    "low": _YELLOW,
    "critical": _RED,
    "exhausted": _RED,
    "disabled": _DIM,
}

_HEALTH_COLOR = {
    "healthy": _GREEN,
    "degraded": _YELLOW,
    "injured": _RED,
    "offline": _DIM,
}

_MODE_COLOR = {
    "plow": _GREEN,
    "graze": _CYAN,
    "fallow": _DIM,
}

_SEVERITY_COLOR = {
    "info": _DIM,
    "warn": _YELLOW,
    "error": _RED,
    "critical": _RED + _BOLD,
}

_BAR_WIDTH = 20


def _color_bar(fraction: float, width: int = _BAR_WIDTH) -> str:
    """Render a horizontal bar chart."""
    filled = int(fraction * width)
    color = (
        _RED if fraction < 0.15
        else _YELLOW if fraction < 0.4
        else _GREEN
    )
    return f"{color}{'█' * filled}{'░' * (width - filled)}{_RESET}"


def _time_ago(ts: float) -> str:
    """Human-readable 'time ago' string."""
    delta = time.time() - ts
    if delta < 60:
        return f"{delta:.0f}s ago"
    if delta < 3600:
        return f"{delta / 60:.0f}m ago"
    if delta < 86400:
        return f"{delta / 3600:.1f}h ago"
    return f"{delta / 86400:.1f}d ago"


def _try_rich(console: ShepherdsConsole) -> str | None:
    """Try to use rich for rendering. Returns None if not available."""
    try:
        from rich.console import Console as RichConsole
        from rich.table import Table
        from rich.panel import Panel
        from rich.text import Text
        from io import StringIO
    except ImportError:
        return None

    buf = StringIO()
    rc = RichConsole(file=buf, width=100)
    s = console._summary()

    # Header
    rc.print(
        Text("🐑 The Shepherd's Console", style="bold magenta"),
        justify="center",
    )
    rc.print(
        Text(
            f"Animals: {s['healthy_animals']}/{s['total_animals']} healthy  "
            f"Pastures: {s['active_pastures']}/{s['total_pastures']} active  "
            f"Fences: {s['total_fences'] - s['exhausted_fences']}/{s['total_fences']} ok  "
            f"Violations: {s['total_violations']}  "
            f"Tasks: {s['total_tasks']}",
            style="dim",
        ),
        justify="center",
    )
    rc.print()

    # Pastures table
    pt = Table(title="Pastures (PLATO Rooms)", header_style="bold cyan")
    pt.add_column("Name")
    pt.add_column("Mode")
    pt.add_column("Animals", justify="right")
    pt.add_column("Capacity", justify="right")
    pt.add_column("Utilization")
    pt.add_column("Done", justify="right")
    pt.add_column("WIP", justify="right")
    pt.add_column("TPM", justify="right")

    for p in console.pastures.values():
        pt.add_row(
            p.name,
            p.mode.value,
            str(p.occupancy),
            str(p.capacity),
            f"{p.utilization:.0%}",
            str(p.tasks_completed),
            str(p.tasks_in_progress),
            f"{p.throughput:.1f}",
        )
    rc.print(pt)

    # Fences table
    ft = Table(title="Fences (Conservation Enforcers)", header_style="bold yellow")
    ft.add_column("Name")
    ft.add_column("Status")
    ft.add_column("Consumed", justify="right")
    ft.add_column("Limit", justify="right")
    ft.add_column("Budget", justify="right")
    ft.add_column("Violations", justify="right")
    ft.add_column("Action")

    for f in console.fences.values():
        ft.add_row(
            f.name,
            f.status,
            f"{f.consumed:.0f}",
            f"{f.limit:.0f}",
            f"{f.budget_fraction:.0%}",
            str(f.violations),
            f.action,
        )
    rc.print(ft)

    # Kennel table
    kt = Table(title="Kennel (Flux Registry)", header_style="bold blue")
    kt.add_column("Name")
    kt.add_column("Role")
    kt.add_column("Pasture")
    kt.add_column("Health")
    kt.add_column("Tasks", justify="right")
    kt.add_column("Last Active")

    for a in console.kennel.values():
        kt.add_row(
            a.name,
            a.role,
            a.pasture or "—",
            a.health.value,
            str(a.tasks_completed),
            _time_ago(a.last_active),
        )
    rc.print(kt)

    # Audit trail
    lt = Table(title="Audit Trail (Last 10)", header_style="dim")
    lt.add_column("Time", style="dim")
    lt.add_column("Sev", style="dim")
    lt.add_column("Source", style="dim")
    lt.add_column("Message")

    for e in console.logs[-10:]:
        lt.add_row(
            _time_ago(e.timestamp),
            e.severity.value,
            e.source,
            e.message,
        )
    rc.print(lt)

    return buf.getvalue()


def render_terminal(console: ShepherdsConsole) -> str:
    """Render the full dashboard for terminal display."""
    # Try rich first
    rich_output = _try_rich(console)
    if rich_output is not None:
        return rich_output

    # Fallback: ANSI plain text
    lines: list[str] = []
    s = console._summary()

    lines.append(f"{_BOLD}{_MAGENTA}{'═' * 60}{_RESET}")
    lines.append(
        f"{_BOLD}{_MAGENTA}  🐑 The Shepherd's Console{_RESET}"
    )
    lines.append(
        f"{_DIM}  "
        f"Animals: {s['healthy_animals']}/{s['total_animals']} healthy  "
        f"Pastures: {s['active_pastures']}/{s['total_pastures']} active  "
        f"Fences: {s['total_fences'] - s['exhausted_fences']}/{s['total_fences']} ok"
        f"{_RESET}"
    )
    lines.append(f"{_BOLD}{_MAGENTA}{'═' * 60}{_RESET}")
    lines.append("")

    # Pastures
    lines.append(f"{_BOLD}{_CYAN}PASTURES (PLATO Rooms){_RESET}")
    lines.append(
        f"  {'Name':<20} {'Mode':<8} {'Animals':>8} {'Cap':>6} "
        f"{'Util':>6} {'Done':>6} {'TPM':>6}"
    )
    lines.append(f"  {'─' * 64}")
    for p in console.pastures.values():
        mode_c = _MODE_COLOR.get(p.mode.value, "")
        lines.append(
            f"  {p.name:<20} {mode_c}{p.mode.value:<8}{_RESET} "
            f"{p.occupancy:>8} {p.capacity:>6} "
            f"{p.utilization:>5.0%} {p.tasks_completed:>6} "
            f"{p.throughput:>6.1f}"
        )
    lines.append("")

    # Fences
    lines.append(f"{_BOLD}{_YELLOW}FENCES (Conservation Enforcers){_RESET}")
    lines.append(
        f"  {'Name':<20} {'Status':<12} {'Budget':>8} {'Consumed':>10} "
        f"{'Violations':>10} {'Action':<10}"
    )
    lines.append(f"  {'─' * 72}")
    for f in console.fences.values():
        st_c = _STATUS_COLOR.get(f.status, "")
        bar = _color_bar(f.budget_fraction, 10)
        lines.append(
            f"  {f.name:<20} {st_c}{f.status:<12}{_RESET} "
            f"{f.budget_fraction:>7.0%} {bar} "
            f"{f.consumed:>8.0f}/{f.limit:<8.0f} "
            f"{f.violations:>10} {f.action:<10}"
        )
    lines.append("")

    # Kennel
    lines.append(f"{_BOLD}{_BLUE}KENNEL (Flux Registry){_RESET}")
    lines.append(
        f"  {'Name':<20} {'Role':<10} {'Pasture':<16} {'Health':<10} "
        f"{'Tasks':>6} {'Active':<12}"
    )
    lines.append(f"  {'─' * 76}")
    for a in console.kennel.values():
        h_c = _HEALTH_COLOR.get(a.health.value, "")
        lines.append(
            f"  {a.name:<20} {a.role:<10} {a.pasture or '—':<16} "
            f"{h_c}{a.health.value:<10}{_RESET} "
            f"{a.tasks_completed:>6} {_time_ago(a.last_active):<12}"
        )
    lines.append("")

    # Audit trail
    lines.append(f"{_DIM}AUDIT TRAIL (Last 10){_RESET}")
    lines.append(f"  {'─' * 76}")
    for e in console.logs[-10:]:
        sev_c = _SEVERITY_COLOR.get(e.severity.value, "")
        lines.append(
            f"  {_time_ago(e.timestamp):<12} "
            f"{sev_c}{e.severity.value:<8}{_RESET} "
            f"{e.source:<16} {e.message}"
        )
    lines.append("")
    lines.append(f"{_DIM}{'═' * 60}{_RESET}")

    return "\n".join(lines)
