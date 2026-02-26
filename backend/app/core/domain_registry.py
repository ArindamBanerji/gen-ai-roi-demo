"""
Domain Registry — Tracks the active domain module for this demo instance.

In v4.5+, this returns a DomainConfig object. For v3.2, it's a marker.

Usage:
    from app.core.domain_registry import get_active_domain, get_domain_config

    name   = get_active_domain()              # "soc"
    config = get_domain_config()              # SOCDomainConfig (active domain)
    s2p    = get_domain_config("supply_chain") # S2PDomainConfig (by name)
"""
from typing import Optional

from app.domains.soc.config import soc_config
from app.domains.supply_chain.config import s2p_config
from app.domains.base import DomainConfig

ACTIVE_DOMAIN: str = "soc"

# Registry of all available domain configs.
# Add new domains here when they are implemented.
_DOMAIN_CONFIGS = {
    "soc":          soc_config,
    "supply_chain": s2p_config,
}


def get_active_domain() -> str:
    """Return the name of the active domain module."""
    return ACTIVE_DOMAIN


def get_domain_config(domain_name: Optional[str] = None) -> DomainConfig:
    """Return the DomainConfig instance for the active domain, or a named domain.

    Args:
        domain_name: If provided, return config for this domain regardless of
                     ACTIVE_DOMAIN. Raises KeyError if name not in registry.
                     If None (default), return the active domain config.
    """
    name = domain_name if domain_name is not None else ACTIVE_DOMAIN
    return _DOMAIN_CONFIGS[name]
