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

from eoapi.auth_utils import OpenIdConnectAuth
from eoapi.stac.auth import CollectionsScopes, oidc_auth_from_settings
from eoapi.stac.config import Settings
from eoapi.stac.core import EOCClient
from eoapi.stac.extensions.filter import FiltersClient
from eoapi.stac.extensions.titiller import TiTilerExtension
from eoapi.stac.logs import init_logging
from eoapi.stac.middlewares.timeout import add_timeout
from eoapi.stac.utils import fetch_all_collections_with_scopes
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
    TransactionExtension,
)
from stac_fastapi.extensions.third_party import BulkTransactionExtension
from stac_fastapi.pgstac.db import close_db_connection, connect_to_db
from stac_fastapi.pgstac.extensions import QueryExtension
from stac_fastapi.pgstac.transactions import BulkTransactionsClient
from stac_fastapi.pgstac.types.search import PgstacSearch
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette_cramjam.middleware import CompressionMiddleware

from auth import EoApiOpenIdConnectSettings
from extensions.transaction import EoApiTransactionsClient
from eoapi.stac.extensions.collection_search import CollectionSearchExtensionWithIds

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
        client=EoApiTransactionsClient(),
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
    extension = CollectionSearchExtensionWithIds.from_extensions(extensions)
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

    # add restrictions to endpoints
    if auth_settings.openid_configuration_url:
        logger.debug("Add access restrictions to transaction endpoints")
        await lock_transaction_endpoints()
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

itemsearch_exts = [ext for ext in extensions if ext.__class__.__name__ != "CollectionSearchExtensionWithIds"]
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


async def lock_transaction_endpoints():

    # get scopes for collections
    request = Request({"type": "http", "app": app})
    collections = await fetch_all_collections_with_scopes(request)
    CollectionsScopes(collections, settings.eoapi_auth_metadata_field)
    oidc_auth = oidc_auth_from_settings(OpenIdConnectAuth, auth_settings)
    # basic restricted routes
    admin_scope = settings.eoapi_auth_update_scope
    restricted_routes = {
        "/collections": ("POST", admin_scope, "/collections"),
        "/collections/{collection_id}": ("PUT", admin_scope, "/collections/{collection_id}"),
        "/collections/{collection_id}": ("DELETE", admin_scope, "/collections/{collection_id}"),
        "/collections/{collection_id}/items": ("POST", admin_scope, "/collections/{collection_id}/items"),
        "/collections/{collection_id}/items/{item_id}": (
        "PUT", admin_scope, "/collections/{collection_id}/items/{item_id}"),
        "/collections/{collection_id}/items/{item_id}": (
        "DELETE", admin_scope, "/collections/{collection_id}/items/{item_id}"),
    }
    api_routes = {}
    for route in app.routes:
        if isinstance(route, APIRoute):
            if route.path in api_routes:
                api_routes[route.path].append(route)
            else:
                api_routes[route.path] = [route]
    for endpoint, (method, scope, alias) in restricted_routes.items():
        routes = api_routes.get(endpoint)
        if not routes:
            continue
        for route in routes:
            if method not in route.methods:
                continue
            if scope:
                oidc_auth.apply_auth_dependencies(route, required_token_scopes=[scope])


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
