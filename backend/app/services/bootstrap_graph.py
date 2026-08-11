"""Compatibility import for the SOC bootstrap Decision writer."""

from app.services.bootstrap_neo4j import (
    build_bootstrap_decisions,
    write_bootstrap_decisions,
)

__all__ = ["build_bootstrap_decisions", "write_bootstrap_decisions"]
