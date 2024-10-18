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
from typing import List, Optional, Type, Union

import attr
from pydantic import BaseModel, create_model
from stac_fastapi.extensions.core import CollectionSearchExtension
from stac_fastapi.extensions.core.collection_search import ConformanceClasses
from stac_fastapi.extensions.core.collection_search.request import (
    BaseCollectionSearchGetRequest,
)
from stac_fastapi.types.extension import ApiExtension
from stac_fastapi.types.search import APIRequest, BaseSearchGetRequest, _ids_converter


@attr.s
class CollectionSearchGetRequest(BaseCollectionSearchGetRequest):
    """Override the basic Collection-Search GET request parameters for ids filter."""

    ids: Optional[List[str]] = attr.ib(default=None, converter=_ids_converter)  # type: ignore


def _create_request_model(
    model_name="SearchGetRequest",
    base_model: Union[Type[BaseModel], Type[APIRequest]] = BaseSearchGetRequest,
    extensions: Optional[List[ApiExtension]] = None,
    mixins: Optional[Union[List[BaseModel], List[APIRequest]]] = None,
    request_type: Optional[str] = "GET",
) -> Union[Type[BaseModel], Type[APIRequest], type]:
    """Create a pydantic model for validating request bodies.
    use this method instead of create_request_model from stac_fastapi to avoid type errors"""
    fields = {}
    extension_models = []

    # Check extensions for additional parameters to search
    for extension in extensions or []:
        if extension_model := extension.get_request_model(request_type):
            extension_models.append(extension_model)

    mixins = mixins or []

    models = [base_model] + extension_models + mixins

    # Handle GET requests
    if all([issubclass(m, APIRequest) for m in models]):
        return attr.make_class(model_name, attrs={}, bases=tuple(models))

    # Handle POST requests
    elif all([issubclass(m, BaseModel) for m in models]):
        for model in models:
            for k, field_info in model.model_fields.items():
                fields[k] = (field_info.annotation, field_info)
        return create_model(model_name, **fields, __base__=base_model)

    raise TypeError("Mixed Request Model types. Check extension request types.")


@attr.s
class CollectionSearchExtensionWithIds(CollectionSearchExtension):
    """
    Extension of the CollectionSearchExtension which also allows filtering by ids
    """

    GET: type[APIRequest] = attr.ib(default=CollectionSearchGetRequest)
    conformance_classes: List[str] = attr.ib(
        default=[ConformanceClasses.COLLECTIONSEARCH, ConformanceClasses.BASIS]
    )
    schema_href: Optional[str] = attr.ib(default=None)

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

        get_request_model = _create_request_model(
            model_name="CollectionsGetRequest",
            base_model=BaseSearchGetRequest,
            extensions=extensions,
            request_type="GET",
        )

        return cls(
            GET=get_request_model,
            conformance_classes=conformance_classes,
            schema_href=schema_href,
        )
