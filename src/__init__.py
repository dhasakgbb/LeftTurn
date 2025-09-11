"""Top-level package for Azure Excel Data Validation Agent."""

import hashlib
import os

_EXPECTED_LICENSE_HASH = (
    "4629e117c5f5e3edbfddb0a10ce44c7b562603b622f515cb0ad0e609f0785f7d"
)


def _check_license() -> None:
    key = os.getenv("LEFTTURN_LICENSE_KEY")
    if not key:
        raise RuntimeError("LEFTTURN_LICENSE_KEY environment variable is required")
    digest = hashlib.sha256(key.encode()).hexdigest()
    if digest != _EXPECTED_LICENSE_HASH:
        raise RuntimeError("Invalid license key")


_check_license()
