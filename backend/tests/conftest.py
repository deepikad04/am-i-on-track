"""Shared test fixtures — mock boto3 so tests run without AWS credentials."""

import sys
from unittest.mock import MagicMock

# Mock external dependencies before any app module tries to import them
for mod_name in [
    "boto3", "botocore", "botocore.exceptions", "botocore.config",
    "aiofiles", "pypdf",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()
