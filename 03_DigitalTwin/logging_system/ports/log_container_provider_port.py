from __future__ import annotations

from typing import Protocol, runtime_checkable

from .log_container_administrative_port import LogContainerAdministrativePort
from .log_container_consuming_port import LogContainerConsumingPort
from .log_container_managerial_port import LogContainerManagerialPort


@runtime_checkable
class LogContainerProviderPort(
    LogContainerAdministrativePort,
    LogContainerManagerialPort,
    LogContainerConsumingPort,
    Protocol,
):
    pass
