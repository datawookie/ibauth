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


def log_response(response: Response) -> None:
    logger.debug(f"Response: {response.status_code} {response.text}")
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
