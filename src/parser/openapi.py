"""OpenAPI 3.x and Swagger 2.0 parser and Magento field mapper."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - fallback when PyYAML is not installed
    yaml = None  # type: ignore[assignment]

from src.parser.models import AuthConfig, CourierSpec, EndpointConfig

HTTP_METHODS = ("get", "post", "put", "patch", "delete")

SANDBOX_KEYWORDS = ("sandbox", "staging", "test", "dev", "uat", "preprod", "mock")
PROD_KEYWORDS = ("prod", "production", "live")

RATE_KEYWORDS = (
    "rate",
    "rates",
    "quote",
    "quotes",
    "pricing",
    "price",
    "tariff",
    "tariffs",
    "calculate",
    "shipping-options",
    "delivery-options",
)
SHIPMENT_KEYWORDS = (
    "shipment",
    "shipments",
    "label",
    "labels",
    "ship",
    "book",
    "dispatch",
    "manifest",
    "waybill",
)
TRACKING_KEYWORDS = (
    "track",
    "tracking",
    "trace",
    "events",
    "checkpoints",
    "parcel",
)

MAGENTO_REQUEST_FIELDS = (
    "dest_postcode",
    "dest_country_id",
    "package_weight",
    "order_increment_id",
    "origin_postcode",
    "origin_country_id",
)

MAGENTO_RESPONSE_FIELDS = (
    "rates_list",
    "carrier_title",
    "method_code",
    "method_title",
    "price",
    "currency",
    "tracking_number",
    "shipping_label",
    "status",
    "events",
)

REQUEST_SYNONYMS: dict[str, tuple[str, ...]] = {
    "dest_postcode": (
        "dest_postcode",
        "destination_postcode",
        "destination_postal_code",
        "receiver_postcode",
        "receiver_postal_code",
        "recipient_postcode",
        "recipient_postal_code",
        "postal_code",
        "postcode",
        "zip_code",
        "zip",
    ),
    "dest_country_id": (
        "dest_country_id",
        "destination_country_id",
        "destination_country_code",
        "destination_country",
        "receiver_country_code",
        "receiver_country",
        "recipient_country_code",
        "recipient_country",
        "country_code",
        "country_id",
        "country",
    ),
    "origin_postcode": (
        "origin_postcode",
        "origin_postal_code",
        "sender_postcode",
        "sender_postal_code",
        "shipper_postcode",
        "shipper_postal_code",
        "from_postcode",
        "from_postal_code",
        "from_zip",
    ),
    "origin_country_id": (
        "origin_country_id",
        "origin_country_code",
        "origin_country",
        "sender_country_code",
        "sender_country",
        "shipper_country_code",
        "shipper_country",
        "from_country",
    ),
    "package_weight": (
        "package_weight",
        "total_weight",
        "parcel_weight",
        "gross_weight",
        "weight_kg",
        "weight_grams",
        "weight_value",
        "weight",
    ),
    "order_increment_id": (
        "order_increment_id",
        "order_number",
        "order_id",
        "order_ref",
        "customer_reference",
        "shipment_reference",
        "reference",
        "external_id",
    ),
    "tracking_number": (
        "tracking_number",
        "tracking_id",
        "tracking_code",
        "barcode",
        "waybill",
        "awb",
    ),
}

RESPONSE_SYNONYMS: dict[str, tuple[str, ...]] = {
    "rates_list": (
        "rates_list",
        "rates",
        "quotes",
        "shipping_options",
        "delivery_options",
        "options",
        "services",
        "tariffs",
        "products",
        "results",
    ),
    "carrier_title": (
        "carrier_title",
        "carrier_name",
        "carrier",
        "provider_name",
        "provider",
    ),
    "method_code": (
        "method_code",
        "service_code",
        "product_code",
        "rate_code",
        "rate_id",
        "service_id",
        "code",
    ),
    "method_title": (
        "method_title",
        "service_name",
        "service_title",
        "product_name",
        "rate_name",
        "title",
        "name",
        "description",
    ),
    "price": (
        "price",
        "total_price",
        "total_amount",
        "amount",
        "cost",
        "rate",
        "fee",
        "net_price",
        "gross_price",
        "value",
    ),
    "currency": (
        "currency_code",
        "currency",
        "curr",
    ),
    "tracking_number": (
        "tracking_number",
        "tracking_id",
        "tracking_code",
        "barcode",
        "waybill",
        "awb",
        "parcel_number",
    ),
    "shipping_label": (
        "shipping_label",
        "label_data",
        "label_pdf",
        "label_base64",
        "label_content",
        "label",
        "document",
        "pdf",
    ),
    "status": (
        "tracking_status",
        "shipment_status",
        "current_status",
        "status",
        "state",
    ),
    "events": (
        "tracking_events",
        "events",
        "checkpoints",
        "history",
        "scans",
        "milestones",
        "updates",
    ),
}

DEST_CONTEXT = ("dest", "destination", "receiver", "recipient", "to", "consignee")
ORIGIN_CONTEXT = ("origin", "sender", "shipper", "from", "pickup")


def _normalize_token(name: str) -> str:
    """Convert camelCase/kebab-case/spaces to lowercase snake_case."""
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return re.sub(r"[^a-zA-Z0-9]+", "_", s1).strip("_").lower()


def _load_structured_file(path: str | Path) -> dict[str, Any]:
    """Load a JSON or YAML file into a dictionary."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    raw_text = file_path.read_text(encoding="utf-8")
    suffix = file_path.suffix.lower()

    data: Any
    if suffix == ".json" or raw_text.lstrip().startswith("{"):
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError:
            if yaml is None:
                raise
            data = yaml.safe_load(raw_text)
    else:
        if yaml is None:
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError as exc:
                raise ImportError(
                    "PyYAML is required to parse YAML files. Install it with `pip install pyyaml`."
                ) from exc
        else:
            data = yaml.safe_load(raw_text)

    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at root of {file_path}, got {type(data).__name__}")
    return data


def _resolve_ref(doc: dict[str, Any], obj: Any, seen: set[str] | None = None) -> Any:
    """Resolve local JSON Pointer $ref references with cycle protection."""
    if not isinstance(obj, dict) or "$ref" not in obj:
        return obj

    ref = obj["$ref"]
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return obj

    visited = set() if seen is None else set(seen)
    if ref in visited:
        return {}
    visited.add(ref)

    current: Any = doc
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return obj

    resolved = _resolve_ref(doc, current, visited)
    if isinstance(resolved, dict) and len(obj) > 1:
        merged = dict(resolved)
        for key, value in obj.items():
            if key != "$ref":
                merged[key] = value
        return merged
    return resolved


def _substitute_server_vars(url: str, variables: Any) -> str:
    """Replace OpenAPI 3 server template variables with their defaults."""
    if not isinstance(variables, dict):
        return url
    result = url
    for var_name, var_spec in variables.items():
        if isinstance(var_spec, dict) and "default" in var_spec:
            result = result.replace(f"{{{var_name}}}", str(var_spec["default"]))
    return result


def _extract_urls(doc: dict[str, Any]) -> tuple[str, str | None]:
    """Extract production base_url and optional sandbox_url from OpenAPI 3 or Swagger 2."""
    if "servers" in doc and isinstance(doc["servers"], list):
        prod_url: str | None = None
        sandbox_url: str | None = None
        fallback_urls: list[str] = []

        for entry in doc["servers"]:
            if not isinstance(entry, dict) or not entry.get("url"):
                continue
            url = _substitute_server_vars(str(entry["url"]), entry.get("variables")).rstrip("/")
            desc = str(entry.get("description", "")).lower()
            combined = f"{url.lower()} {desc}"

            if any(kw in combined for kw in SANDBOX_KEYWORDS):
                if sandbox_url is None:
                    sandbox_url = url
            elif any(kw in combined for kw in PROD_KEYWORDS):
                if prod_url is None:
                    prod_url = url
            else:
                fallback_urls.append(url)

        if prod_url is None:
            if fallback_urls:
                prod_url = fallback_urls[0]
            elif sandbox_url is not None:
                prod_url = sandbox_url
            else:
                prod_url = ""

        return prod_url, sandbox_url

    # Swagger 2.0
    schemes = doc.get("schemes") or ["https"]
    scheme = "https" if "https" in schemes else str(schemes[0])
    host = str(doc.get("host", "")).strip()
    base_path = str(doc.get("basePath", "")).strip()
    if host:
        base_url = f"{scheme}://{host}{base_path}".rstrip("/")
    else:
        base_url = base_path.rstrip("/")

    sandbox_url = base_url if any(kw in base_url.lower() for kw in SANDBOX_KEYWORDS) else None
    return base_url, sandbox_url


def _scheme_to_auth_config(scheme: dict[str, Any]) -> AuthConfig:
    """Convert a single OpenAPI/Swagger security scheme object to AuthConfig."""
    scheme_type = str(scheme.get("type", "")).lower()

    if scheme_type == "http":
        http_scheme = str(scheme.get("scheme", "")).lower()
        if http_scheme == "bearer":
            return AuthConfig(scheme_type="bearer", header_name="Authorization", prefix="Bearer")
        if http_scheme == "basic":
            return AuthConfig(scheme_type="basic", header_name="Authorization", prefix="Basic")

    if scheme_type == "basic":
        return AuthConfig(scheme_type="basic", header_name="Authorization", prefix="Basic")

    if scheme_type == "apikey":
        location = str(scheme.get("in", "header")).lower()
        param_name = str(scheme.get("name", "X-API-Key"))
        if location == "query":
            return AuthConfig(scheme_type="api_key_query", query_param=param_name)
        return AuthConfig(scheme_type="api_key_header", header_name=param_name)

    if scheme_type == "oauth2":
        return AuthConfig(scheme_type="bearer", header_name="Authorization", prefix="Bearer")

    return AuthConfig(scheme_type="none")


def _extract_auth(doc: dict[str, Any]) -> AuthConfig:
    """Extract primary authentication configuration from the spec."""
    components = doc.get("components")
    if isinstance(components, dict) and isinstance(components.get("securitySchemes"), dict):
        schemes: dict[str, Any] = components["securitySchemes"]
    elif isinstance(doc.get("securityDefinitions"), dict):
        schemes = doc["securityDefinitions"]
    else:
        return AuthConfig(scheme_type="none")

    if not schemes:
        return AuthConfig(scheme_type="none")

    # Prefer the first scheme referenced by top-level `security`
    top_security = doc.get("security")
    if isinstance(top_security, list):
        for req in top_security:
            if isinstance(req, dict):
                for name in req:
                    if name in schemes:
                        resolved = _resolve_ref(doc, schemes[name])
                        if isinstance(resolved, dict):
                            cfg = _scheme_to_auth_config(resolved)
                            if cfg.scheme_type != "none":
                                return cfg

    # Otherwise pick by priority
    priority = {"bearer": 0, "api_key_header": 1, "api_key_query": 2, "basic": 3, "none": 4}
    candidates: list[AuthConfig] = []
    for raw_scheme in schemes.values():
        resolved = _resolve_ref(doc, raw_scheme)
        if isinstance(resolved, dict):
            candidates.append(_scheme_to_auth_config(resolved))

    if not candidates:
        return AuthConfig(scheme_type="none")
    candidates.sort(key=lambda c: priority.get(c.scheme_type, 99))
    return candidates[0]


def _score_operation(
    method: str,
    path: str,
    op: dict[str, Any],
    keywords: tuple[str, ...],
    preferred_method: str,
) -> int:
    """Score how likely an operation matches a courier endpoint category."""
    path_lower = path.lower()
    op_id = str(op.get("operationId", "")).lower()
    summary = str(op.get("summary", "")).lower()
    description = str(op.get("description", "")).lower()
    tags = " ".join(str(t).lower() for t in op.get("tags", []) if isinstance(t, str))

    score = 0
    for kw in keywords:
        if kw in path_lower:
            score += 10
        if kw in op_id:
            score += 8
        if kw in tags:
            score += 5
        if kw in summary:
            score += 4
        if kw in description:
            score += 2

    if score > 0 and method.upper() == preferred_method:
        score += 3
    return score


def _classify_endpoints(doc: dict[str, Any]) -> dict[str, tuple[str, str, dict[str, Any]]]:
    """Identify rate, shipment, and tracking operations from spec paths."""
    paths = doc.get("paths")
    if not isinstance(paths, dict):
        return {}

    operations: list[tuple[str, str, dict[str, Any]]] = []
    for path, path_item in paths.items():
        resolved_item = _resolve_ref(doc, path_item)
        if not isinstance(resolved_item, dict):
            continue
        for method in HTTP_METHODS:
            op = resolved_item.get(method)
            if isinstance(op, dict):
                # Merge path-level parameters into operation copy
                merged_op = dict(op)
                path_params = resolved_item.get("parameters", [])
                op_params = op.get("parameters", [])
                if isinstance(path_params, list) and isinstance(op_params, list):
                    merged_op["parameters"] = [*path_params, *op_params]
                operations.append((method.upper(), str(path), merged_op))

    categories = {
        "tracking": (TRACKING_KEYWORDS, "GET"),
        "rate": (RATE_KEYWORDS, "POST"),
        "shipment": (SHIPMENT_KEYWORDS, "POST"),
    }

    selected: dict[str, tuple[str, str, dict[str, Any]]] = {}
    used_ops: set[tuple[str, str]] = set()

    # Classify tracking first so `/shipments/{id}/tracking` doesn't get claimed as shipment
    for category in ("tracking", "rate", "shipment"):
        keywords, preferred_method = categories[category]
        best_score = 0
        best_op: tuple[str, str, dict[str, Any]] | None = None
        for method, path, op in operations:
            if (method, path) in used_ops:
                continue
            score = _score_operation(method, path, op, keywords, preferred_method)
            if score > best_score:
                best_score = score
                best_op = (method, path, op)
        if best_op is not None:
            selected[category] = best_op
            used_ops.add((best_op[0], best_op[1]))

    return selected


def _collect_schema_fields(
    doc: dict[str, Any],
    schema: Any,
    prefix: str = "",
    max_depth: int = 5,
    seen_refs: set[str] | None = None,
) -> list[tuple[str, str]]:
    """Recursively collect (dot_path, schema_type) pairs from a JSON/OpenAPI schema."""
    if max_depth < 0 or not isinstance(schema, dict):
        return []

    visited = set() if seen_refs is None else set(seen_refs)
    if "$ref" in schema and isinstance(schema["$ref"], str):
        ref = schema["$ref"]
        if ref in visited:
            return []
        schema = _resolve_ref(doc, schema, visited)
        visited.add(ref)
        if not isinstance(schema, dict):
            return []

    fields: list[tuple[str, str]] = []

    for composite_key in ("allOf", "oneOf", "anyOf"):
        sub_schemas = schema.get(composite_key)
        if isinstance(sub_schemas, list):
            for sub in sub_schemas:
                fields.extend(_collect_schema_fields(doc, sub, prefix, max_depth, visited))

    schema_type = str(schema.get("type", "")).lower()
    if schema_type == "array" or "items" in schema:
        if prefix and (prefix, "array") not in fields:
            fields.append((prefix, "array"))
        items = schema.get("items")
        if isinstance(items, dict):
            fields.extend(_collect_schema_fields(doc, items, prefix, max_depth - 1, visited))
        return fields

    props = schema.get("properties")
    if isinstance(props, dict):
        for prop_name, prop_schema in props.items():
            resolved_prop = _resolve_ref(doc, prop_schema, visited)
            dot_path = f"{prefix}.{prop_name}" if prefix else str(prop_name)
            prop_type = (
                str(resolved_prop.get("type", "object")).lower()
                if isinstance(resolved_prop, dict)
                else "string"
            )
            fields.append((dot_path, prop_type))
            if isinstance(resolved_prop, dict) and max_depth > 0:
                if (
                    prop_type in ("object", "array", "")
                    or "properties" in resolved_prop
                    or "items" in resolved_prop
                    or any(k in resolved_prop for k in ("allOf", "oneOf", "anyOf"))
                ):
                    fields.extend(
                        _collect_schema_fields(doc, resolved_prop, dot_path, max_depth - 1, visited)
                    )

    return fields


def _extract_operation_fields(
    doc: dict[str, Any], op: dict[str, Any]
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Extract request and response (dot_path, type) fields for an operation."""
    req_fields: list[tuple[str, str]] = []

    # Parameters (query, path, header, or Swagger 2.0 body)
    params = op.get("parameters")
    if isinstance(params, list):
        for raw_param in params:
            param = _resolve_ref(doc, raw_param)
            if not isinstance(param, dict):
                continue
            param_in = str(param.get("in", "")).lower()
            if param_in == "body" and isinstance(param.get("schema"), dict):
                req_fields.extend(_collect_schema_fields(doc, param["schema"]))
            elif param_in in ("query", "path") and param.get("name"):
                p_type = str(
                    param.get("type")
                    or (param.get("schema", {}) if isinstance(param.get("schema"), dict) else {}).get(
                        "type", "string"
                    )
                ).lower()
                req_fields.append((str(param["name"]), p_type))

    # OpenAPI 3.x requestBody
    req_body = _resolve_ref(doc, op.get("requestBody"))
    if isinstance(req_body, dict) and isinstance(req_body.get("content"), dict):
        content = req_body["content"]
        media = content.get("application/json") or next(iter(content.values()), None)
        if isinstance(media, dict) and isinstance(media.get("schema"), dict):
            req_fields.extend(_collect_schema_fields(doc, media["schema"]))

    # Responses (prefer 200, 201, or first 2xx)
    resp_fields: list[tuple[str, str]] = []
    responses = op.get("responses")
    if isinstance(responses, dict):
        chosen_resp = None
        for code in ("200", "201", "202"):
            if code in responses:
                chosen_resp = responses[code]
                break
        if chosen_resp is None:
            for code, resp_obj in responses.items():
                if str(code).startswith("2"):
                    chosen_resp = resp_obj
                    break

        resolved_resp = _resolve_ref(doc, chosen_resp)
        if isinstance(resolved_resp, dict):
            if isinstance(resolved_resp.get("schema"), dict):
                resp_fields.extend(_collect_schema_fields(doc, resolved_resp["schema"]))
            elif isinstance(resolved_resp.get("content"), dict):
                content = resolved_resp["content"]
                media = content.get("application/json") or next(iter(content.values()), None)
                if isinstance(media, dict) and isinstance(media.get("schema"), dict):
                    resp_fields.extend(_collect_schema_fields(doc, media["schema"]))

    return req_fields, resp_fields


def _score_field_match(
    canonical: str,
    dot_path: str,
    field_type: str,
    synonyms: tuple[str, ...],
) -> int:
    """Score how well a schema field matches a canonical Magento field."""
    parts = [_normalize_token(p) for p in dot_path.split(".")]
    leaf = parts[-1]
    context_tokens = set(parts[:-1])
    full_norm = "_".join(parts)

    score = 0
    for idx, syn in enumerate(synonyms):
        syn_weight = len(synonyms) - idx
        if leaf == syn or full_norm == syn:
            score = max(score, 100 + syn_weight)
        elif syn in leaf or syn in full_norm:
            score = max(score, 50 + syn_weight)

    if score == 0:
        return 0

    # Context disambiguation for origin vs destination fields
    if canonical.startswith("dest_"):
        if context_tokens & set(DEST_CONTEXT):
            score += 40
        elif context_tokens & set(ORIGIN_CONTEXT):
            score -= 60
    elif canonical.startswith("origin_"):
        if context_tokens & set(ORIGIN_CONTEXT):
            score += 40
        elif context_tokens & set(DEST_CONTEXT):
            score -= 60

    if canonical in ("rates_list", "events") and field_type == "array":
        score += 30

    return score


def _auto_map_fields(
    canonical_fields: tuple[str, ...],
    schema_fields: list[tuple[str, str]],
    synonyms_map: dict[str, tuple[str, ...]],
) -> dict[str, str]:
    """Automatically map canonical Magento fields to discovered schema dot-paths."""
    mapping: dict[str, str] = {}
    for canonical in canonical_fields:
        synonyms = synonyms_map.get(canonical, (canonical,))
        best_score = 0
        best_path: str | None = None
        for dot_path, field_type in schema_fields:
            score = _score_field_match(canonical, dot_path, field_type, synonyms)
            if score > best_score:
                best_score = score
                best_path = dot_path
        if best_path is not None:
            mapping[canonical] = best_path
    return mapping


def _build_endpoint_config(
    doc: dict[str, Any],
    category: str,
    method: str,
    path: str,
    op: dict[str, Any],
) -> tuple[EndpointConfig, list[str], list[str]]:
    """Build an EndpointConfig and return discovered request/response field names."""
    req_fields, resp_fields = _extract_operation_fields(doc, op)

    if category == "rate":
        req_targets = MAGENTO_REQUEST_FIELDS
        resp_targets = ("rates_list", "carrier_title", "method_code", "method_title", "price", "currency")
    elif category == "shipment":
        req_targets = MAGENTO_REQUEST_FIELDS
        resp_targets = ("tracking_number", "shipping_label", "status")
    else:  # tracking
        req_targets = ("tracking_number",)
        resp_targets = ("tracking_number", "status", "events")

    req_map = _auto_map_fields(req_targets, req_fields, REQUEST_SYNONYMS)
    resp_map = _auto_map_fields(resp_targets, resp_fields, RESPONSE_SYNONYMS)

    endpoint = EndpointConfig(
        method=method,
        path=path,
        request_mapping=req_map,
        response_mapping=resp_map,
    )
    return endpoint, [f[0] for f in req_fields], [f[0] for f in resp_fields]


def _apply_endpoint_override(endpoint: EndpointConfig | None, override: Any) -> None:
    """Apply request/response mapping overrides from a --map structure."""
    if endpoint is None or not isinstance(override, dict):
        return
    req_override = override.get("request_mapping") or override.get("request")
    if isinstance(req_override, dict):
        for k, v in req_override.items():
            endpoint.request_mapping[str(k)] = str(v)

    resp_override = override.get("response_mapping") or override.get("response")
    if isinstance(resp_override, dict):
        for k, v in resp_override.items():
            endpoint.response_mapping[str(k)] = str(v)


def _apply_map_overrides(spec: CourierSpec, map_data: dict[str, Any]) -> None:
    """Apply overrides from a --map JSON/YAML file onto CourierSpec."""
    endpoints = {
        "rate_endpoint": spec.rate_endpoint,
        "shipment_endpoint": spec.shipment_endpoint,
        "tracking_endpoint": spec.tracking_endpoint,
    }

    # Global request_mapping / response_mapping applied to all present endpoints
    global_req = map_data.get("request_mapping")
    global_resp = map_data.get("response_mapping")
    for ep in endpoints.values():
        if ep is None:
            continue
        if isinstance(global_req, dict):
            for k, v in global_req.items():
                ep.request_mapping[str(k)] = str(v)
        if isinstance(global_resp, dict):
            for k, v in global_resp.items():
                ep.response_mapping[str(k)] = str(v)

    # Flat top-level canonical keys (e.g. `dest_postcode: receiver.zip`)
    for key, value in map_data.items():
        if not isinstance(value, str):
            continue
        if key in MAGENTO_REQUEST_FIELDS:
            for ep in (spec.rate_endpoint, spec.shipment_endpoint):
                if ep is not None:
                    ep.request_mapping[key] = value
        elif key in MAGENTO_RESPONSE_FIELDS:
            for ep in endpoints.values():
                if ep is not None:
                    ep.response_mapping[key] = value

    # Per-endpoint overrides (`rate_endpoint` or `rate`, etc.)
    aliases = {
        "rate_endpoint": ("rate_endpoint", "rate"),
        "shipment_endpoint": ("shipment_endpoint", "shipment"),
        "tracking_endpoint": ("tracking_endpoint", "tracking"),
    }
    for attr_name, keys in aliases.items():
        ep = getattr(spec, attr_name)
        for key in keys:
            if key in map_data:
                _apply_endpoint_override(ep, map_data[key])


def _prompt_mapping(
    label: str,
    target_fields: tuple[str, ...],
    mapping: dict[str, str],
    available_fields: list[str],
) -> bool:
    """Interactively prompt for unmapped or customizable fields on stdin."""
    unique_fields = list(dict.fromkeys(available_fields))
    if unique_fields:
        print(f"\n[{label}] Available schema fields: {', '.join(unique_fields[:20])}")
    for field_name in target_fields:
        current = mapping.get(field_name, "")
        prompt_text = f"  Map '{field_name}' [{current or 'unmapped'}]: "
        try:
            answer = input(prompt_text).strip()
        except EOFError:
            return False
        if answer:
            mapping[field_name] = answer
    return True


def _interactive_map(
    spec: CourierSpec,
    discovered_fields: dict[str, tuple[list[str], list[str]]],
) -> None:
    """Run interactive stdin field mapping for detected endpoints."""
    configs = [
        (
            "rate_endpoint",
            spec.rate_endpoint,
            MAGENTO_REQUEST_FIELDS,
            ("rates_list", "carrier_title", "method_code", "method_title", "price", "currency"),
        ),
        (
            "shipment_endpoint",
            spec.shipment_endpoint,
            MAGENTO_REQUEST_FIELDS,
            ("tracking_number", "shipping_label", "status"),
        ),
        (
            "tracking_endpoint",
            spec.tracking_endpoint,
            ("tracking_number",),
            ("tracking_number", "status", "events"),
        ),
    ]
    for name, ep, req_targets, resp_targets in configs:
        if ep is None:
            continue
        req_avail, resp_avail = discovered_fields.get(name, ([], []))
        if not _prompt_mapping(f"{name} request", req_targets, ep.request_mapping, req_avail):
            return
        if not _prompt_mapping(f"{name} response", resp_targets, ep.response_mapping, resp_avail):
            return


def parse_spec(
    spec_path: str,
    map_path: str | None = None,
    interactive: bool = False,
) -> CourierSpec:
    """Parse an OpenAPI 3.x or Swagger 2.0 JSON/YAML spec into a CourierSpec."""
    doc = _load_structured_file(spec_path)

    info = doc.get("info") if isinstance(doc.get("info"), dict) else {}
    title = str(info.get("title", "Courier API"))
    version = str(info.get("version", "1.0.0"))

    base_url, sandbox_url = _extract_urls(doc)
    auth = _extract_auth(doc)
    classified = _classify_endpoints(doc)

    discovered_fields: dict[str, tuple[list[str], list[str]]] = {}
    endpoints: dict[str, EndpointConfig | None] = {
        "rate": None,
        "shipment": None,
        "tracking": None,
    }

    for category in ("rate", "shipment", "tracking"):
        if category in classified:
            method, path, op = classified[category]
            ep_cfg, req_avail, resp_avail = _build_endpoint_config(doc, category, method, path, op)
            endpoints[category] = ep_cfg
            discovered_fields[f"{category}_endpoint"] = (req_avail, resp_avail)

    spec = CourierSpec(
        title=title,
        version=version,
        base_url=base_url,
        sandbox_url=sandbox_url,
        auth=auth,
        rate_endpoint=endpoints["rate"],
        shipment_endpoint=endpoints["shipment"],
        tracking_endpoint=endpoints["tracking"],
    )

    if map_path is not None:
        map_data = _load_structured_file(map_path)
        _apply_map_overrides(spec, map_data)

    if interactive:
        _interactive_map(spec, discovered_fields)

    return spec
