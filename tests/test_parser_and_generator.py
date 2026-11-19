"""Tests for OpenAPI parsing, --map overrides, and Magento 2.4.9 module generation."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HAS_PARSER = importlib.util.find_spec("src.parser") is not None
HAS_GENERATOR = importlib.util.find_spec("src.generator") is not None

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_SPEC = REPO_ROOT / "examples" / "dutch-courier-openapi.yaml"
EXAMPLE_MAP = REPO_ROOT / "examples" / "dutch-courier-map.yaml"


@unittest.skipUnless(HAS_PARSER, "src.parser not yet merged")
class TestOpenApiParser(unittest.TestCase):
    def test_parse_dutch_courier_spec(self) -> None:
        from src.parser import parse_spec

        spec = parse_spec(str(EXAMPLE_SPEC))

        self.assertEqual(spec.title, "Dutch Parcel Express API")
        self.assertEqual(spec.version, "2.1.0")
        self.assertIn("api.dutchparcel.nl", spec.base_url)
        self.assertIsNotNone(spec.sandbox_url)
        self.assertIn("sandbox", spec.sandbox_url.lower())

        self.assertEqual(spec.auth.scheme_type, "bearer")

        self.assertIsNotNone(spec.rate_endpoint)
        self.assertEqual(spec.rate_endpoint.method.upper(), "POST")
        self.assertIn("rate", spec.rate_endpoint.path.lower())

        self.assertIsNotNone(spec.shipment_endpoint)
        self.assertEqual(spec.shipment_endpoint.method.upper(), "POST")
        self.assertIn("shipment", spec.shipment_endpoint.path.lower())

        self.assertIsNotNone(spec.tracking_endpoint)
        self.assertEqual(spec.tracking_endpoint.method.upper(), "GET")
        self.assertIn("tracking", spec.tracking_endpoint.path.lower())

        # Verify some fields were extracted from schemas
        self.assertTrue(len(spec.rate_endpoint.request_mapping) > 0)
        self.assertTrue(len(spec.rate_endpoint.response_mapping) > 0)

    def test_map_override_yaml_and_json(self) -> None:
        from src.parser import parse_spec

        # YAML override from examples/dutch-courier-map.yaml
        spec_yaml = parse_spec(str(EXAMPLE_SPEC), map_path=str(EXAMPLE_MAP))
        self.assertEqual(
            spec_yaml.rate_endpoint.request_mapping.get("dest_postcode"),
            "receiverPostalCode",
        )
        self.assertEqual(
            spec_yaml.rate_endpoint.response_mapping.get("price"),
            "totalPrice",
        )

        # JSON override in a temp file
        custom_map = {
            "request": {
                "dest_postcode": "customZipCode",
                "package_weight": "customWeightKg",
            },
            "response": {
                "price": "customAmount",
                "tracking_number": "customBarcode",
            },
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            map_file = Path(tmpdir) / "override.json"
            map_file.write_text(json.dumps(custom_map), encoding="utf-8")

            spec_json = parse_spec(str(EXAMPLE_SPEC), map_path=str(map_file))
            self.assertEqual(
                spec_json.rate_endpoint.request_mapping.get("dest_postcode"),
                "customZipCode",
            )
            self.assertEqual(
                spec_json.rate_endpoint.request_mapping.get("package_weight"),
                "customWeightKg",
            )
            self.assertEqual(
                spec_json.rate_endpoint.response_mapping.get("price"),
                "customAmount",
            )
            self.assertEqual(
                spec_json.shipment_endpoint.response_mapping.get("tracking_number"),
                "customBarcode",
            )


@unittest.skipUnless(
    HAS_PARSER and HAS_GENERATOR,
    "src.parser and src.generator not yet merged",
)
class TestModuleGeneration(unittest.TestCase):
    def test_full_module_generation(self) -> None:
        from src.generator import generate_module
        from src.parser import parse_spec

        spec = parse_spec(str(EXAMPLE_SPEC), map_path=str(EXAMPLE_MAP))

        with tempfile.TemporaryDirectory() as tmpdir:
            generated = generate_module(
                spec=spec,
                vendor="Acme",
                carrier="DutchParcel",
                out_dir=tmpdir,
            )
            self.assertGreater(len(generated), 0)

            module_root = Path(tmpdir) / "app" / "code" / "Acme" / "DutchParcel"
            expected_files = [
                module_root / "composer.json",
                module_root / "registration.php",
                module_root / "etc" / "module.xml",
                module_root / "etc" / "config.xml",
                module_root / "etc" / "di.xml",
                module_root / "etc" / "adminhtml" / "system.xml",
                module_root / "Logger" / "Logger.php",
                module_root / "Model" / "Carrier" / "DutchParcel.php",
            ]
            for expected in expected_files:
                self.assertTrue(expected.is_file(), f"Missing generated file: {expected}")

            # Validate composer.json
            composer_data = json.loads((module_root / "composer.json").read_text(encoding="utf-8"))
            self.assertIn("name", composer_data)

            # Validate all XML files
            xml_files = list(module_root.rglob("*.xml"))
            self.assertGreaterEqual(len(xml_files), 4)
            for xml_file in xml_files:
                ET.parse(xml_file)

            # Check no deprecated Laminas/Zend references and validate PHP syntax if php is installed
            php_bin = shutil.which("php")
            for file_path in module_root.rglob("*"):
                if not file_path.is_file():
                    continue
                content = file_path.read_text(encoding="utf-8")
                lowered = content.lower()
                self.assertNotIn(
                    "laminas",
                    lowered,
                    f"Deprecated Laminas reference found in {file_path}",
                )
                self.assertNotIn(
                    "zend",
                    lowered,
                    f"Deprecated Zend reference found in {file_path}",
                )

                if php_bin and file_path.suffix == ".php":
                    proc = subprocess.run(
                        [php_bin, "-l", str(file_path)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(
                        proc.returncode,
                        0,
                        f"PHP syntax error in {file_path}: {proc.stdout}\n{proc.stderr}",
                    )


if __name__ == "__main__":
    unittest.main()
