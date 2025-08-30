from typing import Any, Iterator

import pytest
import tenacity

# Disable all retries.
tenacity.retry = lambda *a, **kw: (lambda f: f)


@pytest.fixture(autouse=True)  # type: ignore[misc]
def disable_timing() -> None:
    import ibauth.timing

    ibauth.timing.timing = lambda *a, **kw: (lambda f: f)


@pytest.fixture(autouse=True)  # type: ignore[misc]
def disable_ibauth_connect(monkeypatch: Any, request: pytest.FixtureRequest) -> Iterator[None]:
    """
    Patch IBAuth._connect to do nothing for all tests.
    """
    if request.node.get_closest_marker("no_patch_connect"):
        # An escape hatch: use this marker and patch will not be applied.
        yield
        return

    monkeypatch.setattr("ibauth.auth.IBAuth._connect", lambda self: None)
    yield
