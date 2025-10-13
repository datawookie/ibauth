from pathlib import Path
from typing import Any, Iterator
from unittest.mock import Mock, AsyncMock
from httpx import Response, Request

import pytest
import tenacity

from ibauth import IBAuth
from ibauth.models import SessionDetailsModel
import ibauth.timing

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Disable all retries.
tenacity.retry = lambda *a, **kw: (lambda f: f)


@pytest.fixture(autouse=True)  # type: ignore[misc]
def disable_timing(monkeypatch: Any) -> Iterator[None]:
    """
    Replace ibauth.timing.timing with a no-op context manager for tests.
    """

    class DummyTiming:
        def __init__(self) -> None:
            pass

    monkeypatch.setattr(ibauth.timing, "AsyncTimer", DummyTiming)
    yield


@pytest.fixture(autouse=True)  # type: ignore[misc]
def disable_ibauth_connect(monkeypatch: Any, request: pytest.FixtureRequest) -> Iterator[Mock | None]:
    """
    Patch IBAuth.connect with a Mock for all tests so calls can be tracked.

    Use @pytest.mark.no_patch_connect if you want the original connect().
    """
    if request.node.get_closest_marker("no_patch_connect"):
        yield None
        return

    mock_connect = AsyncMock(return_value=None)
    monkeypatch.setattr("ibauth.auth.IBAuth.connect", mock_connect)
    yield mock_connect


@pytest.fixture  # type: ignore[misc]
def private_key_file(tmp_path: Path) -> Iterator[Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    key_file = tmp_path / "key.pem"
    key_file.write_bytes(pem)
    yield key_file


@pytest.fixture  # type: ignore[misc]
def flow(private_key_file: Path) -> IBAuth:
    return IBAuth(
        client_id="cid",
        client_key_id="kid",
        credential="cred",
        private_key_file=private_key_file,
        domain="api.ibkr.com",
    )


@pytest.fixture  # type: ignore[misc]
def session_details_payload() -> Any:
    """Return a minimal valid payload for SessionDetailsModel."""
    payload = SessionDetailsModel(
        PAPER_USER_NAME="testuser",
        IS_PENDING_APPLICANT=False,
        SF_ENABLED=False,
        HARDWARE_INFO="info",
        UNIQUE_LOGIN_ID="123",
        AUTH_TIME=1234567890,
        SF_CONFIG="",
        USER_NAME="testuser",
        CREDENTIAL_TYPE=1,
        IS_FREE_TRIAL=False,
        LOGIN_TYPE=2,
        LANDING_APP="PORTAL",
        COUNTERPARTY="counter",
        CREDENTIAL="cred",
        RESULT=True,
        IP="127.0.0.1",
        USER_ID=1,
        EXPIRES=1234567999,
        TOKEN="Bearer:token",
        took=50,
        IS_MASTER=False,
        features={
            "env": "PROD",
            "wlms": True,
            "realtime": True,
            "bond": True,
            "optionChains": True,
            "calendar": True,
            "newMf": True,
        },
        region="EU",
    ).model_dump()

    return payload


def create_mock_response(
    status_code: int = 200, content_type: str = "text/plain", text: str = "", json_data: dict[str, Any] | None = None
) -> Mock:
    mock_response = Mock(spec=Response)
    mock_response.status_code = status_code
    mock_response.text = text
    mock_response.headers = {"Content-Type": content_type}

    req = Request("GET", "https://example.com", headers={"X-Test": "1"})

    mock_response.request = req

    mock_response.raise_for_status.return_value = None

    mock_response.json.return_value = json_data or {}

    return mock_response
