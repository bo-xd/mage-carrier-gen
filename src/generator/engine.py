"""Template engine and Magento 2.4.9 module generator."""

from __future__ import annotations

from pathlib import Path
from string import Template
from typing import TYPE_CHECKING

from src.generator.naming import (
    json_escape,
    php_array_literal,
    php_escape,
    to_kebab_case,
    to_pascal_case,
    to_snake_case,
    xml_escape,
)

if TYPE_CHECKING:
    from src.parser.models import CourierSpec, EndpointConfig

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _render_template(template_rel_path: str, context: dict[str, str]) -> str:
    """Load a string.Template file from src/templates and substitute variables."""
    template_path = TEMPLATES_DIR / template_rel_path
    template = Template(template_path.read_text(encoding="utf-8"))
    return template.substitute(context)


def _endpoint_values(endpoint: EndpointConfig | None) -> tuple[str, str, str, str]:
    """Extract (method, path, request_mapping_php, response_mapping_php) from an endpoint."""
    if endpoint is None:
        return ("POST", "", "[]", "[]")
    return (
        php_escape(endpoint.method.upper()),
        php_escape(endpoint.path),
        php_array_literal(endpoint.request_mapping),
        php_array_literal(endpoint.response_mapping),
    )


def _build_context(spec: CourierSpec, vendor: str, carrier: str) -> dict[str, str]:
    """Build the template substitution dictionary from a CourierSpec."""
    vendor_pascal = to_pascal_case(vendor)
    carrier_pascal = to_pascal_case(carrier)
    carrier_code = to_snake_case(carrier)

    rate_method, rate_path, rate_req_php, rate_resp_php = _endpoint_values(spec.rate_endpoint)
    ship_method, ship_path, ship_req_php, ship_resp_php = _endpoint_values(spec.shipment_endpoint)
    track_method, track_path, _, track_resp_php = _endpoint_values(spec.tracking_endpoint)

    title = spec.title or f"{vendor_pascal} {carrier_pascal}"
    version = spec.version or "1.0.0"
    base_url = spec.base_url or ""
    sandbox_url = spec.sandbox_url or base_url

    return {
        "vendor": vendor_pascal,
        "carrier": carrier_pascal,
        "carrier_code": carrier_code,
        "composer_vendor": to_kebab_case(vendor),
        "composer_carrier": to_kebab_case(carrier),
        "json_description": json_escape(f"{title} ({version}) shipping carrier module for Magento 2.4.9"),
        "json_version": json_escape(version),
        "xml_title": xml_escape(title),
        "xml_base_url": xml_escape(base_url),
        "xml_sandbox_url": xml_escape(sandbox_url),
        "php_title": php_escape(title),
        "auth_scheme": php_escape(spec.auth.scheme_type),
        "auth_header": php_escape(spec.auth.header_name or ""),
        "auth_query_param": php_escape(spec.auth.query_param or ""),
        "auth_prefix": php_escape(spec.auth.prefix or ""),
        "rate_method": rate_method,
        "rate_path": rate_path,
        "rate_request_mapping_php": rate_req_php,
        "rate_response_mapping_php": rate_resp_php,
        "shipment_method": ship_method,
        "shipment_path": ship_path,
        "shipment_request_mapping_php": ship_req_php,
        "shipment_response_mapping_php": ship_resp_php,
        "tracking_method": track_method,
        "tracking_path": track_path,
        "tracking_response_mapping_php": track_resp_php,
    }


def generate_module(
    spec: CourierSpec,
    vendor: str,
    carrier: str,
    out_dir: str | Path,
) -> list[Path]:
    """Generate a Magento 2.4.9 shipping carrier module under out_dir/app/code/<Vendor>/<CarrierName>/."""
    context = _build_context(spec, vendor, carrier)
    module_root = Path(out_dir) / "app" / "code" / context["vendor"] / context["carrier"]

    file_map = {
        "composer.json.tpl": module_root / "composer.json",
        "registration.php.tpl": module_root / "registration.php",
        "etc/module.xml.tpl": module_root / "etc" / "module.xml",
        "etc/config.xml.tpl": module_root / "etc" / "config.xml",
        "etc/adminhtml/system.xml.tpl": module_root / "etc" / "adminhtml" / "system.xml",
        "etc/di.xml.tpl": module_root / "etc" / "di.xml",
        "Logger/Logger.php.tpl": module_root / "Logger" / "Logger.php",
        "Model/Carrier/Carrier.php.tpl": module_root / "Model" / "Carrier" / f"{context['carrier']}.php",
    }

    generated_files: list[Path] = []
    for template_rel, target_path in file_map.items():
        rendered = _render_template(template_rel, context)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(rendered, encoding="utf-8")
        generated_files.append(target_path)

    return generated_files
