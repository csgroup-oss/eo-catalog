# Copyright 2024, CS GROUP - France, https://www.csgroup.eu/
"""
Caching with Redis.
Adapted from
https://github.com/microsoft/planetary-computer-apis/blob/main/pccommon/pccommon/redis.py.
"""

from __future__ import annotations

import logging
import time
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    Literal,
    TypedDict,
    TypeVar,
    Union,
)

import orjson
from fastapi import FastAPI, Request
from redis.asyncio import Redis as RedisClient  # type: ignore
from redis.asyncio import RedisCluster
from stac_fastapi.pgstac.types.base_item_cache import BaseItemCache

from eoapi.stac.constants import CACHE_KEY_BASE_ITEM
from eoapi.stac.logs import get_custom_dimensions  # Assuming you keep using your logging setup

Redis = Union[RedisCluster, RedisClient]

if TYPE_CHECKING:
    from eoapi.stac.config import Settings

logger = logging.getLogger(__name__)


class RedisParams(TypedDict):
    """Redis params"""

    host: str
    password: str
    port: int
    ssl: bool
    decode_responses: Literal[True]


T = TypeVar("T")


async def connect_to_redis(app: FastAPI) -> None:
    """Connect to redis and store instance and script hashes in app state."""
    settings: Settings = app.state.settings

    settings.base_item_cache = RedisBaseItemCache

    redis_params: RedisParams = {
        "host": settings.redis_hostname or "localhost",  # Ensure default to "localhost"
        "password": settings.redis_password,
        "port": settings.redis_port,  # Corrected to use the port setting
        "ssl": settings.redis_ssl,
        "decode_responses": True,
    }

    if settings.redis_cluster:
        app.state.redis = RedisCluster(**redis_params, read_from_replicas=True)
    else:
        app.state.redis = RedisClient(**redis_params)

    logger.info("Connected to Redis on %s:%s", settings.redis_hostname, settings.redis_port)


async def cached_result(
    fn: Callable[..., Coroutine[Any, Any, T]],
    cache_key: str,
    request: Request,
) -> T:
    """Either get the result from redis or run the function and cache the result."""
    settings: Settings = request.app.state.settings
    r: Redis

    # GET key from cache
    try:
        r = request.app.state.redis
        if r:
            ts = time.perf_counter()
            cached: str = await r.get(cache_key)  # type: ignore
            te = time.perf_counter()
            if cached:
                logger.debug(
                    "GET cache: found key",
                    extra=get_custom_dimensions(
                        {
                            "cache_key": cache_key,
                            "duration_ms": f"{(te - ts) * 1000:.0f}",
                        },
                        request,
                    ),
                )
                return orjson.loads(cached)  # pylint: disable=no-member
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Don't fail on redis failure
        logger.error(
            "GET cache: %s",
            e,
            extra=get_custom_dimensions({"cache_key": cache_key}, request),
        )
        if settings.debug:
            raise

    ts = time.perf_counter()
    result = await fn()
    te = time.perf_counter()
    logger.debug(
        "perf: cacheable resource fetch time",
        extra=get_custom_dimensions(
            {"cache_key": cache_key, "duration_ms": f"{(te - ts) * 1000:.0f}"},
            request,
        ),
    )

    # SET key in cache
    try:
        r = request.app.state.redis
        await r.set(
            cache_key,
            orjson.dumps(result),  # pylint: disable=no-member
            settings.redis_ttl,
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Don't fail on redis failure
        logger.error(
            "SET cache: %s",
            e,
            extra=get_custom_dimensions({"cache_key": cache_key}, request),
        )
        if settings.debug:
            raise

    return result


class RedisBaseItemCache(BaseItemCache):
    """
    Return the base item for the collection and cache by collection id.
    First check if the instance has a local cache of the base item, then
    try redis, and finally fetch from the database.
    """

    def __init__(
        self,
        fetch_base_item: Callable[[str], Coroutine[Any, Any, Dict[str, Any]]],
        request: Request,
    ):
        self._base_items: Dict[str, Any] = {}
        super().__init__(fetch_base_item, request)

    async def get(self, collection_id: str) -> Dict[str, Any]:
        async def _fetch() -> Dict[str, Any]:
            return await self._fetch_base_item(collection_id)

        if collection_id not in self._base_items:
            cache_key = f"{CACHE_KEY_BASE_ITEM}:{collection_id}"
            self._base_items[collection_id] = await cached_result(_fetch, cache_key, self._request)

        return self._base_items[collection_id]
