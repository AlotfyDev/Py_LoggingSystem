"""
Unit tests for metric types in Py_LoggingSystem.

Tests the core metric data structures and their behavior.
"""

import pytest
from datetime import datetime, timezone

from logging_system.observability.metrics.types import (
    EMetricType,
    MetricMetadata,
    MetricValue,
    CounterValue,
    GaugeValue,
    HistogramValue,
)


class TestEMetricType:
    """Test the EMetricType enumeration."""

    def test_metric_type_enum_values(self):
        """Test that EMetricType contains exactly the required values."""
        expected_values = {"counter", "gauge", "histogram", "summary"}
        actual_values = {metric_type.value for metric_type in EMetricType}
        assert actual_values == expected_values

        # Verify all enum members exist
        assert EMetricType.COUNTER.value == "counter"
        assert EMetricType.GAUGE.value == "gauge"
        assert EMetricType.HISTOGRAM.value == "histogram"
        assert EMetricType.SUMMARY.value == "summary"


class TestMetricMetadata:
    """Test the MetricMetadata dataclass."""

    def test_metric_metadata_creation(self):
        """Test creating a MetricMetadata instance."""
        metadata = MetricMetadata(
            name="http_requests_total",
            type=EMetricType.COUNTER,
            description="Total number of HTTP requests",
            unit="requests",
            labels={"method": "GET", "status": "200"}
        )

        assert metadata.name == "http_requests_total"
        assert metadata.type == EMetricType.COUNTER
        assert metadata.description == "Total number of HTTP requests"
        assert metadata.unit == "requests"
        assert metadata.labels == {"method": "GET", "status": "200"}

    def test_metric_metadata_minimal(self):
        """Test creating a MetricMetadata with minimal required fields."""
        metadata = MetricMetadata(
            name="memory_usage",
            type=EMetricType.GAUGE,
            description="Current memory usage"
        )

        assert metadata.name == "memory_usage"
        assert metadata.type == EMetricType.GAUGE
        assert metadata.description == "Current memory usage"
        assert metadata.unit is None
        assert metadata.labels is None

    def test_metric_metadata_to_dict(self):
        """Test converting MetricMetadata to dictionary."""
        metadata = MetricMetadata(
            name="response_time",
            type=EMetricType.HISTOGRAM,
            description="HTTP response time",
            unit="seconds",
            labels={"endpoint": "/api/v1"}
        )

        result = metadata.to_dict()

        expected = {
            "name": "response_time",
            "type": "histogram",
            "description": "HTTP response time",
            "unit": "seconds",
            "labels": {"endpoint": "/api/v1"}
        }

        assert result == expected

    def test_metric_metadata_to_dict_empty_labels(self):
        """Test converting MetricMetadata to dictionary with no labels."""
        metadata = MetricMetadata(
            name="cpu_usage",
            type=EMetricType.GAUGE,
            description="CPU usage percentage"
        )

        result = metadata.to_dict()

        expected = {
            "name": "cpu_usage",
            "type": "gauge",
            "description": "CPU usage percentage",
            "unit": None,
            "labels": {}
        }

        assert result == expected


class TestMetricValue:
    """Test the MetricValue base class."""

    def test_metric_value_creation(self):
        """Test creating a MetricValue instance."""
        metadata = MetricMetadata(
            name="test_metric",
            type=EMetricType.GAUGE,
            description="Test metric"
        )
        timestamp = datetime.now(timezone.utc)
        value = MetricValue(
            metadata=metadata,
            timestamp=timestamp,
            value=42.5
        )

        assert value.metadata == metadata
        assert value.timestamp == timestamp
        assert value.value == 42.5

    def test_metric_value_to_dict(self):
        """Test converting MetricValue to dictionary."""
        metadata = MetricMetadata(
            name="test_metric",
            type=EMetricType.GAUGE,
            description="Test metric"
        )
        timestamp = datetime(2026, 4, 17, 16, 30, 0, tzinfo=timezone.utc)
        value = MetricValue(
            metadata=metadata,
            timestamp=timestamp,
            value=42.5
        )

        result = value.to_dict()

        expected = {
            "metadata": {
                "name": "test_metric",
                "type": "gauge",
                "description": "Test metric",
                "unit": None,
                "labels": {}
            },
            "timestamp": "2026-04-17T16:30:00+00:00",
            "value": 42.5
        }

        assert result == expected


class TestCounterValue:
    """Test the CounterValue dataclass."""

    def test_counter_value_creation(self):
        """Test creating a CounterValue instance."""
        metadata = MetricMetadata(
            name="requests_total",
            type=EMetricType.COUNTER,
            description="Total requests"
        )
        timestamp = datetime.now(timezone.utc)

        counter = CounterValue(
            metadata=metadata,
            timestamp=timestamp,
            value=100
        )

        assert counter.metadata == metadata
        assert counter.timestamp == timestamp
        assert counter.value == 100

    def test_counter_value_negative_validation(self):
        """Test that negative counter values are rejected."""
        metadata = MetricMetadata(
            name="test_counter",
            type=EMetricType.COUNTER,
            description="Test counter"
        )

        with pytest.raises(ValueError, match="Counter values must be non-negative"):
            CounterValue(
                metadata=metadata,
                timestamp=datetime.now(timezone.utc),
                value=-1
            )

    def test_counter_value_zero_allowed(self):
        """Test that zero counter values are allowed."""
        metadata = MetricMetadata(
            name="test_counter",
            type=EMetricType.COUNTER,
            description="Test counter"
        )

        counter = CounterValue(
            metadata=metadata,
            timestamp=datetime.now(timezone.utc),
            value=0
        )

        assert counter.value == 0

    def test_counter_increment(self):
        """Test incrementing a counter value."""
        metadata = MetricMetadata(
            name="test_counter",
            type=EMetricType.COUNTER,
            description="Test counter"
        )
        original_timestamp = datetime(2026, 4, 17, 16, 0, 0, tzinfo=timezone.utc)

        counter = CounterValue(
            metadata=metadata,
            timestamp=original_timestamp,
            value=50
        )

        # Increment by default (1)
        new_counter = counter.increment()

        assert new_counter.value == 51
        assert new_counter.metadata == metadata
        assert new_counter.timestamp != original_timestamp  # Should be updated to current time

        # Increment by specific amount
        new_counter2 = counter.increment(5)
        assert new_counter2.value == 55

    def test_counter_increment_negative_amount(self):
        """Test that negative increment amounts are rejected."""
        metadata = MetricMetadata(
            name="test_counter",
            type=EMetricType.COUNTER,
            description="Test counter"
        )

        counter = CounterValue(
            metadata=metadata,
            timestamp=datetime.now(timezone.utc),
            value=50
        )

        with pytest.raises(ValueError, match="Increment amount must be non-negative"):
            counter.increment(-1)


class TestGaugeValue:
    """Test the GaugeValue dataclass."""

    def test_gauge_value_creation(self):
        """Test creating a GaugeValue instance."""
        metadata = MetricMetadata(
            name="memory_usage",
            type=EMetricType.GAUGE,
            description="Memory usage",
            unit="bytes"
        )
        timestamp = datetime.now(timezone.utc)

        gauge = GaugeValue(
            metadata=metadata,
            timestamp=timestamp,
            value=1024.5
        )

        assert gauge.metadata == metadata
        assert gauge.timestamp == timestamp
        assert gauge.value == 1024.5

    def test_gauge_value_update(self):
        """Test updating a gauge value."""
        metadata = MetricMetadata(
            name="temperature",
            type=EMetricType.GAUGE,
            description="Temperature",
            unit="celsius"
        )
        original_timestamp = datetime(2026, 4, 17, 16, 0, 0, tzinfo=timezone.utc)

        gauge = GaugeValue(
            metadata=metadata,
            timestamp=original_timestamp,
            value=25.0
        )

        # Update to new value
        new_gauge = gauge.update(30.5)

        assert new_gauge.value == 30.5
        assert new_gauge.metadata == metadata
        assert new_gauge.timestamp != original_timestamp  # Should be updated to current time

    def test_gauge_value_negative_allowed(self):
        """Test that negative gauge values are allowed."""
        metadata = MetricMetadata(
            name="temperature_change",
            type=EMetricType.GAUGE,
            description="Temperature change"
        )

        gauge = GaugeValue(
            metadata=metadata,
            timestamp=datetime.now(timezone.utc),
            value=-5.2
        )

        assert gauge.value == -5.2


class TestHistogramValue:
    """Test the HistogramValue dataclass."""

    def test_histogram_value_creation(self):
        """Test creating a HistogramValue instance."""
        metadata = MetricMetadata(
            name="response_time",
            type=EMetricType.HISTOGRAM,
            description="Response time",
            unit="seconds"
        )
        timestamp = datetime.now(timezone.utc)

        histogram = HistogramValue(
            metadata=metadata,
            timestamp=timestamp,
            value=0.0,  # Histogram value is not used directly
            count=100,
            sum=250.5,
            buckets=[0.1, 0.5, 1.0, 2.0],
            bucket_counts=[10, 30, 40, 15, 5],
            min=0.05,
            max=2.8
        )

        assert histogram.metadata == metadata
        assert histogram.timestamp == timestamp
        assert histogram.count == 100
        assert histogram.sum == 250.5
        assert histogram.buckets == [0.1, 0.5, 1.0, 2.0]
        assert histogram.bucket_counts == [10, 30, 40, 15, 5]
        assert histogram.min == 0.05
        assert histogram.max == 2.8

    def test_histogram_value_bucket_validation(self):
        """Test that histogram bucket counts must match bucket boundaries + 1."""
        metadata = MetricMetadata(
            name="test_histogram",
            type=EMetricType.HISTOGRAM,
            description="Test histogram"
        )

        # buckets has 4 elements, bucket_counts should have 5
        with pytest.raises(ValueError, match="bucket_counts must have one more element than buckets"):
            HistogramValue(
                metadata=metadata,
                timestamp=datetime.now(timezone.utc),
                value=0.0,
                count=10,
                sum=50.0,
                buckets=[0.1, 0.5, 1.0, 2.0],  # 4 buckets
                bucket_counts=[1, 2, 3, 4]      # 4 counts (should be 5)
            )

    def test_histogram_value_negative_count(self):
        """Test that negative count values are rejected."""
        metadata = MetricMetadata(
            name="test_histogram",
            type=EMetricType.HISTOGRAM,
            description="Test histogram"
        )

        with pytest.raises(ValueError, match="Count must be non-negative"):
            HistogramValue(
                metadata=metadata,
                timestamp=datetime.now(timezone.utc),
                value=0.0,
                count=-1,
                sum=0.0,
                buckets=[1.0],
                bucket_counts=[0, 0]
            )

    def test_histogram_value_negative_bucket_count(self):
        """Test that negative bucket counts are rejected."""
        metadata = MetricMetadata(
            name="test_histogram",
            type=EMetricType.HISTOGRAM,
            description="Test histogram"
        )

        with pytest.raises(ValueError, match="Bucket counts must be non-negative"):
            HistogramValue(
                metadata=metadata,
                timestamp=datetime.now(timezone.utc),
                value=0.0,
                count=10,
                sum=50.0,
                buckets=[1.0],
                bucket_counts=[5, -1]  # Negative bucket count
            )

    def test_histogram_observe(self):
        """Test observing values in a histogram."""
        metadata = MetricMetadata(
            name="test_histogram",
            type=EMetricType.HISTOGRAM,
            description="Test histogram"
        )

        histogram = HistogramValue(
            metadata=metadata,
            timestamp=datetime(2026, 4, 17, 16, 0, 0, tzinfo=timezone.utc),
            value=0.0,
            count=0,
            sum=0.0,
            buckets=[1.0, 5.0, 10.0],
            bucket_counts=[0, 0, 0, 0]
        )

        # Observe a value of 3.0 (should go in bucket 1: <= 5.0)
        new_histogram = histogram.observe(3.0)

        assert new_histogram.count == 1
        assert new_histogram.sum == 3.0
        assert new_histogram.min == 3.0
        assert new_histogram.max == 3.0
        assert new_histogram.bucket_counts == [0, 1, 1, 1]  # Buckets: <=1.0, <=5.0, <=10.0, >10.0

    def test_histogram_percentile(self):
        """Test calculating percentiles from histogram data."""
        metadata = MetricMetadata(
            name="test_histogram",
            type=EMetricType.HISTOGRAM,
            description="Test histogram"
        )

        histogram = HistogramValue(
            metadata=metadata,
            timestamp=datetime.now(timezone.utc),
            value=0.0,
            count=100,
            sum=500.0,
            buckets=[10.0, 50.0, 100.0],
            bucket_counts=[10, 30, 40, 20]  # 10 values <=10, 30 <=50, 40 <=100, 20 >100
        )

        # 50th percentile should be around 50.0 (middle bucket)
        p50 = histogram.percentile(50.0)
        assert p50 == 50.0  # Should return the bucket boundary

        # 90th percentile should be around 100.0
        p90 = histogram.percentile(90.0)
        assert p90 == 100.0

        # Test edge cases
        assert histogram.percentile(-1) is None  # Invalid percentile
        assert histogram.percentile(101) is None  # Invalid percentile

    def test_histogram_percentile_empty(self):
        """Test percentile calculation on empty histogram."""
        metadata = MetricMetadata(
            name="empty_histogram",
            type=EMetricType.HISTOGRAM,
            description="Empty histogram"
        )

        histogram = HistogramValue(
            metadata=metadata,
            timestamp=datetime.now(timezone.utc),
            value=0.0,
            count=0,
            sum=0.0,
            buckets=[1.0, 5.0],
            bucket_counts=[0, 0, 0]
        )

        assert histogram.percentile(50.0) is None