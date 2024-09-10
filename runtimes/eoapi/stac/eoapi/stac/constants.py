# -*- coding: utf-8 -*-
# MIT License

# Copyright 2024, CS GROUP - France, https://www.csgroup.eu/
# Copyright (c) Microsoft Corporation.

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
"""Constants."""

DEFAULT_TTL = 600  # 10 minutes

# Headers containing information about the requester's
# IP address. Checked in the order listed here.
X_ORIGINAL_FORWARDED_FOR = "X-Original-Forwarded-For"
X_FORWARDED_FOR = "X-Forwarded-For"

X_REQUEST_ENTITY = "X-Request-Entity"

QS_REQUEST_ENTITY = "request_entity"

HTTP_429_TOO_MANY_REQUESTS = 429


# See https://opentelemetry.io/docs/specs/semconv/attributes-registry/
HTTP_METHOD = "http.request.method"
HTTP_URL = "url.full"
HTTP_PATH = "url.path"


CACHE_KEY_ITEM = "/item"
CACHE_KEY_ITEMS = "/items"
CACHE_KEY_SEARCH = "/search"
CACHE_KEY_LANDING = "/landing-page"
CACHE_KEY_COLLECTION = "/collection"
CACHE_KEY_COLLECTIONS = "/collections"
CACHE_KEY_QUERYABLES = "/queryables"

CACHE_KEY_BASE_ITEM = "/base-item"
