from __future__ import annotations

import argparse
from collections.abc import Sequence

import uvicorn


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the FIT CustomGPT Action server.")
    parser.add_argument("--host", default="0.0.0.0", help="Interface to bind the ASGI server to.")
    parser.add_argument("--port", default=8000, type=int, help="Port to bind the ASGI server to.")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development only).",
    )
    args = parser.parse_args(argv)

    uvicorn.run(
        "fitfile_customgpt_action.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )


if __name__ == "__main__":
    main()
