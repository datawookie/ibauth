from http import HTTPStatus
import math
from typing import Any
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from .const import GRANT_TYPE, CLIENT_ASSERTION_TYPE, SCOPE, VALID_DOMAINS, DEFAULT_DOMAIN
from .logger import logger
from .timing import AsyncTimer
from .util import make_jws, get, post, ReadTimeout, HTTPStatusError
from .models import SessionDetailsModel


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
        timeout: float = 10.0,
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
            self._domain = domain

        self.client_id = client_id
        self.client_key_id = client_key_id
        self.credential = credential
        self.timeout = timeout

        logger.debug(f"Load private key from {private_key_file}.")
        with open(private_key_file, "r") as file:
            self.private_key = serialization.load_pem_private_key(
                file.read().encode(),
                password=None,
            )

        self.access_token: str | None = None
        self.bearer_token: str | None = None

        # These fields are set in the tickle() method.
        #
        self.authenticated: bool | None = None
        self.connected: bool | None = None
        self.competing: bool | None = None

        self.IP = None

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
    def header(self) -> dict[str, str]:
        """
        Return the authorization header for API requests.
        """
        if self.bearer_token is None:
            raise ValueError("⛔ No bearer token found. Please connect first.")
        return {"Authorization": "Bearer " + self.bearer_token}

    @property
    def domain(self) -> str:
        return self._domain

    def is_connected(self) -> bool:
        return self.connected and self.authenticated  # type: ignore[return-value]

    @domain.setter  # type: ignore[no-redef,attr-defined,misc]
    def domain(self, value: str) -> None:
        """
        Set and validate the domain.
        """
        if value not in VALID_DOMAINS:
            raise ValueError(f"Invalid domain: {value}. Must be one of {VALID_DOMAINS}.")
        logger.info(f"Domain: {value}")
        self._domain = value

    async def _check_ip(self) -> Any:
        """
        Get public IP address.
        """
        logger.debug("Check public IP.")
        IP = (await get("https://api.ipify.org", timeout=self.timeout)).content.decode("utf8")

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

        logger.debug(f"Create JWS for {url}.")
        logger.debug(f"  - header: {header}.")
        logger.debug(f"  - claims: {claims}.")

        return make_jws(header, claims, self.private_key)

    async def get_access_token(self) -> None:
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

        logger.info(f"Request access token ({url}).")
        response = await post(url=url, headers=headers, data=form_data)

        # TODO: Add Pydantic model for response.
        self.access_token = response.json()["access_token"]

    async def get_bearer_token(self) -> None:
        """
        Create a new SSO session.
        """
        url = f"{self.url_gateway}/api/v1/sso-sessions"

        headers = {
            "Authorization": "Bearer " + self.access_token,  # type: ignore
            "Content-Type": "application/jwt",
        }

        # Initialise IP (it's embedded in the bearer token).
        await self._check_ip()

        claims = {
            "ip": self.IP,
            "credential": f"{self.credential}",
            # TODO: Check if iss parameter actually required.
            "iss": f"{self.client_id}",
        }

        logger.info(f"Request bearer token ({url}).")
        response = await post(url=url, headers=headers, data=self._compute_jws(claims, url, exp=86400))
        logger.info("🟢 Brokerage session initiated.")

        # TODO: Add Pydantic model for response.
        self.bearer_token = response.json()["access_token"]

    async def validate_sso(self) -> None:
        url = f"{self.url_client_portal}/v1/api/sso/validate"

        headers = {
            "Authorization": "Bearer " + self.bearer_token,  # type: ignore
            "User-Agent": "python/3.11",
        }

        logger.info(f"Validate brokerage session ({url}).")
        response = await get(url=url, headers=headers)  # noqa: F841

        # Extract session details.
        session = SessionDetailsModel(**response.json())
        logger.debug("Session details:")
        logger.debug(f"  - User: {session.USER_NAME}")

    async def ssodh_init(self) -> None:
        """
        Initialise a brokerage session.

        There is apparently a "known issue", where new paper trading accounts
        can get a 500 error on this endpoint. According to IBKR support they
        'have seen this issue typically resolve itself out after a week or 2',
        which seems a rather organic and unreliable way to handle it.
        """
        url = f"{self.url_client_portal}/v1/api/iserver/auth/ssodh/init"

        headers = {
            "Authorization": "Bearer " + self.bearer_token,  # type: ignore
            "User-Agent": "python/3.11",
        }

        logger.info(f"Initialise a brokerage session ({url}).")
        try:
            response = await post(url=url, headers=headers, json={"publish": True, "compete": True})
        except HTTPStatusError as error:
            status_code = error.response.status_code
            logger.error(f"⛔ Error initialising brokerage session (status={status_code}).")
            raise

        logger.debug(f"Response content: {response.json()}.")

    async def tickle(self) -> str:
        """
        Keeps session alive.

        Returns:
            Session ID.
        """
        url = f"{self.url_client_portal}/v1/api/tickle"

        headers = {
            "User-Agent": "python/3.11",
            **self.header,
        }

        try:
            # Ping the API and record RTT (round trip time).
            async with AsyncTimer() as duration:
                response = await get(url=url, headers=headers, timeout=self.timeout)
            logger.info(f"🔔 Tickle (RTT: {duration.duration:.3f} s) [status={response.status_code}]")
        except HTTPStatusError as error:
            status_code = error.response.status_code
            if status_code == HTTPStatus.UNAUTHORIZED:
                logger.error("⛔ Unauthorised.")
                # Infer updated status.
                self.authenticated = False
                self.competing = None
                self.connected = False
            else:
                logger.error(f"⛔ Error connecting to session in tickle (status={status_code}): {error}.")
            raise
        except ReadTimeout:
            logger.error("⛔ Timeout connecting to session in tickle.")
            raise

        self.session_id: str = response.json()["session"]
        auth_status = response.json()["iserver"]["authStatus"]
        self.authenticated = auth_status["authenticated"]
        self.competing = auth_status["competing"]
        self.connected = auth_status["connected"]

        def _bool_to_symbol(value: bool | None) -> str:
            return "✅" if value else "⚠️" if value is False else "🚨"

        logger.info(f"- Session ID: {self.session_id}")
        logger.info(f"  * authenticated: {self.authenticated!s:^5} {_bool_to_symbol(self.authenticated)}")
        logger.info(f"  * competing:     {self.competing!s:^5} {_bool_to_symbol(not self.competing)}")
        logger.info(f"  * connected:     {self.connected!s:^5} {_bool_to_symbol(self.connected)}")

        logger.debug(f"Response content: {response.json()}.")

        # Check if still authenticated.
        if not self.authenticated:
            #
            # It's not clear why one would be disconnected if you're keeping the
            # connection open with regular requests but it does seem to happen
            # from time to time.
            #
            # This is what I have observed:
            #
            # 1. You start getting 500 ("Please query /accounts first") errors.
            # 2. On next tickle you find that you are neither connected nor
            #    authenticated.
            # 3. After the tickle you might start getting 401 ("not authenticated") errors.
            #
            logger.error("⛔ Not authenticated.")
            await self.connect()

        return self.session_id

    async def logout(self) -> None:
        url = f"{self.url_client_portal}/v1/api/logout"

        if self.bearer_token is None:
            logger.warning("🚨 Not terminating brokerage session (no bearer token found).")
            return

        headers = {
            "Authorization": "Bearer " + self.bearer_token,
            "User-Agent": "python/3.11",
        }

        try:
            await post(url=url, headers=headers)
        except HTTPStatusError as error:
            status_code = error.response.status_code
            if status_code == 401:
                # We are no longer authenticated, so can't terminate the session.
                logger.warning("🚨 Can't terminate brokerage session (not authenticated).")
            else:
                logger.error("⛔ Error terminating brokerage session.")
                raise
        else:
            logger.info("🔴 Brokerage session terminated.")

    async def connect(self) -> None:
        """
        Connect to the brokerage API.
        """
        await self.get_access_token()
        await self.get_bearer_token()
        await self.validate_sso()
        await self.ssodh_init()
