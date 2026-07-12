"""Web dashboard renderer for The Shepherd's Console.

Generates a single self-contained HTML page with auto-refresh.
"""

from __future__ import annotations

import html
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shepherds_console import ShepherdsConsole


def _esc(s: str | int | float | bool) -> str:
    """HTML-escape a value."""
    return html.escape(str(s))


def render_html(console: ShepherdsConsole, refresh_seconds: int = 5) -> str:
    """Render a self-contained HTML dashboard page.

    Args:
        console: The ShepherdsConsole instance.
        refresh_seconds: Auto-refresh interval (0 to disable).
    """
    s = console._summary()
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    # Build pasture rows
    pasture_rows: list[str] = []
    for p in console.pastures.values():
        util_pct = p.utilization * 100
        util_class = (
            "critical" if util_pct >= 90
            else "warn" if util_pct >= 70
            else "ok"
        )
        pasture_rows.append(f"""
        <tr>
          <td>{_esc(p.name)}</td>
          <td><span class="badge mode-{_esc(p.mode.value)}">{_esc(p.mode.value)}</span></td>
          <td class="num">{p.occupancy}</td>
          <td class="num">{p.capacity}</td>
          <td>
            <div class="bar-container">
              <div class="bar-fill {util_class}" style="width:{util_pct:.0f}%"></div>
              <span class="bar-label">{util_pct:.0f}%</span>
            </div>
          </td>
          <td class="num">{p.tasks_completed}</td>
          <td class="num">{p.tasks_in_progress}</td>
          <td class="num">{p.throughput:.1f}</td>
        </tr>""")

    # Build fence rows
    fence_rows: list[str] = []
    for f in console.fences.values():
        pct = f.budget_fraction * 100
        fence_rows.append(f"""
        <tr>
          <td>{_esc(f.name)}</td>
          <td><span class="badge status-{_esc(f.status)}">{_esc(f.status)}</span></td>
          <td class="num">{f.consumed:.0f}</td>
          <td class="num">{f.limit:.0f}</td>
          <td>
            <div class="bar-container">
              <div class="bar-fill {f.status}" style="width:{pct:.0f}%"></div>
              <span class="bar-label">{pct:.0f}%</span>
            </div>
          </td>
          <td class="num">{f.violations}</td>
          <td>{_esc(f.action)}</td>
        </tr>""")

    # Build kennel rows
    kennel_rows: list[str] = []
    for a in console.kennel.values():
        ago = _time_ago(a.last_active)
        kennel_rows.append(f"""
        <tr>
          <td>{_esc(a.name)}</td>
          <td>{_esc(a.role)}</td>
          <td>{_esc(a.pasture or '—')}</td>
          <td><span class="badge health-{_esc(a.health.value)}">{_esc(a.health.value)}</span></td>
          <td class="num">{a.tasks_completed}</td>
          <td>{_esc(ago)}</td>
        </tr>""")

    # Build audit entries
    log_rows: list[str] = []
    for e in console.logs[-15:]:
        log_rows.append(f"""
        <tr class="log-{_esc(e.severity.value)}">
          <td class="muted">{_esc(time.strftime('%H:%M:%S', time.localtime(e.timestamp)))}</td>
          <td><span class="badge sev-{_esc(e.severity.value)}">{_esc(e.severity.value)}</span></td>
          <td>{_esc(e.source)}</td>
          <td>{_esc(e.message)}</td>
        </tr>""")

    refresh_tag = (
        f'<meta http-equiv="refresh" content="{refresh_seconds}">'
        if refresh_seconds > 0
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{refresh_tag}
<title>🐑 The Shepherd's Console</title>
<style>
  :root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3a;
    --text: #e0e0e8;
    --muted: #6b7080;
    --accent: #c792ea;
    --green: #c3e88d;
    --yellow: #ffcb6b;
    --red: #f07178;
    --cyan: #89ddff;
    --blue: #82aaff;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'SF Mono', 'Fira Code', 'JetBrains Mono', monospace;
    background: var(--bg);
    color: var(--text);
    padding: 20px;
    max-width: 1200px;
    margin: 0 auto;
  }}
  header {{
    text-align: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
  }}
  header h1 {{
    font-size: 1.8em;
    color: var(--accent);
  }}
  header .meta {{
    color: var(--muted);
    font-size: 0.85em;
    margin-top: 8px;
  }}
  .summary {{
    display: flex;
    gap: 24px;
    justify-content: center;
    flex-wrap: wrap;
    margin: 12px 0;
  }}
  .stat {{
    text-align: center;
    padding: 8px 16px;
    background: var(--surface);
    border-radius: 8px;
    border: 1px solid var(--border);
  }}
  .stat .val {{ font-size: 1.5em; font-weight: bold; }}
  .stat .lbl {{ font-size: 0.75em; color: var(--muted); }}
  section {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
  }}
  section h2 {{
    font-size: 0.9em;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--muted);
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85em;
  }}
  th {{ text-align: left; color: var(--muted); padding: 6px 8px; font-weight: normal; }}
  td {{ padding: 6px 8px; }}
  tr {{ border-bottom: 1px solid var(--border); }}
  tr:last-child {{ border-bottom: none; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .muted {{ color: var(--muted); }}
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.8em;
    font-weight: bold;
  }}
  .mode-plow {{ background: rgba(195,232,141,.15); color: var(--green); }}
  .mode-graze {{ background: rgba(137,221,255,.15); color: var(--cyan); }}
  .mode-fallow {{ background: rgba(107,112,128,.15); color: var(--muted); }}
  .status-healthy {{ background: rgba(195,232,141,.15); color: var(--green); }}
  .status-moderate {{ background: rgba(195,232,141,.15); color: var(--green); }}
  .status-low {{ background: rgba(255,203,107,.15); color: var(--yellow); }}
  .status-critical {{ background: rgba(240,113,120,.15); color: var(--red); }}
  .status-exhausted {{ background: rgba(240,113,120,.25); color: var(--red); }}
  .status-disabled {{ background: rgba(107,112,128,.15); color: var(--muted); }}
  .health-healthy {{ background: rgba(195,232,141,.15); color: var(--green); }}
  .health-degraded {{ background: rgba(255,203,107,.15); color: var(--yellow); }}
  .health-injured {{ background: rgba(240,113,120,.15); color: var(--red); }}
  .health-offline {{ background: rgba(107,112,128,.15); color: var(--muted); }}
  .sev-info {{ color: var(--muted); }}
  .sev-warn {{ background: rgba(255,203,107,.15); color: var(--yellow); }}
  .sev-error {{ background: rgba(240,113,120,.15); color: var(--red); }}
  .sev-critical {{ background: rgba(240,113,120,.25); color: var(--red); }}
  .bar-container {{
    position: relative;
    width: 120px;
    height: 18px;
    background: var(--bg);
    border-radius: 4px;
    overflow: hidden;
    display: inline-block;
  }}
  .bar-fill {{
    height: 100%;
    border-radius: 4px;
    transition: width .3s;
  }}
  .bar-fill.ok {{ background: var(--green); }}
  .bar-fill.warn, .bar-fill.low {{ background: var(--yellow); }}
  .bar-fill.critical, .bar-fill.exhausted, .bar-fill.moderate {{ background: var(--red); }}
  .bar-fill.healthy {{ background: var(--green); }}
  .bar-fill.disabled {{ background: var(--muted); }}
  .bar-label {{
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75em;
    color: var(--text);
  }}
  .log-error td, .log-critical td {{ color: var(--red); }}
  .log-warn td {{ color: var(--yellow); }}
  footer {{
    text-align: center;
    color: var(--muted);
    font-size: 0.75em;
    padding: 16px 0;
  }}
</style>
</head>
<body>
  <header>
    <h1>🐑 The Shepherd's Console</h1>
    <div class="meta">Last updated: {now}</div>
    <div class="summary">
      <div class="stat"><div class="val">{s['healthy_animals']}/{s['total_animals']}</div><div class="lbl">healthy animals</div></div>
      <div class="stat"><div class="val">{s['active_pastures']}/{s['total_pastures']}</div><div class="lbl">active pastures</div></div>
      <div class="stat"><div class="val">{s['total_fences'] - s['exhausted_fences']}/{s['total_fences']}</div><div class="lbl">fences ok</div></div>
      <div class="stat"><div class="val">{s['total_violations']}</div><div class="lbl">violations</div></div>
      <div class="stat"><div class="val">{s['total_tasks']}</div><div class="lbl">tasks done</div></div>
    </div>
  </header>

  <section>
    <h2>🚜 Pastures (PLATO Rooms)</h2>
    <table>
      <thead>
        <tr>
          <th>Name</th><th>Mode</th><th>Animals</th><th>Cap</th>
          <th>Utilization</th><th>Done</th><th>WIP</th><th>TPM</th>
        </tr>
      </thead>
      <tbody>
        {''.join(pasture_rows) or '<tr><td colspan="8" class="muted">No pastures registered</td></tr>'}
      </tbody>
    </table>
  </section>

  <section>
    <h2>🚧 Fences (Conservation Enforcers)</h2>
    <table>
      <thead>
        <tr>
          <th>Name</th><th>Status</th><th>Consumed</th><th>Limit</th>
          <th>Budget</th><th>Violations</th><th>Action</th>
        </tr>
      </thead>
      <tbody>
        {''.join(fence_rows) or '<tr><td colspan="7" class="muted">No fences registered</td></tr>'}
      </tbody>
    </table>
  </section>

  <section>
    <h2>🐕 Kennel (Flux Registry)</h2>
    <table>
      <thead>
        <tr>
          <th>Name</th><th>Role</th><th>Pasture</th><th>Health</th>
          <th>Tasks</th><th>Last Active</th>
        </tr>
      </thead>
      <tbody>
        {''.join(kennel_rows) or '<tr><td colspan="6" class="muted">No animals registered</td></tr>'}
      </tbody>
    </table>
  </section>

  <section>
    <h2>📋 Audit Trail</h2>
    <table>
      <thead>
        <tr><th>Time</th><th>Severity</th><th>Source</th><th>Message</th></tr>
      </thead>
      <tbody>
        {''.join(log_rows) or '<tr><td colspan="4" class="muted">No events logged</td></tr>'}
      </tbody>
    </table>
  </section>

  <footer>
    The Shepherd's Console — Working Animal Architecture ·
    <a href="https://github.com/SuperInstance/shepherds-console" style="color:var(--muted)">GitHub</a>
  </footer>
</body>
</html>"""


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
