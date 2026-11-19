"""OpenAPI 3.x / Swagger 2.0 parser and field mapper for courier APIs."""

from src.parser.models import AuthConfig, AuthSchemeType, CourierSpec, EndpointConfig
from src.parser.openapi import parse_spec

__all__ = [
    "AuthConfig",
    "AuthSchemeType",
    "CourierSpec",
    "EndpointConfig",
    "parse_spec",
]
