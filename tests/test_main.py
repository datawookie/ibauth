import pytest
from pathlib import Path
from unittest.mock import patch, Mock, AsyncMock
from typing import Any

import yaml

from ibauth import IBAuth, auth_from_yaml, util

from conftest import create_mock_response


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


def test_property_header(flow: IBAuth) -> None:
    with pytest.raises(ValueError):
        flow.header

    flow.bearer_token = "bearer123"
    header = flow.header
    assert "Authorization" in header
    assert header["Authorization"].startswith("Bearer ")


def test_is_connected(flow: IBAuth) -> None:
    flow.authenticated = True
    flow.connected = True
    assert flow.is_connected()


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.get")
async def test_check_ip_sets_ip(mock_get: Mock, flow: IBAuth) -> None:
    mock_get.return_value.content = b"1.2.3.4"
    ip = await flow._check_ip()
    assert ip == "1.2.3.4"
    assert flow.IP == "1.2.3.4"


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.post")
async def test_get_access_token(mock_post: AsyncMock, flow: IBAuth) -> None:
    mock_response = Mock()
    mock_response.json.return_value = {"access_token": "abc123"}

    mock_post.return_value = mock_response

    await flow.get_access_token()
    assert flow.access_token == "abc123"


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.post")
@patch.object(IBAuth, "_check_ip")
async def test_get_bearer_token(mock_check_ip: Mock, mock_post: AsyncMock, flow: IBAuth) -> None:
    flow.access_token = "abc123"
    mock_check_ip.return_value = "1.2.3.4"

    mock_response = Mock()
    mock_response.json.return_value = {"access_token": "bearer123"}
    mock_post.return_value = mock_response

    await flow.get_bearer_token()
    assert flow.bearer_token == "bearer123"


@pytest.mark.asyncio  # type: ignore[misc]
@pytest.mark.usefixtures("flow")  # type: ignore[misc]
async def test_check_ip_change(flow: IBAuth, caplog: pytest.LogCaptureFixture) -> None:
    # Get initial IP.
    with patch("ibauth.auth.get") as mock_get:
        mock_get.return_value.content = b"1.2.3.4"
        ip1 = await flow._check_ip()
        assert ip1 == "1.2.3.4"

    # Get new IP.
    with patch("ibauth.auth.get") as mock_get:
        mock_get.return_value.content = b"5.6.7.8"

        caplog.set_level("WARNING")
        ip2 = await flow._check_ip()

        assert ip2 == "5.6.7.8"
        # Verify warning was logged
        warnings = [rec.getMessage() for rec in caplog.records if rec.levelname == "WARNING"]
        assert any("Public IP has changed" in msg for msg in warnings)


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.post")
async def test_ssodh_init_success(mock_post: Mock, flow: IBAuth) -> None:
    flow.bearer_token = "bearer123"
    mock_response = Mock()
    mock_response.json.return_value = {"status": "ok"}
    mock_post.return_value = mock_response
    await flow.ssodh_init()


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.post")
async def test_ssodh_init_failure(mock_post: Mock, flow: IBAuth, monkeypatch: Any) -> None:
    mock_response = create_mock_response(status_code=400)

    flow.bearer_token = "not.valid"
    mock_post.side_effect = util.HTTPStatusError("bad request", request=mock_response.request, response=mock_response)

    with pytest.raises(util.HTTPStatusError):
        await flow.ssodh_init()


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.get")
async def test_validate_sso(mock_get: Mock, flow: IBAuth, session_details_payload: dict[str, Any]) -> None:
    flow.bearer_token = "bearer123"

    mock_response = Mock()
    mock_response.json.return_value = session_details_payload

    mock_get.return_value = mock_response
    await flow.validate_sso()
    mock_get.assert_called_once()


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.post")
async def test_logout_with_token(mock_post: Mock, flow: IBAuth) -> None:
    flow.bearer_token = "bearer123"
    await flow.logout()
    mock_post.assert_called_once()


@pytest.mark.asyncio  # type: ignore[misc]
async def test_logout_without_token(flow: IBAuth) -> None:
    flow.bearer_token = None
    await flow.logout()


@pytest.mark.asyncio  # type: ignore[misc]
@patch("ibauth.auth.post")
async def test_logout_not_authenticated(mock_post: Mock, flow: IBAuth, caplog: pytest.LogCaptureFixture) -> None:
    mock_response = create_mock_response(status_code=401)
    mock_post.side_effect = util.HTTPStatusError("Unauthorised", request=mock_response.request, response=mock_response)

    flow.bearer_token = "bearer123"
    with caplog.at_level("WARNING"):
        await flow.logout()

    assert any("Can't terminate brokerage session (not authenticated)." in msg for msg in caplog.messages)


@pytest.mark.asyncio  # type: ignore[misc]
@pytest.mark.no_patch_connect  # type: ignore[misc]
@patch("ibauth.auth.IBAuth.get_access_token", return_value=None)
@patch("ibauth.auth.IBAuth.get_bearer_token", return_value=None)
@patch("ibauth.auth.IBAuth.ssodh_init", return_value=None)
@patch("ibauth.auth.IBAuth.validate_sso", return_value=None)
async def test_connect(
    mock_get_access_token: Mock,
    mock_get_bearer_token: Mock,
    mock_ssodh_init: Mock,
    mock_validate_sso: Mock,
    request: pytest.FixtureRequest,
) -> None:
    # Create the flow fixture once all of the patches have been applied.
    flow = request.getfixturevalue("flow")
    assert isinstance(flow, IBAuth)

    await flow.connect()

    mock_get_access_token.assert_called_once()
    mock_get_bearer_token.assert_called_once()
    mock_ssodh_init.assert_called_once()
    mock_validate_sso.assert_called_once()


@patch("ibauth.auth.IBAuth.connect")
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


@pytest.mark.asyncio  # type: ignore[misc]
@pytest.mark.no_patch_connect  # type: ignore[misc]
@patch("ibauth.auth.post")
async def test_auth_from_yaml_failure(mock_post: Mock, tmp_path: Path, private_key_file: str) -> None:
    mock_response = create_mock_response(status_code=400)
    mock_post.side_effect = util.HTTPStatusError("bad request", request=mock_response.request, response=mock_response)

    config = {
        "client_id": "cid",
        "client_key_id": "kid",
        "credential": "cred",
        "private_key_file": str(private_key_file),
        "domain": "api.ibkr.com",
    }
    file = tmp_path / "conf.yaml"
    file.write_text(yaml.dump(config))

    with pytest.raises(util.HTTPStatusError):
        auth = auth_from_yaml(file)
        await auth.connect()
