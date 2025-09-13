from json import dumps
import time
import jwt
import requests
from typing import Any

from requests import Response
from requests.exceptions import HTTPError, ReadTimeout  # noqa

from .logger import logger

__all__ = ["ReadTimeout", "HTTPError"]

from .const import *

RESP_HEADERS_TO_PRINT = ["Cookie", "Cache-Control", "Content-Type", "Host"]


class AuthenticationError(Exception):
    def __init__(self, message: str, *, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


def log_response(response: Response) -> None:
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        content = dumps(response.json(), indent=2)
    else:
        content = response.text
    logger.debug(f"Response: {response.status_code} {content}")
    response.raise_for_status()


def get(url: str, headers: dict[str, str] | None = None, timeout: float | None = None) -> requests.Response:
    logger.debug(f"🔄 GET {url}")
    response = requests.get(url, headers=headers, timeout=timeout)
    log_response(response)
    return response


def post(
    url: str,
    data: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
) -> requests.Response:
    logger.debug(f"🔄 POST {url}")
    logger.debug(f"  - headers: {headers}")
    logger.debug(f"  - data: {dumps(data, indent=2) if data else None}")
    logger.debug(f"  - JSON: {dumps(json, indent=2) if json else None}")
    response = requests.post(url, data=data, json=json, headers=headers, timeout=timeout)
    log_response(response)
    return response


def make_jws(header: dict[str, Any], claims: dict[str, Any], clientPrivateKey: Any) -> Any:
    """
    Create a JSON Web Signature (JWS) using the specified header, claims, and private key.
    """
    # Set expiration time.
    claims["exp"] = int(time.time()) + 600
    claims["iat"] = int(time.time())

    return jwt.encode(claims, clientPrivateKey, algorithm="RS256", headers=header)
