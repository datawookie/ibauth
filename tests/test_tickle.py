from typing import Any
from unittest.mock import patch, Mock
from httpx import HTTPStatusError, ReadTimeout, Request, Response

import pytest


from ibauth import IBAuth


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.get")
async def test_tickle_success(mock_get: Mock, flow: IBAuth) -> None:
    flow.bearer_token = "bearer123"

    mock_response = Mock()
    mock_response.json.return_value = {
        "session": "session",
        "iserver": {
            "authStatus": {
                "authenticated": True,
                "competing": False,
                "connected": True,
            }
        },
    }

    mock_get.return_value = mock_response

    sid = await flow.tickle()
    assert sid == "session"
    assert flow.authenticated
    assert flow.connected
    assert not flow.competing


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.get")
async def test_tickle_not_authenticated(
    mock_get: Mock, flow: IBAuth, disable_ibauth_connect: Mock, monkeypatch: Any
) -> None:
    flow.bearer_token = "bearer123"

    mock_response = Mock()
    mock_response.json.return_value = {
        "session": "session",
        "iserver": {
            "authStatus": {
                "authenticated": False,
                "competing": False,
                "connected": True,
            }
        },
    }

    mock_get.return_value = mock_response

    await flow.connect()
    sid = await flow.tickle()

    assert sid == "session"
    assert not flow.authenticated
    assert flow.connected
    assert not flow.competing

    # Should be called twice:
    #
    # - once on initial connect() and
    # - once again from within tickle() when it sees we're not authenticated.
    #
    assert disable_ibauth_connect.call_count == 2


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.get")
async def test_tickle_http_error(mock_get: Mock, flow: IBAuth) -> None:
    flow.bearer_token = "bearer123"

    request = Request("GET", "https://mocked-url.com")
    response = Response(status_code=401, request=request)
    error = HTTPStatusError("401 Unauthorized", request=request, response=response)

    mock_get.side_effect = error

    with pytest.raises(HTTPStatusError):
        await flow.tickle()

    assert flow.authenticated is False
    assert flow.connected is False
    assert flow.competing is None

    response = Response(status_code=500, request=request)
    error = HTTPStatusError("500 Internal Server Error", request=request, response=response)

    mock_get.side_effect = error

    with pytest.raises(HTTPStatusError):
        await flow.tickle()

    assert flow.authenticated is False
    assert flow.connected is False
    assert flow.competing is None


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.get")
async def test_tickle_timeout(mock_get: Mock, flow: IBAuth) -> None:
    flow.bearer_token = "bearer123"

    mock_get.side_effect = ReadTimeout("Request timed out")

    with pytest.raises(ReadTimeout):
        await flow.tickle()
