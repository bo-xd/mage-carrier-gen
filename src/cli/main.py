"""Command-line interface for mage-carrier-gen."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from src import __version__


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="mage-carrier-gen",
        description="Generate a Magento 2.4.9 shipping carrier module from an OpenAPI/Swagger spec.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate a Magento 2 carrier module from an OpenAPI/Swagger specification.",
    )
    gen_parser.add_argument(
        "--spec",
        required=True,
        help="Path to OpenAPI 3.x or Swagger 2.0 specification (YAML or JSON).",
    )
    gen_parser.add_argument(
        "--vendor",
        required=True,
        help="Magento module vendor namespace (e.g. Acme).",
    )
    gen_parser.add_argument(
        "--carrier",
        required=True,
        help="Magento carrier name (e.g. DutchParcel).",
    )
    gen_parser.add_argument(
        "--out",
        required=True,
        help="Output directory where app/code/<Vendor>/<Carrier>/ will be created.",
    )
    gen_parser.add_argument(
        "--map",
        dest="map_path",
        default=None,
        help="Optional path to JSON/YAML field mapping override file.",
    )
    gen_parser.add_argument(
        "--interactive",
        action="store_true",
        default=False,
        help="Prompt interactively on stdin for unmapped courier fields.",
    )

    return parser


def _run_generate(args: argparse.Namespace) -> int:
    """Execute the `generate` subcommand."""
    from src.generator import generate_module
    from src.parser import parse_spec

    spec_path = Path(args.spec)
    if not spec_path.is_file():
        print(f"Error: spec file not found: {spec_path}", file=sys.stderr)
        return 1

    if args.map_path is not None and not Path(args.map_path).is_file():
        print(f"Error: mapping file not found: {args.map_path}", file=sys.stderr)
        return 1

    try:
        spec = parse_spec(
            spec_path=str(spec_path),
            map_path=args.map_path,
            interactive=args.interactive,
        )
        generated_files = generate_module(
            spec=spec,
            vendor=args.vendor,
            carrier=args.carrier,
            out_dir=args.out,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Generated Magento 2 module {args.vendor}_{args.carrier} ({len(generated_files)} files):")
    for path in generated_files:
        print(f"  - {path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the mage-carrier-gen CLI."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "generate":
        return _run_generate(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
