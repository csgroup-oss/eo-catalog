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
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI
from fastapi.responses import ORJSONResponse
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
from stac_fastapi.pgstac.transactions import BulkTransactionsClient, TransactionsClient
from stac_fastapi.pgstac.types.search import PgstacSearch
from stac_fastapi.types.extension import ApiExtension
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from starlette_cramjam.middleware import CompressionMiddleware

from eoapi.stac.auth import (
    AuthSettings,
    init_oidc_auth,
    verify_scope_for_collection,
)
from eoapi.stac.config import Settings
from eoapi.stac.core import EOCClient
from eoapi.stac.extensions.collection_search import CollectionSearchExtensionWithIds
from eoapi.stac.extensions.filter import FiltersClient
from eoapi.stac.extensions.titiller import TiTilerExtension
from eoapi.stac.logs import init_logging
from eoapi.stac.middlewares.timeout import add_timeout

try:
    from importlib.resources import files as resources_files  # type: ignore
except ImportError:
    # Try backported to PY<39 `importlib_resources`.
    from importlib_resources import files as resources_files  # type: ignore

templates = Jinja2Templates(directory=str(resources_files(__package__) / "templates"))

settings = Settings()
auth_settings = AuthSettings(_env_prefix="AUTH_")

# Logs
init_logging(service_name=settings.otel_service_name, debug=settings.debug)
logger = logging.getLogger(__name__)

extensions_map: Dict[str, Optional[ApiExtension]] = {
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

# some extensions are supported in combination with the collection search extension
collection_extensions_map: Dict[str, ApiExtension] = {
    "query": QueryExtension(),
    "sort": SortExtension(),
    "fields": FieldsExtension(),
    "filter": FilterExtension(client=FiltersClient()),
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

swagger_ui_init_oauth: Optional[Dict[str, Any]] = (
    {
        "clientId": auth_settings.client_id,
        "usePkceWithAuthorizationCodeGrant": auth_settings.use_pkce,
    }
    if auth_settings.openid_configuration_url
    else None
)

api = StacApi(
    app=FastAPI(
        lifespan=lifespan,
        openapi_url=settings.openapi_url,
        docs_url=settings.docs_url,
        redoc_url=None,
        swagger_ui_init_oauth=swagger_ui_init_oauth,
        root_path=settings.app_root_path,
        dependencies=[Depends(verify_scope_for_collection)],
    ),
    settings=settings,
    extensions=extensions,
    client=EOCClient(post_request_model=post_request_model),
    items_get_request_model=items_get_request_model,
    search_get_request_model=get_request_model,
    search_post_request_model=post_request_model,
    collections_get_request_model=collections_get_request_model,
    response_class=ORJSONResponse,
    middlewares=middlewares,
)
app = api.app

init_oidc_auth(app, auth_settings)
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
