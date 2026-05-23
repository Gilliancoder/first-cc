"""Microsoft Graph API authentication helper.
Uses OAuth2 device code flow — works with personal Outlook.com accounts."""

import msal
from config import MS_GRAPH_CLIENT_ID, MS_GRAPH_TENANT_ID, MS_GRAPH_USER_ID

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
SCOPES = ["Mail.Read"]


def get_access_token() -> str:
    """Get access token via device code flow (cached to disk)."""
    if not MS_GRAPH_CLIENT_ID:
        raise ValueError("MS_GRAPH_CLIENT_ID is required. Register an app at https://portal.azure.com")

    cache = msal.SerializableTokenCache()

    # Load cached tokens
    import os
    cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", ".cache")
    os.makedirs(cache_path, exist_ok=True)
    token_file = os.path.join(cache_path, "ms_graph_token.bin")
    if os.path.exists(token_file):
        with open(token_file, "r") as f:
            cache.deserialize(f.read())

    authority = f"https://login.microsoftonline.com/{MS_GRAPH_TENANT_ID or 'consumers'}"
    app = msal.PublicClientApplication(MS_GRAPH_CLIENT_ID, authority=authority, token_cache=cache)

    # Try silent acquire first
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result:
            with open(token_file, "w") as f:
                f.write(cache.serialize())
            return result["access_token"]

    # Device code flow
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(f"Device flow failed: {flow.get('error_description', flow)}")

    print(f"\n{'='*60}")
    print(f"  Microsoft 设备登录")
    print(f"{'='*60}")
    print(f"  1. 打开浏览器访问: {flow['verification_uri']}")
    print(f"  2. 输入代码: {flow['user_code']}")
    print(f"{'='*60}\n")

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(f"Login failed: {result.get('error_description', result)}")

    with open(token_file, "w") as f:
        f.write(cache.serialize())

    print("[auth] Token acquired and cached")
    return result["access_token"]


def get_user_id() -> str:
    """Get user ID from config, or fetch from /me if using 'me'."""
    if MS_GRAPH_USER_ID in ("", "me", None):
        return "me"
    return MS_GRAPH_USER_ID
