# Copyright 2024, CS GROUP - France, https://www.csgroup.eu/
"""eocatalog.stac app."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
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
    OffsetPaginationExtension,
    SortExtension,
    TokenPaginationExtension,
    TransactionExtension,
)
from stac_fastapi.extensions.third_party import BulkTransactionExtension
from stac_fastapi.pgstac.db import close_db_connection, connect_to_db
from stac_fastapi.pgstac.extensions import QueryExtension
from stac_fastapi.pgstac.transactions import BulkTransactionsClient
from stac_fastapi.pgstac.types.search import PgstacSearch
from stac_fastapi.types.extension import ApiExtension
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette_cramjam.middleware import CompressionMiddleware

from eoapi.auth_utils import OpenIdConnectAuth
from eoapi.stac.auth import (
    CollectionsScopes,
    EoApiOpenIdConnectSettings,
    oidc_auth_from_settings,
    verify_scope_for_collection,
)
from eoapi.stac.config import Settings
from eoapi.stac.core import EOCClient
from eoapi.stac.extensions.collection_search import CollectionSearchExtensionWithIds
from eoapi.stac.extensions.filter import FiltersClient
from eoapi.stac.extensions.titiller import TiTilerExtension
from eoapi.stac.extensions.transaction import EoApiTransactionsClient
from eoapi.stac.logs import init_logging
from eoapi.stac.middlewares.timeout import add_timeout
from eoapi.stac.utils import fetch_all_collections_with_scopes

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
extensions_map: dict[str, ApiExtension] = {
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
    "freetext_advanced": FreeTextAdvancedExtension(),
}

if settings.titiler_endpoint:
    extensions_map["titiler"] = TiTilerExtension(titiler_endpoint=settings.titiler_endpoint)


# some extensions are supported in combination with the collection search extension
collection_extensions_map: dict[str, ApiExtension] = {
    "query": QueryExtension(),
    "sort": SortExtension(),
    "fields": FieldsExtension(),
    "filter": FilterExtension(client=FiltersClient()),
    "pagination": OffsetPaginationExtension(),
    "freetext_advanced": FreeTextAdvancedExtension(),
}

enabled_extensions = (
    os.environ["ENABLED_EXTENSIONS"].split(",")
    if "ENABLED_EXTENSIONS" in os.environ
    else list(extensions_map.keys()) + ["collection_search"]
)
extensions = [extension for key, extension in extensions_map.items() if key in enabled_extensions]

items_get_request_model = (
    create_request_model(
        model_name="ItemCollectionUri",
        base_model=ItemCollectionUri,
        mixins=[TokenPaginationExtension().GET],
        request_type="GET",
    )
    if any(isinstance(ext, TokenPaginationExtension) for ext in extensions)
    else ItemCollectionUri
)


collection_search_extension = (
    CollectionSearchExtensionWithIds.from_extensions(
        [extension for key, extension in collection_extensions_map.items() if key in enabled_extensions]
    )
    if "collection_search" in enabled_extensions
    else None
)

collections_get_request_model = collection_search_extension.GET if collection_search_extension else EmptyRequest

post_request_model = create_post_request_model(extensions, base_model=PgstacSearch)
get_request_model = create_get_request_model(extensions)


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
middlewares = [
    Middleware(CompressionMiddleware),
    Middleware(ProxyHeaderMiddleware),
    Middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=settings.cors_methods,
    ),
]

if settings.otel_enabled:
    from eoapi.stac.middlewares.tracing import TraceMiddleware

    middlewares.append(Middleware(TraceMiddleware, service_name=settings.otel_service_name))

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
        dependencies=[Depends(verify_scope_for_collection)],
    ),
    settings=settings,
    extensions=extensions + [collection_search_extension] if collection_search_extension else extensions,
    client=EOCClient(post_request_model=post_request_model),  # type: ignore
    items_get_request_model=items_get_request_model,
    search_get_request_model=get_request_model,
    search_post_request_model=post_request_model,
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
    # get scopes for collections which will be used in dependencies
    collections = await fetch_all_collections_with_scopes(request)
    CollectionsScopes(collections, settings.eoapi_auth_metadata_field)
    oidc_auth = oidc_auth_from_settings(OpenIdConnectAuth, auth_settings)
    # basic restricted routes
    admin_scope = settings.eoapi_auth_update_scope
    restricted_routes = [
        ("POST", admin_scope, "/collections"),
        ("PUT", admin_scope, "/collections/{collection_id}"),
        ("DELETE", admin_scope, "/collections/{collection_id}"),
        ("POST", admin_scope, "/collections/{collection_id}/items"),
        ("PUT", admin_scope, "/collections/{collection_id}/items/{item_id}"),
        ("DELETE", admin_scope, "/collections/{collection_id}/items/{item_id}"),
    ]
    api_routes = {}
    for route in app.routes:
        if isinstance(route, APIRoute):
            if route.path in api_routes:
                api_routes[route.path].append(route)
            else:
                api_routes[route.path] = [route]
    for method, scope, endpoint in restricted_routes:
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
