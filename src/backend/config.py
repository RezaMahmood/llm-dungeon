"""Application configuration, sourced from environment variables / Function App settings."""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration values for Azure AD and Cosmos DB, read from the environment.

    In production these are supplied as Azure Functions application settings
    (configured by 007-azure-infrastructure-provisioning); locally they come
    from a `.env` file (see `.env.example`).
    """

    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
    AZURE_APP_ID = os.environ.get("AZURE_APP_ID", "")
    COSMOS_ENDPOINT = os.environ.get("COSMOS_ENDPOINT", "")

    COSMOS_DATABASE_NAME = os.environ.get("COSMOS_DATABASE_NAME") or os.environ.get("COSMOS_DATABASE") or "llmdungeon"
    ALLOW_LIST_CONTAINER = "allowListEntries"
    CAPABILITY_CONTAINER = "capabilityAssignments"

    JWKS_CACHE_SECONDS = 24 * 60 * 60

    @classmethod
    def issuer(cls) -> str:
        return f"https://login.microsoftonline.com/{cls.AZURE_TENANT_ID}/v2.0"

    @classmethod
    def jwks_uri(cls) -> str:
        return f"https://login.microsoftonline.com/{cls.AZURE_TENANT_ID}/discovery/v2.0/keys"


config = Config()
