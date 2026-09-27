"""RelayX — Python client for the RelayX X (Twitter) data API.

    from relayxapi import RelayX
    x = RelayX("YOUR_KEY")
    print(x.user_info("jack")["data"]["followers"])
    for tweet in x.paginate(x.search, "from:nasa", max_pages=3):
        print(tweet["text"])

Docs: https://relayxapi.com/docs/  ·  Get a key: https://relayxapi.com/app/
"""
from __future__ import annotations

from .client import RelayX, RelayXError

__all__ = ["RelayX", "RelayXError"]
__version__ = "0.1.0"
