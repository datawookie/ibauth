from typing import Any
from unittest.mock import patch, Mock

import pytest

from ibauth import IBAuth
from ibauth.util import HTTPError


@patch("ibauth.auth.get")
def test_tickle_success(mock_get: Mock, flow: IBAuth) -> None:
    flow.bearer_token = "bearer123"
    mock_get.return_value.json.return_value = {
        "session": "session",
        "iserver": {
            "authStatus": {
                "authenticated": True,
                "competing": False,
                "connected": True,
            }
        },
    }
    sid = flow.tickle()
    assert sid == "session"
    assert flow.authenticated
    assert flow.connected
    assert not flow.competing


@patch("ibauth.auth.get")
def test_tickle_failure(mock_get: Mock, flow: IBAuth, monkeypatch: Any) -> None:
    flow.access_token = "not.valid"
    flow.bearer_token = "not.valid"

    mock_response = Mock()
    mock_response.raise_for_status.side_effect = HTTPError("bad request")
    mock_response.json.return_value = {"error": "bad request"}
    mock_get.return_value = mock_response

    monkeypatch.setattr(flow, "get_bearer_token", lambda: None)
    monkeypatch.setattr(flow, "ssodh_init", lambda: None)

    with pytest.raises(HTTPError):
        flow.tickle()


@patch("ibauth.auth.get")
def test_tickle_not_authenticated(mock_get: Mock, flow: IBAuth, disable_ibauth_connect: Mock, monkeypatch: Any) -> None:
    flow.bearer_token = "bearer123"
    mock_get.return_value.json.return_value = {
        "session": "session",
        "iserver": {
            "authStatus": {
                "authenticated": False,
                "competing": False,
                "connected": True,
            }
        },
    }

    sid = flow.tickle()

    assert sid == "session"
    assert not flow.authenticated
    assert flow.connected
    assert not flow.competing

    # Should be called twice:
    #
    # - once on initial connection and
    # - once again from within tickle() when it sees we're not authenticated.
    #
    assert disable_ibauth_connect.call_count == 2
