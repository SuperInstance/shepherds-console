"""Console entry point for shepherds-console."""

from __future__ import annotations

import argparse
import http.server
import sys

from shepherds_console import ShepherdsConsole


def _build_demo_console() -> ShepherdsConsole:
    """Build a demo console with sample data."""
    c = ShepherdsConsole()

    # Pastures
    c.add_pasture("translation-farm", mode="plow", capacity=12)
    c.add_pasture("code-review-meadow", mode="plow", capacity=8)
    c.add_pasture("idle-grove", mode="fallow", capacity=5)

    # Fences
    c.add_fence("token-budget", limit=500_000, action="throttle")
    c.add_fence("rate-limit", limit=1000, action="block")
    c.add_fence("context-window", limit=128_000, action="alert")

    # Animals
    c.add_animal("translator-7", pasture="translation-farm", role="flux")
    c.add_animal("translator-12", pasture="translation-farm", role="flux")
    c.add_animal("reviewer-3", pasture="code-review-meadow", role="sentinel")
    c.add_animal("reviewer-5", pasture="code-review-meadow", role="sentinel")
    c.add_animal("scout-1", pasture="idle-grove", role="scout", health="offline")

    # Simulate some activity
    c.fences["token-budget"].consumed = 342_000
    c.fences["rate-limit"].consumed = 847
    c.fences["context-window"].consumed = 91_000

    for _ in range(142):
        c.complete_task("translator-7", cost=200)
    for _ in range(87):
        c.complete_task("translator-12", cost=150)
    for _ in range(53):
        c.complete_task("reviewer-3")
    for _ in range(31):
        c.complete_task("reviewer-5")

    c.pastures["translation-farm"].tasks_in_progress = 3
    c.pastures["code-review-meadow"].tasks_in_progress = 1
    c.pastures["translation-farm"].throughput = 7.2
    c.pastures["code-review-meadow"].throughput = 2.8

    return c


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="shepherds-console",
        description="🐑 The Shepherd's Console — single-pane operations for working animal infrastructure.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--web",
        action="store_true",
        help="Serve web dashboard instead of terminal output",
    )
    mode.add_argument(
        "--json",
        action="store_true",
        help="Output JSON status",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for web server (default: 8080)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for web server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use demo data (no live connections)",
    )

    args = parser.parse_args(argv)

    console = _build_demo_console() if args.demo else ShepherdsConsole()

    if args.json:
        import json
        print(json.dumps(console.status(), indent=2))
        return 0

    if args.web:
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    console.render_html().encode()
                )

            def log_message(self, *a):
                pass  # suppress access logs

        server = http.server.HTTPServer((args.host, args.port), Handler)
        print(
            f"🐑 Shepherd's Console serving at "
            f"http://{args.host}:{args.port}"
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")
            server.shutdown()
        return 0

    # Terminal mode
    print(console.render_terminal())
    return 0


if __name__ == "__main__":
    sys.exit(main())
