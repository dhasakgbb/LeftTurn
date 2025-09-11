"""Top-level package for Azure Excel Data Validation Agent.

This package does not enforce licensing at import time. If you need to enforce
an enterprise license, set `ENFORCE_LICENSE=true` and provide
`LEFTTURN_LICENSE_KEY`. The check is intentionally lenient for CI/tests.
"""

import hashlib
import os
import logging

logger = logging.getLogger(__name__)

_EXPECTED_LICENSE_HASH = "4629e117c5f5e3edbfddb0a10ce44c7b562603b622f515cb0ad0e609f0785f7d"


def _check_license() -> None:
    if os.getenv("ENFORCE_LICENSE", "false").lower() not in {"1", "true", "yes"}:
        return
    key = os.getenv("LEFTTURN_LICENSE_KEY")
    if not key:
        logger.warning("License enforcement enabled but no LEFTTURN_LICENSE_KEY set")
        return
        
    digest = hashlib.sha256(key.encode()).hexdigest()
    if digest != _EXPECTED_LICENSE_HASH:
        raise RuntimeError("Invalid license key")


_check_license()
