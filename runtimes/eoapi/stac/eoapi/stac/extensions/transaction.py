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

from typing import Optional, Union

from stac_fastapi.pgstac.db import dbfunc
from stac_fastapi.pgstac.models.links import CollectionLinks
from stac_fastapi.pgstac.transactions import TransactionsClient
from stac_fastapi.types import stac as stac_types
from stac_pydantic import Collection
from starlette.requests import Request
from starlette.responses import Response

from eoapi.stac.auth import CollectionsScopes
from eoapi.stac.config import Settings
from eoapi.stac.constants import CACHE_KEY_COLLECTIONS
from eoapi.stac.utils import fetch_all_collections_with_scopes


async def _update_collection_scopes(request: Request):
    """
    updates the cached collection scopes in memory and possibly also in redis (depending on app settings)
    Args:
        request: starlette request used to check the app settings
    """
    settings: Settings = request.app.state.settings
    if settings.redis_enabled:
        r = request.app.state.redis
        r.delete(f"{CACHE_KEY_COLLECTIONS}_all")
    collections = await fetch_all_collections_with_scopes(request)
    CollectionsScopes(collections, settings.eoapi_auth_metadata_field).set_scopes_for_collections()


class EoApiTransactionsClient(TransactionsClient):
    async def create_collection(
        self,
        collection: Collection,
        request: Request,
        **kwargs,
    ) -> Optional[Union[stac_types.Collection, Response]]:
        """Create collection; called with POST /collections
        overwrites create_collection from stac_fastapi to ensure that cached scopes are updated
        """
        collection = collection.model_dump(mode="json")

        self._validate_collection(request, collection)

        async with request.app.state.get_connection(request, "w") as conn:
            await dbfunc(conn, "create_collection", collection)

        collection["links"] = await CollectionLinks(
            collection_id=collection["id"], request=request
        ).get_links(extra_links=collection["links"])

        await _update_collection_scopes(request)

        return stac_types.Collection(**collection)

    async def update_collection(
        self,
        collection: Collection,
        request: Request,
        **kwargs,
    ) -> Optional[Union[stac_types.Collection, Response]]:
        """Update collection; called with PUT /collections
        overwrites update_collection from stac_fastapi to ensure that cached scopes are updated
        """

        col = collection.model_dump(mode="json")

        async with request.app.state.get_connection(request, "w") as conn:
            await dbfunc(conn, "update_collection", col)

        col["links"] = await CollectionLinks(collection_id=col["id"], request=request).get_links(
            extra_links=col.get("links")
        )

        await _update_collection_scopes(request)

        return stac_types.Collection(**col)
