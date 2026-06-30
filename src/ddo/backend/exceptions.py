"""Custom exception hierarchy for Debian Desktop Optimizer."""

from __future__ import annotations


class DDOError(Exception):
    """Base exception for all DDO errors."""


class AptError(DDOError):
    """Raised when an apt operation fails."""

    def __init__(self, message: str, returncode: int = -1) -> None:
        super().__init__(message)
        self.returncode = returncode


class AptSimulationError(AptError):
    """Raised when apt dry-run simulation fails."""


class DangerousOperationError(DDOError):
    """Raised when a requested operation is deemed unsafe."""


class PackageNotFoundError(DDOError):
    """Raised when a package cannot be found in the apt cache."""


class ConfigurationError(DDOError):
    """Raised when configuration is invalid or missing."""


class DetectionError(DDOError):
    """Raised when system detection fails."""


class PermissionError(DDOError):
    """Raised when elevated privileges are required but not available."""


class LanguageDetectionError(DetectionError):
    """Raised when language/locale detection fails."""


class RollbackError(DDOError):
    """Raised when a rollback operation fails."""
