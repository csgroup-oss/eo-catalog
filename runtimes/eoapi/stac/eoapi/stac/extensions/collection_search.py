# -*- coding: utf-8 -*-
# MIT License

# Copyright 2024, CS GROUP - France, https://www.csgroup.eu/

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
# SOFTWARE.
"""Collection-Search extension."""
import warnings
from typing import List, Optional

import attr
from stac_fastapi.api.models import create_request_model
from stac_fastapi.extensions.core import CollectionSearchExtension
from stac_fastapi.extensions.core.collection_search import ConformanceClasses
from stac_fastapi.extensions.core.collection_search.request import (
    BaseCollectionSearchGetRequest,
)
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.search import _ids_converter


@attr.s
class CollectionSearchGetRequest(BaseCollectionSearchGetRequest):
    """Override the basic Collection-Search GET request parameters for ids filter."""

    ids: Optional[List[str]] = attr.ib(default=None, converter=_ids_converter)  # type: ignore

@attr.s
class CollectionSearchExtensionWithIds(CollectionSearchExtension):
    """
    Extension of the CollectionSearchExtension which also allows filtering by ids
    """

    GET: CollectionSearchGetRequest = attr.ib(default=CollectionSearchGetRequest)

    @classmethod
    def from_extensions(
            cls,
            extensions: List[ApiExtension],
            schema_href: Optional[str] = None,
    ) -> "CollectionSearchExtensionWithIds":
        """Create CollectionSearchExtension object from extensions."""
        supported_extensions = {
            "FreeTextExtension": ConformanceClasses.FREETEXT,
            "FreeTextAdvancedExtension": ConformanceClasses.FREETEXT,
            "QueryExtension": ConformanceClasses.QUERY,
            "SortExtension": ConformanceClasses.SORT,
            "FieldsExtension": ConformanceClasses.FIELDS,
            "FilterExtension": ConformanceClasses.FILTER,
        }
        conformance_classes = [
            ConformanceClasses.COLLECTIONSEARCH,
            ConformanceClasses.BASIS,
        ]
        for ext in extensions:
            conf = supported_extensions.get(ext.__class__.__name__, None)
            if not conf:
                warnings.warn(
                    f"Conformance class for `{ext.__class__.__name__}` extension not found.",  # noqa: E501
                    UserWarning,
                )
            else:
                conformance_classes.append(conf)

        get_request_model = create_request_model(
            model_name="CollectionsGetRequest",
            base_model=CollectionSearchGetRequest,
            extensions=extensions,
            request_type="GET",
        )

        return cls(
            GET=get_request_model,
            conformance_classes=conformance_classes,
            schema_href=schema_href,
        )