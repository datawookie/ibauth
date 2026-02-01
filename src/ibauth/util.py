from json import dumps
import time
import jwt
import httpx
from typing import Any

from httpx import HTTPStatusError, ReadTimeout  # noqa

from .logger import logger

__all__ = ["ReadTimeout", "HTTPStatusError"]

from .const import *

RESP_HEADERS_TO_PRINT = ["Cookie", "Cache-Control", "Content-Type", "Host"]


class AuthenticationError(Exception):
    def __init__(self, message: str, *, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


def log_response(response: httpx.Response) -> None:
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        content = dumps(response.json(), indent=2)
    else:
        content = response.text
    logger.debug(f"Response: {response.status_code} {content}")
    response.raise_for_status()


async def get(url: str, headers: dict[str, str] | None = None, timeout: float | None = None) -> httpx.Response:
    logger.debug(f"🔄 GET {url}")
    logger.debug(f"  - headers: {headers}")
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers)
        log_response(response)
        return response


async def post(
    url: str,
    data: dict[str, Any] | str | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
) -> httpx.Response:
    logger.debug(f"🔄 POST {url}")
    logger.debug(f"  - headers: {headers}")
    logger.debug(f"  - data: {dumps(data, indent=2) if data else None}")

    is_form = headers and headers.get("Content-Type") == "application/x-www-form-urlencoded"

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            # Data is raw string.
            content=data if isinstance(data, str) else None,
            # Data is form-encoded.
            data=data if isinstance(data, dict) and is_form else None,
            # Data is not form-encoded.
            json=data if isinstance(data, dict) and not is_form else None,
            headers=headers,
        )
        log_response(response)
        return response


def make_jws(header: dict[str, Any], claims: dict[str, Any], clientPrivateKey: Any) -> Any:
    """
    Create a JSON Web Signature (JWS) using the specified header, claims, and private key.
    """
    # Only set defaults if caller didn't set them.
    now = int(time.time())
    claims.setdefault("exp", now + 600)
    claims.setdefault("iat", now)

    return jwt.encode(claims, clientPrivateKey, algorithm="RS256", headers=header)
