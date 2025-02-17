# Copyright (c) 2025, CS GROUP - France, https://cs-soprasteria.com

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
"""Collection-Search extension."""

from typing import Annotated, List, Optional

import attr
from fastapi import FastAPI, Query
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.search import APIRequest, _ids_converter  # type: ignore


@attr.s
class GETCollectionSearchIds(APIRequest):
    """Override the basic Collection-Search GET request parameters for ids filter."""

    ids: Annotated[Optional[List[str]], Query()] = attr.ib(
        default=None,
        converter=lambda x: _ids_converter(x),  # pylint: disable=unnecessary-lambda
    )


@attr.s
class CollectionSearchIdsExtension(ApiExtension):
    """
    Extension of the CollectionSearchExtension which also allows filtering by ids
    """

    GET = GETCollectionSearchIds

    conformance_classes: List[str] = attr.ib(factory=list)
    schema_href: Optional[str] = attr.ib(default=None)

    def register(self, app: FastAPI) -> None:
        """Register the extension with a FastAPI application.

        Args:
            app: target FastAPI application.

        Returns:
            None
        """
        pass
