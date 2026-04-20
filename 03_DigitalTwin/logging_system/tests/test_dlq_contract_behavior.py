import pytest

from logging_system.errors import (
    DLQConfig,
    DLQEntry,
    DLQStatistics,
    EDLQStatus,
)


class TestEDLQStatus:
    def test_dlq_status_values(self):
        assert EDLQStatus.PENDING.value == "PENDING"
        assert EDLQStatus.RETRYING.value == "RETRYING"
        assert EDLQStatus.FAILED.value == "FAILED"
        assert EDLQStatus.EXPIRED.value == "EXPIRED"
        assert EDLQStatus.DISCARDED.value == "DISCARDED"

    def test_dlq_status_count(self):
        assert len(EDLQStatus) == 5

    def test_dlq_status_is_string_enum(self):
        assert isinstance(EDLQStatus.PENDING, str)
        assert EDLQStatus.PENDING == "PENDING"


class TestDLQEntry:
    def test_dlq_entry_creation(self):
        entry = DLQEntry(
            entry_id="test-001",
            error_code="NETWORK_ERROR",
            message="Connection failed",
            payload={"url": "http://example.com"},
        )
        assert entry.entry_id == "test-001"
        assert entry.error_code == "NETWORK_ERROR"
        assert entry.message == "Connection failed"
        assert entry.payload == {"url": "http://example.com"}
        assert entry.status == EDLQStatus.PENDING
        assert entry.retry_count == 0
        assert entry.max_attempts == 3
        assert entry.timestamp_utc is not None

    def test_dlq_entry_with_metadata(self):
        entry = DLQEntry(
            entry_id="test-002",
            error_code="TIMEOUT",
            message="Request timed out",
            payload={"timeout": 30},
            metadata={"request_id": "12345"},
        )
        assert entry.metadata == {"request_id": "12345"}

    def test_dlq_entry_to_dict(self):
        entry = DLQEntry(
            entry_id="test-003",
            error_code="NETWORK_ERROR",
            message="Error message",
            payload="test",
        )
        result = entry.to_dict()
        assert result["entry_id"] == "test-003"
        assert result["error_code"] == "NETWORK_ERROR"
        assert result["status"] == "PENDING"
        assert "timestamp_utc" in result

    def test_dlq_entry_is_frozen(self):
        entry = DLQEntry(
            entry_id="test",
            error_code="ERROR",
            message="msg",
            payload=None,
        )
        with pytest.raises(Exception):
            entry.retry_count = 5


class TestDLQConfig:
    def test_dlq_config_defaults(self):
        config = DLQConfig()
        assert config.max_entries == 1000
        assert config.max_attempts == 3
        assert config.retry_delay_seconds == 60.0
        assert config.expiration_seconds == 86400.0
        assert config.enable_auto_retry is True
        assert config.auto_retry_interval_seconds == 300.0

    def test_dlq_config_custom_values(self):
        config = DLQConfig(
            max_entries=500,
            max_attempts=5,
            retry_delay_seconds=120.0,
            expiration_seconds=172800.0,
        )
        assert config.max_entries == 500
        assert config.max_attempts == 5
        assert config.retry_delay_seconds == 120.0
        assert config.expiration_seconds == 172800.0

    def test_dlq_config_validation_max_entries_negative(self):
        with pytest.raises(ValueError, match="max_entries"):
            DLQConfig(max_entries=-1)

    def test_dlq_config_validation_max_attempts_zero(self):
        with pytest.raises(ValueError, match="max_attempts"):
            DLQConfig(max_attempts=0)

    def test_dlq_config_validation_retry_delay_zero(self):
        with pytest.raises(ValueError, match="retry_delay"):
            DLQConfig(retry_delay_seconds=0)

    def test_dlq_config_validation_expiration_zero(self):
        with pytest.raises(ValueError, match="expiration"):
            DLQConfig(expiration_seconds=0)

    def test_dlq_config_is_frozen(self):
        config = DLQConfig()
        with pytest.raises(Exception):
            config.max_entries = 500


class TestDLQStatistics:
    def test_dlq_statistics_defaults(self):
        stats = DLQStatistics()
        assert stats.total_entries == 0
        assert stats.pending_entries == 0
        assert stats.retrying_entries == 0
        assert stats.failed_entries == 0
        assert stats.expired_entries == 0
        assert stats.discarded_entries == 0
        assert stats.total_retries == 0
        assert stats.successful_recoveries == 0
        assert stats.last_updated_utc is not None

    def test_dlq_statistics_to_dict(self):
        stats = DLQStatistics(
            total_entries=100,
            pending_entries=50,
            failed_entries=10,
        )
        result = stats.to_dict()
        assert result["total_entries"] == 100
        assert result["pending_entries"] == 50
        assert result["failed_entries"] == 10
