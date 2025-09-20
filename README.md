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

## Configuration

Authentication parameters are supplied via a YAML configuration file:

```
client_id: "your-client-id"
client_key_id: "your-client-key-id"
credential: "your-credential"
private_key_file: "/path/to/privatekey.pem"
domain: "api.ibkr.com"
```

- **client_id**: Application client ID from IBKR.
- **client_key_id**: Key identifier associated with your private key.
- **credential**: IBKR credential string.
- **private_key_file**: Path to your RSA private key (`.pem`).
- **domain**: Usually `api.ibkr.com`, but IBKR supports numbered subdomains
  (`1.api.ibkr.com`, `5.api.ibkr.com`, …).

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
