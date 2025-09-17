import pytest
from pathlib import Path
from unittest.mock import patch, Mock
from typing import Any

import yaml

from ibauth import IBAuth, auth_from_yaml
from ibauth.util import HTTPError, AuthenticationError


def test_init_valid(flow: IBAuth) -> None:
    assert flow.client_id == "cid"
    assert flow.domain == "api.ibkr.com"
    assert flow.private_key is not None


def test_invalid_domain_constructor(private_key_file: Path) -> None:
    with pytest.raises(ValueError):
        IBAuth("cid", "kid", "cred", private_key_file, domain="not.valid")


def test_invalid_domain_setter(flow: IBAuth) -> None:
    with pytest.raises(ValueError):
        flow.domain = "not.valid"


def test_missing_client_id(private_key_file: Path) -> None:
    with pytest.raises(ValueError):
        IBAuth("", "kid", "cred", private_key_file, domain="api.ibkr.com")


def test_missing_key_id(private_key_file: Path) -> None:
    with pytest.raises(ValueError):
        IBAuth("cid", "", "cred", private_key_file, domain="api.ibkr.com")


def test_missing_credential(private_key_file: Path) -> None:
    with pytest.raises(ValueError):
        IBAuth("cid", "kid", "", private_key_file, domain="api.ibkr.com")


def test_missing_private_key_file(private_key_file: Path) -> None:
    with pytest.raises(ValueError):
        IBAuth("cid", "kid", "cred", "", domain="api.ibkr.com")


@patch("ibauth.auth.get")
def test_check_ip_sets_ip(mock_get: Mock, flow: IBAuth) -> None:
    mock_get.return_value.content = b"1.2.3.4"
    ip = flow._check_ip()
    assert ip == "1.2.3.4"
    assert flow.IP == "1.2.3.4"


@patch("ibauth.auth.post")
def test_get_access_token(mock_post: Mock, flow: IBAuth) -> None:
    mock_post.return_value.json.return_value = {"access_token": "abc123"}
    flow.get_access_token()
    assert flow.access_token == "abc123"


@patch("ibauth.auth.post")
@patch.object(IBAuth, "_check_ip")
def test_get_bearer_token(mock_check_ip: Mock, mock_post: Mock, flow: IBAuth) -> None:
    flow.access_token = "abc123"
    mock_check_ip.return_value = "1.2.3.4"
    mock_post.return_value.json.return_value = {"access_token": "bearer123"}

    flow.get_bearer_token()
    assert flow.bearer_token == "bearer123"


@pytest.mark.usefixtures("flow")  # type: ignore[misc]
def test_check_ip_change(flow: IBAuth, caplog: Any) -> None:
    # Get initial IP.
    with patch("ibauth.auth.get") as mock_get:
        mock_get.return_value.content = b"1.2.3.4"
        ip1 = flow._check_ip()
        assert ip1 == "1.2.3.4"

    # Get new IP.
    with patch("ibauth.auth.get") as mock_get:
        mock_get.return_value.content = b"5.6.7.8"

        caplog.set_level("WARNING")
        ip2 = flow._check_ip()

        assert ip2 == "5.6.7.8"
        # Verify warning was logged
        warnings = [rec.getMessage() for rec in caplog.records if rec.levelname == "WARNING"]
        assert any("Public IP has changed" in msg for msg in warnings)


@patch("ibauth.auth.post")
def test_ssodh_init_success(mock_post: Mock, flow: IBAuth) -> None:
    flow.bearer_token = "bearer123"
    mock_post.return_value.json.return_value = {"status": "ok"}
    flow.ssodh_init()


@patch("ibauth.auth.post")
def test_ssodh_init_failure(mock_post: Mock, flow: IBAuth, monkeypatch: Any) -> None:
    flow.bearer_token = "not.valid"
    mock_post.side_effect = HTTPError("bad request")

    with pytest.raises(HTTPError):
        flow.ssodh_init()


@patch("ibauth.auth.get")
def test_validate_sso(mock_get: Mock, flow: IBAuth, session_details_payload: dict[str, Any]) -> None:
    flow.bearer_token = "bearer123"
    mock_get.return_value.json.return_value = session_details_payload
    flow.validate_sso()
    mock_get.assert_called_once()


@patch("ibauth.auth.post")
def test_logout_with_token(mock_post: Mock, flow: IBAuth) -> None:
    flow.bearer_token = "bearer123"
    flow.logout()
    mock_post.assert_called_once()


def test_logout_without_token(flow: IBAuth) -> None:
    flow.bearer_token = None
    flow.logout()


@patch("ibauth.auth.post")
def test_logout_not_authenticated(mock_post: Mock, flow: IBAuth, caplog: Any) -> None:
    response = Mock()
    response.status_code = 401
    mock_post.side_effect = HTTPError("Unauthorised", response=response)

    flow.bearer_token = "bearer123"
    with caplog.at_level("WARNING"):
        flow.logout()

    assert any("Can't terminate brokerage session (not authenticated)." in msg for msg in caplog.messages)


@pytest.mark.no_patch_connect  # type: ignore[misc]
@patch("ibauth.auth.IBAuth.get_access_token", return_value=None)
@patch("ibauth.auth.IBAuth.get_bearer_token", return_value=None)
@patch("ibauth.auth.IBAuth.ssodh_init", return_value=None)
@patch("ibauth.auth.IBAuth.validate_sso", return_value=None)
def test_connect(
    mock_get_access_token: Mock,
    mock_get_bearer_token: Mock,
    mock_ssodh_init: Mock,
    mock_validate_sso: Mock,
    request: pytest.FixtureRequest,
) -> None:
    # Create the flow fixture once all of the patches have been applied.
    flow = request.getfixturevalue("flow")
    assert isinstance(flow, IBAuth)

    mock_get_access_token.assert_called_once()
    mock_get_bearer_token.assert_called_once()
    mock_ssodh_init.assert_called_once()
    mock_validate_sso.assert_called_once()


@patch("ibauth.auth.IBAuth._connect")
def test_auth_from_yaml(mock_connect: Mock, tmp_path: Path, private_key_file: str) -> None:
    mock_connect.return_value = None
    config = {
        "client_id": "cid",
        "client_key_id": "kid",
        "credential": "cred",
        "private_key_file": str(private_key_file),
        "domain": "api.ibkr.com",
    }
    file = tmp_path / "conf.yaml"
    file.write_text(yaml.dump(config))
    flow = auth_from_yaml(file)
    assert isinstance(flow, IBAuth)
    assert flow.client_id == "cid"


@pytest.mark.no_patch_connect  # type: ignore[misc]
@patch("ibauth.auth.post")
def test_auth_from_yaml_failure(mock_post: Mock, tmp_path: Path, private_key_file: str) -> None:
    mock_post.side_effect = HTTPError("bad request")

    config = {
        "client_id": "cid",
        "client_key_id": "kid",
        "credential": "cred",
        "private_key_file": str(private_key_file),
        "domain": "api.ibkr.com",
    }
    file = tmp_path / "conf.yaml"
    file.write_text(yaml.dump(config))

    with pytest.raises(AuthenticationError):
        auth_from_yaml(file)
