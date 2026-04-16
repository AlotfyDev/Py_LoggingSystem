from __future__ import annotations

from typing import Any


DEFAULT_CONTENT_SCHEMA_ID = "log.content.default.v1"
AUDIT_CONTENT_SCHEMA_ID = "log.content.audit.v1"
ERROR_CONTENT_SCHEMA_ID = "log.content.error.v1"


def build_default_content_schema_catalog() -> dict[str, dict[str, Any]]:
    return {
        DEFAULT_CONTENT_SCHEMA_ID: {
            "schema_id": DEFAULT_CONTENT_SCHEMA_ID,
            "schema_name": "DefaultLogContentSchema",
            "required_keys": ["level", "message", "attributes", "context"],
            "allow_additional_properties": True,
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["DEBUG", "INFO", "WARN", "ERROR", "FATAL", "TRACE"],
                },
                "message": {"type": "string", "min_length": 1},
                "attributes": {"type": "object"},
                "context": {"type": "object"},
            },
        },
        AUDIT_CONTENT_SCHEMA_ID: {
            "schema_id": AUDIT_CONTENT_SCHEMA_ID,
            "schema_name": "AuditLogContentSchema",
            "required_keys": ["level", "message", "attributes", "context", "actor_id", "action"],
            "allow_additional_properties": True,
            "properties": {
                "level": {"type": "string", "enum": ["INFO", "WARN", "ERROR"]},
                "message": {"type": "string", "min_length": 1},
                "attributes": {"type": "object"},
                "context": {"type": "object"},
                "actor_id": {"type": "string", "min_length": 1},
                "action": {"type": "string", "min_length": 1},
            },
        },
        ERROR_CONTENT_SCHEMA_ID: {
            "schema_id": ERROR_CONTENT_SCHEMA_ID,
            "schema_name": "ErrorLogContentSchema",
            "required_keys": ["level", "message", "attributes", "context", "error_code"],
            "allow_additional_properties": True,
            "properties": {
                "level": {"type": "string", "enum": ["ERROR", "FATAL"]},
                "message": {"type": "string", "min_length": 1},
                "attributes": {"type": "object"},
                "context": {"type": "object"},
                "error_code": {"type": "string", "min_length": 1},
            },
        },
    }
