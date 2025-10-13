<img src="https://github.com/user-attachments/assets/def9c19a-f270-4b65-92b4-e7de15abe4f6" />

# IBKR Authentication Workflow

![PyPI - Version](https://img.shields.io/pypi/v/ibauth)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/ibauth)](https://pypi.org/project/ibauth/)
![Codecov](https://img.shields.io/codecov/c/github/datawookie/ibauth)

Interactive Brokers provides an extensive
[API](https://www.interactivebrokers.com/campus/ibkr-api-page/webapi-ref/) that
can be used for trading and account management.

It's also possible to authenticate for the API via [OAuth](ib-oauth.pdf).

**ibauth** is a Python client for handling the full **Interactive Brokers (IBKR) Web API authentication flow**.
It wraps the OAuth2 + session lifecycle steps (`access_token`, `bearer_token`, `ssodh_init`, `tickle`, etc.) into a simple, reusable interface.

🔑 Features:
- Obtain and refresh IBKR OAuth2 tokens.
- Manage brokerage sessions (`ssodh_init`, `validate_sso`, `tickle`, `logout`).
- YAML-based configuration (easy to keep credentials outside of code).
- Logging of requests and responses for troubleshooting.

Documentation for the IBKR Web API can be found in the [official reference](https://www.interactivebrokers.com/campus/ibkr-api-page/webapi-ref/).

---

## Requirements

- Python **3.11+**
- A valid IBKR account with Web API access enabled.
- An RSA private key (`.pem`) registered with IBKR.

---

## Installation

You can install either from PyPI (preferred) or GitHub (which may give access to
updates not yet published on PyPI).

```bash
# Install from PyPI.
uv add ibauth
pip install ibauth

# Install from GitHub.
uv add "git+https://github.com/datawookie/ibkr-oauth-flow"
pip install "git+https://github.com/datawookie/ibkr-oauth-flow"
```

---

## Getting Started

The package implements authentication via the `IBAuth` class. There are two
approaches to instantiating this class:

- directly via the constructor or
- using the `auth_from_yaml()` factory function.

### Authenticator Objects

Instantiate a `IBAuth` object (illustrative values for constructor parameters):

```python
from ibauth import IBAuth

auth = IBAuth(
  client_id = "Authenticator-Client",
  client_key_id = "main",
  credential = "DiV7hxH5yXAN5x",
  private_key_file: "/path/to/ibkr-private-key.pem",
)
```

where

- `client_id` — client ID;
- `client_key_id` — key identifier associated with your private key;
- `credential` — credential string; and
- `private_key_file` — path to your RSA private key (`.pem`).

There are a couple of other optional arguments:

- `domain` — the API domain (defaults to `api.ibkr.com` but supports numbered subdomains like `1.api.ibkr.com`, `5.api.ibkr.com`, …; and
- `timeout` — timeout (seconds) applied to all network requests.

### Configuration File

A more flexible approach is to create a YAML configuration file rather than
baking those values into your code. The file might look something like this:

```yaml
client_id: "Authenticator-Client"
client_key_id: "main"
credential: "DiV7hxH5yXAN5x"
private_key_file: "/path/to/ibkr-private-key.pem"
domain: "api.ibkr.com"
```

Then use the factory function:

```python
from ibauth import auth_from_yaml

auth = auth_from_yaml("config.yaml")
```

### Methods

Use the following public methods:

- `connect()` — run the authentication flow to connect to the API; and
- `tickle()` — keep the API connection alive.

### Attributes

These are some useful attributes:

- `bearer_token` — the bearer token acquired during the authentication flow;
- `header` — the authentication header (as a dictionary);
- `authenticated` — are we authenticated?;
- `connected` — are we connected?; and
- `competing` — is there a competing connection?

The `authenticated`, `connected` and `competing` attributes are set and updated by running the `tickle()` method.

## Development

Clone the repo and install dependencies into a virtual environment:

```
git clone https://github.com/datawookie/ibkr-oauth-flow.git
cd ibkr-oauth-flow
uv sync
```

You can test the authentication workflow:

```bash
# Use config.yaml in current directory.
uv run ibauth
# Use config.yaml in home directory and include debugging output.
uv run ibauth --config ~/config.yaml --debug
```

### Test Suite

This project uses pytest. To run the test suite:

```bash
uv run pytest
```

To include coverage:

```bash
uv run pytest --cov=.
```

### Deploy to PyPI

This requires `UV_PUBLISH_TOKEN` to be set to a PyPi token in environment.

```
make deploy
```
