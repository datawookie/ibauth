import asyncio
import yaml
from pathlib import Path

from .const import DEFAULT_DOMAIN
from .logger import logger
from .auth import IBAuth
from .util import AuthenticationError

__all__ = [
    "IBAuth",
    "auth_from_yaml",
]


def auth_from_yaml(path: str | Path) -> IBAuth:
    """
    Create an IBAuth instance from a YAML configuration file.

    Args:
        path (str | Path): The path to the YAML configuration file.

    Returns:
        IBAuth: An instance of IBAuth.
    """
    path_absolute = Path(path).resolve()
    logger.debug(f"Load configuration from {path_absolute}.")
    with open(path_absolute, "r") as f:
        config = yaml.safe_load(f)

    return IBAuth(
        client_id=config["client_id"],
        client_key_id=config["client_key_id"],
        credential=config["credential"],
        private_key_file=config["private_key_file"],
        domain=config.get("domain", DEFAULT_DOMAIN),
    )


def main() -> None:  # pragma: no cover
    import argparse
    import sys
    import logging

    parser = argparse.ArgumentParser(description="IBAuth Command Line Interface")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to the YAML configuration file.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )

    async def run() -> None:
        try:
            auth = auth_from_yaml(args.config)
            await auth.connect()
            logger.info(f"- IP: {auth.IP}")
            logger.info(f"- domain: {auth.domain}")
            logger.info(f"- header: {auth.header}")
            logger.info("✅ Successfully created IBAuth instance and connected.")
            await auth.tickle()
        except AuthenticationError:
            logger.error("🚨 Failed to create IBAuth instance.")
            sys.exit(1)

    asyncio.run(run())
