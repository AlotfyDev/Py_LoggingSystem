from __future__ import annotations

import unittest

from logging_system.resource_management.adapters.thread_pool_resource_management_client import (
    ThreadPoolResourceManagementClient,
)


class ThreadPoolResourceManagementBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = ThreadPoolResourceManagementClient()
        self.profile_id = "exec.logging.local.default"

    def tearDown(self) -> None:
        self.client.close()

    # ===== Execution Lease Tests =====

    def test_execution_lease_lifecycle(self) -> None:
        """Test complete execution lease lifecycle: request, validate, get, release."""
        lease = self.client.request_execution_lease(
            logger_instance_id="logger-1",
            execution_binding_id="exec.binding.a",
            required_execution_profile_id=self.profile_id,
        )
        lease_id = str(lease["execution_lease_id"])
        self.assertTrue(self.client.validate_execution_lease(lease_id))
        stored = self.client.get_execution_lease(lease_id)
        self.assertEqual(stored["execution_binding_id"], "exec.binding.a")
        self.client.release_execution_lease(lease_id)
        self.assertFalse(self.client.validate_execution_lease(lease_id))

    def test_execution_lease_invalid_id_returns_false(self) -> None:
        """Test that validating an invalid lease ID returns False."""
        self.assertFalse(self.client.validate_execution_lease("invalid-lease-id"))
        self.assertFalse(self.client.validate_execution_lease(""))

    def test_execution_lease_get_invalid_raises_key_error(self) -> None:
        """Test that getting an invalid lease raises KeyError."""
        with self.assertRaises(KeyError):
            self.client.get_execution_lease("invalid-lease-id")

    def test_execution_lease_release_invalid_raises_key_error(self) -> None:
        """Test that releasing an invalid lease raises KeyError."""
        with self.assertRaises(KeyError):
            self.client.release_execution_lease("invalid-lease-id")

    def test_execution_lease_with_invalid_profile_raises_key_error(self) -> None:
        """Test that requesting a lease with invalid profile raises KeyError."""
        with self.assertRaises(KeyError):
            self.client.request_execution_lease(
                logger_instance_id="logger-x",
                execution_binding_id="exec.binding.x",
                required_execution_profile_id="invalid.profile.id",
            )

    # ===== Container Lease Tests =====

    def test_container_lease_lifecycle(self) -> None:
        """Test complete container lease lifecycle: request, validate, get, release."""
        lease = self.client.request_container_lease(
            logger_instance_id="logger-c1",
            container_binding_id="container.binding.a",
            container_backend_profile_id="container.backend.profile",
        )
        lease_id = str(lease["container_lease_id"])
        self.assertTrue(self.client.validate_container_lease(lease_id))
        stored = self.client.get_container_lease(lease_id)
        self.assertEqual(stored["container_binding_id"], "container.binding.a")
        self.client.release_container_lease(lease_id)
        self.assertFalse(self.client.validate_container_lease(lease_id))

    def test_container_lease_invalid_id_returns_false(self) -> None:
        """Test that validating an invalid container lease ID returns False."""
        self.assertFalse(self.client.validate_container_lease("invalid-container-lease"))
        self.assertFalse(self.client.validate_container_lease(""))

    def test_container_lease_get_invalid_raises_key_error(self) -> None:
        """Test that getting an invalid container lease raises KeyError."""
        with self.assertRaises(KeyError):
            self.client.get_container_lease("invalid-container-lease")

    def test_container_lease_release_invalid_raises_key_error(self) -> None:
        """Test that releasing an invalid container lease raises KeyError."""
        with self.assertRaises(KeyError):
            self.client.release_container_lease("invalid-container-lease")

    def test_container_lease_requires_logger_instance_id(self) -> None:
        """Test that container lease requires logger_instance_id."""
        with self.assertRaises(ValueError):
            self.client.request_container_lease(
                logger_instance_id="",
                container_binding_id="binding",
                container_backend_profile_id="backend",
            )

    def test_container_lease_requires_container_binding_id(self) -> None:
        """Test that container lease requires container_binding_id."""
        with self.assertRaises(ValueError):
            self.client.request_container_lease(
                logger_instance_id="logger",
                container_binding_id="",
                container_backend_profile_id="backend",
            )

    def test_container_lease_requires_container_backend_profile_id(self) -> None:
        """Test that container lease requires container_backend_profile_id."""
        with self.assertRaises(ValueError):
            self.client.request_container_lease(
                logger_instance_id="logger",
                container_binding_id="binding",
                container_backend_profile_id="",
            )

    # ===== Execution Profile Tests =====

    def test_get_execution_profile(self) -> None:
        """Test retrieving execution profile."""
        profile = self.client.get_execution_profile(self.profile_id)
        self.assertEqual(profile["execution_profile_id"], self.profile_id)
        self.assertIn("worker_pool", profile)
        self.assertIn("queue_bounds", profile)

    def test_get_execution_profile_invalid_raises_key_error(self) -> None:
        """Test that getting invalid profile raises KeyError."""
        with self.assertRaises(KeyError):
            self.client.get_execution_profile("invalid.profile")

    def test_get_execution_profile_empty_id_raises_value_error(self) -> None:
        """Test that getting profile with empty ID raises ValueError."""
        with self.assertRaises(ValueError):
            self.client.get_execution_profile("")

    # ===== Dispatch Tasks Tests =====

    def test_execute_dispatch_tasks_runs_in_provider(self) -> None:
        """Test that dispatch tasks execute and return correct results."""
        lease = self.client.request_execution_lease(
            logger_instance_id="logger-2",
            execution_binding_id="exec.binding.b",
            required_execution_profile_id=self.profile_id,
        )
        lease_id = str(lease["execution_lease_id"])
        tasks = [lambda i=i: i * 2 for i in range(5)]
        results = self.client.execute_dispatch_tasks(
            execution_lease_id=lease_id,
            required_execution_profile_id=self.profile_id,
            tasks=tasks,
        )
        self.assertEqual(results, [0, 2, 4, 6, 8])

    def test_execute_dispatch_tasks_fail_closed_on_task_error(self) -> None:
        """Test that task error raises RuntimeError and cancels pending tasks."""
        lease = self.client.request_execution_lease(
            logger_instance_id="logger-3",
            execution_binding_id="exec.binding.c",
            required_execution_profile_id=self.profile_id,
        )
        lease_id = str(lease["execution_lease_id"])

        def ok() -> int:
            return 1

        def fail() -> int:
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            self.client.execute_dispatch_tasks(
                execution_lease_id=lease_id,
                required_execution_profile_id=self.profile_id,
                tasks=[ok, fail, ok],
            )

    def test_execute_dispatch_tasks_empty_list_returns_empty(self) -> None:
        """Test that empty task list returns empty results."""
        lease = self.client.request_execution_lease(
            logger_instance_id="logger-4",
            execution_binding_id="exec.binding.d",
            required_execution_profile_id=self.profile_id,
        )
        lease_id = str(lease["execution_lease_id"])
        results = self.client.execute_dispatch_tasks(
            execution_lease_id=lease_id,
            required_execution_profile_id=self.profile_id,
            tasks=[],
        )
        self.assertEqual(results, [])

    def test_execute_dispatch_tasks_invalid_lease_raises_runtime_error(self) -> None:
        """Test that invalid lease raises RuntimeError."""
        with self.assertRaises(RuntimeError):
            self.client.execute_dispatch_tasks(
                execution_lease_id="invalid-lease",
                required_execution_profile_id=self.profile_id,
                tasks=[lambda: 1],
            )

    def test_execute_dispatch_tasks_invalid_profile_raises_key_error(self) -> None:
        """Test that invalid profile raises KeyError."""
        lease = self.client.request_execution_lease(
            logger_instance_id="logger-5",
            execution_binding_id="exec.binding.e",
            required_execution_profile_id=self.profile_id,
        )
        lease_id = str(lease["execution_lease_id"])
        with self.assertRaises(KeyError):
            self.client.execute_dispatch_tasks(
                execution_lease_id=lease_id,
                required_execution_profile_id="invalid.profile",
                tasks=[lambda: 1],
            )

    def test_execute_dispatch_tasks_queue_bounds_exceeded_raises(self) -> None:
        """Test that task batch exceeding queue bounds raises RuntimeError."""
        profile = self.client.get_execution_profile(self.profile_id)
        queue_bounds = profile.get("queue_bounds")
        max_items = queue_bounds.get("max_items") if queue_bounds else None

        if max_items and max_items > 0:
            lease = self.client.request_execution_lease(
                logger_instance_id="logger-6",
                execution_binding_id="exec.binding.f",
                required_execution_profile_id=self.profile_id,
            )
            lease_id = str(lease["execution_lease_id"])
            tasks = [lambda i=i: i for i in range(max_items + 1)]
            with self.assertRaises(RuntimeError) as ctx:
                self.client.execute_dispatch_tasks(
                    execution_lease_id=lease_id,
                    required_execution_profile_id=self.profile_id,
                    tasks=tasks,
                )
            self.assertIn("queue_bounds.max_items", str(ctx.exception))

    # ===== Executor Reuse Tests =====

    def test_executor_reuse_same_profile(self) -> None:
        """Test that same profile reuses existing executor."""
        lease1 = self.client.request_execution_lease(
            logger_instance_id="logger-7",
            execution_binding_id="exec.binding.g",
            required_execution_profile_id=self.profile_id,
        )
        results1 = self.client.execute_dispatch_tasks(
            execution_lease_id=str(lease1["execution_lease_id"]),
            required_execution_profile_id=self.profile_id,
            tasks=[lambda: "first"],
        )

        lease2 = self.client.request_execution_lease(
            logger_instance_id="logger-8",
            execution_binding_id="exec.binding.h",
            required_execution_profile_id=self.profile_id,
        )
        results2 = self.client.execute_dispatch_tasks(
            execution_lease_id=str(lease2["execution_lease_id"]),
            required_execution_profile_id=self.profile_id,
            tasks=[lambda: "second"],
        )

        self.assertEqual(results1, ["first"])
        self.assertEqual(results2, ["second"])

    # ===== Parameter Validation Tests =====

    def test_execution_lease_requires_logger_instance_id(self) -> None:
        """Test that execution lease requires logger_instance_id."""
        with self.assertRaises(ValueError):
            self.client.request_execution_lease(
                logger_instance_id="",
                execution_binding_id="binding",
                required_execution_profile_id=self.profile_id,
            )

    def test_execution_lease_requires_execution_binding_id(self) -> None:
        """Test that execution lease requires execution_binding_id."""
        with self.assertRaises(ValueError):
            self.client.request_execution_lease(
                logger_instance_id="logger",
                execution_binding_id="",
                required_execution_profile_id=self.profile_id,
            )

    def test_execution_lease_requires_execution_profile_id(self) -> None:
        """Test that execution lease requires execution_profile_id."""
        with self.assertRaises(ValueError):
            self.client.request_execution_lease(
                logger_instance_id="logger",
                execution_binding_id="binding",
                required_execution_profile_id="",
            )


if __name__ == "__main__":
    unittest.main()
