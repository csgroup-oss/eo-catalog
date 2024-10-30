# Copyright 2024, CS GROUP - France, https://www.csgroup.eu/
"""Logging configuration.
Adapted from https://github.com/microsoft/planetary-computer-apis/blob/main/pccommon/pccommon/logging.py.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union, cast

from eoapi.stac.constants import (
    HTTP_METHOD,
    HTTP_PATH,
    HTTP_URL,
    QS_REQUEST_ENTITY,
    X_REQUEST_ENTITY,
)
from eoapi.stac.utils import request_to_path

if TYPE_CHECKING:
    from fastapi import Request


# Custom filter that outputs custom_dimensions, only if present
class OptionalCustomDimensionsFilter(logging.Formatter):
    def __init__(
        self,
        message_fmt: Optional[str],
        dt_fmt: Optional[str],
        service_name: Optional[str],
    ):
        logging.Formatter.__init__(self, message_fmt, dt_fmt)
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        if "custom_dimensions" not in record.__dict__:
            record.__dict__["custom_dimensions"] = ""
        else:
            # Add the service name to custom_dimensions, so it's queryable
            record.__dict__["custom_dimensions"]["service"] = self.service_name
        return super().format(record)


# Log filter for targeted messages (containing custom_dimensions)
class CustomDimensionsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return bool(record.__dict__["custom_dimensions"])


# Prevent successful health check pings from being logged
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not record.args or len(record.args) != 5:
            return True

        args = cast(Tuple[str, str, str, str, int], record.args)
        endpoint = args[2]
        status = args[4]
        if endpoint == "/_mgmt/ping" and status == 200:
            return False

        return True


# Initialize logging, including a console handler, and sending all logs containing
# custom_dimensions to Application Insights
def init_logging(service_name: str, debug: bool = False) -> None:
    # Exclude health check endpoint pings from the uvicorn logs
    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

    logger = logging.getLogger("eo_catalog.stac")
    logger.setLevel(logging.INFO)

    # Console log handler that includes custom dimensions
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(logging.DEBUG)
    formatter = OptionalCustomDimensionsFilter(
        "[%(levelname)s] %(asctime)s - %(message)s %(custom_dimensions)s",
        None,
        service_name,
    )
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

    if debug:
        logger.setLevel(logging.DEBUG)


def get_request_entity(request: Request) -> Union[str, None]:
    """Get the request entity from the given request. If not present as a
    header, attempt to parse from the query string
    """
    return request.headers.get(X_REQUEST_ENTITY) or request.query_params.get(QS_REQUEST_ENTITY)


def get_custom_dimensions(dimensions: Dict[str, Any], request: Request) -> dict[str, dict[str, Any]]:
    """Merge the base dimensions with the given dimensions."""
    settings = request.app.state.settings

    base_dimensions = {
        "request_entity": get_request_entity(request),
        "service": settings.otel_service_name,
        HTTP_URL: str(request.url),
        HTTP_METHOD: str(request.method),
        HTTP_PATH: request_to_path(request),
    }
    base_dimensions.update(dimensions)
    return {"custom_dimensions": base_dimensions}
