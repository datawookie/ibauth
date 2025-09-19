import os.path

import pytest
from ibauth import auth_from_yaml


@pytest.fixture(scope="session", autouse=True)  # type: ignore[misc]
def _ensure_configuration_present() -> None:
    """Skip the integration suite if there is no config.yaml file."""
    if not os.path.isfile("config.yaml"):
        pytest.skip("No config.yaml file.")


@pytest.mark.asyncio  # type: ignore[misc]
@pytest.mark.integration  # type: ignore[misc]
@pytest.mark.timeout(20)  # type: ignore[misc]
async def test_full_auth_flow_real() -> None:
    auth = auth_from_yaml("config.yaml")
    await auth.connect()
    await auth.get_access_token()
    await auth.get_bearer_token()
    await auth.ssodh_init()
    await auth.validate_sso()
    for _ in range(3):
        await auth.tickle()
    auth.domain = "5.api.ibkr.com"
    await auth.tickle()
    await auth.logout()
