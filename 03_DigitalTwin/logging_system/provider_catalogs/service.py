from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Mapping

from .models import ConnectionCatalogEntry, PersistenceCatalogEntry, ProviderCatalogEntry


@dataclass
class ProviderCatalogService:
    _providers_by_id: dict[str, ProviderCatalogEntry] = field(default_factory=dict)
    _connections_by_id: dict[str, ConnectionCatalogEntry] = field(default_factory=dict)
    _persistence_by_id: dict[str, PersistenceCatalogEntry] = field(default_factory=dict)
    _lock: RLock = field(default_factory=RLock)

    def seed_defaults_if_empty(
        self,
        *,
        provider_entries: list[Mapping[str, Any]],
        connection_entries: list[Mapping[str, Any]],
        persistence_entries: list[Mapping[str, Any]],
    ) -> None:
        with self._lock:
            if len(self._providers_by_id) > 0 or len(self._connections_by_id) > 0 or len(self._persistence_by_id) > 0:
                return
            for raw in provider_entries:
                entry = ProviderCatalogEntry.from_mapping(raw)
                self._providers_by_id[entry.provider_id] = entry
            for raw in connection_entries:
                entry = ConnectionCatalogEntry.from_mapping(raw)
                self._connections_by_id[entry.connector_profile_id] = entry
            for raw in persistence_entries:
                entry = PersistenceCatalogEntry.from_mapping(raw)
                self._persistence_by_id[entry.persistence_profile_id] = entry
            self._assert_integrity_locked()

    def create_provider_entry(self, payload: Mapping[str, Any]) -> None:
        entry = ProviderCatalogEntry.from_mapping(payload)
        with self._lock:
            if entry.provider_id in self._providers_by_id:
                raise KeyError(f"provider_id already exists: {entry.provider_id}")
            self._mutate_with_integrity_guard_locked(
                lambda: self._providers_by_id.__setitem__(entry.provider_id, entry)
            )

    def get_provider_entry(self, provider_id: str) -> Mapping[str, Any]:
        key = str(provider_id).strip()
        if key == "":
            raise ValueError("provider_id is required")
        with self._lock:
            entry = self._providers_by_id.get(key)
        if entry is None:
            raise KeyError(f"provider_id is not registered: {key}")
        return entry.to_mapping()

    def update_provider_entry(self, payload: Mapping[str, Any]) -> None:
        entry = ProviderCatalogEntry.from_mapping(payload)
        with self._lock:
            if entry.provider_id not in self._providers_by_id:
                raise KeyError(f"provider_id is not registered: {entry.provider_id}")
            self._mutate_with_integrity_guard_locked(
                lambda: self._providers_by_id.__setitem__(entry.provider_id, entry)
            )

    def delete_provider_entry(self, provider_id: str) -> None:
        key = str(provider_id).strip()
        if key == "":
            raise ValueError("provider_id is required")
        with self._lock:
            if key not in self._providers_by_id:
                raise KeyError(f"provider_id is not registered: {key}")
            self._mutate_with_integrity_guard_locked(lambda: self._providers_by_id.pop(key))

    def list_provider_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._providers_by_id.keys())

    def create_connection_entry(self, payload: Mapping[str, Any]) -> None:
        entry = ConnectionCatalogEntry.from_mapping(payload)
        with self._lock:
            if entry.connector_profile_id in self._connections_by_id:
                raise KeyError(f"connector_profile_id already exists: {entry.connector_profile_id}")
            self._mutate_with_integrity_guard_locked(
                lambda: self._connections_by_id.__setitem__(entry.connector_profile_id, entry)
            )

    def get_connection_entry(self, connector_profile_id: str) -> Mapping[str, Any]:
        key = str(connector_profile_id).strip()
        if key == "":
            raise ValueError("connector_profile_id is required")
        with self._lock:
            entry = self._connections_by_id.get(key)
        if entry is None:
            raise KeyError(f"connector_profile_id is not registered: {key}")
        return entry.to_mapping()

    def update_connection_entry(self, payload: Mapping[str, Any]) -> None:
        entry = ConnectionCatalogEntry.from_mapping(payload)
        with self._lock:
            if entry.connector_profile_id not in self._connections_by_id:
                raise KeyError(f"connector_profile_id is not registered: {entry.connector_profile_id}")
            self._mutate_with_integrity_guard_locked(
                lambda: self._connections_by_id.__setitem__(entry.connector_profile_id, entry)
            )

    def delete_connection_entry(self, connector_profile_id: str) -> None:
        key = str(connector_profile_id).strip()
        if key == "":
            raise ValueError("connector_profile_id is required")
        with self._lock:
            if key not in self._connections_by_id:
                raise KeyError(f"connector_profile_id is not registered: {key}")
            self._mutate_with_integrity_guard_locked(lambda: self._connections_by_id.pop(key))

    def list_connection_profile_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._connections_by_id.keys())

    def create_persistence_entry(self, payload: Mapping[str, Any]) -> None:
        entry = PersistenceCatalogEntry.from_mapping(payload)
        with self._lock:
            if entry.persistence_profile_id in self._persistence_by_id:
                raise KeyError(f"persistence_profile_id already exists: {entry.persistence_profile_id}")
            self._mutate_with_integrity_guard_locked(
                lambda: self._persistence_by_id.__setitem__(entry.persistence_profile_id, entry)
            )

    def get_persistence_entry(self, persistence_profile_id: str) -> Mapping[str, Any]:
        key = str(persistence_profile_id).strip()
        if key == "":
            raise ValueError("persistence_profile_id is required")
        with self._lock:
            entry = self._persistence_by_id.get(key)
        if entry is None:
            raise KeyError(f"persistence_profile_id is not registered: {key}")
        return entry.to_mapping()

    def update_persistence_entry(self, payload: Mapping[str, Any]) -> None:
        entry = PersistenceCatalogEntry.from_mapping(payload)
        with self._lock:
            if entry.persistence_profile_id not in self._persistence_by_id:
                raise KeyError(f"persistence_profile_id is not registered: {entry.persistence_profile_id}")
            self._mutate_with_integrity_guard_locked(
                lambda: self._persistence_by_id.__setitem__(entry.persistence_profile_id, entry)
            )

    def delete_persistence_entry(self, persistence_profile_id: str) -> None:
        key = str(persistence_profile_id).strip()
        if key == "":
            raise ValueError("persistence_profile_id is required")
        with self._lock:
            if key not in self._persistence_by_id:
                raise KeyError(f"persistence_profile_id is not registered: {key}")
            self._mutate_with_integrity_guard_locked(lambda: self._persistence_by_id.pop(key))

    def list_persistence_profile_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._persistence_by_id.keys())

    def validate_integrity(self) -> Mapping[str, Any]:
        with self._lock:
            violations = self._collect_integrity_violations_locked()
            return {
                "pass_fail": len(violations) == 0,
                "violations_count": len(violations),
                "violations": violations,
                "counts": {
                    "provider_entries": len(self._providers_by_id),
                    "connection_entries": len(self._connections_by_id),
                    "persistence_entries": len(self._persistence_by_id),
                },
            }

    def export_state(self) -> Mapping[str, Any]:
        with self._lock:
            return {
                "provider_entries": [entry.to_mapping() for entry in self._providers_by_id.values()],
                "connection_entries": [entry.to_mapping() for entry in self._connections_by_id.values()],
                "persistence_entries": [entry.to_mapping() for entry in self._persistence_by_id.values()],
            }

    def import_state(self, payload: Mapping[str, Any]) -> None:
        if not isinstance(payload, Mapping):
            return
        provider_entries = payload.get("provider_entries")
        connection_entries = payload.get("connection_entries")
        persistence_entries = payload.get("persistence_entries")
        if not isinstance(provider_entries, list) or not isinstance(connection_entries, list) or not isinstance(
            persistence_entries,
            list,
        ):
            return

        parsed_providers: dict[str, ProviderCatalogEntry] = {}
        parsed_connections: dict[str, ConnectionCatalogEntry] = {}
        parsed_persistence: dict[str, PersistenceCatalogEntry] = {}
        try:
            for raw in provider_entries:
                if not isinstance(raw, Mapping):
                    continue
                entry = ProviderCatalogEntry.from_mapping(raw)
                parsed_providers[entry.provider_id] = entry
            for raw in connection_entries:
                if not isinstance(raw, Mapping):
                    continue
                entry = ConnectionCatalogEntry.from_mapping(raw)
                parsed_connections[entry.connector_profile_id] = entry
            for raw in persistence_entries:
                if not isinstance(raw, Mapping):
                    continue
                entry = PersistenceCatalogEntry.from_mapping(raw)
                parsed_persistence[entry.persistence_profile_id] = entry
        except Exception:
            return

        with self._lock:
            snapshot = self._snapshot_locked()
            self._providers_by_id = parsed_providers
            self._connections_by_id = parsed_connections
            self._persistence_by_id = parsed_persistence
            violations = self._collect_integrity_violations_locked()
            if len(violations) > 0:
                self._restore_snapshot_locked(snapshot)

    def _mutate_with_integrity_guard_locked(self, mutator: Any) -> None:
        snapshot = self._snapshot_locked()
        mutator()
        violations = self._collect_integrity_violations_locked()
        if len(violations) > 0:
            self._restore_snapshot_locked(snapshot)
            first = violations[0]
            raise ValueError(f"provider catalog integrity violation: {first['code']}: {first['message']}")

    def _assert_integrity_locked(self) -> None:
        violations = self._collect_integrity_violations_locked()
        if len(violations) > 0:
            first = violations[0]
            raise ValueError(f"provider catalog integrity violation: {first['code']}: {first['message']}")

    def _collect_integrity_violations_locked(self) -> list[dict[str, Any]]:
        violations: list[dict[str, Any]] = []
        for provider in self._providers_by_id.values():
            connection = self._connections_by_id.get(provider.connection_profile_id)
            persistence = self._persistence_by_id.get(provider.persistence_profile_id)
            if connection is None:
                violations.append(
                    {
                        "code": "unresolved_provider_connection_reference",
                        "message": "provider.connection_profile_id does not resolve",
                        "provider_id": provider.provider_id,
                        "connection_profile_id": provider.connection_profile_id,
                    }
                )
            elif connection.provider_id != provider.provider_id:
                violations.append(
                    {
                        "code": "provider_connection_provider_id_mismatch",
                        "message": "connection.provider_id must match provider.provider_id",
                        "provider_id": provider.provider_id,
                        "connection_profile_id": provider.connection_profile_id,
                        "connection_provider_id": connection.provider_id,
                    }
                )

            if persistence is None:
                violations.append(
                    {
                        "code": "unresolved_provider_persistence_reference",
                        "message": "provider.persistence_profile_id does not resolve",
                        "provider_id": provider.provider_id,
                        "persistence_profile_id": provider.persistence_profile_id,
                    }
                )
            else:
                if persistence.provider_id != provider.provider_id:
                    violations.append(
                        {
                            "code": "provider_persistence_provider_id_mismatch",
                            "message": "persistence.provider_id must match provider.provider_id",
                            "provider_id": provider.provider_id,
                            "persistence_profile_id": provider.persistence_profile_id,
                            "persistence_provider_id": persistence.provider_id,
                        }
                    )
                if persistence.ack_semantics != provider.ack_model:
                    violations.append(
                        {
                            "code": "provider_persistence_ack_model_mismatch",
                            "message": "provider.ack_model must equal persistence.ack_semantics",
                            "provider_id": provider.provider_id,
                            "provider_ack_model": provider.ack_model,
                            "persistence_ack_semantics": persistence.ack_semantics,
                        }
                    )
        return violations

    def _snapshot_locked(self) -> dict[str, Any]:
        return {
            "providers_by_id": {key: value for key, value in self._providers_by_id.items()},
            "connections_by_id": {key: value for key, value in self._connections_by_id.items()},
            "persistence_by_id": {key: value for key, value in self._persistence_by_id.items()},
        }

    def _restore_snapshot_locked(self, snapshot: Mapping[str, Any]) -> None:
        self._providers_by_id = dict(snapshot.get("providers_by_id", {}))
        self._connections_by_id = dict(snapshot.get("connections_by_id", {}))
        self._persistence_by_id = dict(snapshot.get("persistence_by_id", {}))
