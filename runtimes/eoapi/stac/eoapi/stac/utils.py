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
# SOFTWARE.
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Dict, Optional
from urllib.parse import urlparse

from buildpg import render
from eoapi.stac.config import Settings
from eoapi.stac.constants import X_FORWARDED_FOR, X_ORIGINAL_FORWARDED_FOR, CACHE_KEY_COLLECTIONS
from stac_fastapi.types.stac import Collections

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
        search_request = {
            "fields": {"include": ["id", "scope"]},
            "limit": 100000
        }
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
