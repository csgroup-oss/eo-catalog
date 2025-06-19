"""Transaction extension."""

import attr
from fastapi import BackgroundTasks
from stac_pydantic import Item
from stac_pydantic.shared import MimeTypes

from stac_fastapi.api.routes import create_async_endpoint
from stac_fastapi.extensions.core import TransactionExtension
from stac_fastapi.extensions.core.transaction import PostItem, PutItem



@attr.s
class PostItemWithBackgroundTasks(PostItem):
    """Create Item with BackgroundTasks."""

    background_tasks: BackgroundTasks = attr.ib(default=None)


@attr.s
class PutItemWithBackgroundTasks(PutItem):
    """Update Item with BackgroundTasks."""

    background_tasks: BackgroundTasks = attr.ib(default=None)


class BackgroundTasksTransactionExtension(TransactionExtension):
    """Transaction Extension.

    The transaction extension adds several endpoints which allow the creation,
    and updating of items and collections:
        POST /collections/{collection_id}/items
        PUT /collections/{collection_id}/items

    https://github.com/stac-api-extensions/transaction
    https://github.com/stac-api-extensions/collection-transaction

    Attributes:
        client: CRUD application logic

    """

    def register_create_item(self):
        """Register create item endpoint with BackgroundTasks (POST /collections/{collection_id}/items)."""
        self.router.add_api_route(
            name="Create Item",
            path="/collections/{collection_id}/items",
            status_code=201,
            response_model=Item if self.settings.enable_response_models else None,
            responses={
                201: {
                    "content": {
                        MimeTypes.geojson.value: {},
                    },
                    "model": Item,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["POST"],
            endpoint=create_async_endpoint(self.client.create_item, PostItemWithBackgroundTasks),
        )

    def register_update_item(self):
        """Register update item endpoint with BackgroundTasks (PUT
        /collections/{collection_id}/items/{item_id})."""
        self.router.add_api_route(
            name="Update Item",
            path="/collections/{collection_id}/items/{item_id}",
            response_model=Item if self.settings.enable_response_models else None,
            responses={
                200: {
                    "content": {
                        MimeTypes.geojson.value: {},
                    },
                    "model": Item,
                }
            },
            response_class=self.response_class,
            response_model_exclude_unset=True,
            response_model_exclude_none=True,
            methods=["PUT"],
            endpoint=create_async_endpoint(self.client.update_item, PutItemWithBackgroundTasks),
        )
