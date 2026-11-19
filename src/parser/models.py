"""Data models for parsed courier API specifications."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

AuthSchemeType = Literal["bearer", "api_key_header", "api_key_query", "basic", "none"]


@dataclass
class AuthConfig:
    """Authentication configuration extracted from an API specification."""

    scheme_type: AuthSchemeType
    header_name: str | None = None
    query_param: str | None = None
    prefix: str = ""


@dataclass
class EndpointConfig:
    """Configuration and field mappings for a single courier API endpoint."""

    method: str
    path: str
    request_mapping: dict[str, str] = field(default_factory=dict)
    response_mapping: dict[str, str] = field(default_factory=dict)


@dataclass
class CourierSpec:
    """Normalized courier API specification consumed by the Magento module generator."""

    title: str
    version: str
    base_url: str
    sandbox_url: str | None
    auth: AuthConfig
    rate_endpoint: EndpointConfig | None = None
    shipment_endpoint: EndpointConfig | None = None
    tracking_endpoint: EndpointConfig | None = None
