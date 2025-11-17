"""
Centralized display names for Phoenix apps, used only in the header.

Best practices:
- Keep a single source of truth here.
- Provide multiple resolution strategies (path prefix, blueprint, endpoint)
    so display names are robust to routing structure.
"""
from typing import Optional

# Ordered list of (prefix, display_name) tuples; first match wins
DISPLAY_NAME_PREFIXES = [
    ('/derplexity', 'Derplexity'),
]

# Fallback mapping by Flask blueprint name
BLUEPRINT_DISPLAY_NAMES = {
    'subscription': 'Subscription',
    'stripe': 'Subscription',
}

# Fallback mapping by Flask endpoint (function) name
ENDPOINT_DISPLAY_NAMES = {
    'derplexity': 'Derplexity',
    'derplexity_enhanced': 'Derplexity',
    'derplexity_legacy': 'Derplexity',
}


def get_display_name(path: Optional[str], blueprint: Optional[str] = None, endpoint: Optional[str] = None) -> Optional[str]:
    """Return the app display name using path, blueprint, or endpoint.

    Order: path prefix -> blueprint -> endpoint.
    """
    # 1) Path-based
    if path:
        for prefix, name in DISPLAY_NAME_PREFIXES:
            if path.startswith(prefix):
                return name

    # 2) Blueprint-based
    if blueprint and blueprint in BLUEPRINT_DISPLAY_NAMES:
        return BLUEPRINT_DISPLAY_NAMES[blueprint]

    # 3) Endpoint-based
    if endpoint and endpoint in ENDPOINT_DISPLAY_NAMES:
        return ENDPOINT_DISPLAY_NAMES[endpoint]

    return None
