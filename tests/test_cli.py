"""Unit tests for the mage-carrier-gen CLI."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.cli.main import build_parser, main

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_SPEC = REPO_ROOT / "examples" / "dutch-courier-openapi.yaml"
EXAMPLE_MAP = REPO_ROOT / "examples" / "dutch-courier-map.yaml"


class TestCliParser(unittest.TestCase):
    def test_generate_required_and_optional_args(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "generate",
                "--spec",
                str(EXAMPLE_SPEC),
                "--vendor",
                "Acme",
                "--carrier",
                "DutchParcel",
                "--out",
                "/tmp/out",
                "--map",
                str(EXAMPLE_MAP),
                "--interactive",
            ]
        )
        self.assertEqual(args.command, "generate")
        self.assertEqual(args.spec, str(EXAMPLE_SPEC))
        self.assertEqual(args.vendor, "Acme")
        self.assertEqual(args.carrier, "DutchParcel")
        self.assertEqual(args.out, "/tmp/out")
        self.assertEqual(args.map_path, str(EXAMPLE_MAP))
        self.assertTrue(args.interactive)

    def test_missing_spec_file_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_parser_mod = types.ModuleType("src.parser")
            fake_parser_mod.parse_spec = MagicMock()
            fake_gen_mod = types.ModuleType("src.generator")
            fake_gen_mod.generate_module = MagicMock()

            with patch.dict(
                sys.modules,
                {"src.parser": fake_parser_mod, "src.generator": fake_gen_mod},
            ):
                rc = main(
                    [
                        "generate",
                        "--spec",
                        str(Path(tmpdir) / "does-not-exist.yaml"),
                        "--vendor",
                        "Acme",
                        "--carrier",
                        "DutchParcel",
                        "--out",
                        tmpdir,
                    ]
                )
            self.assertEqual(rc, 1)

    def test_generate_invokes_parser_and_generator(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dummy_spec = object()
            fake_out_file = Path(tmpdir) / "app/code/Acme/DutchParcel/registration.php"

            fake_parser_mod = types.ModuleType("src.parser")
            fake_parser_mod.parse_spec = MagicMock(return_value=dummy_spec)
            fake_gen_mod = types.ModuleType("src.generator")
            fake_gen_mod.generate_module = MagicMock(return_value=[fake_out_file])

            with patch.dict(
                sys.modules,
                {"src.parser": fake_parser_mod, "src.generator": fake_gen_mod},
            ):
                rc = main(
                    [
                        "generate",
                        "--spec",
                        str(EXAMPLE_SPEC),
                        "--vendor",
                        "Acme",
                        "--carrier",
                        "DutchParcel",
                        "--out",
                        tmpdir,
                        "--map",
                        str(EXAMPLE_MAP),
                        "--interactive",
                    ]
                )

            self.assertEqual(rc, 0)
            fake_parser_mod.parse_spec.assert_called_once_with(
                spec_path=str(EXAMPLE_SPEC),
                map_path=str(EXAMPLE_MAP),
                interactive=True,
            )
            fake_gen_mod.generate_module.assert_called_once_with(
                spec=dummy_spec,
                vendor="Acme",
                carrier="DutchParcel",
                out_dir=tmpdir,
            )

    @unittest.skipUnless(
        importlib.util.find_spec("src.parser") is not None
        and importlib.util.find_spec("src.generator") is not None,
        "src.parser and src.generator not yet merged",
    )
    def test_cli_end_to_end_with_real_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            rc = main(
                [
                    "generate",
                    "--spec",
                    str(EXAMPLE_SPEC),
                    "--vendor",
                    "Acme",
                    "--carrier",
                    "DutchParcel",
                    "--out",
                    tmpdir,
                    "--map",
                    str(EXAMPLE_MAP),
                ]
            )
            self.assertEqual(rc, 0)
            module_root = Path(tmpdir) / "app" / "code" / "Acme" / "DutchParcel"
            self.assertTrue((module_root / "registration.php").is_file())
            self.assertTrue((module_root / "etc" / "module.xml").is_file())


if __name__ == "__main__":
    unittest.main()
