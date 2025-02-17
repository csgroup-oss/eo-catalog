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
"""Core"""

import json
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar
from urllib.parse import unquote_plus, urljoin

import attr
import orjson
from buildpg import render
from fastapi import Depends, Request
from stac_fastapi.pgstac.core import CoreCrudClient
from stac_fastapi.pgstac.models.links import CollectionLinks, CollectionSearchPagingLinks
from stac_fastapi.pgstac.types.search import PgstacSearch
from stac_fastapi.types.core import Relations
from stac_fastapi.types.requests import get_base_url
from stac_fastapi.types.stac import (
    Collection,
    Collections,
    Item,
    ItemCollection,
    LandingPage,
)
from stac_pydantic.shared import BBox, MimeTypes

from eoapi.auth_utils import OpenIdConnectAuth
from eoapi.stac.auth import (
    EoApiOpenIdConnectSettings,
    get_collections_for_user_scope,
    oidc_auth_from_settings,
    verify_scope_for_collection,
)
from eoapi.stac.config import Settings
from eoapi.stac.constants import (
    CACHE_KEY_COLLECTION,
    CACHE_KEY_COLLECTIONS,
    CACHE_KEY_ITEM,
    CACHE_KEY_ITEMS,
    CACHE_KEY_LANDING,
    CACHE_KEY_SEARCH,
)
from eoapi.stac.logs import get_custom_dimensions

logger = logging.getLogger(__name__)


@attr.s
class EOCClient(CoreCrudClient):
    """Client for core endpoints defined by stac."""

    extra_conformance_classes: List[str] = attr.ib(factory=list)
    auth_settings = EoApiOpenIdConnectSettings()
    oidc_auth = oidc_auth_from_settings(OpenIdConnectAuth, auth_settings)

    async def landing_page(self, **kwargs: Any) -> LandingPage:
        """
        Override from stac-fastapi-pgstac to cache result.
        """
        _super: CoreCrudClient = super()
        request: Request = kwargs["request"]

        async def _fetch() -> LandingPage:
            return await _super.landing_page(  # type: ignore[reportUnknownMemberType]
                request=request
            )

        return await cached_result(_fetch, CACHE_KEY_LANDING, request)

    async def all_collections(  # noqa: C901
        self,
        request: Request,
        # Extensions
        bbox: Optional[BBox] = None,
        datetime: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        fields: Optional[List[str]] = None,
        sortby: Optional[str] = None,
        filter_expr: Optional[str] = None,
        filter_lang: Optional[str] = None,
        q: Optional[List[str]] = None,
        ids: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Collections:
        """Cross catalog search (GET).
        Override from stac-fastapi-pgstac to cache result and support pagination with
        collection-search.
        Can be simplified once https://github.com/stac-utils/stac-fastapi-pgstac/pull/155.
        """
        # filter ids depending on the user scope
        collections_with_scopes = get_collections_for_user_scope(request, EOCClient.oidc_auth)
        if not ids:
            ids = collections_with_scopes
        elif collections_with_scopes:
            ids = list(set(collections_with_scopes) & set(ids))

        # don't return the scope of the collection
        fields = fields or []
        fields.append("-scope")

        clean_args = {}
        if self.extension_is_enabled("CollectionSearchExtension"):
            if query:
                query = orjson.loads(unquote_plus(query))  # pylint: disable=no-member
            base_args: dict[str, Any] = {
                "ids": ids,
                "bbox": bbox,
                "limit": limit,
                "offset": offset,
                "query": query,
            }
            clean_args = self._clean_search_args(
                base_args=base_args,
                datetime=datetime,
                fields=fields,
                sortby=sortby,
                filter_query=filter_expr,
                filter_lang=filter_lang,
                q=q,
            )

        async def _fetch() -> Collections:
            base_url = get_base_url(request)

            next_link: Optional[Dict[str, Any]] = None
            prev_link: Optional[Dict[str, Any]] = None
            result: Collections

            if self.extension_is_enabled("CollectionSearchExtension"):
                async with request.app.state.get_connection(request, "r") as conn:
                    q, p = render(
                        """
                        SELECT * FROM collection_search(:req::text::jsonb);
                        """,
                        req=json.dumps(clean_args, default=list),
                    )  # type: ignore
                    result = await conn.fetchval(q, *p)

                if links := result.get("links"):
                    for link in links:
                        if link["rel"] == "next":
                            next_link = link
                        elif link["rel"] == "prev":
                            prev_link = link

            else:
                async with request.app.state.get_connection(request, "r") as conn:
                    cols = await conn.fetchval(
                        """
                        SELECT * FROM all_collections();
                        """
                    )
                    result = {"collections": cols, "links": []}

            linked_collections: List[Collection] = []
            collections = result["collections"]  # type: ignore[reportTypedDictNotRequiredAccess]
            if collections:
                for c in collections:
                    coll = Collection(**c)
                    coll["links"] = await CollectionLinks(
                        collection_id=coll["id"],  # type: ignore[reportTypedDictNotRequiredAccess]
                        request=request,
                    ).get_links(extra_links=coll.get("links"))

                    if self.extension_is_enabled("FilterExtension") or self.extension_is_enabled(
                        "ItemCollectionFilterExtension"
                    ):
                        url = urljoin(
                            base_url,
                            (
                                "collections/"
                                + coll["id"]  # type: ignore[reportTypedDictNotRequiredAccess]
                                + "/queryables"
                            ),
                        )
                        coll["links"].append(
                            {
                                "rel": Relations.queryables.value,
                                "type": MimeTypes.jsonschema.value,
                                "title": "Queryables",
                                "href": url,
                            }
                        )

                    linked_collections.append(coll)

            links = await CollectionSearchPagingLinks(
                request=request,
                next=next_link,
                prev=prev_link,
            ).get_links()

            return Collections(
                collections=linked_collections or [],
                links=links,
                numberMatched=result.get("numberMatched", len(linked_collections)),
                numberReturned=result.get("numberReturned", len(linked_collections)),
            )

        settings: Settings = request.app.state.settings

        json_args = json.dumps(clean_args, default=list)

        if settings.otel_enabled:
            from eoapi.stac.middlewares.tracing import (  # pylint: disable=import-outside-toplevel
                add_stac_attributes_from_search,
            )

            add_stac_attributes_from_search(json_args, request)

        logger.info(
            "STAC: Collection search body",
            extra=get_custom_dimensions({"search_body": clean_args}, request),
        )

        hashed_search = hash(json_args)
        cache_key = f"{CACHE_KEY_COLLECTIONS}:{hashed_search}"
        return await cached_result(_fetch, cache_key, request)

    async def get_collection(
        self,
        collection_id: str,
        request: Request,
        _: None = Depends(verify_scope_for_collection),
        **kwargs: Any,
    ) -> Collection:
        """
        Override from stac-fastapi-pgstac to cache result.
        """
        _super: CoreCrudClient = super()

        async def _fetch() -> Collection:
            return await _super.get_collection(  # type: ignore[reportUnknownMemberType]
                collection_id, request=request, **kwargs
            )

        cache_key = f"{CACHE_KEY_COLLECTION}:{collection_id}"
        result = await cached_result(_fetch, cache_key, request)
        result.pop("scope", None)  # type: ignore
        return result

    async def _search_base(
        self,
        search_request: PgstacSearch,
        request: Request,
    ) -> ItemCollection:
        """Cross catalog search (POST).

        Override from stac-fastapi-pgstac to cache results and add telemetry.
        """
        _super: CoreCrudClient = super()

        settings: Settings = request.app.state.settings

        collections_with_scopes = get_collections_for_user_scope(request, EOCClient.oidc_auth)
        if not search_request.collections:
            search_request.collections = collections_with_scopes
        elif collections_with_scopes:
            search_request.collections = list(
                set(collections_with_scopes) & set(search_request.collections)
            )

        async def _fetch() -> ItemCollection:
            result = await _super._search_base(search_request, request=request)  # pylint: disable=protected-access

            ts = time.perf_counter()
            item_collection = ItemCollection(**result)
            te = time.perf_counter()

            logger.debug(
                "Perf: item search result post processing",
                extra=get_custom_dimensions({"duration": f"{te - ts:0.4f}"}, request),
            )
            return item_collection

        search_json = search_request.model_dump_json()

        if settings.otel_enabled:
            from eoapi.stac.middlewares.tracing import (  # pylint: disable=import-outside-toplevel
                add_stac_attributes_from_search,
            )

            add_stac_attributes_from_search(search_json, request)

        logger.info(
            "STAC: Item search body",
            extra=get_custom_dimensions({"search_body": search_json}, request),
        )

        hashed_search = hash(search_json)
        cache_key = f"{CACHE_KEY_SEARCH}:{hashed_search}"
        return await cached_result(_fetch, cache_key, request)

    async def item_collection(
        self,
        collection_id: str,
        request: Request,
        bbox: Optional[BBox] = None,
        datetime: Optional[str] = None,
        limit: Optional[int] = None,
        # Extensions
        query: Optional[str] = None,
        fields: Optional[List[str]] = None,
        sortby: Optional[str] = None,
        filter_expr: Optional[str] = None,
        filter_lang: Optional[str] = None,
        token: Optional[str] = None,
        _: None = Depends(verify_scope_for_collection),
        **kwargs: Any,
    ) -> ItemCollection:
        """
        Override from stac-fastapi-pgstac to cache result.
        """
        _super: CoreCrudClient = super()

        base_args: dict[str, Any] = {
            "collection_id": collection_id,
            "bbox": bbox,
            "datetime": datetime,
            "limit": limit,
            "token": token,
            "query": query,
        }

        clean_args = self._clean_search_args(
            base_args=base_args,
            datetime=datetime,
            fields=fields,
            sortby=sortby,
            filter_query=filter_expr,
            filter_lang=filter_lang,
        )

        hashed_search = hash(json.dumps(clean_args, default=list))

        async def _fetch() -> ItemCollection:
            return await _super.item_collection(  # type: ignore[reportUnknownMemberType]
                collection_id,
                request=request,
                bbox=bbox,
                datetime=datetime,
                limit=limit,
                token=token,
                query=query,
                fields=fields,
                sortby=sortby,
                filter_expr=filter_expr,
                filter_lang=filter_lang,
                **kwargs,
            )

        cache_key = f"{CACHE_KEY_ITEMS}:{hashed_search}"
        return await cached_result(_fetch, cache_key, request)

    async def get_item(
        self,
        item_id: str,
        collection_id: str,
        request: Request,
        _: None = Depends(verify_scope_for_collection),
        **kwargs: Any,
    ) -> Item:
        """
        Override from stac-fastapi-pgstac to cache result.
        """
        _super: CoreCrudClient = super()

        async def _fetch() -> Item:
            item = await _super.get_item(item_id, collection_id, request, **kwargs)  # type: ignore[reportUnknownMemberType]
            return item

        cache_key = f"{CACHE_KEY_ITEM}:{collection_id}:{item_id}"
        return await cached_result(_fetch, cache_key, request)


T = TypeVar("T")


async def cached_result(
    fn: Callable[..., Coroutine[Any, Any, T]],
    cache_key: str,
    request: Request,
) -> T:
    """
    If Redis is enable, cache result.
    """
    settings: Settings = request.app.state.settings

    if settings.redis_enabled:
        from eoapi.stac.redis import (  # pylint: disable=import-outside-toplevel
            cached_result as redis_cached,
        )

        return await redis_cached(fn, cache_key, request)

    return await fn()
