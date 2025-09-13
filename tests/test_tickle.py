from typing import Any
from unittest.mock import patch, Mock


from ibauth import IBAuth


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
