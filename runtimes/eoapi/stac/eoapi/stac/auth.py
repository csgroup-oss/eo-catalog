from typing import Optional, Sequence, List

import jwt
from eoapi.auth_utils import OpenIdConnectAuth
from fastapi import HTTPException
from pydantic import AnyHttpUrl

from pydantic_settings import BaseSettings  # type:ignore
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


def oidc_auth_from_settings(cls, settings: EoApiOpenIdConnectSettings) -> OpenIdConnectAuth:
    return OpenIdConnectAuth(**settings.model_dump(include=cls.__dataclass_fields__.keys()))


def get_user_scopes_from_request(request: Request, oidc_auth: OpenIdConnectAuth) -> List[str]:
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