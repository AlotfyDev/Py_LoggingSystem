from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from logging_system.cli.run_cli import run_cli


class CliBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._state_file = str(Path(self._tmp.name) / "logsys_state.json")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _args(self, *args: str) -> list[str]:
        return ["--state-file", self._state_file, *args]

    def test_status_command(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_cli(self._args("status"))
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().strip(), "ready")
        self.assertEqual(err.getvalue().strip(), "")

    def test_list_adapters_command(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = run_cli(self._args("list-adapters"))
        self.assertEqual(code, 0)
        keys = json.loads(out.getvalue())
        self.assertIn("telemetry.noop", keys)

    def test_emit_invalid_level_fails_closed(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_cli(self._args("emit", "--level", "INVALID", "--message", "x"))
        self.assertEqual(code, 1)
        self.assertIn("unsupported level", err.getvalue())

    def test_query_invalid_json_fails_closed(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_cli(self._args("query", "--filters-json", "[]"))
        self.assertEqual(code, 1)
        self.assertIn("JSON payload must be an object", err.getvalue())

    def test_schema_list_and_get(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = run_cli(self._args("schema-list"))
        self.assertEqual(code, 0)
        schema_ids = json.loads(out.getvalue())
        self.assertIn("log.content.default.v1", schema_ids)

        out2 = io.StringIO()
        with redirect_stdout(out2):
            code2 = run_cli(self._args("schema-get", "--schema-id", "log.content.default.v1"))
        self.assertEqual(code2, 0)
        row = json.loads(out2.getvalue())
        self.assertEqual(row["schema_id"], "log.content.default.v1")

    def test_schema_create_update_and_protected_delete(self) -> None:
        create_payload = json.dumps(
            {
                "required_keys": ["message"],
                "properties": {"message": {"type": "string", "min_length": 1}},
            }
        )
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_cli(
                self._args(
                    "schema-create",
                    "--schema-id",
                    "cli.custom.schema.v1",
                    "--schema-json",
                    create_payload,
                )
            )
        self.assertEqual(code, 0)
        self.assertIn('"status": "created"', out.getvalue())

        # New CLI process (new run_cli call) should read persisted schema.
        out_read = io.StringIO()
        err_read = io.StringIO()
        with redirect_stdout(out_read), redirect_stderr(err_read):
            code_read = run_cli(self._args("schema-get", "--schema-id", "cli.custom.schema.v1"))
        self.assertEqual(code_read, 0)
        read_payload = json.loads(out_read.getvalue())
        self.assertEqual(read_payload["required_keys"], ["message"])

        update_payload = json.dumps(
            {
                "required_keys": ["message", "attributes"],
                "properties": {
                    "message": {"type": "string", "min_length": 1},
                    "attributes": {"type": "object"},
                },
            }
        )
        out2 = io.StringIO()
        err2 = io.StringIO()
        with redirect_stdout(out2), redirect_stderr(err2):
            code2 = run_cli(
                self._args(
                    "schema-update",
                    "--schema-id",
                    "log.content.default.v1",
                    "--schema-json",
                    update_payload,
                )
            )
        self.assertEqual(code2, 0)
        self.assertIn('"status": "updated"', out2.getvalue())

        out3 = io.StringIO()
        err3 = io.StringIO()
        with redirect_stdout(out3), redirect_stderr(err3):
            code3 = run_cli(self._args("schema-delete", "--schema-id", "log.content.default.v1"))
        self.assertEqual(code3, 1)
        self.assertIn("protected", err3.getvalue().lower())

    def test_policy_crud_commands(self) -> None:
        create_payload = json.dumps({"mode": "bounded", "max_retries": 3})
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_cli(
                self._args(
                    "policy-create",
                    "--policy-id",
                    "policy.dispatch.v1",
                    "--policy-json",
                    create_payload,
                )
            )
        self.assertEqual(code, 0)
        self.assertIn('"status": "created"', out.getvalue())

        out_get = io.StringIO()
        with redirect_stdout(out_get):
            code_get = run_cli(self._args("policy-get", "--policy-id", "policy.dispatch.v1"))
        self.assertEqual(code_get, 0)
        payload = json.loads(out_get.getvalue())
        self.assertEqual(payload["mode"], "bounded")

        out_list = io.StringIO()
        with redirect_stdout(out_list):
            code_list = run_cli(self._args("policy-list"))
        self.assertEqual(code_list, 0)
        policy_ids = json.loads(out_list.getvalue())
        self.assertIn("policy.dispatch.v1", policy_ids)

        out_del = io.StringIO()
        with redirect_stdout(out_del):
            code_del = run_cli(self._args("policy-delete", "--policy-id", "policy.dispatch.v1"))
        self.assertEqual(code_del, 0)
        self.assertIn('"status": "deleted"', out_del.getvalue())

    def test_dedicated_level_commands(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_cli(
                self._args(
                    "log-error",
                    "--message",
                    "hard-fail",
                    "--attributes-json",
                    '{"scope":"cli"}',
                    "--context-json",
                    '{"request_id":"r-1"}',
                )
            )
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertIn("record_id", payload)

    def test_specialized_policy_commands(self) -> None:
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_cli(self._args("set-signal-qos-profile", "--policy-json", '{"logs":"at_least_once"}'))
        self.assertEqual(code, 0)
        self.assertIn("signal.qos_profile", out.getvalue())

        out2 = io.StringIO()
        with redirect_stdout(out2):
            code2 = run_cli(self._args("policy-get", "--policy-id", "signal.qos_profile"))
        self.assertEqual(code2, 0)
        row = json.loads(out2.getvalue())
        self.assertEqual(row["logs"], "at_least_once")

    def test_previewer_commands(self) -> None:
        out_emit = io.StringIO()
        err_emit = io.StringIO()
        with redirect_stdout(out_emit), redirect_stderr(err_emit):
            code_emit = run_cli(self._args("emit", "--level", "INFO", "--message", "preview-me"))
        self.assertEqual(code_emit, 0)

        out_console = io.StringIO()
        with redirect_stdout(out_console):
            code_console = run_cli(self._args("preview-console", "--mode", "collective", "--limit", "5"))
        self.assertEqual(code_console, 0)
        self.assertIn("preview-me", out_console.getvalue())

        out_web = io.StringIO()
        with redirect_stdout(out_web):
            code_web = run_cli(self._args("preview-web", "--mode", "collective", "--limit", "5"))
        self.assertEqual(code_web, 0)
        payload = json.loads(out_web.getvalue())
        self.assertIn("records", payload)


    def test_typed_configuration_crud_and_apply(self) -> None:
        config_payload = json.dumps(
            {
                "config_version": "1.0.0",
                "adapter_key": "telemetry.noop",
                "binding_metadata": {"source": "cli-test"},
            }
        )

        out_create = io.StringIO()
        err_create = io.StringIO()
        with redirect_stdout(out_create), redirect_stderr(err_create):
            code_create = run_cli(
                self._args(
                    "config-create",
                    "--config-type",
                    "adapter_binding",
                    "--config-id",
                    "binding.cli.noop",
                    "--config-json",
                    config_payload,
                )
            )
        self.assertEqual(code_create, 0)

        out_get = io.StringIO()
        with redirect_stdout(out_get):
            code_get = run_cli(
                self._args(
                    "config-get",
                    "--config-type",
                    "adapter_binding",
                    "--config-id",
                    "binding.cli.noop",
                )
            )
        self.assertEqual(code_get, 0)
        row = json.loads(out_get.getvalue())
        self.assertEqual(row["adapter_key"], "telemetry.noop")

        out_apply = io.StringIO()
        with redirect_stdout(out_apply):
            code_apply = run_cli(
                self._args(
                    "config-apply",
                    "--config-type",
                    "adapter_binding",
                    "--config-id",
                    "binding.cli.noop",
                )
            )
        self.assertEqual(code_apply, 0)
        applied = json.loads(out_apply.getvalue())
        self.assertTrue(applied["applied"])

    def test_execution_assignment_commands_and_config_apply(self) -> None:
        out_bind = io.StringIO()
        err_bind = io.StringIO()
        with redirect_stdout(out_bind), redirect_stderr(err_bind):
            code_bind = run_cli(
                self._args(
                    "bind-execution-assignment",
                    "--execution-binding-id",
                    "exec.binding.cli",
                    "--required-execution-profile-id",
                    "exec.logging.local.default",
                )
            )
        self.assertEqual(code_bind, 0)
        payload = json.loads(out_bind.getvalue())
        self.assertEqual(payload["required_execution_profile_id"], "exec.logging.local.default")
        self.assertTrue(payload["execution_lease_valid"])

        out_status = io.StringIO()
        with redirect_stdout(out_status):
            code_status = run_cli(self._args("execution-assignment-status"))
        self.assertEqual(code_status, 0)
        status_payload = json.loads(out_status.getvalue())
        self.assertTrue(status_payload["execution_lease_valid"])

        exec_config_payload = json.dumps(
            {
                "config_version": "1.0.0",
                "execution_binding_id": "exec.binding.cfg",
                "required_execution_profile_id": "exec.logging.local.default",
                "queue_policy_id": "queue.policy.cfg",
                "thread_safety_mode": "single_writer_per_partition",
                "binding_metadata": {"source": "cli-test"},
            }
        )
        out_create = io.StringIO()
        with redirect_stdout(out_create):
            code_create = run_cli(
                self._args(
                    "config-create",
                    "--config-type",
                    "execution_binding",
                    "--config-id",
                    "execution.binding.cli.cfg",
                    "--config-json",
                    exec_config_payload,
                )
            )
        self.assertEqual(code_create, 0)

        out_apply = io.StringIO()
        with redirect_stdout(out_apply):
            code_apply = run_cli(
                self._args(
                    "config-apply",
                    "--config-type",
                    "execution_binding",
                    "--config-id",
                    "execution.binding.cli.cfg",
                )
            )
        self.assertEqual(code_apply, 0)
        applied = json.loads(out_apply.getvalue())
        self.assertTrue(applied["applied"])
        self.assertIn("execution_assignment", applied)

        out_unbind = io.StringIO()
        with redirect_stdout(out_unbind):
            code_unbind = run_cli(self._args("unbind-execution-assignment"))
        self.assertEqual(code_unbind, 0)
        self.assertIn('"status": "unbound"', out_unbind.getvalue())

    def test_production_profile_commands_and_config_apply(self) -> None:
        profile_payload = json.dumps(
            {
                "config_version": "1.0.0",
                "status": "active",
                "provider_ref": "provider.local.inmemory.level_containers",
                "connection_ref": "connector.local.memory",
                "persistence_ref": "persistence.local.volatile",
                "required_execution_profile_id": "exec.logging.local.default",
                "container_backend_profile_id": "container.backend.local.custom",
                "container_binding_id": "container.binding.local.custom",
                "execution_binding_id": "execution.binding.local.custom",
                "adapter_key": "telemetry.noop",
                "metadata": {"source": "cli-test"},
            }
        )

        out_create = io.StringIO()
        with redirect_stdout(out_create):
            code_create = run_cli(
                self._args(
                    "production-profile-create",
                    "--profile-id",
                    "prod.logging.local.custom",
                    "--profile-json",
                    profile_payload,
                )
            )
        self.assertEqual(code_create, 0)
        self.assertIn('"status": "created"', out_create.getvalue())

        out_apply = io.StringIO()
        with redirect_stdout(out_apply):
            code_apply = run_cli(
                self._args(
                    "production-profile-activate",
                    "--profile-id",
                    "prod.logging.local.custom",
                )
            )
        self.assertEqual(code_apply, 0)
        applied = json.loads(out_apply.getvalue())
        self.assertEqual(applied["profile_id"], "prod.logging.local.custom")
        self.assertTrue(applied["container_assignment"]["container_lease_valid"])

        out_cfg_create = io.StringIO()
        with redirect_stdout(out_cfg_create):
            code_cfg_create = run_cli(
                self._args(
                    "config-create",
                    "--config-type",
                    "production_profile",
                    "--config-id",
                    "prod.logging.local.custom.cfg",
                    "--config-json",
                    profile_payload,
                )
            )
        self.assertEqual(code_cfg_create, 0)

        out_cfg_apply = io.StringIO()
        with redirect_stdout(out_cfg_apply):
            code_cfg_apply = run_cli(
                self._args(
                    "config-apply",
                    "--config-type",
                    "production_profile",
                    "--config-id",
                    "prod.logging.local.custom.cfg",
                )
            )
        self.assertEqual(code_cfg_apply, 0)
        cfg_result = json.loads(out_cfg_apply.getvalue())
        self.assertTrue(cfg_result["applied"])



if __name__ == "__main__":
    unittest.main()
