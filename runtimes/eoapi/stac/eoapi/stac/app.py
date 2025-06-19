# Copyright 2024-2025, CS GROUP - France, https://www.csgroup.eu/
"""eocatalog.stac app."""

import logging
import os
from contextlib import asynccontextmanager

import jinja2
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
from stac_fastapi.api.openapi import update_openapi
from stac_fastapi.extensions.core import (
    CollectionSearchExtension,
    CollectionSearchFilterExtension,
    FieldsExtension,
    FreeTextExtension,
    ItemCollectionFilterExtension,
    OffsetPaginationExtension,
    SearchFilterExtension,
    SortExtension,
    TokenPaginationExtension,
)
from stac_fastapi.extensions.core.fields import FieldsConformanceClasses
from stac_fastapi.extensions.core.free_text import FreeTextConformanceClasses
from stac_fastapi.extensions.core.query import QueryConformanceClasses
from stac_fastapi.extensions.core.sort import SortConformanceClasses
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
from eoapi.stac.extensions.collection_search import CollectionSearchIdsExtension
from eoapi.stac.extensions.filter import FiltersClient
from eoapi.stac.extensions.titiller import TiTilerExtension
from eoapi.stac.extensions.transaction import EoApiTransactionsClient
from eoapi.stac.logs import init_logging
from eoapi.stac.middlewares.timeout import add_timeout
from eoapi.stac.utils import fetch_all_collections_with_scopes
from eoapi.stac.extensions.custom_transaction_extension import BackgroundTasksTransactionExtension

PACKAGE_NAME = __package__ or "eoapi.stac"

jinja2_env = jinja2.Environment(
    loader=jinja2.ChoiceLoader([jinja2.PackageLoader(PACKAGE_NAME, "templates")])
)
templates = Jinja2Templates(env=jinja2_env)

auth_settings = EoApiOpenIdConnectSettings()
settings = Settings(enable_response_models=True)  # type: ignore[ReportCallIssue]

# Logs
init_logging(service_name=settings.otel_service_name, debug=settings.debug)
logger = logging.getLogger(__name__)

application_extensions_map: dict[str, ApiExtension] = {
    "transaction": BackgroundTasksTransactionExtension(
        client=EoApiTransactionsClient(),
        settings=settings,
        response_class=ORJSONResponse,
    ),
    "bulk_transactions": BulkTransactionExtension(client=BulkTransactionsClient()),
}

search_extensions_map: dict[str, ApiExtension] = {
    "query": QueryExtension(),
    "sort": SortExtension(),
    "fields": FieldsExtension(),
    "filter": SearchFilterExtension(client=FiltersClient()),
    "pagination": TokenPaginationExtension(),
}

cs_extensions_map: dict[str, ApiExtension] = {
    "query": QueryExtension(conformance_classes=[QueryConformanceClasses.COLLECTIONS]),
    "sort": SortExtension(conformance_classes=[SortConformanceClasses.COLLECTIONS]),
    "fields": FieldsExtension(conformance_classes=[FieldsConformanceClasses.COLLECTIONS]),
    "filter": CollectionSearchFilterExtension(client=FiltersClient()),
    "free_text": FreeTextExtension(
        conformance_classes=[FreeTextConformanceClasses.COLLECTIONS],
    ),
    "pagination": OffsetPaginationExtension(),
    "ids": CollectionSearchIdsExtension(),
}

itm_col_extensions_map: dict[str, ApiExtension] = {
    "query": QueryExtension(
        conformance_classes=[QueryConformanceClasses.ITEMS],
    ),
    "sort": SortExtension(
        conformance_classes=[SortConformanceClasses.ITEMS],
    ),
    "fields": FieldsExtension(conformance_classes=[FieldsConformanceClasses.ITEMS]),
    "filter": ItemCollectionFilterExtension(client=FiltersClient()),
    "pagination": TokenPaginationExtension(),
}

known_extensions = {
    *application_extensions_map.keys(),
    *search_extensions_map.keys(),
    *cs_extensions_map.keys(),
    *itm_col_extensions_map.keys(),
    "collection_search",
}

enabled_extensions = (
    os.environ["ENABLED_EXTENSIONS"].split(",")
    if "ENABLED_EXTENSIONS" in os.environ
    else known_extensions
)

application_extensions = [
    extension for key, extension in application_extensions_map.items() if key in enabled_extensions
]

if settings.titiler_endpoint:
    application_extensions.append(TiTilerExtension(titiler_endpoint=settings.titiler_endpoint))


# /search models
search_extensions = [
    extension for key, extension in search_extensions_map.items() if key in enabled_extensions
]
post_request_model = create_post_request_model(
    search_extensions,
    base_model=PgstacSearch,  # type: ignore[reportArgumentType]
)
get_request_model = create_get_request_model(search_extensions)
application_extensions.extend(search_extensions)

# /collections/{collectionId}/items model
items_get_request_model = ItemCollectionUri  # pylint: disable=invalid-name
itm_col_extensions = [
    extension for key, extension in itm_col_extensions_map.items() if key in enabled_extensions
]
if itm_col_extensions:
    items_get_request_model = create_request_model(
        model_name="ItemCollectionUri",
        base_model=ItemCollectionUri,  # type: ignore[reportArgumentType]
        extensions=itm_col_extensions,
        request_type="GET",
    )
    application_extensions.extend(itm_col_extensions)

# /collections model
collections_get_request_model = EmptyRequest  # pylint: disable=invalid-name
if "collection_search" in enabled_extensions:
    cs_extensions = [
        extension for key, extension in cs_extensions_map.items() if key in enabled_extensions
    ]
    collection_search_extension = CollectionSearchExtension.from_extensions(cs_extensions)
    collections_get_request_model = collection_search_extension.GET
    application_extensions.append(collection_search_extension)


@asynccontextmanager
async def lifespan(app: FastAPI):  # pylint: disable=redefined-outer-name
    """FastAPI Lifespan."""
    await connect_to_db(app)

    if settings.redis_enabled:
        from eoapi.stac.redis import connect_to_redis  # pylint: disable=import-outside-toplevel

        await connect_to_redis(app)

    # add restrictions to endpoints
    if auth_settings.openid_configuration_url:
        logger.info("Add access restrictions to transaction endpoints")
        await lock_transaction_endpoints()
    yield

    await close_db_connection(app)


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
    app=update_openapi(
        FastAPI(
            lifespan=lifespan,
            openapi_url=settings.openapi_url,
            docs_url=settings.docs_url,
            redoc_url=None,
            swagger_ui_init_oauth={
                "clientId": auth_settings.client_id,
                "usePkceWithAuthorizationCodeGrant": auth_settings.use_pkce,
            },
            root_path=settings.root_path,
            title=settings.stac_fastapi_title,
            version=settings.stac_fastapi_version,
            description=settings.stac_fastapi_description,
            dependencies=[Depends(verify_scope_for_collection)],
        )
    ),
    settings=settings,
    extensions=application_extensions,
    client=EOCClient(pgstac_search_model=post_request_model),  # type: ignore
    response_class=ORJSONResponse,
    items_get_request_model=items_get_request_model,  # type: ignore[reportArgumentType]
    search_get_request_model=get_request_model,  # type: ignore[reportArgumentType]
    search_post_request_model=post_request_model,  # type: ignore[reportArgumentType]
    collections_get_request_model=collections_get_request_model,  # type: ignore[reportArgumentType]
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
    """Lock transaction endpoints."""
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
        import uvicorn  # pylint: disable=import-outside-toplevel

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
