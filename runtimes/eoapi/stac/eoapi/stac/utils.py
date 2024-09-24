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

from typing import TYPE_CHECKING, Dict, Optional
from urllib.parse import urlparse

from eoapi.stac.constants import X_FORWARDED_FOR, X_ORIGINAL_FORWARDED_FOR
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

class CollectionsScopes:

    collection_scopes = {}

    def __init__(self, collections: Collections):
        self.collections = collections

    def set_scopes_for_collections(self):
        scopes = {}
        for collection in self.collections["collections"]:
            if "scope" in collection:
                scopes[collection["id"]] = collection["scope"]
        CollectionsScopes.collection_scopes = scopes
        print(CollectionsScopes.collection_scopes)
