from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable

import jwt


@dataclass(frozen=True)
class JwtSettings:
    secret: str
    algorithm: str = "HS256"
    audience: str = "aeromind-sitl"
    issuer: str = "aeromind-demo"


@dataclass(frozen=True)
class TokenResult:
    token: str
    valid: bool
    subject: str | None = None
    error: str | None = None


def validate_token(token: str, settings: JwtSettings) -> TokenResult:
    try:
        payload = jwt.decode(token, settings.secret, algorithms=[settings.algorithm], audience=settings.audience, issuer=settings.issuer)
        return TokenResult(token, True, str(payload.get("sub", "")) or None)
    except jwt.PyJWTError as exc:
        return TokenResult(token, False, error=str(exc))


async def validate_tokens_parallel(tokens: Iterable[str], settings: JwtSettings, *, max_concurrency: int = 32) -> list[TokenResult]:
    semaphore = asyncio.Semaphore(max_concurrency)

    async def one(token: str) -> TokenResult:
        async with semaphore:
            return await asyncio.to_thread(validate_token, token, settings)

    return await asyncio.gather(*(one(token) for token in tokens))
