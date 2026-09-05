"""Application configuration, sourced from environment variables — Function App
settings in production, a local `.env` file in development.
"""

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
    PROVISIONED_ACCOUNTS_CONTAINER = "provisionedAccountEntries"
    STORY_DRAFTS_CONTAINER = "storyDrafts"
    STORIES_CONTAINER = "stories"
    SEED_ADMIN_EMAIL = os.environ.get("SEED_ADMIN_EMAIL", "")
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "")

    AZURE_AI_FOUNDRY_ENDPOINT = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT", "")
    AZURE_AI_FOUNDRY_DEPLOYMENT_NAME = os.environ.get("AZURE_AI_FOUNDRY_DEPLOYMENT_NAME", "")
    LLM_INPUT_TOKEN_PRICE_USD = float(os.environ.get("LLM_INPUT_TOKEN_PRICE_USD", "0") or "0")
    LLM_OUTPUT_TOKEN_PRICE_USD = float(os.environ.get("LLM_OUTPUT_TOKEN_PRICE_USD", "0") or "0")

    JWKS_CACHE_SECONDS = 24 * 60 * 60

    # Microsoft's fixed, well-known tenant ID representing every personal
    # Microsoft account (MSA) — not this project's own tenant. The app
    # registration's signInAudience is AzureADandPersonalMicrosoftAccount
    # (spec.md: "it must be a microsoft account", not restricted to this
    # org), so a token from a personal account (e.g. the seed administrator's
    # own @hotmail.com/@outlook.com/@live.com address) carries this tenant ID
    # as `tid`/`iss`, never AZURE_TENANT_ID. Validating against AZURE_TENANT_ID
    # alone rejects every personal-account sign-in outright.
    MICROSOFT_CONSUMERS_TENANT_ID = "9188040d-6c67-4c5b-b112-36a304b66dad"

    @classmethod
    def valid_issuers(cls) -> tuple[str, str]:
        return (
            f"https://login.microsoftonline.com/{cls.AZURE_TENANT_ID}/v2.0",
            f"https://login.microsoftonline.com/{cls.MICROSOFT_CONSUMERS_TENANT_ID}/v2.0",
        )

    @classmethod
    def valid_audiences(cls) -> tuple[str, str]:
        # The frontend requests the `api://{clientId}/access_as_user` scope
        # (msalConfig.js) so the access token's audience is this app itself
        # rather than Microsoft Graph. Which literal value Entra ID stamps into
        # `aud` for that token — the bare client ID GUID, or the App ID URI
        # (`api://{clientId}`) — depends on the app registration's
        # accessTokenAcceptedVersion manifest setting, not on anything this
        # repo controls. Accepting either form here means a valid token is
        # never rejected purely because of that manifest detail (#212: every
        # login was hitting 401 from /api/auth/me because only the bare GUID
        # was accepted).
        return (cls.AZURE_APP_ID, f"api://{cls.AZURE_APP_ID}")

    @classmethod
    def jwks_uri(cls) -> str:
        # /common/ rather than the org-specific tenant: signing keys for both
        # organizational and personal-account (consumers) v2.0 tokens are
        # published from this shared endpoint.
        return "https://login.microsoftonline.com/common/discovery/v2.0/keys"


config = Config()
