import math
from typing import Any
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from tenacity import retry, stop_after_attempt, wait_exponential

from .const import GRANT_TYPE, CLIENT_ASSERTION_TYPE, SCOPE, VALID_DOMAINS, DEFAULT_DOMAIN
from .logger import logger
from .timing import timing
from .util import make_jws, get, post, ReadTimeout, HTTPError


class IBAuth:
    """
    Handle the Interactive Brokers (IBKR) Web API OAuth authentication workflow.

    This class encapsulates the OAuth2 and session lifecycle required to
    interact with the IBKR Web API. It manages loading the private key,
    retrieving and refreshing tokens, establishing a brokerage session,
    and maintaining it via keep-alive requests.

    Args:
        client_id (str): Application client ID issued by IBKR.
        client_key_id (str): Identifier for the private key registered with IBKR.
        credential (str): IBKR credential string used for authentication.
        private_key_file (str | Path): Path to the RSA private key file (PEM format).
        domain (str, optional): IBKR API domain (default: `api.ibkr.com`).

    Raises:
        ValueError: If any required parameter is missing or invalid.
    """

    def __init__(
        self,
        client_id: str,
        client_key_id: str,
        credential: str,
        private_key_file: str | Path,
        domain: str = DEFAULT_DOMAIN,
    ):
        if not client_id:
            raise ValueError("Required parameter 'client_id' is missing.")

        if not client_key_id:
            raise ValueError("Required parameter 'client_key_id' is missing.")

        if not credential:
            raise ValueError("Required parameter 'credential' is missing.")

        if not private_key_file:
            raise ValueError("Required parameter 'private_key_file' is missing.")

        if domain not in VALID_DOMAINS:
            raise ValueError(f"Invalid domain: {domain}.")
        else:
            self.domain = domain

        self.client_id = client_id
        self.client_key_id = client_key_id
        self.credential = credential

        logger.info(f"Load private key from {private_key_file}.")
        with open(private_key_file, "r") as file:
            self.private_key = serialization.load_pem_private_key(
                file.read().encode(),
                password=None,
            )

        self.access_token: str | None = None
        self.bearer_token: str | None = None

        # These fields are set in the tickle() method.
        #
        self.authenticated = None
        self.connected = None
        self.competing = None

        self.IP = None

        self._connect()

    @property
    def url_oauth2(self) -> str:
        return f"https://{self.domain}/oauth2"

    @property
    def url_gateway(self) -> str:
        return f"https://{self.domain}/gw"

    @property
    def url_client_portal(self) -> str:
        return f"https://{self.domain}"

    @property
    def domain(self) -> str:
        return self._domain

    @domain.setter
    def domain(self, value: str) -> None:
        """
        Set and validate the domain.
        """
        if value not in VALID_DOMAINS:
            raise ValueError(f"Invalid domain: {value}. Must be one of {VALID_DOMAINS}.")
        logger.info(f"Domain: {value}")
        self._domain = value

    def _check_ip(self) -> Any:
        """
        Get public IP address.
        """
        logger.debug("Check public IP.")
        IP = get("https://api.ipify.org", timeout=10).content.decode("utf8")

        logger.info(f"Public IP: {IP}.")
        if self.IP and self.IP != IP:
            logger.warning("🚨 Public IP has changed.")

        self.IP = IP
        return IP

    def _compute_jws(self, claims: dict[str, Any], url: str, exp: int = 0, iat: int = 0) -> Any:
        """
        Args:
            claims (dict[str, any]): The claims to include in the JWS.
            url (str): The URL for which the JWS is being created.
            exp (int, optional): The expiration time offset for the JWS. Defaults to 0.
            iat (int, optional): The issued-at time offset for the JWS. Defaults to 0.
        """
        now = math.floor(time.time())
        header = {"alg": "RS256", "typ": "JWT", "kid": f"{self.client_key_id}"}

        claims["exp"] = now + exp
        claims["iat"] = now + iat

        logger.debug(f"Header: {header}.")
        logger.debug(f"Claims: {claims}.")

        return make_jws(header, claims, self.private_key)

    def get_access_token(self) -> None:
        """
        Obtain an OAuth 2.0 access token.
        """
        url = f"{self.url_oauth2}/api/v1/token"

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        claims = {
            "iss": f"{self.client_id}",
            "sub": f"{self.client_id}",
            "aud": "/token",
        }

        form_data = {
            "grant_type": GRANT_TYPE,
            "client_assertion": self._compute_jws(claims, url, exp=20, iat=-10),
            "client_assertion_type": CLIENT_ASSERTION_TYPE,
            "scope": SCOPE,
        }

        logger.info("Request access token.")
        response = post(url=url, headers=headers, data=form_data)

        # TODO: Add Pydantic model for response.
        self.access_token = response.json()["access_token"]

    def get_bearer_token(self) -> None:
        """
        Create a new SSO session.
        """
        url = f"{self.url_gateway}/api/v1/sso-sessions"

        headers = {
            "Authorization": "Bearer " + self.access_token,  # type: ignore
            "Content-Type": "application/jwt",
        }

        # Initialise IP (it's embedded in the bearer token).
        self._check_ip()

        claims = {
            "ip": self.IP,
            "credential": f"{self.credential}",
            # TODO: Check if iss parameter actually required.
            "iss": f"{self.client_id}",
        }

        logger.info("Request bearer token.")
        response = post(url=url, headers=headers, data=self._compute_jws(claims, url, exp=86400))

        # TODO: Add Pydantic model for response.
        self.bearer_token = response.json()["access_token"]

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=5))  # type: ignore
    def ssodh_init(self) -> None:
        """
        Initialise a brokerage session.
        """
        url = f"{self.url_client_portal}/v1/api/iserver/auth/ssodh/init"

        headers = {
            "Authorization": "Bearer " + self.bearer_token,  # type: ignore
            "User-Agent": "python/3.11",
        }

        logger.info("Initiate a brokerage session.")
        try:
            response = post(url=url, headers=headers, json={"publish": True, "compete": True})
            response.raise_for_status()
        except HTTPError:
            logger.error("⛔ Error initiating a brokerage session.")
            raise

        logger.debug(f"Response content: {response.json()}.")

    def validate_sso(self) -> None:
        url = f"{self.url_client_portal}/v1/api/sso/validate"

        headers = {
            "Authorization": "Bearer " + self.bearer_token,  # type: ignore
            "User-Agent": "python/3.11",
        }

        logger.info("Validate brokerage session.")
        response = get(url=url, headers=headers)

        logger.debug(f"Response content: {response.json()}.")

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=5))  # type: ignore
    def tickle(self) -> str:
        """
        Keeps session alive.

        Returns:
            Session ID.
        """
        url = f"{self.url_client_portal}/v1/api/tickle"

        headers = {
            "Authorization": "Bearer " + self.bearer_token,  # type: ignore
            "User-Agent": "python/3.11",
        }

        try:
            # Ping the API and record RTT (round trip time).
            logger.info("🔔 Send tickle.")
            with timing() as duration:
                response = get(url=url, headers=headers, timeout=10)
            logger.info(f"⏳ Tickle RTT: {duration.duration:.3f} s [status={response.status_code}]")
            response.raise_for_status()
        except (HTTPError, ReadTimeout):
            logger.error("⛔ Error connecting to session.")
            self._connect()
            raise

        self.session_id: str = response.json()["session"]
        auth_status = response.json()["iserver"]["authStatus"]
        self.authenticated = auth_status["authenticated"]
        self.competing = auth_status["competing"]
        self.connected = auth_status["connected"]

        logger.debug(f"Session ID: {self.session_id}")
        logger.debug(f"- authenticated: {self.authenticated}")
        logger.debug(f"- competing:     {self.competing}")
        logger.debug(f"- connected:     {self.connected}")

        logger.debug(f"Response content: {response.json()}.")

        return self.session_id

    def logout(self) -> None:
        url = f"{self.url_client_portal}/v1/api/logout"

        if self.bearer_token is None:
            logger.warning("🚨 Not terminating brokerage session (no bearer token found).")
            return

        headers = {
            "Authorization": "Bearer " + self.bearer_token,
            "User-Agent": "python/3.11",
        }

        logger.info("Terminate brokerage session.")
        post(url=url, headers=headers)

    def _connect(self) -> None:
        """
        Connect to the brokerage API.
        """
        self.get_access_token()
        self.get_bearer_token()
        self.ssodh_init()
        self.validate_sso()
