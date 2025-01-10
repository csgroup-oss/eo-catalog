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
import json
import logging
import re
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar
from urllib.parse import unquote_plus, urljoin

import attr
import orjson
from buildpg import render
from fastapi import Depends, Request
from pygeofilter.backends.cql2_json import to_cql2
from pygeofilter.parsers.cql2_text import parse as parse_cql2_text
from stac_fastapi.pgstac.core import CoreCrudClient
from stac_fastapi.pgstac.models.links import CollectionLinks
from stac_fastapi.pgstac.types.search import PgstacSearch
from stac_fastapi.pgstac.utils import format_datetime_range
from stac_fastapi.types.core import Relations
from stac_fastapi.types.requests import get_base_url
from stac_fastapi.types.rfc3339 import DateTimeType
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
from eoapi.stac.models import CollectionSearchPagingLinks

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
            return await _super.landing_page(request=request)

        return await cached_result(_fetch, CACHE_KEY_LANDING, request)

    async def all_collections(  # noqa: C901
        self,
        request: Request,
        # Extensions
        ids: Optional[List[str]] = None,
        bbox: Optional[BBox] = None,
        datetime: Optional[DateTimeType] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        fields: Optional[List[str]] = None,
        sortby: Optional[str] = None,
        filter: Optional[str] = None,
        filter_lang: Optional[str] = None,
        q: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Collections:
        """Cross catalog search (GET).
        Override from stac-fastapi-pgstac to cache result and support pagination with collection-search.
        Can be simplified once https://github.com/stac-utils/stac-fastapi-pgstac/pull/155.
        """

        # filter ids depending on the user scope
        collections_with_scopes = get_collections_for_user_scope(request, EOCClient.oidc_auth)
        if not ids:
            ids = collections_with_scopes
        elif collections_with_scopes:
            ids = list(set(collections_with_scopes) & set(ids))
        # don't return the scope of the collection
        if not fields:
            fields = []
        fields.append("-scope")

        clean_args = {}
        if self.extension_is_enabled("CollectionSearchExtensionWithIds"):
            base_args: dict[str, Any] = {
                "ids": ids,
                "bbox": bbox,
                "limit": limit,
                "offset": offset,
                "query": orjson.loads(unquote_plus(query)) if query else query,
                "q": q,
            }

            clean_args = clean_search_args(
                base_args=base_args,
                datetime=datetime,
                fields=fields,
                sortby=sortby,
                filter_query=filter,
                filter_lang=filter_lang,
            )

        json_args = json.dumps(clean_args, default=list)

        async def _fetch() -> Collections:
            base_url = get_base_url(request)

            next_link: Optional[Dict[str, Any]] = None
            prev_link: Optional[Dict[str, Any]] = None
            collections_result: Collections

            if self.extension_is_enabled("CollectionSearchExtensionWithIds"):
                async with request.app.state.get_connection(request, "r") as conn:
                    q, p = render(
                        """
                        SELECT * FROM collection_search(:req::text::jsonb);
                        """,
                        req=json_args,
                    )
                    collections_result = await conn.fetchval(q, *p)

                if links := collections_result.get("links"):
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
                    collections_result = {"collections": cols, "links": []}

            linked_collections: List[Collection] = []
            collections = collections_result.get("collections")
            if collections is not None and len(collections) > 0:
                for c in collections:
                    coll = Collection(**c)
                    coll["links"] = await CollectionLinks(collection_id=coll["id"], request=request).get_links(
                        extra_links=coll.get("links")
                    )

                    if self.extension_is_enabled("FilterExtension"):
                        coll["links"].append(
                            {
                                "rel": Relations.queryables.value,
                                "type": MimeTypes.jsonschema.value,
                                "title": "Queryables",
                                "href": urljoin(base_url, f"collections/{coll['id']}/queryables"),
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
            )

        settings: Settings = request.app.state.settings

        if settings.otel_enabled:
            from eoapi.stac.middlewares.tracing import add_stac_attributes_from_search

            add_stac_attributes_from_search(clean_args, request)

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
        dep: dict = Depends(verify_scope_for_collection),
    ) -> Collection:
        """
        Override from stac-fastapi-pgstac to cache result.
        """
        _super: CoreCrudClient = super()

        async def _fetch() -> Collection:
            return await _super.get_collection(collection_id, request=request)

        cache_key = f"{CACHE_KEY_COLLECTION}:{collection_id}"
        result = await cached_result(_fetch, cache_key, request)
        result.pop("scope", None)
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
            search_request.collections = list(set(collections_with_scopes) & set(search_request.collections))

        async def _fetch() -> ItemCollection:
            result = await _super._search_base(search_request, request=request)

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
            from eoapi.stac.middlewares.tracing import add_stac_attributes_from_search

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
        datetime: Optional[DateTimeType] = None,
        limit: Optional[int] = None,
        token: Optional[str] = None,
        dep: dict = Depends(verify_scope_for_collection),
    ) -> ItemCollection:
        """
        Override from stac-fastapi-pgstac to cache result.
        """
        _super: CoreCrudClient = super()

        async def _fetch() -> ItemCollection:
            return await _super.item_collection(
                collection_id,
                request=request,
                bbox=bbox,
                datetime=datetime,
                limit=limit,
                token=token,
            )

        cache_key = f"{CACHE_KEY_ITEMS}:{collection_id}:{bbox}:{datetime}:{limit}:{token}"
        return await cached_result(_fetch, cache_key, request)

    async def get_item(
        self,
        item_id: str,
        collection_id: str,
        request: Request,
        dep: dict = Depends(verify_scope_for_collection),
    ) -> Item:
        """
        Override from stac-fastapi-pgstac to cache result.
        """
        _super: CoreCrudClient = super()

        async def _fetch() -> Item:
            item = await _super.get_item(item_id, collection_id, request)
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
        from eoapi.stac.redis import cached_result

        return await cached_result(fn, cache_key, request)

    return await fn()


def clean_search_args(  # noqa: C901
    base_args: Dict[str, Any],
    intersects: Optional[str] = None,
    datetime: Optional[DateTimeType] = None,
    fields: Optional[List[str]] = None,
    sortby: Optional[str] = None,
    filter_query: Optional[str] = None,
    filter_lang: Optional[str] = None,
) -> Dict[str, Any]:
    """Clean up search arguments to match format expected by pgstac"""
    if filter_query:
        if filter_lang == "cql2-text":
            filter_query = to_cql2(parse_cql2_text(filter_query))
            filter_lang = "cql2-json"

        base_args["filter"] = orjson.loads(filter_query)
        base_args["filter_lang"] = filter_lang

    if datetime:
        base_args["datetime"] = format_datetime_range(datetime)

    if intersects:
        base_args["intersects"] = orjson.loads(unquote_plus(intersects))

    if sortby:
        # https://github.com/radiantearth/stac-spec/tree/master/api-spec/extensions/sort#http-get-or-post-form
        sort_param = []
        for sort in sortby:
            sortparts = re.match(r"^([+-]?)(.*)$", sort)
            if sortparts:
                sort_param.append(
                    {
                        "field": sortparts.group(2).strip(),
                        "direction": "desc" if sortparts.group(1) == "-" else "asc",
                    }
                )
        base_args["sortby"] = sort_param

    if fields:
        includes = set()
        excludes = set()
        for field in fields:
            if field[0] == "-":
                excludes.add(field[1:])
            elif field[0] == "+":
                includes.add(field[1:])
            else:
                includes.add(field)
        base_args["fields"] = {"include": includes, "exclude": excludes}

    # Remove None values from dict
    clean = {}
    for k, v in base_args.items():
        if v is not None and v != []:
            clean[k] = v

    return clean
