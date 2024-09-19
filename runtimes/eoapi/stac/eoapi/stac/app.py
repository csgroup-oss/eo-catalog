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
# SOFTWARE
"""eoapi.stac app."""

import logging
import os
from contextlib import asynccontextmanager

from buildpg import render
from eoapi.auth_utils import OpenIdConnectAuth
from eoapi.stac.config import Settings
from eoapi.stac.constants import CACHE_KEY_COLLECTIONS
from eoapi.stac.core import EOCClient
from eoapi.stac.extensions.filter import FiltersClient
from eoapi.stac.extensions.titiller import TiTilerExtension
from eoapi.stac.logs import init_logging
from eoapi.stac.middlewares.timeout import add_timeout
from eoapi.stac.utils import get_scopes_for_collections
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.routing import APIRoute
from stac_fastapi.api.app import StacApi
from stac_fastapi.api.middleware import ProxyHeaderMiddleware
from stac_fastapi.api.models import (
    EmptyRequest,
    ItemCollectionUri,
    create_get_request_model,
    create_post_request_model,
    create_request_model,
)
from stac_fastapi.extensions.core import (
    FieldsExtension,
    FilterExtension,
    FreeTextAdvancedExtension,
    SortExtension,
    TokenPaginationExtension,
    TransactionExtension, CollectionSearchExtension,
)
from stac_fastapi.extensions.third_party import BulkTransactionExtension
from stac_fastapi.pgstac.db import close_db_connection, connect_to_db
from stac_fastapi.pgstac.extensions import QueryExtension
from stac_fastapi.pgstac.transactions import BulkTransactionsClient, TransactionsClient
from stac_fastapi.pgstac.types.search import PgstacSearch
from stac_fastapi.types.stac import Collections
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette_cramjam.middleware import CompressionMiddleware

from auth import EoApiOpenIdConnectSettings, oidc_auth_from_settings

try:
    from importlib.resources import files as resources_files  # type: ignore
except ImportError:
    # Try backported to PY<39 `importlib_resources`.
    from importlib_resources import files as resources_files  # type: ignore

templates = Jinja2Templates(directory=str(resources_files(__package__) / "templates"))
auth_settings = EoApiOpenIdConnectSettings()
settings = Settings(enable_response_models=True)

# Logs
init_logging(service_name=settings.otel_service_name, debug=settings.debug)
logger = logging.getLogger(__name__)

# Extensions
extensions_map = {
    "transaction": TransactionExtension(
        client=TransactionsClient(),
        settings=settings,
        response_class=ORJSONResponse,
    ),
    "query": QueryExtension(),
    "sort": SortExtension(),
    "fields": FieldsExtension(),
    "pagination": TokenPaginationExtension(),
    "filter": FilterExtension(client=FiltersClient()),
    "bulk_transactions": BulkTransactionExtension(client=BulkTransactionsClient()),
    "titiler": (TiTilerExtension(titiler_endpoint=settings.titiler_endpoint) if settings.titiler_endpoint else None),
    "freetext_advanced": FreeTextAdvancedExtension(),
}

if enabled_extensions := settings.stac_extensions:
    extensions = [extensions_map[name] for name in enabled_extensions if extensions_map.get(name)]
else:
    extensions = [k[v] for k, v in extensions_map.items() if v]

if not (enabled_extensions := settings.stac_extensions) or "collection_search" in enabled_extensions:
    extension = CollectionSearchExtension.from_extensions(extensions)
    extensions.append(extension)
    collections_get_request_model = extension.GET
else:
    collections_get_request_model = EmptyRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan."""
    logger.debug("Connecting to db...")
    await connect_to_db(app)
    logger.debug("Connected to db.")

    if settings.redis_enabled:
        from eoapi.stac.redis import connect_to_redis

        await connect_to_redis(app)

    if auth_settings.openid_configuration_url:
        collections = await fetch_all_collections_raw()
        collection_scopes = get_scopes_for_collections(collections)
        oidc_auth = oidc_auth_from_settings(OpenIdConnectAuth, auth_settings)

        restricted_routes = {
            "/collections": ("POST", "admin"),
            "/collections/{collection_id}": ("PUT", "admin"),
            "/collections/{collection_id}": ("DELETE", "admin"),
            "/collections/{collection_id}/items": ("POST", "admin"),
            "/collections/{collection_id}/items/{item_id}": ("PUT", "admin"),
            "/collections/{collection_id}/items/{item_id}": ("DELETE", "admin"),
        }
        for collection_id, scope in collection_scopes.items():
            route = f"/collections/{collection_id}"
            restricted_routes[route] = ("GET", scope)

        api_routes = {
            route.path: route for route in api.app.routes if isinstance(route, APIRoute)
        }
        for endpoint, (method, scope) in restricted_routes.items():
            route = api_routes.get(endpoint)
            if route and method in route.methods:
                required_token_scopes = None
                if scope:
                    required_token_scopes = [scope]
                oidc_auth.apply_auth_dependencies(route, required_token_scopes=required_token_scopes)

    yield

    logger.debug("Closing db connections...")
    await close_db_connection(app)
    logger.debug("Closed db connection.")


# Middlewares
middlewares = [Middleware(CompressionMiddleware), Middleware(ProxyHeaderMiddleware)]
if settings.cors_origins:
    middlewares.append(
        Middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=settings.cors_methods,
            allow_headers=["*"],
        )
    )
if settings.otel_enabled:
    from eoapi.stac.middlewares.tracing import TraceMiddleware

    middlewares.append(Middleware(TraceMiddleware, service_name=settings.otel_service_name))


# Custom Models
items_get_model = ItemCollectionUri
if any(isinstance(ext, TokenPaginationExtension) for ext in extensions):
    items_get_model = create_request_model(
        model_name="ItemCollectionUri",
        base_model=ItemCollectionUri,
        mixins=[TokenPaginationExtension().GET],
        request_type="GET",
    )

itemsearch_exts = [ext for ext in extensions if ext.__class__.__name__ != "CollectionSearchExtension"]
search_get_model = create_get_request_model(itemsearch_exts)
search_post_model = create_post_request_model(itemsearch_exts, base_model=PgstacSearch)

api = StacApi(
    app=FastAPI(
        lifespan=lifespan,
        openapi_url=settings.openapi_url,
        docs_url=settings.docs_url,
        redoc_url=None,
        swagger_ui_init_oauth={
            "clientId": auth_settings.client_id,
            "usePkceWithAuthorizationCodeGrant": auth_settings.use_pkce,
        },
        root_path=settings.app_root_path,
    ),
    settings=settings,
    extensions=extensions,
    client=EOCClient(post_request_model=search_post_model),
    items_get_request_model=items_get_model,
    search_get_request_model=search_get_model,
    search_post_request_model=search_post_model,
    collections_get_request_model=collections_get_request_model,
    response_class=ORJSONResponse,
    middlewares=middlewares,
)
app = api.app

add_timeout(app, settings.request_timeout)


async def fetch_all_collections_raw() -> Collections:
    request = Request({"type": "http", "app": app})
    async def _fetch() -> Collections:

        async with app.state.get_connection(request, "r") as conn:
            q, p = render(
                """
                SELECT * FROM collection_search(:req::text::jsonb);
                """,
                req="{}",
            )
            collections_result: Collections = await conn.fetchval(q, *p)
            return collections_result

    cache_key = f"{CACHE_KEY_COLLECTIONS}_all"
    settings: Settings = app.state.settings

    if settings.redis_enabled:
        from eoapi.stac.redis import cached_result
        return await cached_result(_fetch, cache_key, request)
    return await _fetch()


@app.get("/index.html", response_class=HTMLResponse)
async def viewer_page(request: Request):
    """Search viewer."""
    return templates.TemplateResponse(
        request,
        name="stac-viewer.html",
        context={
            "endpoint": str(request.url).replace("/index.html", ""),
        },
        media_type="text/html",
    )



def run() -> None:
    """Run app from command line using uvicorn if available."""
    try:
        import uvicorn

        uvicorn.run(
            "eoapi.stac.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_level="info",
            reload=settings.reload,
            root_path=os.getenv("UVICORN_ROOT_PATH", ""),
        )
    except ImportError as e:
        raise RuntimeError("Uvicorn must be installed in order to use command") from e


if __name__ == "__main__":
    run()
