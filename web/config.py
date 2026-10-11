from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'AeroMind AI'
    environment: Literal['development', 'staging', 'production'] = Field('production', alias='AEROMIND_ENV')
    port: int = Field(10000, alias='PORT')
    session_secret: str = Field(..., alias='AEROMIND_SESSION_SECRET')
    allowed_origins: str = Field('', alias='AEROMIND_ALLOWED_ORIGINS')
    allowed_hosts: str = Field('*.onrender.com,localhost,127.0.0.1', alias='AEROMIND_ALLOWED_HOSTS')
    entra_tenant_id: str | None = Field(None, alias='ENTRA_TENANT_ID')
    entra_client_id: str | None = Field(None, alias='ENTRA_CLIENT_ID')
    entra_client_secret: str | None = Field(None, alias='ENTRA_CLIENT_SECRET')
    entra_redirect_uri: str | None = Field(None, alias='ENTRA_REDIRECT_URI')
    oidc_issuer: str | None = Field(None, alias='OIDC_ISSUER')
    oidc_client_id: str | None = Field(None, alias='OIDC_CLIENT_ID')
    oidc_client_secret: str | None = Field(None, alias='OIDC_CLIENT_SECRET')
    oidc_redirect_uri: str | None = Field(None, alias='OIDC_REDIRECT_URI')
    openai_api_key: str | None = Field(None, alias='OPENAI_API_KEY')
    openai_api_base: str = Field('https://api.openai.com/v1', alias='OPENAI_API_BASE')
    openai_model: str = Field('gpt-5-mini', alias='OPENAI_MODEL')

    @field_validator('session_secret')
    @classmethod
    def strong_secret(cls, value: str) -> str:
        if len(value.encode()) < 32:
            raise ValueError('AEROMIND_SESSION_SECRET must contain at least 32 bytes')
        return value

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.allowed_origins.split(',') if x.strip()]

    @property
    def hosts(self) -> list[str]:
        return [x.strip() for x in self.allowed_hosts.split(',') if x.strip()]

    @property
    def oidc(self) -> dict[str, str] | None:
        if self.oidc_issuer and self.oidc_client_id and self.oidc_client_secret and self.oidc_redirect_uri:
            return {'issuer': self.oidc_issuer.rstrip('/'), 'client_id': self.oidc_client_id, 'client_secret': self.oidc_client_secret, 'redirect_uri': self.oidc_redirect_uri}
        if self.entra_tenant_id and self.entra_client_id and self.entra_client_secret and self.entra_redirect_uri:
            return {'issuer': f'https://login.microsoftonline.com/{self.entra_tenant_id}/v2.0', 'client_id': self.entra_client_id, 'client_secret': self.entra_client_secret, 'redirect_uri': self.entra_redirect_uri}
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
