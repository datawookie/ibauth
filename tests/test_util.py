import time
import pytest
from unittest.mock import Mock, patch
from requests import Response, Request
from requests.exceptions import HTTPError
from ibauth import util
from typing import Any


def test_log_response_success(caplog: Any) -> None:
    mock_response = Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.text = "ok"

    req = Request("GET", "https://example.com", headers={"X-Test": "1"}).prepare()
    mock_response.request = req

    mock_response.raise_for_status.return_value = None

    caplog.set_level("DEBUG")
    util.log_response(mock_response)

    logs = caplog.messages
    assert any("Response: 200 ok" in msg for msg in logs)
    mock_response.raise_for_status.assert_called_once()


def test_log_response_http_error() -> None:
    mock_response = Mock(spec=Response)
    mock_response.status_code = 400
    mock_response.text = "bad"
    mock_response.request = Mock()

    req = Request("GET", "https://example.com", headers={"X-Test": "1"}).prepare()
    mock_response.request = req

    mock_response.raise_for_status.side_effect = HTTPError("boom")

    with pytest.raises(HTTPError):
        util.log_response(mock_response)


@patch("ibauth.util.requests.get")
def test_get_calls_requests_get(mock_get: Mock) -> None:
    mock_response = Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.text = "ok"
    mock_response.request = Mock()

    req = Request("GET", "https://example.com", headers={"X-Test": "1"}).prepare()
    mock_response.request = req

    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    resp = util.get("https://example.com", headers={"h": "v"}, timeout=1.0)

    mock_get.assert_called_once_with("https://example.com", headers={"h": "v"}, timeout=1.0)
    assert resp is mock_response


@patch("ibauth.util.requests.post")
def test_post_calls_requests_post(mock_post: Mock) -> None:
    mock_response = Mock(spec=Response)
    mock_response.status_code = 200
    mock_response.text = "ok"
    mock_response.request = Mock()

    req = Request("GET", "https://example.com", headers={"X-Test": "1"}).prepare()
    mock_response.request = req

    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    resp = util.post("https://example.com", data={"a": "b"}, json=None, headers={"h": "v"}, timeout=2.0)

    mock_post.assert_called_once_with(
        "https://example.com", data={"a": "b"}, json=None, headers={"h": "v"}, timeout=2.0
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
