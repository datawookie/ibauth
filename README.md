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

## API Gateway

https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#gw-step-one

> Basically during the process the java app creates a local address to which you use as the base URL. The java app then handles all the encrypted stuff between it and IBKR.  Once the portal is setup, then you need to go to it, and there will be a loing page, you need to input your details and submit, I used Python believe it or not, with Selenium. At that stage the warning bells should have rung that Matlab could not do this, hence having to do Python.  And no ChatGPT back then, it was shit hard figure it out.  Dunno how I did it, must have been all thos monkeys typing random stuff on those keyboards.  Anyhow, then when you submite, they requre authentication.  Forpaper trading account you could use and SMS code, and this could be achieved through google messages, no hardware needed.  BUT, when it came to live acounts, that is 2FA, straight through their app and it pops up asking you to click, then to ask if you want to proceed, then provide your fingerprint.  That is where the robot came in.

> When OAuth is selected as an authentication method with IBKR, this is typically allocated to a FA (Financial Advisor) account, which may have 1 or more client accounts under its control. Typically the FA account will have have paid data subscriptions which provide real-time market data, and this may be applied in the trading functions on all the client accounts. The FA account directs trading on behalf of the client accounts, with their allocated capital.

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
- **domain**: Usually `api.ibkr.com`, but IBKR supports numbered subdomains
  (`1.api.ibkr.com`, `5.api.ibkr.com`, …).

## Setting us RSA Keys

To register for OAuth 2.0 access you'll need to generate a RSA key pair.

First create a private key.

```bash
openssl genrsa -out privatekey.pem 3072
```

That'll write the private key to a file named `privatekey.pem`. The key size
will be 3072 bits. This is a reasonable choice for a relatively secure key and
is stronger than the common 2048 bit size. You can choose a larger key size (for
example, 4096 bits) if you want.

The file contains a PEM-encoded text representation of the key and will look something like
this (for illustration only!):

```
-----BEGIN PRIVATE KEY-----
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
I/j7w625XNINkx5E1qLDyQ==
-----END PRIVATE KEY-----
```

As the name implies, this is a _private_ key and so should not be shared. You
should keep this somewhere secure.

Next create the corresponding public key.


```bash
openssl rsa -pubout -in privatekey.pem -out publickey.pem -outform PEM
```

The contents of the public key will look something like this:

```
-----BEGIN PUBLIC KEY-----
MIIBojANBgkqhkiG9w0BAQEFAAOCAY8AMIIBigKCAYEAyrYRpPxUKT7jAMFzEHCb
05pJ4xNZl/eOHA1xuItL7MheIWMlOBgoxQnhTnEKrtTk1jAbYbljOEYrlHxq81AO
ijTxIT8quyVD2l9NZQ2HpOLWxUs598hG/LadKYqXwM3HqypoTucqNTRijxvjQ+s2
akVlrXLcMAZsoYxx4ZM8MvsPbCg513UgsfEwf7jdfO3mr9ojH75JYxdadZet5arR
2Kvtqb2PzCOfnsxJkwVzj6h6m/V42R8X9xOcEAOIJo2Tts1ZV3JN7YPVMwxvxFhn
D4X5CGn922F7YzzYtfkN653sD2brATNIO/+n+sxyBenYjUvnjp/LelF5JXNIORRL
xkF0J5N/j23XE5I644b2UzdrH4RxWdtmWiIh+bUcpScDS0jYnGTluUNBTYGA4rFs
JFRf3uDgwIZMPHtqG4KoOC/sB78tZXGpoQ5oz42lzjHJi2B+dL8XsevVwg6eVB5v
ccvAhDHrO+N5sc9/BV3R+HeIRVm19CpG9YVB3alk0PnPAgMBAAE=
-----END PUBLIC KEY-----
```

Again, as the name implies, this is a _public_ key and can be shared freely.

You'll need to upload this public key onto the IBKR platform.

1. Login to www.ibkr.com.
2. Click the “Bell” Icon.
3. Messages
4. Compose a New Ticket for API
5. Paste the contents of your RSA public key.
6. Notify IBKR of the ticket.
7. Wait patiently.

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

## API Error Codes

- `500` `Please query /accounts first`
- `401` `not authenticated`
