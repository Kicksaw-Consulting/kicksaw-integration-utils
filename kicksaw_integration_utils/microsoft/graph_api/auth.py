import datetime
import json

from abc import ABC, abstractmethod
from typing import Literal, Optional

import requests

from pydantic import BaseModel, Field, SecretStr


# Properties shared by both application and delegated token response
class AuthTokenBase(BaseModel):
    token_type: Literal["Bearer"]
    expires_in: int
    access_token: SecretStr


class ApplicationAuthToken(AuthTokenBase):
    ext_expires_in: int

    # Helper attributes
    creation_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @property
    def expiration_time(self) -> datetime.datetime:
        return self.creation_time + datetime.timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        return (self.expiration_time - datetime.datetime.utcnow()).total_seconds() < 60


class DelegatedAuthToken(AuthTokenBase):
    scope: str
    refresh_token: SecretStr


class AuthBase(ABC):
    def __init__(self, client_id: str, client_secret: str, tenant_id) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret

    @property
    @abstractmethod
    def access_token(self) -> AuthTokenBase:
        pass

    @abstractmethod
    def refresh_access_token(self) -> None:
        pass


class ApplicationAuth(AuthBase):
    """Used to access Graph API without a user (server application)."""

    _token: Optional[ApplicationAuthToken]

    @property
    def access_token(self) -> ApplicationAuthToken:
        try:
            token = self._token
        except AttributeError:
            self.refresh_access_token()
            token = self._token
        else:
            if token is None or token.is_expired:
                self.refresh_access_token()
        assert token is not None
        return token

    def refresh_access_token(self) -> None:
        """
        https://learn.microsoft.com/en-us/graph/auth-v2-service?view=graph-rest-1.0#4-get-an-access-token

        """
        response = requests.post(
            url=(
                f"https://login.microsoftonline.com/{self.tenant_id}"
                f"/oauth2/v2.0/token"
            ),
            data={
                "client_id": self.client_id,
                "scope": "https://graph.microsoft.com/.default",
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
            timeout=30,
            headers={
                "Host": "login.microsoftonline.com",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
        self._token = ApplicationAuthToken.parse_obj(json.loads(response.content))


class DelegatedAuth(AuthBase):
    """
    Used to access Graph API on behalf of a user using OAuth 2.0
    authorization code grant flow.

    """
