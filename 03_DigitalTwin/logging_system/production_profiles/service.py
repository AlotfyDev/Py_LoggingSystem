from __future__ import annotations

from threading import RLock
from typing import Any, Callable, Mapping

from .catalog_entries import build_default_production_profiles
from .dtos import ProductionProfileDTO
from .mappers import to_runtime_payload
from .validators import ProductionProfileValidator


class ProductionProfileCatalogService:
    def __init__(
        self,
        profile_store: dict[str, Mapping[str, Any]],
        *,
        provider_lookup: Callable[[str], Mapping[str, Any]],
        connection_lookup: Callable[[str], Mapping[str, Any]],
        persistence_lookup: Callable[[str], Mapping[str, Any]],
    ) -> None:
        self._profile_store = profile_store
        self._provider_lookup = provider_lookup
        self._connection_lookup = connection_lookup
        self._persistence_lookup = persistence_lookup
        self._validator = ProductionProfileValidator()
        self._lock = RLock()

    def seed_defaults_if_empty(self) -> None:
        with self._lock:
            if len(self._profile_store) > 0:
                return
            for payload in build_default_production_profiles():
                dto = ProductionProfileDTO.from_mapping(payload)
                self._validate_all(dto)
                self._profile_store[dto.profile_id] = to_runtime_payload(dto)

    def create_profile(self, payload: Mapping[str, Any]) -> None:
        dto = ProductionProfileDTO.from_mapping(payload)
        self._validate_all(dto)
        with self._lock:
            if dto.profile_id in self._profile_store:
                raise KeyError(f"profile_id already exists: {dto.profile_id}")
            self._profile_store[dto.profile_id] = to_runtime_payload(dto)

    def update_profile(self, payload: Mapping[str, Any]) -> None:
        dto = ProductionProfileDTO.from_mapping(payload)
        self._validate_all(dto)
        with self._lock:
            if dto.profile_id not in self._profile_store:
                raise KeyError(f"profile_id is not registered: {dto.profile_id}")
            self._profile_store[dto.profile_id] = to_runtime_payload(dto)

    def get_profile(self, profile_id: str) -> Mapping[str, Any]:
        key = str(profile_id).strip()
        if key == "":
            raise ValueError("profile_id is required")
        with self._lock:
            row = self._profile_store.get(key)
        if row is None:
            raise KeyError(f"profile_id is not registered: {key}")
        return dict(row)

    def delete_profile(self, profile_id: str) -> None:
        key = str(profile_id).strip()
        if key == "":
            raise ValueError("profile_id is required")
        with self._lock:
            if key not in self._profile_store:
                raise KeyError(f"profile_id is not registered: {key}")
            del self._profile_store[key]

    def list_profile_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._profile_store.keys())

    def validate_integrity(self) -> Mapping[str, Any]:
        violations: list[dict[str, Any]] = []
        with self._lock:
            rows = {key: dict(value) for key, value in self._profile_store.items()}
        for profile_id, row in rows.items():
            try:
                dto = ProductionProfileDTO.from_mapping(row)
                self._validate_all(dto)
            except Exception as exc:
                violations.append(
                    {
                        "code": "invalid_production_profile_entry",
                        "profile_id": profile_id,
                        "message": str(exc),
                    }
                )
        return {
            "pass_fail": len(violations) == 0,
            "violations_count": len(violations),
            "violations": violations,
            "counts": {"production_profiles": len(rows)},
        }

    def _validate_all(self, dto: ProductionProfileDTO) -> None:
        self._validator.validate_shape(dto)
        provider = self._provider_lookup(dto.provider_ref)
        connection = self._connection_lookup(dto.connection_ref)
        persistence = self._persistence_lookup(dto.persistence_ref)
        self._validator.validate_bindings(
            dto,
            provider_payload=provider,
            connection_payload=connection,
            persistence_payload=persistence,
        )
