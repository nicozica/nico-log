from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Callable


SERVICE_NAME = "nico-log-build.service"
STATUS_COMMAND = ("/usr/bin/systemctl", "show", SERVICE_NAME, "--property=ActiveState", "--value")
START_COMMAND = ("/usr/bin/sudo", "-n", "/usr/bin/systemctl", "start", SERVICE_NAME)


@dataclass(frozen=True)
class DeploymentResult:
    success: bool
    message: str


class SystemdPublisher:
    """Trigger only the fixed canonical publication unit and return sanitized results."""

    def __init__(
        self,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        timeout_seconds: float = 180,
    ) -> None:
        self._runner = runner
        self._sleep = sleep
        self._monotonic = monotonic
        self._timeout_seconds = timeout_seconds

    def _wait_until_idle(self) -> DeploymentResult | None:
        deadline = self._monotonic() + self._timeout_seconds
        while True:
            try:
                result = self._runner(
                    STATUS_COMMAND,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                return DeploymentResult(False, "No se pudo consultar el estado del publicador.")
            if result.returncode != 0:
                return DeploymentResult(False, "No se pudo consultar el estado del publicador.")
            state = result.stdout.strip()
            if state in {"inactive", "failed"}:
                return None
            if self._monotonic() >= deadline:
                return DeploymentResult(False, "Ya hay una publicación en curso y no terminó a tiempo.")
            self._sleep(0.5)

    def deploy(self) -> DeploymentResult:
        waiting_error = self._wait_until_idle()
        if waiting_error is not None:
            return waiting_error
        try:
            result = self._runner(
                START_COMMAND,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return DeploymentResult(False, "La publicación excedió el tiempo máximo de espera.")
        except OSError:
            return DeploymentResult(False, "No se pudo iniciar el servicio de publicación.")
        if result.returncode != 0:
            return DeploymentResult(
                False,
                "El sitio no se pudo actualizar. La versión publicada quedó preservada.",
            )
        return DeploymentResult(True, "La nota y el sitio se actualizaron correctamente.")
