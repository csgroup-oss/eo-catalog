"""link helpers.

From https://github.com/stac-utils/stac-fastapi-pgstac/blob/60deedd3ec5f5c6ec552c624e1231cc14e0db35d/stac_fastapi/pgstac/models/links.py

Can be removed once collection pagination has been merged in STAC FastApi Pgstac.
"""

from typing import Any, Dict, Optional

import attr
from stac_fastapi.pgstac.models.links import BaseLinks, merge_params  # type: ignore
from stac_pydantic.links import Relations
from stac_pydantic.shared import MimeTypes


@attr.s
class CollectionSearchPagingLinks(BaseLinks):
    next: Optional[Dict[str, Any]] = attr.ib(kw_only=True, default=None)
    prev: Optional[Dict[str, Any]] = attr.ib(kw_only=True, default=None)

    def link_next(self) -> Optional[Dict[str, Any]]:
        """Create link for next page."""
        if self.next is not None:
            method = self.request.method
            if method == "GET":
                # if offset is equal to default value (0), drop it
                if self.next["body"].get("offset", -1) == 0:
                    _ = self.next["body"].pop("offset")

                href = merge_params(self.url, self.next["body"])

                # if next link is equal to this link, skip it
                if href == self.url:
                    return None

                return {
                    "rel": Relations.next.value,
                    "type": MimeTypes.geojson.value,
                    "method": method,
                    "href": href,
                }

        return None

    def link_prev(self) -> Optional[Dict[str, Any]]:
        if self.prev is not None:
            method = self.request.method
            if method == "GET":
                href = merge_params(self.url, self.prev["body"])

                # if prev link is equal to this link, skip it
                if href == self.url:
                    return None

                return {
                    "rel": Relations.previous.value,
                    "type": MimeTypes.geojson.value,
                    "method": method,
                    "href": href,
                }

        return None
