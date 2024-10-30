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
from typing import Any, Dict, Optional

from fastapi import Request
from stac_fastapi.pgstac.extensions.filter import FiltersClient as BaseFiltersClient

from eoapi.stac.constants import CACHE_KEY_QUERYABLES
from eoapi.stac.core import cached_result


class FiltersClient(BaseFiltersClient):
    async def get_queryables(
        self, request: Request, collection_id: Optional[str] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        """Override pgstac backend get_queryables to make use of cached results"""
        _super: BaseFiltersClient = super()

        async def _fetch() -> Dict[str, Any]:
            return await _super.get_queryables(request, collection_id, **kwargs)

        cache_key = f"{CACHE_KEY_QUERYABLES}:{collection_id}"
        return await cached_result(_fetch, cache_key, request)
