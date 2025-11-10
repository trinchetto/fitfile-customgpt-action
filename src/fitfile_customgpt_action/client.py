from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Sequence, cast

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_OUTPUT = Path("generated.fit")


def parse_fit(base_url: str, fit_path: Path) -> dict[str, Any]:
    """Upload a FIT file to the parse endpoint and return the parsed JSON."""
    url = _normalize(f"{base_url}/fit/parse")
    with fit_path.open("rb") as handle:
        response = httpx.post(
            url,
            files={"file": (fit_path.name, handle, "application/octet-stream")},
            timeout=30.0,
        )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


def produce_fit(base_url: str, payload_path: Path, output_path: Path) -> Path:
    """Post a JSON payload to the produce endpoint and write the returned FIT bytes."""
    url = _normalize(f"{base_url}/fit/produce")
    payload = json.loads(payload_path.read_text())
    response = httpx.post(url, json=payload, timeout=30.0)
    response.raise_for_status()
    output_path.write_bytes(response.content)
    return output_path


_DUPLICATE_FIT_SEGMENT = re.compile(r"(?<!:)//fit")


def _normalize(url: str) -> str:
    """Collapse duplicate path separators immediately before /fit."""
    return _DUPLICATE_FIT_SEGMENT.sub("/fit", url)


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point for the simple FIT client."""
    parser = argparse.ArgumentParser(description="Simple client for the FIT CustomGPT Action.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Service base URL.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_cmd = subparsers.add_parser("parse", help="Parse a FIT file via the API.")
    parse_cmd.add_argument("fit_path", type=Path, help="Path to the FIT file to upload.")

    produce_cmd = subparsers.add_parser("produce", help="Generate a FIT file from a JSON payload.")
    produce_cmd.add_argument("payload", type=Path, help="JSON payload describing FIT messages.")
    produce_cmd.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to store the FIT file (default: {DEFAULT_OUTPUT}).",
    )

    args = parser.parse_args(argv)
    base_url = args.base_url.rstrip("/")

    if args.command == "parse":
        result = parse_fit(base_url, args.fit_path)
        print(json.dumps(result, indent=2))
    elif args.command == "produce":
        output_file = produce_fit(base_url, args.payload, args.output)
        print(f"Wrote FIT file to {output_file}")
    else:  # pragma: no cover
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":  # pragma: no cover
    main()
