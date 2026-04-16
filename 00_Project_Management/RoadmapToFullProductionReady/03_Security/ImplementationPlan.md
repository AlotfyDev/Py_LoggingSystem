# Security - Implementation Roadmap

**Current Score:** 6/10  
**Target Score:** 9/10  
**Priority:** HIGH

---

## Executive Summary

The logging system has good input validation and audit trails, but lacks security hardening for production environments. Key gaps include secrets handling, encryption, path traversal protection, and comprehensive security testing.

---

## Gap Analysis

| Gap | Severity | Current State | Target State |
|-----|----------|---------------|--------------|
| Secrets Handling | CRITICAL | Plain text | Encrypted, vault integration |
| Path Traversal | HIGH | Potential vulnerability | Sanitized paths |
| Input Sanitization | MEDIUM | Basic validation | Comprehensive sanitization |
| Audit Log Security | MEDIUM | Stored locally | Tamper-evident logs |
| Rate Limiting | MEDIUM | None | Per-tenant rate limits |
| Security Testing | MEDIUM | Partial | SAST, DAST, fuzzing |

---

## Implementation Phases (Dependency-Ordered)

### Phase 1: Security Foundations (No Dependencies)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 1: SECURITY FOUNDATIONS                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  1.1 Security Configuration Types                                          │
│      ├── SecurityConfig dataclass                                           │
│      ├── EncryptionConfig dataclass                                         │
│      └── RateLimitConfig dataclass                                         │
│                                                                             │
│  1.2 Input Sanitization                                                     │
│      ├── sanitize_identifier() - prevent injection                          │
│      ├── sanitize_path() - prevent traversal                               │
│      └── sanitize_json() - prevent payloads attacks                        │
│                                                                             │
│  1.3 Security Constants                                                    │
│      ├── ALLOWED_CHARACTERS for identifiers                               │
│      ├── FORBIDDEN_PATTERNS for detection                                  │
│      └── MAX_* constants for size limits                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 1.1.1 Security Configuration

**File:** `logging_system/security/config.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EEncryptionMode(str, Enum):
    NONE = "none"
    AES_256_GCM = "aes_256_gcm"
    FERNET = "fernet"


class ERateLimitAlgorithm(str, Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass(frozen=True)
class SecurityConfig:
    enable_input_sanitization: bool = True
    enable_path_validation: bool = True
    enable_rate_limiting: bool = False
    enable_encryption: bool = False
    encryption_mode: EEncryptionMode = EEncryptionMode.NONE
    encryption_key_ref: str | None = None
    max_identifier_length: int = 255
    max_payload_size_bytes: int = 1024 * 1024  # 1MB
    allowed_schemes: frozenset[str] = frozenset({"http", "https"})


@dataclass(frozen=True)
class EncryptionConfig:
    mode: EEncryptionMode
    key_ref: str | None = None
    key_rotation_days: int = 90
    iv_length_bytes: int = 12
    tag_length_bytes: int = 16


@dataclass(frozen=True)
class RateLimitConfig:
    algorithm: ERateLimitAlgorithm = ERateLimitAlgorithm.TOKEN_BUCKET
    requests_per_second: float = 100.0
    burst_size: int = 200
    per_tenant: bool = True
    exempt_adapters: frozenset[str] = frozenset({"internal"})


@dataclass
class RateLimitEntry:
    tokens: float
    last_update: float
    request_count: int = 0
    blocked_count: int = 0
```

#### 1.2.1 Input Sanitization

**File:** `logging_system/security/sanitization.py`

```python
from __future__ import annotations
import re
from pathlib import Path
from typing import Any
import html


class SecurityPatterns:
    """Precompiled regex patterns for security checks."""

    # Identifier patterns
    IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9._-]{0,253}$')

    # Dangerous patterns
    PATH_TRAVERSAL_PATTERNS = [
        re.compile(r'\.\./'),  # Directory traversal
        re.compile(r'\.\.\\'),  # Windows traversal
        re.compile(r'/%2e%2e/'),  # URL encoded
        re.compile(r'^\.\.[\\/]'),
    ]

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        re.compile(r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\b)", re.IGNORECASE),
        re.compile(r"(--|#|/\*|\*/)"),  # Comment injection
        re.compile(r"(['\"])(\s*(OR|AND)\s*['\"]=)"),  # Boolean injection
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        re.compile(r'[;&|`$(){}<>]', re.IGNORECASE),
        re.compile(r'\s+(rm|cat|ls|wget|curl|nc)\s+', re.IGNORECASE),
    ]

    # HTML/script injection patterns
    XSS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
    ]

    # Null bytes
    NULL_BYTE_PATTERN = re.compile(r'\x00')

    # ReDoS dangerous patterns
    REDOS_PATTERNS = [
        re.compile(r'(.+)*'),  # Catastrophic backtracking
        re.compile(r'(a+)+$'),  # Exponential backtracking
    ]


class InputSanitizer:
    """Central input sanitization for the logging system."""

    FORBIDDEN_CHARS = frozenset({'<', '>', '"', "'", '&', '\x00', '\r', '\n'})
    MAX_DEPTH = 10
    MAX_STRING_LENGTH = 10000

    @classmethod
    def sanitize_identifier(cls, value: str) -> str:
        """Sanitize identifiers (schema IDs, policy IDs, etc.)"""
        if not value:
            raise ValueError("Identifier cannot be empty")

        if len(value) > 255:
            raise ValueError(f"Identifier too long: {len(value)} > 255")

        if not SecurityPatterns.IDENTIFIER_PATTERN.match(value):
            raise ValueError(f"Invalid identifier format: {value}")

        # Check for path traversal
        for pattern in SecurityPatterns.PATH_TRAVERSAL_PATTERNS:
            if pattern.search(value):
                raise ValueError(f"Path traversal detected in identifier: {value}")

        return value.strip()

    @classmethod
    def sanitize_path(cls, path: str | Path) -> Path:
        """Sanitize and validate file paths to prevent traversal."""
        path_str = str(path)
        resolved = Path(path_str).resolve()

        # Check for null bytes
        if '\x00' in path_str:
            raise ValueError("Null byte in path")

        # Check for traversal patterns
        for pattern in SecurityPatterns.PATH_TRAVERSAL_PATTERNS:
            if pattern.search(path_str):
                raise ValueError(f"Path traversal detected: {path_str}")

        # Validate within allowed base directories
        allowed_bases = [
            Path.cwd() / "state",
            Path.cwd() / "logs",
            Path.cwd() / "data",
        ]

        is_allowed = any(
            str(resolved).startswith(str(base))
            for base in allowed_bases
        )

        if not is_allowed:
            raise ValueError(f"Path outside allowed directories: {resolved}")

        return resolved

    @classmethod
    def sanitize_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """Sanitize log payloads recursively."""
        return cls._sanitize_value(payload, depth=0)

    @classmethod
    def _sanitize_value(cls, value: Any, depth: int) -> Any:
        if depth > cls.MAX_DEPTH:
            raise ValueError(f"Payload depth exceeded: {depth} > {cls.MAX_DEPTH}")

        if isinstance(value, str):
            return cls._sanitize_string(value)
        elif isinstance(value, dict):
            return {k: cls._sanitize_value(v, depth + 1) for k, v in value.items()}
        elif isinstance(value, list):
            return [cls._sanitize_value(item, depth + 1) for item in value]
        elif isinstance(value, bytes):
            return cls._sanitize_bytes(value)
        else:
            return value

    @classmethod
    def _sanitize_string(cls, value: str) -> str:
        # Truncate if too long
        if len(value) > cls.MAX_STRING_LENGTH:
            value = value[:cls.MAX_STRING_LENGTH]

        # Remove null bytes
        value = value.replace('\x00', '')

        # HTML escape for display safety
        value = html.escape(value)

        return value

    @classmethod
    def _sanitize_bytes(cls, value: bytes) -> bytes:
        # Reject null bytes in binary
        if b'\x00' in value:
            raise ValueError("Null byte in binary data")
        return value

    @classmethod
    def check_for_sql_injection(cls, value: str) -> bool:
        """Check if value contains SQL injection patterns."""
        for pattern in SecurityPatterns.SQL_INJECTION_PATTERNS:
            if pattern.search(value):
                return True
        return False

    @classmethod
    def check_for_command_injection(cls, value: str) -> bool:
        """Check if value contains command injection patterns."""
        for pattern in SecurityPatterns.COMMAND_INJECTION_PATTERNS:
            if pattern.search(value):
                return True
        return False

    @classmethod
    def check_for_xss(cls, value: str) -> bool:
        """Check if value contains XSS patterns."""
        for pattern in SecurityPatterns.XSS_PATTERNS:
            if pattern.search(value):
                return True
        return False
```

---

### Phase 2: Secrets Management (Depends on Phase 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 2: SECRETS MANAGEMENT                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  2.1 Secrets Configuration Types                                           │
│      ├── SecretRef dataclass                                               │
│      ├── SecretValue dataclass                                            │
│      └── SecretProviderType enum                                          │
│                                                                             │
│  2.2 Secrets Provider Interface                                            │
│      ├── ISecretsProvider port interface                                   │
│      ├── EnvironmentSecretsProvider                                        │
│      ├── HashiCorpVaultProvider                                           │
│      └── AWSSecretsManagerProvider                                        │
│                                                                             │
│  2.3 Secrets Encryption                                                    │
│      ├── Fernet encryption wrapper                                         │
│      └── Key rotation support                                             │
│                                                                             │
│  2.4 Secrets Injection into Configuration                                  │
│      ├── SecretResolver class                                             │
│      └── Auto-resolve ${SECRET:ref} patterns                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 2.1.1 Secrets Types

**File:** `logging_system/security/secrets/types.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ESecretProviderType(str, Enum):
    ENVIRONMENT = "environment"
    HASHICORP_VAULT = "hashicorp_vault"
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    AZURE_KEY_VAULT = "azure_key_vault"
    GCP_SECRET_MANAGER = "gcp_secret_manager"


@dataclass(frozen=True)
class SecretRef:
    ref: str
    provider: ESecretProviderType = ESecretProviderType.ENVIRONMENT
    version: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def is_uri(self) -> bool:
        return ":" in self.ref

    def to_uri(self) -> str:
        return f"{self.provider.value}:{self.ref}"


@dataclass
class SecretValue:
    ref: SecretRef
    value: str
    version: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    cached: bool = False

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_stale(self) -> bool:
        if self.version is None:
            return False
        return False  # Staleness depends on version comparison


@dataclass
class SecretRotation:
    secret_ref: SecretRef
    current_version: str
    previous_version: str | None = None
    rotation_due_at: datetime | None = None
    last_rotated_at: datetime | None = None
```

#### 2.2.1 Secrets Provider Interface

**File:** `logging_system/security/secrets/provider.py`

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import SecretRef, SecretValue


class ISecretsProvider(ABC):
    """Interface for secrets providers."""

    @abstractmethod
    async def get(self, ref: SecretRef) -> SecretValue:
        """Retrieve a secret value."""
        ...

    @abstractmethod
    async def set(self, ref: SecretRef, value: str) -> None:
        """Store a secret value."""
        ...

    @abstractmethod
    async def delete(self, ref: SecretRef) -> None:
        """Delete a secret."""
        ...

    @abstractmethod
    async def list_versions(self, ref: SecretRef) -> list[str]:
        """List available versions."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is available."""
        ...


class EnvironmentSecretsProvider(ISecretsProvider):
    """Provider that reads from environment variables."""

    def __init__(self) -> None:
        import os
        self._env = os.environ

    async def get(self, ref: SecretRef) -> SecretValue:
        import os
        from .types import SecretValue, SecretRef

        # Convert ref to env var name
        env_var = self._ref_to_env_var(ref.ref)
        value = self._env.get(env_var)

        if value is None:
            raise KeyError(f"Environment variable not found: {env_var}")

        return SecretValue(
            ref=ref,
            value=value,
            version=os.environ.get(f"{env_var}_VERSION"),
        )

    async def set(self, ref: SecretRef, value: str) -> None:
        import os
        env_var = self._ref_to_env_var(ref.ref)
        os.environ[env_var] = value

    async def delete(self, ref: SecretRef) -> None:
        import os
        env_var = self._ref_to_env_var(ref.ref)
        os.environ.pop(env_var, None)

    async def list_versions(self, ref: SecretRef) -> list[str]:
        return ["1"]  # Environment doesn't support versions

    async def is_available(self) -> bool:
        return True

    def _ref_to_env_var(self, ref: str) -> str:
        return ref.upper().replace(":", "_").replace("-", "_")


class SecretResolver:
    """Resolves secret references in configuration."""

    def __init__(self, providers: dict[ESecretProviderType, ISecretsProvider]) -> None:
        self._providers = providers
        self._cache: dict[str, SecretValue] = {}
        self._cache_ttl_seconds: int = 300

    async def resolve(self, config: dict[str, Any]) -> dict[str, Any]:
        """Resolve all secret references in a configuration dict."""
        import json
        config_str = json.dumps(config)
        resolved_str = await self._resolve_string(config_str)
        return json.loads(resolved_str)

    async def resolve_value(self, value: str) -> str:
        """Resolve a single value that may contain secret references."""
        return await self._resolve_string(value)

    async def _resolve_string(self, text: str) -> str:
        import re
        pattern = re.compile(r'\$\{SECRET:([^}]+)\}')

        async def replace_match(match):
            ref_str = match.group(1)
            return await self._resolve_secret_ref(ref_str)

        result = text
        for match in pattern.finditer(text):
            replacement = await replace_match(match)
            result = result.replace(match.group(0), replacement)

        return result

    async def _resolve_secret_ref(self, ref_str: str) -> str:
        if ref_str in self._cache:
            cached = self._cache[ref_str]
            if not cached.is_expired():
                return cached.value

        # Parse ref
        parts = ref_str.split(":")
        if len(parts) >= 2:
            provider_type = ESecretProviderType(parts[0])
            ref_path = ":".join(parts[1:])
        else:
            provider_type = ESecretProviderType.ENVIRONMENT
            ref_path = ref_str

        ref = SecretRef(ref=ref_path, provider=provider_type)
        provider = self._providers.get(provider_type)

        if not provider:
            raise ValueError(f"No provider for {provider_type}")

        secret_value = await provider.get(ref)
        self._cache[ref_str] = secret_value
        return secret_value.value

    def clear_cache(self) -> None:
        self._cache.clear()
```

---

### Phase 3: Encryption (Depends on Phases 1, 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PHASE 3: ENCRYPTION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  3.1 Encryption Interface                                                   │
│      ├── IEncryptionService port interface                                  │
│      └── EncryptionResult dataclass                                         │
│                                                                             │
│  3.2 Fernet Implementation                                                  │
│      ├── FernetEncryptionService                                            │
│      ├── Key generation                                                     │
│      └── Key rotation support                                               │
│                                                                             │
│  3.3 Payload Encryption Integration                                         │
│      ├── Encrypt sensitive fields in payloads                               │
│      ├── Field-level encryption support                                     │
│      └── Schema-aware encryption                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 3.1.1 Encryption Service

**File:** `logging_system/security/encryption/service.py`

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import base64
import os
from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .secrets.types import SecretRef


@dataclass
class EncryptionResult:
    success: bool
    ciphertext: bytes | None = None
    plaintext: str | None = None
    error: str | None = None


class IEncryptionService(ABC):
    """Interface for encryption services."""

    @abstractmethod
    async def encrypt(self, plaintext: str) -> EncryptionResult:
        ...

    @abstractmethod
    async def decrypt(self, ciphertext: bytes) -> EncryptionResult:
        ...

    @abstractmethod
    async def generate_key(self) -> bytes:
        ...

    @abstractmethod
    async def rotate_key(self) -> bytes:
        ...


class FernetEncryptionService(IEncryptionService):
    """Fernet (AES-128-CBC + HMAC) encryption implementation."""

    def __init__(
        self,
        key: bytes | str | None = None,
        key_rotation_days: int = 90,
    ) -> None:
        if key is None:
            key = Fernet.generate_key()
        elif isinstance(key, str):
            key = key.encode()

        self._fernet = Fernet(key)
        self._key = key
        self._key_rotation_days = key_rotation_days
        self._key_created_at = datetime.utcnow()
        self._previous_key: bytes | None = None

    async def encrypt(self, plaintext: str) -> EncryptionResult:
        try:
            plaintext_bytes = plaintext.encode()
            ciphertext = self._fernet.encrypt(plaintext_bytes)
            return EncryptionResult(success=True, ciphertext=ciphertext)
        except Exception as e:
            return EncryptionResult(success=False, error=str(e))

    async def decrypt(self, ciphertext: bytes) -> EncryptionResult:
        try:
            plaintext_bytes = self._fernet.decrypt(ciphertext)
            plaintext = plaintext_bytes.decode()
            return EncryptionResult(success=True, plaintext=plaintext)
        except InvalidToken:
            # Try with previous key
            if self._previous_key:
                try:
                    fernet_prev = Fernet(self._previous_key)
                    plaintext_bytes = fernet_prev.decrypt(ciphertext)
                    plaintext = plaintext_bytes.decode()
                    return EncryptionResult(success=True, plaintext=plaintext)
                except InvalidToken:
                    pass
            return EncryptionResult(success=False, error="Decryption failed")
        except Exception as e:
            return EncryptionResult(success=False, error=str(e))

    async def generate_key(self) -> bytes:
        return Fernet.generate_key()

    async def rotate_key(self) -> bytes:
        new_key = Fernet.generate_key()
        self._previous_key = self._key
        self._key = new_key
        self._fernet = Fernet(new_key)
        self._key_created_at = datetime.utcnow()
        return new_key

    def needs_rotation(self) -> bool:
        age = datetime.utcnow() - self._key_created_at
        return age > timedelta(days=self._key_rotation_days)

    @property
    def key_id(self) -> str:
        return base64.urlsafe_b64encode(self._key[:16]).decode()


class EncryptionFacade:
    """Facade for encryption operations with field-level support."""

    SENSITIVE_FIELD_PATTERNS = [
        "password",
        "secret",
        "token",
        "apikey",
        "api_key",
        "private_key",
        "credential",
    ]

    def __init__(self, encryption_service: IEncryptionService) -> None:
        self._service = encryption_service

    async def encrypt_payload(
        self,
        payload: dict,
        sensitive_fields: list[str] | None = None,
    ) -> dict:
        """Encrypt sensitive fields in a payload."""
        if sensitive_fields is None:
            sensitive_fields = self._detect_sensitive_fields(payload)

        encrypted = dict(payload)
        for field in sensitive_fields:
            if field in encrypted:
                result = await self._service.encrypt(str(encrypted[field]))
                if result.success:
                    encrypted[field] = f"ENCRYPTED:{result.ciphertext.decode()}"

        return encrypted

    async def decrypt_payload(
        self,
        payload: dict,
        sensitive_fields: list[str] | None = None,
    ) -> dict:
        """Decrypt sensitive fields in a payload."""
        if sensitive_fields is None:
            sensitive_fields = self._detect_sensitive_fields(payload)

        decrypted = dict(payload)
        for field in sensitive_fields:
            if field in decrypted and isinstance(encrypted[field], str):
                if encrypted[field].startswith("ENCRYPTED:"):
                    ciphertext_b64 = encrypted[field].split(":", 1)[1]
                    ciphertext = base64.urlsafe_b64decode(ciphertext_b64)
                    result = await self._service.decrypt(ciphertext)
                    if result.success:
                        decrypted[field] = result.plaintext

        return decrypted

    def _detect_sensitive_fields(self, payload: dict) -> list[str]:
        """Auto-detect sensitive fields based on naming patterns."""
        sensitive = []
        for key in payload.keys():
            key_lower = key.lower()
            if any(pattern in key_lower for pattern in self.SENSITIVE_FIELD_PATTERNS):
                sensitive.append(key)
        return sensitive
```

---

### Phase 4: Rate Limiting (Depends on Phase 1)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 4: RATE LIMITING                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  4.1 Rate Limiter Interface                                                 │
│      ├── IRateLimiter port interface                                       │
│      └── RateLimitResult dataclass                                         │
│                                                                             │
│  4.2 Rate Limiter Implementations                                           │
│      ├── TokenBucketRateLimiter                                            │
│      ├── SlidingWindowRateLimiter                                          │
│      └── FixedWindowRateLimiter                                            │
│                                                                             │
│  4.3 Rate Limit Integration                                                │
│      ├── Per-adapter rate limiting                                         │
│      ├── Per-tenant rate limiting                                         │
│      └── CLI rate limiting                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 4.1.1 Rate Limiter

**File:** `logging_system/security/rate_limiting/rate_limiter.py`

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from threading import RLock
import time

from .config import RateLimitConfig, ERateLimitAlgorithm


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: float
    reset_at: float
    retry_after: float | None = None


class IRateLimiter(ABC):
    """Interface for rate limiters."""

    @abstractmethod
    async def check(self, key: str) -> RateLimitResult:
        """Check if request is allowed under rate limit."""
        ...

    @abstractmethod
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        ...


class TokenBucketRateLimiter(IRateLimiter):
    """Token bucket algorithm rate limiter."""

    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._buckets: dict[str, dict] = {}
        self._lock = RLock()

    async def check(self, key: str) -> RateLimitResult:
        now = time.monotonic()

        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = {
                    "tokens": self._config.burst_size,
                    "last_update": now,
                }

            bucket = self._buckets[key]

            # Replenish tokens
            elapsed = now - bucket["last_update"]
            tokens_to_add = elapsed * self._config.requests_per_second
            bucket["tokens"] = min(
                self._config.burst_size,
                bucket["tokens"] + tokens_to_add,
            )
            bucket["last_update"] = now

            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return RateLimitResult(
                    allowed=True,
                    remaining=bucket["tokens"],
                    reset_at=now + (1 / self._config.requests_per_second),
                )
            else:
                retry_after = (1 - bucket["tokens"]) / self._config.requests_per_second
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=now + retry_after,
                    retry_after=retry_after,
                )

    async def reset(self, key: str) -> None:
        with self._lock:
            if key in self._buckets:
                del self._buckets[key]


class RateLimitingDecorator:
    """Decorator that applies rate limiting to operations."""

    def __init__(
        self,
        rate_limiter: IRateLimiter,
        get_key: callable,
    ) -> None:
        self._limiter = rate_limiter
        self._get_key = get_key

    async def check_rate_limit(self, context: dict) -> RateLimitResult:
        key = self._get_key(context)
        return await self._limiter.check(key)


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, result: RateLimitResult) -> None:
        self.result = result
        super().__init__(
            f"Rate limit exceeded. Retry after {result.retry_after:.2f}s"
        )
```

---

### Phase 5: Audit Log Security (Depends on Phases 1, 2, 3)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PHASE 5: AUDIT LOG SECURITY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  5.1 Tamper-Evident Audit Logging                                            │
│      ├── Append-only audit log                                             │
│      ├── Log signing with HMAC                                            │
│      └── Integrity verification                                            │
│                                                                             │
│  5.2 Audit Log Configuration                                               │
│      ├── AuditLogConfig dataclass                                          │
│      └── Audit event types                                                 │
│                                                                             │
│  5.3 Audit Log Verification                                                │
│      ├── Signature verification                                            │
│      ├── Gap detection                                                     │
│      └── Tamper detection                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 5.1.1 Tamper-Evident Audit Log

**File:** `logging_system/security/audit/audit_log.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import hashlib
import hmac
import json
from pathlib import Path
from threading import RLock
from typing import Any


class EAuditEventType(str, Enum):
    SCHEMA_CREATED = "schema.created"
    SCHEMA_UPDATED = "schema.updated"
    SCHEMA_DELETED = "schema.deleted"
    POLICY_CREATED = "policy.created"
    PROFILE_ACTIVATED = "profile.activated"
    CONFIG_APPLIED = "config.applied"
    ADAPTER_BOUND = "adapter.bound"
    ADAPTER_UNBOUND = "adapter.unbound"
    CONTAINER_ASSIGNED = "container.assigned"
    CONTAINER_UNASSIGNED = "container.unassigned"
    EXECUTION_ASSIGNED = "execution.assigned"
    EXECUTION_UNASSIGNED = "execution.unassigned"


@dataclass
class AuditEvent:
    event_id: str
    event_type: EAuditEventType
    timestamp_utc: str
    actor: str
    resource_type: str
    resource_id: str
    changes: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    signature: str | None = None
    previous_hash: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, default=str)

    def compute_hash(self) -> str:
        content = self.to_json()
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class AuditLogConfig:
    log_path: Path
    enable_signing: bool = True
    enable_hash_chain: bool = True
    key_ref: str | None = None
    retention_days: int = 365


class TamperEvidentAuditLog:
    """Audit log with tamper detection via hash chain and HMAC signatures."""

    def __init__(self, config: AuditLogConfig, signing_key: bytes) -> None:
        self._config = config
        self._signing_key = signing_key
        self._lock = RLock()
        self._last_hash: str | None = None
        self._load_last_hash()

    def append(self, event: AuditEvent) -> None:
        with self._lock:
            # Set previous hash for chain
            event.previous_hash = self._last_hash

            # Compute event hash
            event_hash = event.compute_hash()

            # Sign the event
            if self._config.enable_signing:
                signature = hmac.new(
                    self._signing_key,
                    event_hash.encode(),
                    hashlib.sha256,
                ).hexdigest()
                event.signature = signature

            # Write to log
            self._append_to_file(event)

            # Update chain
            if self._config.enable_hash_chain:
                self._last_hash = event_hash

    def verify_integrity(self) -> dict[str, Any]:
        """Verify the integrity of the entire audit log."""
        issues = []
        expected_hash: str | None = None

        with self._lock:
            if not self._config.log_path.exists():
                return {"valid": True, "issues": []}

            with open(self._config.log_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        event_data = json.loads(line)
                        event = AuditEvent(**event_data)

                        # Verify previous hash chain
                        if self._config.enable_hash_chain:
                            if event.previous_hash != expected_hash:
                                issues.append({
                                    "type": "hash_chain_broken",
                                    "line": line_num,
                                    "event_id": event.event_id,
                                    "expected": expected_hash,
                                    "found": event.previous_hash,
                                })

                        # Verify signature
                        if self._config.enable_signing and event.signature:
                            computed_hash = event.compute_hash()
                            expected_sig = hmac.new(
                                self._signing_key,
                                computed_hash.encode(),
                                hashlib.sha256,
                            ).hexdigest()

                            if event.signature != expected_sig:
                                issues.append({
                                    "type": "invalid_signature",
                                    "line": line_num,
                                    "event_id": event.event_id,
                                })

                        expected_hash = event.compute_hash()

                    except Exception as e:
                        issues.append({
                            "type": "parse_error",
                            "line": line_num,
                            "error": str(e),
                        })

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_events": line_num if issues else 0,
        }

    def _append_to_file(self, event: AuditEvent) -> None:
        self._config.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config.log_path, "a", encoding="utf-8") as f:
            f.write(event.to_json() + "\n")

    def _load_last_hash(self) -> None:
        if not self._config.log_path.exists():
            return

        with open(self._config.log_path, "r", encoding="utf-8") as f:
            for line in f:
                event_data = json.loads(line)
                event_hash = AuditEvent(**event_data).compute_hash()
                self._last_hash = event_hash
```

---

## File Structure After Implementation

```
logging_system/
├── security/
│   ├── __init__.py
│   ├── config.py                      # Phase 1
│   ├── sanitization.py              # Phase 1
│   ├── patterns.py                  # Phase 1
│   ├── secrets/
│   │   ├── __init__.py
│   │   ├── types.py                 # Phase 2
│   │   ├── provider.py              # Phase 2
│   │   └── resolver.py              # Phase 2
│   ├── encryption/
│   │   ├── __init__.py
│   │   ├── service.py              # Phase 3
│   │   └── facade.py               # Phase 3
│   ├── rate_limiting/
│   │   ├── __init__.py
│   │   ├── rate_limiter.py         # Phase 4
│   │   └── decorators.py           # Phase 4
│   └── audit/
│       ├── __init__.py
│       ├── audit_log.py            # Phase 5
│       └── verifier.py             # Phase 5
```

---

## Contract Additions

| Contract | Name | Purpose |
|----------|------|---------|
| 33 | `33_LoggingSystem_SecuritySanitization_Contract.template.yaml` | Input sanitization contract |
| 34 | `34_LoggingSystem_SecretsManagement_Contract.template.yaml` | Secrets provider contract |
| 35 | `35_LoggingSystem_Encryption_Contract.template.yaml` | Encryption service contract |
| 36 | `36_LoggingSystem_RateLimiting_Contract.template.yaml` | Rate limiting contract |

---

## Test Plan

| Phase | Tests | Focus |
|-------|-------|-------|
| 1 | 20 | Input sanitization, pattern matching |
| 2 | 15 | Secrets resolution, caching |
| 3 | 15 | Encryption/decryption, key rotation |
| 4 | 15 | Rate limiter algorithms |
| 5 | 10 | Audit log integrity verification |

---

## Security Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| `security_sanitization_rejections_total` | Rejected inputs | < 1% |
| `security_rate_limit_blocks_total` | Rate limit blocks | < 5% |
| `security_audit_events_total` | Audit events logged | > 99.9% |
| `security_audit_verification_failures` | Integrity check failures | 0 |

---

**Estimated Implementation Time:** 2-3 weeks  
**Estimated Effort:** ~2000 lines of new code  
**Risk Level:** High (security-critical components)
