from typing import Optional, Sequence, List

import jwt
from eoapi.auth_utils import OpenIdConnectAuth
from fastapi import HTTPException
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings
from stac_fastapi.types.stac import Collections
from starlette import status
from starlette.requests import Request


class EoApiOpenIdConnectSettings(BaseSettings):
    # Swagger UI config for Authorization Code Flow
    client_id: str = ""
    use_pkce: bool = True
    openid_configuration_url: Optional[AnyHttpUrl] = None
    openid_configuration_internal_url: Optional[AnyHttpUrl] = None

    allowed_jwt_audiences: Optional[Sequence[str]] = []

    model_config = {
        "env_prefix": "EOAPI_AUTH_",
        "env_file": ".env",
        "extra": "allow",
    }

class CollectionsScopes:

    collection_scopes = {}

    def __init__(self, collections: Collections, scope_var: str):
        self.collections = collections
        self.scope_var = scope_var
        self.set_scopes_for_collections()

    def set_scopes_for_collections(self):
        """
        fills the class variable collection_scopes with the scopes given in self.collections using the variable self.scope_var
        to find the scope in the collection metadata
        """
        scopes = {}
        for collection in self.collections["collections"]:
            if self.scope_var in collection:
                scopes[collection["id"]] = collection[self.scope_var]
            else:
                scopes[collection["id"]] = None
        CollectionsScopes.collection_scopes = scopes


def oidc_auth_from_settings(cls, settings: EoApiOpenIdConnectSettings) -> OpenIdConnectAuth:
    """
    creates an OpenIdConnectAuth object from the given settings
    Args:
        cls: class of the auth object to be created
        settings: open id connect settings to be used

    Returns:
        OpenIdConnectAuth object
    """
    return OpenIdConnectAuth(**settings.model_dump(include=cls.__dataclass_fields__.keys()))


def get_user_scopes_from_request(request: Request, oidc_auth: OpenIdConnectAuth) -> List[str]:
    """
    retrieves the scopes of the user based on the given request
    Args:
        request: the scopes will be retrieved from the token in the headers of the starlette request
        oidc_auth: authentication object from which the signing key and the allowed audiences are retrieved

    Returns:
        List of the user scopes

    Raises:
        HTTPException if the token cannot be decoded or is invalid
    """
    if not "Authorization" in request.headers:
        return []
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


def verify_scope_for_collection(request: Request, collection_id: str, oidc_auth: OpenIdConnectAuth):
    """
    checks if the user scopes from the request contain the scope necessary to access the collection with the given id
    Args:
        request: the scopes will be retrieved from the token in the headers of the starlette request
        collection_id: id of the collection for which the scope should be checked
        oidc_auth: authentication object from which the signing key and the allowed audiences are retrieved
    Raises:
        HTTPException if the token in the request header does not contain the necessary scope
    """
    scopes = get_user_scopes_from_request(request, oidc_auth)
    collection_scopes = CollectionsScopes.collection_scopes
    if collection_id in collection_scopes and collection_scopes[collection_id]:
        required_scope = collection_scopes[collection_id]
        if not required_scope in scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access to collection {collection_id} not allowed")


def get_collections_for_user_scope(request: Request, oidc_auth: OpenIdConnectAuth) -> List[str]:
    """
    returns the collections which can be accessed with the user scopes from the authorization token of the given request
    Args:
        request: the scopes will be retrieved from the token in the headers of the starlette request
        oidc_auth: authentication object from which the signing key and the allowed audiences are retrieved

    Returns:
        a list of the ids of the collections the user is allowed to access
    """
    scopes = get_user_scopes_from_request(request, oidc_auth)
    collection_scopes = CollectionsScopes.collection_scopes
    collections_with_scope = []
    for collection_id, scope in collection_scopes.items():
        if not scope or scope in scopes:
            collections_with_scope.append(collection_id)
    return collections_with_scope

