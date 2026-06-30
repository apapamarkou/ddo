"""Human-readable formatting helpers."""

from __future__ import annotations


def format_bytes(n: int) -> str:
    """Return a human-readable byte count string."""
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KiB"
    if n < 1024**3:
        return f"{n / 1024 ** 2:.1f} MiB"
    return f"{n / 1024 ** 3:.2f} GiB"


def format_package_count(n: int) -> str:
    """Return a grammatically correct package count string."""
    return f"{n} package{'s' if n != 1 else ''}"
