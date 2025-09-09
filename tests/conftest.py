from pathlib import Path
from typing import Any, Iterator, Literal
from unittest.mock import Mock

import pytest
import tenacity

from ibauth import IBAuth
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
        def __enter__(self) -> "DummyTiming":
            return self

        def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Literal[False]:
            return False

        duration = 0.0

    def fake_timing(*a: Any, **kw: Any) -> DummyTiming:
        return DummyTiming()

    monkeypatch.setattr(ibauth.timing, "timing", fake_timing)
    yield


@pytest.fixture(autouse=True)  # type: ignore[misc]
def disable_ibauth_connect(monkeypatch: Any, request: pytest.FixtureRequest) -> Iterator[Mock | None]:
    """
    Patch IBAuth._connect with a Mock for all tests so calls can be tracked.

    Use @pytest.mark.no_patch_connect if you want the original _connect().
    """
    if request.node.get_closest_marker("no_patch_connect"):
        yield None
        return

    mock_connect = Mock(return_value=None)
    monkeypatch.setattr("ibauth.auth.IBAuth._connect", mock_connect)
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
