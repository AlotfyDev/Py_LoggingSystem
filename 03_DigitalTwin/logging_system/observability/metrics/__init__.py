"""
Metrics package for Py_LoggingSystem observability.

This module provides metric collection, storage, and export capabilities
following OpenTelemetry and Prometheus patterns.
"""

from .instruments import Counter, Gauge, Histogram
from .registry import (
    MetricRegistry,
    counter,
    gauge_set,
    gauge_inc,
    histogram_observe,
    collect,
)
from .types import (
    EMetricType,
    MetricMetadata,
    MetricValue,
    CounterValue,
    GaugeValue,
    HistogramValue,
)

__all__ = [
    "EMetricType",
    "MetricMetadata",
    "MetricValue",
    "CounterValue",
    "GaugeValue",
    "HistogramValue",
]