"""Conector Ruvic para Microsoft Sentinel (incidentes y consultas KQL)."""

from .client import SentinelClient
from .config import ENV_PREFIX, SentinelConfig
from .exceptions import (
    SentinelAuthError,
    SentinelConfigError,
    SentinelConnectorError,
    SentinelDataError,
    SentinelNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "SentinelAuthError",
    "SentinelClient",
    "SentinelConfig",
    "SentinelConfigError",
    "SentinelConnectorError",
    "SentinelDataError",
    "SentinelNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
