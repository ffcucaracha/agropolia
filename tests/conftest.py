import os

import pytest


def pytest_collection_modifyitems(config, items):
    if os.getenv("AGROPOLIA_RUN_INTEGRATION") == "1":
        return
    marker = pytest.mark.skip(reason="integration/security tests require PostgreSQL, Redis and NATS")
    for item in items:
        path = str(item.fspath)
        if "/integration/" in path or "/security/" in path:
            item.add_marker(marker)
