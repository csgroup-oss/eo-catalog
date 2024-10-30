# Copyright (c) 2024, CS GROUP - France, https://csgroup.eu

# This file is part of EO Catalog project:

#     https://github.com/csgroup-oss/eo-catalog

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import json
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from buildpg import render
from stac_fastapi.types.stac import Collections

from eoapi.stac.config import Settings
from eoapi.stac.constants import (
    CACHE_KEY_COLLECTIONS,
    X_FORWARDED_FOR,
    X_ORIGINAL_FORWARDED_FOR,
)

if TYPE_CHECKING:
    from fastapi import Request

collections_list = Collections()


def request_to_path(request: Request) -> str:
    parsed_url = urlparse(f"{request.url}")
    return parsed_url.path


def get_request_ip(request: Request) -> str:
    """Gets the IP address of the request."""

    ip_header = request.headers.get(X_ORIGINAL_FORWARDED_FOR) or request.headers.get(X_FORWARDED_FOR)

    # If multiple IPs, take the last one
    return ip_header.split(",")[-1] if ip_header else ""


async def fetch_all_collections_with_scopes(request: Request) -> Collections:
    """
    fetches the ids and scopes of all collections from the database or the redis cache (if enabled)
    updates the redis cache (if enabled) if the data was fetched from the database
    Args:
        request: starlette request

    Returns: a Collections object containing all collection ids and scopes

    """

    async def _fetch() -> Collections:
        search_request = {"fields": {"include": ["id", "scope"]}, "limit": 100000}
        async with request.app.state.get_connection(request, "r") as conn:
            q, p = render(
                """
                SELECT * FROM collection_search(:req::text::jsonb);
                """,
                req=json.dumps(search_request),
            )
            collections_result: Collections = await conn.fetchval(q, *p)
            return collections_result

    cache_key = f"{CACHE_KEY_COLLECTIONS}_all"
    settings: Settings = request.app.state.settings

    if settings.redis_enabled:
        from eoapi.stac.redis import cached_result

        return await cached_result(_fetch, cache_key, request)
    return await _fetch()
