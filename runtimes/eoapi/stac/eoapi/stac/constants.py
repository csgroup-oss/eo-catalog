# Copyright (c) 2024, CS GROUP - France, https://cs-soprasteria.com

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
