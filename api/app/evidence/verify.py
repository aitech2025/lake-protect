"""Pack verification. The checker lives in the pipeline package (`lp verify-pack`), written apart
from the pack builder, so the API and anyone outside the system run the same independent check."""
from lake_protect.packverify import verify

__all__ = ["verify"]
