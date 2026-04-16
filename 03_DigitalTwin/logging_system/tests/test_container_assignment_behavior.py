from __future__ import annotations

import unittest

from logging_system.resource_management.adapters.in_memory_resource_management_client import InMemoryResourceManagementClient
from logging_system.resource_management.adapters.thread_pool_resource_management_client import (
    ThreadPoolResourceManagementClient,
)
from logging_system.services.logging_service import LoggingService
from logging_system.tests.support import InMemoryStateStore


class ContainerAssignmentBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = LoggingService(_state_store=InMemoryStateStore())
        self.service.bind_adapter("telemetry.noop")

    def test_dispatch_fails_closed_when_assignment_unbound(self) -> None:
        self.service.unbind_container_assignment()
        self.service.log_info("hello", context={"tenant": "alpha"})
        with self.assertRaises(RuntimeError):
            self.service.dispatch_round("round-unbound")

    def test_bind_container_assignment_enables_dispatch(self) -> None:
        self.service.bind_container_assignment(
            container_binding_id="binding.alpha",
            container_backend_profile_id="backend.local",
        )
        self.service.log_info("hello", context={"tenant": "alpha"})
        self.service.dispatch_round("round-ok")
        evidence = self.service.collect_operational_evidence()
        self.assertEqual(evidence["totals"]["dispatched"], 1)

    def test_container_binding_config_apply(self) -> None:
        self.service.create_configuration(
            "container_binding",
            "container.binding.alpha",
            {
                "config_version": "1.0.0",
                "container_binding_id": "binding.cfg.alpha",
                "container_backend_profile_id": "backend.cfg.local",
                "binding_metadata": {"source": "test"},
            },
        )
        result = self.service.apply_configuration("container_binding", "container.binding.alpha")
        self.assertTrue(result["applied"])
        status = self.service.get_container_assignment_status()
        self.assertEqual(status["container_binding_id"], "binding.cfg.alpha")
        self.assertTrue(status["container_lease_valid"])

    def test_dispatch_fails_closed_when_execution_assignment_unbound(self) -> None:
        self.service.unbind_execution_assignment()
        self.service.log_info("hello", context={"tenant": "alpha"})
        with self.assertRaises(RuntimeError):
            self.service.dispatch_round("round-exec-unbound")

    def test_block_backpressure_requeues_records_and_fails_closed(self) -> None:
        rm_client = InMemoryResourceManagementClient()
        profile = dict(rm_client.get_execution_profile("exec.logging.local.default"))
        profile["queue_bounds"] = {"max_items": 1}
        profile["backpressure_policy"] = {"action": "block"}
        rm_client._execution_profiles_by_id["exec.logging.local.default"] = profile

        service = LoggingService(_state_store=InMemoryStateStore(), _resource_management_client=rm_client)
        service.bind_adapter("telemetry.noop")
        service.log_info("m1")
        service.log_info("m2")
        with self.assertRaises(RuntimeError):
            service.dispatch_round("round-blocked")

        evidence = service.collect_operational_evidence()
        self.assertEqual(evidence["queue_depth"], 2)
        self.assertEqual(evidence["totals"]["dispatched"], 0)

    def test_drop_oldest_backpressure_dispatches_with_trimmed_batch(self) -> None:
        rm_client = InMemoryResourceManagementClient()
        profile = dict(rm_client.get_execution_profile("exec.logging.local.default"))
        profile["queue_bounds"] = {"max_items": 1}
        profile["backpressure_policy"] = {"action": "drop_oldest"}
        rm_client._execution_profiles_by_id["exec.logging.local.default"] = profile

        service = LoggingService(_state_store=InMemoryStateStore(), _resource_management_client=rm_client)
        service.bind_adapter("telemetry.noop")
        service.log_info("m1")
        service.log_info("m2")
        service.dispatch_round("round-drop-oldest")

        evidence = service.collect_operational_evidence()
        self.assertEqual(evidence["totals"]["dispatched"], 1)
        self.assertEqual(evidence["totals"]["evicted"], 1)

    def test_dispatch_works_with_thread_pool_resource_client(self) -> None:
        rm_client = ThreadPoolResourceManagementClient()
        try:
            service = LoggingService(_state_store=InMemoryStateStore(), _resource_management_client=rm_client)
            service.bind_adapter("telemetry.noop")
            service.log_info("pool-a")
            service.log_warn("pool-b")
            service.dispatch_round("round-thread-pool")
            evidence = service.collect_operational_evidence()
            self.assertEqual(evidence["totals"]["dispatched"], 2)
            self.assertTrue(evidence["execution_assignment"]["execution_lease_valid"])
        finally:
            rm_client.close()


if __name__ == "__main__":
    unittest.main()
