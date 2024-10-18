# -*- coding: utf-8 -*-
# MIT License

# Copyright 2024, CS GROUP - France, https://www.csgroup.eu/
# Copyright (c) 2024 Development Seed

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE
"""API settings."""

from typing import List, Optional

from pydantic import Field, computed_field, field_validator
from stac_fastapi.pgstac.config import Settings as BaseSettings

from eoapi.stac.constants import DEFAULT_TTL


class Settings(BaseSettings):
    """API settings"""

    app_root_path: str = ""

    cors_origins: str = "*"
    cors_methods: str = "GET,POST,OPTIONS"
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

    stac_extensions: List[str] = [
        "transaction",
        "query",
        "sort",
        "fields",
        "pagination",
        "filter",
        "bulk_transactions",
        "titiler",
        "freetext_advanced",
        "collection_search",
    ]

    otel_enabled: bool = False
    otel_service_name: str = "eo-catalog-stac"

    @field_validator("cors_origins")
    def parse_cors_origin(cls, v):
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]

    @field_validator("cors_methods")
    def parse_cors_methods(cls, v):
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
