# Copyright (c) 2024, CS GROUP - France, https://cs-soprasteria.com

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

import asyncio
import logging
import os
import httpx
from typing import Optional, Union, Any, Dict

from stac_fastapi.pgstac.db import dbfunc
from stac_fastapi.pgstac.models.links import CollectionLinks, ItemLinks
from stac_fastapi.pgstac.transactions import TransactionsClient
from stac_fastapi.types import stac as stac_types
from stac_pydantic import Collection, Item
from starlette.requests import Request
from starlette.responses import Response
from starlette.background import BackgroundTasks
from pydantic import BaseModel

from eoapi.stac.auth import CollectionsScopes
from eoapi.stac.config import Settings
from eoapi.stac.constants import CACHE_KEY_COLLECTIONS
from eoapi.stac.utils import fetch_all_collections_with_scopes

logger = logging.getLogger(__name__)


class WebhookPayload(BaseModel):
    """Webhook payload structure."""
    event_type: str  # "insert" or "update"
    status: str  # "success" or "failed"
    collection_id: str
    item_id: str
    item_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


async def _update_collection_scopes(request: Request):
    """
    updates the cached collection scopes in memory and possibly also in redis (depending on app settings)
    Args:
        request: starlette request used to check the app settings
    """
    settings: Settings = request.app.state.settings
    if settings.redis_enabled:
        r = request.app.state.redis
        r.delete(f"{CACHE_KEY_COLLECTIONS}_all")
    collections = await fetch_all_collections_with_scopes(request)
    CollectionsScopes(collections, settings.eoapi_auth_metadata_field).set_scopes_for_collections()


async def send_webhook(webhook_url: str, payload: WebhookPayload) -> None:
    """Send webhook notification as a background task.
    Args:
        webhook_url: The URL to send the webhook to
        payload: The webhook payload
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload.model_dump(),
                timeout=30.0
            )
            response.raise_for_status()
            logger.info(f"Webhook sent successfully to {webhook_url} for {payload.event_type} {payload.item_id}")
    except httpx.HTTPError as e:
        logger.error(f"Failed to send webhook to {webhook_url}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error sending webhook: {str(e)}")


class EoApiTransactionsClient(TransactionsClient):
    def __init__(self):
        super().__init__()
        self.webhook_url = os.getenv("ANTFLOW_WEBHOOK_URL")
        if self.webhook_url:
            logger.info(f"Webhook URL configured: {self.webhook_url}")
        else:
            logger.warning("No webhook URL configured. Set ANTFLOW_WEBHOOK_URL to enable webhooks.")

    async def create_collection(
        self,
        collection: Collection,
        request: Request,
        **kwargs,
    ) -> Optional[Union[stac_types.Collection, Response]]:
        """Create collection; called with POST /collections
        overwrites create_collection from stac_fastapi to ensure that cached scopes are updated
        """
        collection = collection.model_dump(mode="json")

        self._validate_collection(request, collection)

        async with request.app.state.get_connection(request, "w") as conn:
            await dbfunc(conn, "create_collection", collection)

        collection["links"] = await CollectionLinks(
            collection_id=collection["id"], request=request
        ).get_links(extra_links=collection["links"])

        await _update_collection_scopes(request)

        return stac_types.Collection(**collection)

    async def update_collection(
        self,
        collection: Collection,
        request: Request,
        **kwargs,
    ) -> Optional[Union[stac_types.Collection, Response]]:
        """Update collection; called with PUT /collections
        overwrites update_collection from stac_fastapi to ensure that cached scopes are updated
        """

        col = collection.model_dump(mode="json")

        async with request.app.state.get_connection(request, "w") as conn:
            await dbfunc(conn, "update_collection", col)

        col["links"] = await CollectionLinks(collection_id=col["id"], request=request).get_links(
            extra_links=col.get("links")
        )

        await _update_collection_scopes(request)

        return stac_types.Collection(**col)

    async def create_item(
        self,
        item: Item,
        request: Request,
        **kwargs,
    ) -> Optional[Union[stac_types.Item, Response]]:
        """Create item; called with POST /collections/{collection_id}/items
        overwrites create_item from stac_fastapi to add webhook support
        """
        collection_id = request.path_params.get("collection_id")
        item_dict = item.model_dump(mode="json")
        item_id = item_dict.get("id")

        webhook_payload = None
        status = "failed"
        error_message = None

        try:
            """Remove collection_id from kwargs if present to avoid conflict
            error: TransactionsClient.create_item() got multiple values for argument 'collection_id'
            """
            kwargs_filtered = {k: v for k, v in kwargs.items() if k != 'collection_id'}
            result = await super().create_item(collection_id, item, request, **kwargs_filtered)

            if result:
                status = "success"
                """Handle both dict and Pydantic model results
                error: AttributeError: 'dict' object has no attribute 'model_dump
                """
                if hasattr(result, 'model_dump'):
                    item_dict = result.model_dump()
                else:
                    item_dict = result

                item_dict["links"] = await ItemLinks(
                    collection_id=collection_id,
                    item_id=item_id,
                    request=request,
                ).get_links(extra_links=item_dict.get("links"))

            return result

        except Exception as e:
            logger.error(f"Error creating item {item_id} in collection {collection_id}: {str(e)}")
            error_message = str(e)
            raise

        finally:
            if self.webhook_url and collection_id and item_id:
                webhook_payload = WebhookPayload(
                    event_type="insert",
                    status=status,
                    collection_id=collection_id,
                    item_id=item_id,
                    item_data=item_dict if status == "success" else None,
                    error=error_message
                )

                background_tasks = BackgroundTasks()
                background_tasks.add_task(send_webhook, self.webhook_url, webhook_payload)

                asyncio.create_task(background_tasks())

    async def update_item(
        self,
        item: Item,
        request: Request,
        **kwargs,
    ) -> Optional[Union[stac_types.Item, Response]]:
        """Update item; called with PUT /collections/{collection_id}/items/{item_id}
        overwrites update_item from stac_fastapi to add webhook support
        """
        collection_id = request.path_params.get("collection_id")
        item_id = request.path_params.get("item_id")
        item_dict = item.model_dump(mode="json")

        webhook_payload = None
        status = "failed"
        error_message = None

        try:
            kwargs_filtered = {k: v for k, v in kwargs.items() if k not in ['collection_id', 'item_id']}
            result = await super().update_item(request, collection_id, item_id, item, **kwargs_filtered)

            if result:
                status = "success"
                if hasattr(result, 'model_dump'):
                    item_dict = result.model_dump()
                else:
                    item_dict = result

                item_dict["links"] = await ItemLinks(
                    collection_id=collection_id,
                    item_id=item_id,
                    request=request,
                ).get_links(extra_links=item_dict.get("links"))

            return result

        except Exception as e:
            logger.error(f"Error updating item {item_id} in collection {collection_id}: {str(e)}")
            error_message = str(e)
            raise

        finally:
            if self.webhook_url and collection_id and item_id:
                webhook_payload = WebhookPayload(
                    event_type="update",
                    status=status,
                    collection_id=collection_id,
                    item_id=item_id,
                    item_data=item_dict if status == "success" else None,
                    error=error_message
                )

                background_tasks = BackgroundTasks()
                background_tasks.add_task(send_webhook, self.webhook_url, webhook_payload)

                asyncio.create_task(background_tasks())
