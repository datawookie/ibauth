import time
import pytest
from unittest.mock import Mock, patch
from httpx import Response, Request
from ibauth import util
from typing import Any


def create_mock_response(status_code: int = 200) -> Mock:
    mock_response = Mock(spec=Response)
    mock_response.status_code = status_code
    mock_response.text = ""
    mock_response.headers = {"Content-Type": "text/plain"}

    req = Request("GET", "https://example.com", headers={"X-Test": "1"})

    mock_response.request = req

    mock_response.raise_for_status.return_value = None

    return mock_response


def test_log_response_success(caplog: Any) -> None:
    mock_response = create_mock_response()

    caplog.set_level("DEBUG")
    util.log_response(mock_response)

    logs = caplog.messages
    assert any("Response: 200" in msg for msg in logs)
    mock_response.raise_for_status.assert_called_once()


def test_log_response_http_error() -> None:
    mock_response = create_mock_response(status_code=400)

    mock_response.raise_for_status.side_effect = util.HTTPStatusError(
        "boom", request=mock_response.request, response=mock_response
    )

    with pytest.raises(util.HTTPStatusError):
        util.log_response(mock_response)


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.util.httpx.AsyncClient.get")
async def test_get_calls_requests_get(mock_get: Mock) -> None:
    mock_response = create_mock_response()

    mock_get.return_value = mock_response

    resp = await util.get("https://example.com", headers={"h": "v"})

    mock_get.assert_called_once_with("https://example.com", headers={"h": "v"})
    assert resp is mock_response


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.util.httpx.AsyncClient.post")
async def test_post_calls_requests_post(mock_post: Mock) -> None:
    mock_response = create_mock_response()

    mock_post.return_value = mock_response

    resp = await util.post("https://example.com", data={"a": "b"}, json=None, headers={"h": "v"})

    mock_post.assert_called_once_with(
        "https://example.com", content={"a": "b"}, data=None, json=None, headers={"h": "v"}
    )
    assert resp is mock_response


@patch("ibauth.util.jwt.encode")
def test_make_jws_sets_claims_and_calls_jwt(mock_encode: Mock) -> None:
    fake_key = "secret"
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {"foo": "bar"}

    t0 = int(time.time())
    mock_encode.return_value = "encoded.jwt"

    token = util.make_jws(header, claims.copy(), fake_key)

    assert token == "encoded.jwt"

    # Check positional args
    called_claims, called_key = mock_encode.call_args[0]
    assert isinstance(called_claims, dict)
    assert called_key == fake_key
    assert called_claims["iat"] >= t0
    assert called_claims["exp"] >= t0

    # Check keyword args
    kwargs = mock_encode.call_args[1]
    assert kwargs["algorithm"] == "RS256"
    assert kwargs["headers"] == header


def test_authentication_error_with_code() -> None:
    err = util.AuthenticationError("Invalid credentials", code=401)

    # Exception should carry the message
    assert str(err) == "Invalid credentials"
    # And the custom code
    assert err.code == 401
    # It should also be an Exception subclass
    assert isinstance(err, Exception)


def test_authentication_error_without_code() -> None:
    err = util.AuthenticationError("Something went wrong")

    assert str(err) == "Something went wrong"
    assert err.code is None
