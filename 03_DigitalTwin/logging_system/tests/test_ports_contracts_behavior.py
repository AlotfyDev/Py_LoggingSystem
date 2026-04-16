from __future__ import annotations

import unittest

from logging_system.ports.administrative_port import AdministrativePort
from logging_system.ports.consuming_port import ConsumingPort
from logging_system.ports.managerial_port import ManagerialPort
from logging_system.services.logging_service import LoggingService
from logging_system.tests.support import InMemoryStateStore


class PortsContractBehaviorTests(unittest.TestCase):
    def test_service_conforms_to_role_ports(self) -> None:
        svc = LoggingService(_state_store=InMemoryStateStore())
        self.assertIsInstance(svc, AdministrativePort)
        self.assertIsInstance(svc, ManagerialPort)
        self.assertIsInstance(svc, ConsumingPort)

    def test_invalid_identifiers_are_rejected(self) -> None:
        svc = LoggingService(_state_store=InMemoryStateStore())
        with self.assertRaises(ValueError):
            svc.register_schema(" ", {"fields": []})
        with self.assertRaises(ValueError):
            svc.register_policy("", {"policy": True})
        with self.assertRaises(ValueError):
            svc.bind_adapter(" ")

    def test_provider_catalog_surface_is_available(self) -> None:
        svc = LoggingService(_state_store=InMemoryStateStore())
        report = svc.validate_provider_catalog_integrity()
        self.assertTrue(report["pass_fail"])
        self.assertGreaterEqual(len(svc.list_provider_catalog_entries()), 2)


if __name__ == "__main__":
    unittest.main()
