from __future__ import annotations

import unittest

from logging_system.services.logging_service import LoggingService
from logging_system.tests.support import InMemoryStateStore


class ProductionProfilesBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = LoggingService(_state_store=InMemoryStateStore())

    def test_default_production_profiles_seeded_and_integrity_passes(self) -> None:
        ids = self.service.list_production_profile_ids()
        self.assertIn("prod.logging.local.default", ids)
        self.assertIn("prod.logging.redis.default", ids)
        report = self.service.validate_production_profile_integrity()
        self.assertTrue(report["pass_fail"])
        self.assertEqual(report["violations_count"], 0)

    def test_create_production_profile_fails_on_catalog_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            self.service.create_production_profile(
                "prod.invalid.mismatch",
                {
                    "config_version": "1.0.0",
                    "status": "active",
                    "provider_ref": "provider.local.inmemory.level_containers",
                    "connection_ref": "connector.redis.tcp_tls",
                    "persistence_ref": "persistence.local.volatile",
                    "required_execution_profile_id": "exec.logging.local.default",
                    "container_backend_profile_id": "container.backend.local.inmemory",
                    "container_binding_id": "container.binding.invalid",
                    "execution_binding_id": "execution.binding.invalid",
                    "adapter_key": "telemetry.noop",
                    "metadata": {},
                },
            )

    def test_activate_production_profile_applies_bindings(self) -> None:
        result = self.service.activate_production_profile("prod.logging.local.default")
        self.assertEqual(result["profile_id"], "prod.logging.local.default")
        self.assertEqual(result["active_adapter_key"], "telemetry.noop")
        self.assertTrue(result["container_assignment"]["container_lease_valid"])
        self.assertTrue(result["execution_assignment"]["execution_lease_valid"])

    def test_configurator_production_profile_roundtrip_and_apply(self) -> None:
        profile_payload = {
            "config_version": "1.0.0",
            "status": "active",
            "description": "custom",
            "provider_ref": "provider.local.inmemory.level_containers",
            "connection_ref": "connector.local.memory",
            "persistence_ref": "persistence.local.volatile",
            "required_execution_profile_id": "exec.logging.local.default",
            "container_backend_profile_id": "container.backend.local.custom",
            "container_binding_id": "container.binding.local.custom",
            "execution_binding_id": "execution.binding.local.custom",
            "adapter_key": "telemetry.noop",
            "metadata": {"source": "test"},
        }
        self.service.create_configuration("production_profile", "prod.logging.local.custom", profile_payload)

        ids = self.service.list_configuration_ids("production_profile")
        self.assertIn("prod.logging.local.custom", ids)

        result = self.service.apply_configuration("production_profile", "prod.logging.local.custom")
        self.assertTrue(result["applied"])
        activation = result["activation"]
        self.assertEqual(activation["profile_id"], "prod.logging.local.custom")


if __name__ == "__main__":
    unittest.main()
