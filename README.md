# mage-carrier-gen

Generate production-ready **Magento 2.4.9 (PHP 8.4/8.5)** shipping carrier modules directly from OpenAPI 3.x or Swagger 2.0 specifications.

## Features

- Parses OpenAPI 3.x and Swagger 2.0 specs (YAML or JSON)
- Extracts authentication schemes (Bearer, API Key header/query, Basic), production & sandbox server URLs, rate/quote, shipment/label, and tracking endpoints
- Supports `--map` JSON/YAML field mapping overrides and `--interactive` stdin mapping fallback
- Generates a complete Magento 2.4.9 module (`declare(strict_types=1);`, PSR-12, zero deprecated Laminas/Zend classes)

## Installation

```bash
pip install -e .
```

## Usage

```bash
mage-carrier-gen generate \
  --spec examples/dutch-courier-openapi.yaml \
  --vendor Acme \
  --carrier DutchParcel \
  --out ./build \
  --map examples/dutch-courier-map.yaml
```

### Options

| Flag | Required | Description |
| --- | --- | --- |
| `--spec` | Yes | Path to OpenAPI 3.x / Swagger 2.0 YAML or JSON file |
| `--vendor` | Yes | Magento module Vendor namespace (e.g. `Acme`) |
| `--carrier` | Yes | Magento carrier name (e.g. `DutchParcel`) |
| `--out` | Yes | Output directory for `app/code/<Vendor>/<Carrier>/` |
| `--map` | No | Path to JSON/YAML field mapping override file |
| `--interactive` | No | Prompt interactively on stdin for unmapped fields |

## Generated Module Structure

```text
app/code/<Vendor>/<Carrier>/
├── composer.json
├── registration.php
├── etc/
│   ├── module.xml
│   ├── config.xml
│   ├── di.xml
│   └── adminhtml/
│       └── system.xml
├── Logger/
│   └── Logger.php
└── Model/
    └── Carrier/
        └── <Carrier>.php
```

## Running Tests

```bash
python3 -m unittest discover -s tests
```
