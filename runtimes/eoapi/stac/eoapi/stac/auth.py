import json
import logging
import urllib.request
from typing import Annotated, Any, Callable, List, Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, security
from fastapi.routing import APIRoute
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings
from starlette import status
from starlette.requests import Request

from eoapi.auth_utils import OpenIdConnectAuth
from eoapi.auth_utils.errors import OidcFetchError
from eoapi.stac.utils import all_collections_scopes

logger = logging.getLogger()


class OpenIdConnectSettings(BaseSettings):
    # Custom class instead of eoapi.auth_utils one because they use pydantic v1 instead of v2.
    # Swagger UI config for Authorization Code Flow
    client_id: str = ""
    use_pkce: bool = True
    openid_configuration_url: Optional[AnyHttpUrl] = None
    openid_configuration_internal_url: Optional[AnyHttpUrl] = None

    allowed_jwt_audiences: str = ""

    model_config = {
        "env_prefix": "EOAPI_AUTH_",
        "env_file": ".env",
        "extra": "allow",
    }

    metadata_field: str = "scope"
    update_scope: str = "eo_catalog.admin"

    @field_validator("allowed_jwt_audiences")
    def parse_audiences(cls, v: str):
        """Parse CORS methods."""
        return [aud.strip() for aud in v.split(",")]


class OptionalOpenIdConnectAuth(OpenIdConnectAuth):
    """Override OpenIdConnectAuth for optional authentication.
    For that we need to set auto_error=False
    """

    def __post_init__(self):
        logger.debug("Requesting OIDC config")
        with urllib.request.urlopen(
            str(self.openid_configuration_internal_url or self.openid_configuration_url)
        ) as response:
            if response.status != 200:
                logger.error(
                    "Received a non-200 response when fetching OIDC config: %s",
                    response.text,
                )
                raise OidcFetchError(
                    f"Request for OIDC config failed with status {response.status}"
                )
            oidc_config = json.load(response)
            self.jwks_client = jwt.PyJWKClient(oidc_config["jwks_uri"])

        self.auth_scheme = security.OpenIdConnect(
            openIdConnectUrl=str(self.openid_configuration_url), auto_error=False
        )
        self.valid_token_dependency = self.create_auth_token_dependency(
            auth_scheme=self.auth_scheme,
            jwks_client=self.jwks_client,
            allowed_jwt_audiences=self.allowed_jwt_audiences,
        )


def init_oidc_auth(app: FastAPI, auth_settings: OpenIdConnectSettings) -> None:
    """Initialize OpenID Connect authentication."""
    if not auth_settings.openid_configuration_url:
        return

    # Helper function to apply authentication dependencies to routes
    def apply_auth_to_route(
        auth: OpenIdConnectAuth,
        method: str,
        endpoint: str,
        scope: Optional[str] = None,
        dependency_func: Optional[Callable[..., Any]] = None,
    ):
        route = next(
            (
                r
                for r in app.routes
                if isinstance(r, APIRoute)
                and r.path == endpoint
                and method in r.methods
            ),
            None,
        )
        if not route:
            logger.warning(f"Cannot lock: {method} {endpoint} not found.")
            return

        if dependency_func:
            auth.apply_auth_dependencies(route, dependency=dependency_func)
        elif scope:
            auth.apply_auth_dependencies(route, required_token_scopes=[scope])

    oidc_auth = OpenIdConnectAuth.from_settings(auth_settings)
    opt_oidc_auth = OptionalOpenIdConnectAuth.from_settings(auth_settings)

    # Restricted routes requiring token scopes
    restricted_routes = [
        ("POST", auth_settings.update_scope, "/collections"),
        ("PUT", auth_settings.update_scope, "/collections/{collection_id}"),
        ("DELETE", auth_settings.update_scope, "/collections/{collection_id}"),
        ("POST", auth_settings.update_scope, "/collections/{collection_id}/items"),
        (
            "PUT",
            auth_settings.update_scope,
            "/collections/{collection_id}/items/{item_id}",
        ),
        (
            "DELETE",
            auth_settings.update_scope,
            "/collections/{collection_id}/items/{item_id}",
        ),
        ("POST", auth_settings.update_scope, "/collections/{collection_id}/bulk_items"),
    ]
    for method, scope, endpoint in restricted_routes:
        apply_auth_to_route(oidc_auth, method, endpoint, scope)

    # Optional routes for collections endpoints
    collection_routes = [
        ("GET", "/collections/{collection_id}"),
        ("GET", "/collections/{collection_id}/items"),
        ("GET", "/collections/{collection_id}/items/{item_id}"),
    ]
    for method, endpoint in collection_routes:
        apply_auth_to_route(
            opt_oidc_auth,
            method,
            endpoint,
            dependency_func=verify_scope_for_collection,
        )

    # Set app state
    app.state.oidc_auth = oidc_auth
    app.state.auth_settings = auth_settings

    logger.info(
        f"Authentication enabled using {auth_settings.openid_configuration_url=}, "
        f"{auth_settings.client_id=}, {auth_settings.update_scope=}."
    )


def get_user_scopes_from_request(request: Request) -> List[str]:
    """
    retrieves the scopes of the user based on the given request
    Args:
        request: the scopes will be retrieved from the token in the headers of the starlette request
    Returns:
        List of the user scopes

    Raises:
        HTTPException if the token cannot be decoded or is invalid
    """
    if "Authorization" not in request.headers:
        return []

    oidc_auth: OpenIdConnectAuth = request.app.state.oidc_auth

    token = request.headers["Authorization"].replace("Bearer ", "")
    try:
        key = oidc_auth.jwks_client.get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            # NOTE: Audience validation MUST match audience claim if set in token (https://pyjwt.readthedocs.io/en/stable/changelog.html?highlight=audience#id40)
            audience=oidc_auth.allowed_jwt_audiences,
        )
    except (jwt.exceptions.InvalidTokenError, jwt.exceptions.DecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    return payload["scope"].split()


async def verify_scope_for_collection(
    request: Request,
    collection_id: str,
    scopes: Annotated[List[str], Depends(get_user_scopes_from_request)],
):
    """
    checks if the user scopes from the request contain the scope necessary to access the collection with the given id
    Args:
        request: the scopes will be retrieved from the token in the headers of the starlette request
        collection_id: id of the collection for which the scope should be checked
    Raises:
        HTTPException if the token in the request header does not contain the necessary scope
    """
    auth_settings = request.app.state.auth_settings

    collections = await all_collections_scopes(request)

    collection = next(
        (c for c in collections["collections"] if c["id"] == collection_id), None
    )

    if not collection:
        return

    col_scope = collection.get(auth_settings.metadata_field)
    if col_scope and col_scope not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to collection {collection_id} is forbidden.",
        )


async def get_collections_for_user_scope(request: Request) -> List[str]:
    """
    returns the collections which can be accessed with the user scopes from the authorization token of the given request
    Args:
        request: the scopes will be retrieved from the token in the headers of the starlette request

    Returns:
        a list of the ids of the collections the user is allowed to access
    """
    auth_settings: OpenIdConnectSettings = request.app.state.auth_settings

    scopes = get_user_scopes_from_request(request)
    collections = await all_collections_scopes(request)

    collections_with_scope: List[str] = []
    for collection in collections["collections"]:
        col_scope = collection.get(auth_settings.metadata_field)
        if not col_scope or col_scope in scopes:
            collections_with_scope.append(collection["id"])
    return collections_with_scope
