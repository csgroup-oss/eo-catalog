from typing import Optional, Sequence

from eoapi.auth_utils import OpenIdConnectAuth
from pydantic import AnyHttpUrl

from pydantic_settings import BaseSettings  # type:ignore


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