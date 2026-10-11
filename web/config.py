from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'AeroMind AI'
    environment: Literal['development', 'staging', 'production'] = Field('production', alias='AEROMIND_ENV')
    port: int = Field(10000, alias='PORT')
    session_secret: str = Field(..., alias='AEROMIND_SESSION_SECRET')
    superadmin_emails: str = Field('', alias='AEROMIND_SUPERADMIN_EMAILS')
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

    @field_validator('openai_api_base', mode='before')
    @classmethod
    def normalize_openai_base(cls, value: str) -> str:
        value = str(value or '').strip().strip('"\'')
        if value and not value.startswith(('http://', 'https://')):
            value = f'https://{value}'
        return value.rstrip('/') or 'https://api.openai.com/v1'

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
        # Render fournit un Host sans schéma. Accepter aussi par tolérance
        # une valeur saisie comme URL, sans jamais laisser une variable vide
        # désactiver involontairement tous les hôtes autorisés.
        raw = [x.strip() for x in self.allowed_hosts.split(',') if x.strip()]
        hosts: list[str] = []
        for value in raw:
            candidate = value if '://' in value else f'http://{value}'
            parsed = urlparse(candidate)
            host = parsed.netloc.split('@')[-1].split(':')[0].lower().rstrip('.')
            if host:
                hosts.append(host)
        return hosts or ['*.onrender.com', 'localhost', '127.0.0.1']

    @property
    def superadmin_email_set(self) -> set[str]:
        return {email.strip().casefold() for email in self.superadmin_emails.split(',') if email.strip()}

    def is_superadmin_email(self, email: str | None) -> bool:
        return bool(email and email.strip().casefold() in self.superadmin_email_set)

    @property
    def oidc(self) -> dict[str, str] | None:
        if self.oidc_issuer and self.oidc_client_id and self.oidc_client_secret and self.oidc_redirect_uri:
            issuer = self.oidc_issuer.strip().strip('"\'')
            if not issuer.startswith(('http://', 'https://')):
                issuer = f'https://{issuer}'
            return {'issuer': issuer.rstrip('/'), 'client_id': self.oidc_client_id, 'client_secret': self.oidc_client_secret, 'redirect_uri': self.oidc_redirect_uri}
        if self.entra_tenant_id and self.entra_client_id and self.entra_client_secret and self.entra_redirect_uri:
            return {'issuer': f'https://login.microsoftonline.com/{self.entra_tenant_id}/v2.0', 'client_id': self.entra_client_id, 'client_secret': self.entra_client_secret, 'redirect_uri': self.entra_redirect_uri}
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
