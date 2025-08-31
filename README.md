# IBKR Authentication Workflow

[![codecov](https://codecov.io/gh/datawookie/ibauth/branch/master/graph/badge.svg)](https://codecov.io/gh/datawookie/ibauth)

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

Dependencies are listed in `requirements.txt`.

---

## Installation

You can install either from PyPI (preferred) or GitHub (which may give access to
updates not yet published on PyPI).

```bash
# Install from PyPI.
pip install ibauth

# Install from GitHub.
pip install git+https://github.com/datawookie/ibkr-oauth-flow
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
- **domain**: Usually `api.ibkr.com`, but IBKR supports numbered subdomains (`1.api.ibkr.com`, `5.api.ibkr.com`, …).

---

## How It Works

The IBKR Web API requires multiple steps to establish and maintain a brokerage session.
`ibauth` automates these steps:

1. **Access Token**
   Exchange your client credentials + JWS for an **access token**.
   → `auth.get_access_token()`

2. **Bearer Token**
   Use the access token and your public IP to obtain a **bearer token**.
   → `auth.get_bearer_token()`

3. **Session Initialisation**
   Start a brokerage session using the bearer token.
   → `auth.ssodh_init()`

4. **Session Validation (optional)**
   Confirm that your session is active.
   → `auth.validate_sso()`

5. **Keepalive ("Tickle")**
   Periodically ping the API to keep the session alive.
   → `auth.tickle()`

6. **Logout**
   End the session when finished.
   → `auth.logout()`

```
    +--------------+        +--------------+        +---------------+
    |  Access      |        |  Bearer      |        |  Brokerage    |
    |  Token       | -----> |  Token       | -----> |  Session      |
    +--------------+        +--------------+        +---------------+
           |                        |                        |
           v                        v                        v
    get_access_token()     get_bearer_token()       ssodh_init() / tickle()
```

---

## Quick Start

```python
import logging
import time
import ibauth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)7s] %(message)s",
)

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("charset_normalizer").setLevel(logging.WARNING)

if __name__ == "__main__":
    auth = ibauth.auth_from_yaml("config.yaml")

    auth.get_access_token()
    auth.get_bearer_token()

    auth.ssodh_init()
    auth.validate_sso()

    # Keep session alive
    for _ in range(3):
        auth.tickle()
        time.sleep(10)

    # Dynamically change the API domain
    auth.domain = "5.api.ibkr.com"
    auth.tickle()

    auth.logout()
```

## Testing

This project uses pytest. To run the test suite:

```
pytest
```

To include coverage:

pytest --cov=src/ibauth --cov-report=term-missing

## Development

Clone the repo and install dependencies into a virtual environment:

```
git clone https://github.com/datawookie/ibkr-oauth-flow.git
cd ibkr-oauth-flow
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Deploy to PyPI

This requires `UV_PUBLISH_TOKEN` to be set to a PyPi token in environment.

Publishing requires a PyPI token (UV_PUBLISH_TOKEN) to be available in your
environment.

```
make deploy
```
