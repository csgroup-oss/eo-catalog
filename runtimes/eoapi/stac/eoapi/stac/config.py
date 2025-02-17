# Copyright 2024, CS GROUP - France, https://www.csgroup.eu/
"""API settings."""

from typing import Optional

from pydantic import Field, computed_field, field_validator
from stac_fastapi.pgstac.config import Settings as BaseSettings

from eoapi.stac.constants import DEFAULT_TTL


class Settings(BaseSettings):
    """API settings"""

    cachecontrol: str = "public, max-age=3600"
    debug: bool = False

    titiler_endpoint: Optional[str] = None

    request_timeout: int = Field(default=30, description="Timeout pending requests.")

    redis_cluster: bool = False
    redis_ttl: int = Field(default=DEFAULT_TTL)
    redis_hostname: Optional[str] = None
    redis_password: str = ""
    redis_port: int = 6379
    redis_ssl: bool = True

    eoapi_auth_metadata_field: str = "scope"
    eoapi_auth_update_scope: str = "admin"

    otel_enabled: bool = False
    otel_service_name: str = "eo-catalog-stac"

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origin(cls, v: str):  # pylint: disable=arguments-differ
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]

    @field_validator("cors_methods")
    @classmethod
    def parse_cors_methods(cls, v: str):  # pylint: disable=arguments-differ
        """Parse CORS methods."""
        return [method.strip() for method in v.split(",")]

    @computed_field  # type: ignore[misc]
    @property
    def redis_enabled(self) -> bool:
        """Return true if redis_hostname is set."""
        return bool(self.redis_hostname)

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }
