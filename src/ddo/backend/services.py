"""System service detection and management."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """Information about a systemd service."""

    name: str
    description: str
    active: bool
    enabled: bool
    can_disable: bool = True


# Services that should never be touched
_PROTECTED_SERVICES: frozenset[str] = frozenset(
    {
        "systemd-journald",
        "systemd-logind",
        "systemd-udevd",
        "dbus",
        "network-manager",
        "ssh",
        "sshd",
    }
)

# Optional services that can safely be disabled
_OPTIONAL_SERVICES: dict[str, str] = {
    "bluetooth": "Bluetooth daemon",
    "cups": "CUPS printing daemon",
    "cups-browsed": "CUPS network printer discovery",
    "ModemManager": "Mobile broadband modem manager",
    "avahi-daemon": "mDNS/DNS-SD network discovery (Bonjour)",
    "geoclue": "Geolocation service",
    "speech-dispatcher": "Text-to-speech service",
    "pcscd": "PC/SC Smart Card daemon",
}


class ServiceManager:
    """Query and manage systemd services."""

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10)

    def list_optional_services(self) -> list[ServiceInfo]:
        """Return status info for each optional service."""
        services: list[ServiceInfo] = []
        for svc_name, description in _OPTIONAL_SERVICES.items():
            active = self._is_active(svc_name)
            enabled = self._is_enabled(svc_name)
            services.append(
                ServiceInfo(
                    name=svc_name,
                    description=description,
                    active=active,
                    enabled=enabled,
                    can_disable=svc_name not in _PROTECTED_SERVICES,
                )
            )
        return services

    def _is_active(self, name: str) -> bool:
        r = self._run(["systemctl", "is-active", "--quiet", name])
        return r.returncode == 0

    def _is_enabled(self, name: str) -> bool:
        r = self._run(["systemctl", "is-enabled", "--quiet", name])
        return r.returncode == 0

    def disable(self, name: str) -> None:
        """Disable and stop a service."""
        if name in _PROTECTED_SERVICES:
            raise ValueError(f"Cannot disable protected service: {name}")
        subprocess.run(["systemctl", "disable", "--now", name], check=False)
        logger.info("Disabled service: %s", name)

    def enable(self, name: str) -> None:
        """Enable and start a service."""
        subprocess.run(["systemctl", "enable", "--now", name], check=False)
        logger.info("Enabled service: %s", name)
