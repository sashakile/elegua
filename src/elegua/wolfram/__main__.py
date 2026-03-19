"""CLI entry point: ``python -m elegua.wolfram serve``."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    """Parse arguments and run the oracle server."""
    parser = argparse.ArgumentParser(
        prog="python -m elegua.wolfram",
        description="Wolfram kernel oracle HTTP server for Elegua.",
    )
    sub = parser.add_subparsers(dest="command")

    serve_cmd = sub.add_parser("serve", help="Start the oracle HTTP server.")
    serve_cmd.add_argument("--host", default="0.0.0.0", help="Bind address (default: 0.0.0.0)")
    serve_cmd.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")

    args = parser.parse_args()

    if args.command == "serve":
        from elegua.wolfram.server import serve

        serve(host=args.host, port=args.port)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
