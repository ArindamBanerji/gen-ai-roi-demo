"""Deprecated: renamed to graph_client.py.

This file exists only for backward compatibility during migration.
Import from app.db.graph_client instead.
"""

from app.db.graph_client import *  # noqa: F401,F403
from app.db.graph_client import graph_client as neo4j_client  # noqa: F401
