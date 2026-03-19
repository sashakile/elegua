"""Domain exception hierarchy for elegua.

All elegua-specific exceptions inherit from ``EleguaError``, making it
possible to catch any library error with a single ``except EleguaError``.
``SchemaError`` also inherits ``ValueError`` so existing ``except ValueError``
handlers continue to work.
"""

from __future__ import annotations


class EleguaError(Exception):
    """Base for all elegua domain errors."""


class SchemaError(EleguaError, ValueError):
    """TOML/validation schema errors. Inherits ``ValueError`` for backward compat."""


class AdapterError(EleguaError):
    """Adapter execution failures."""


class OracleError(AdapterError):
    """Oracle-specific failures."""
