# Copyright 2024, CS GROUP - France, https://www.csgroup.eu/
"""
timeout middleware from https://github.com/microsoft/planetary-computer-apis/blob/main/pccommon/pccommon/middleware.py.
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable

from fastapi.applications import FastAPI
from fastapi.dependencies.utils import (
    get_body_field,
    get_dependant,
    get_parameterless_sub_dependant,
)
from fastapi.routing import APIRoute, request_response
from starlette.responses import PlainTextResponse
from starlette.status import HTTP_504_GATEWAY_TIMEOUT

logger = logging.getLogger(__name__)


def with_timeout(
    timeout_seconds: float,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def with_timeout_(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):
            logger.debug("Adding timeout to function %s", func.__name__)

            @wraps(func)
            async def inner(*args: Any, **kwargs: Any) -> Any:
                start_time = time.monotonic()
                try:
                    return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
                except asyncio.TimeoutError as e:
                    process_time = time.monotonic() - start_time
                    # don't have a request object here to get custom dimensions.
                    log_dimensions = {
                        "request_time": process_time,
                    }
                    logger.exception(
                        f"Request timeout {e}",
                        extra=log_dimensions,
                    )

                    return PlainTextResponse(
                        "The request exceeded the maximum allowed time, please try again.",
                        status_code=HTTP_504_GATEWAY_TIMEOUT,
                    )

            return inner
        else:
            return func

    return with_timeout_


def add_timeout(app: FastAPI, timeout_seconds: float) -> None:
    for route in app.router.routes:
        if isinstance(route, APIRoute):
            new_endpoint = with_timeout(timeout_seconds)(route.endpoint)
            route.endpoint = new_endpoint
            route.dependant = get_dependant(path=route.path_format, call=route.endpoint)
            for depends in route.dependencies[::-1]:
                route.dependant.dependencies.insert(
                    0,
                    get_parameterless_sub_dependant(depends=depends, path=route.path_format),
                )
            route.body_field = get_body_field(
                flat_dependant=route.dependant, name=route.unique_id, embed_body_fields=True
            )
            route.app = request_response(route.get_route_handler())
