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
# SOFTWARE.
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
