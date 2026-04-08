"""Custom exception hierarchy for tasekit."""


class TaseError(Exception):
    """Base exception for all tasekit errors."""


class TaseNetworkError(TaseError):
    """HTTP or connectivity error when communicating with the TASE API."""


class TaseParsingError(TaseError):
    """The API response could not be parsed (unexpected format)."""


class SecurityNotFoundError(TaseError):
    """The requested security ID returned no data or is invalid."""
