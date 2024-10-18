import logging
from typing import List

import jwt
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from starlette import status
from starlette.requests import Request

from eoapi.auth_utils import OpenIdConnectAuth, OpenIdConnectSettings
from eoapi.stac.utils import all_collections_scopes

logger = logging.getLogger()


class AuthSettings(OpenIdConnectSettings):
    metadata_field: str = "scope"
    update_scope: str = "admin"


def init_oidc_auth(app: FastAPI, auth_settings: AuthSettings) -> None:
    """Initialize Openid Connect authentication."""
    if not auth_settings.openid_configuration_url:
        return

    oidc_auth = OpenIdConnectAuth.from_settings(auth_settings)

    # Lock transaction extension here.
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
    ]
    api_routes = {
        route.path: route for route in app.routes if isinstance(route, APIRoute)
    }
    for method, scope, endpoint in restricted_routes:
        route = api_routes.get(endpoint)
        if route and method in route.methods:
            oidc_auth.apply_auth_dependencies(route, required_token_scopes=[scope])

    logger.info(
        f"Authentication enabled using {auth_settings.openid_configuration_url=}"
        f" {auth_settings.client_id=} {auth_settings.update_scope=}."
    )

    app.state.oidc_auth = oidc_auth
    app.state.auth_settings = auth_settings


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


async def verify_scope_for_collection(request: Request, collection_id: str = ""):
    """
    checks if the user scopes from the request contain the scope necessary to access the collection with the given id
    Args:
        request: the scopes will be retrieved from the token in the headers of the starlette request
        collection_id: id of the collection for which the scope should be checked
    Raises:
        HTTPException if the token in the request header does not contain the necessary scope
    """
    auth_settings = getattr(request.app.state, "auth_settings")

    if not collection_id or not auth_settings:
        return

    scopes = get_user_scopes_from_request(request)
    collections = await all_collections_scopes(request)

    collection = next(
        (c for c in collections["collections"] if c["id"] == collection_id), None
    )

    if not collection:
        return

    col_scope = collection.get(auth_settings.metadata_field)
    if col_scope not in scopes:
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
    auth_settings: AuthSettings = request.app.state.auth_settings

    scopes = get_user_scopes_from_request(request)
    collections = await all_collections_scopes(request)

    collections_with_scope: List[str] = []
    for collection in collections["collections"]:
        col_scope = collection.get(auth_settings.metadata_field)
        if not col_scope or col_scope in scopes:
            collections_with_scope.append(collection["id"])
    return collections_with_scope
