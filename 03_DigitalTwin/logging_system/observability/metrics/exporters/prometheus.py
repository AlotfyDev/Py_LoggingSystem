"""
Prometheus exporter for Py_LoggingSystem observability metrics.

This module provides exporters that can convert metrics to Prometheus text format
for integration with Prometheus monitoring systems.
"""

from typing import List, Dict, Any
from ..registry import MetricRegistry
from ..types import EMetricType, MetricValue, CounterValue, GaugeValue, HistogramValue


class PrometheusExporter:
    """
    Exports metrics in Prometheus text format.

    This exporter converts metrics from the registry into the Prometheus
    text-based exposition format for scraping by Prometheus servers.
    """

    def __init__(self, registry: MetricRegistry):
        """
        Initialize the Prometheus exporter.

        Args:
            registry: Metric registry to export from
        """
        self._registry = registry

    def export(self) -> str:
        """
        Export all metrics in Prometheus text format.

        Returns:
            String containing all metrics in Prometheus format
        """
        lines = []

        # Get all metrics from registry
        metrics = self._registry.collect()

        # Group metrics by name for better organization
        metrics_by_name = {}
        for metric in metrics:
            name = metric.metadata.name
            if name not in metrics_by_name:
                metrics_by_name[name] = []
            metrics_by_name[name].append(metric)

        # Export each metric group
        for name, metric_list in metrics_by_name.items():
            # Use the first metric for type and help (they should be consistent)
            first_metric = metric_list[0]

            # Add TYPE annotation
            metric_type = self._get_prometheus_type(first_metric.metadata.type)
            lines.append(f"# TYPE {name} {metric_type}")

            # Add HELP comment if description exists
            if first_metric.metadata.description:
                lines.append(f"# HELP {name} {first_metric.metadata.description}")

            # Export each metric instance
            for metric in metric_list:
                lines.extend(self._export_metric(name, metric))

        return "\n".join(lines) + "\n"

    def _get_prometheus_type(self, metric_type: EMetricType) -> str:
        """
        Convert internal metric type to Prometheus type string.

        Args:
            metric_type: Internal metric type

        Returns:
            Prometheus type string
        """
        type_mapping = {
            EMetricType.COUNTER: "counter",
            EMetricType.GAUGE: "gauge",
            EMetricType.HISTOGRAM: "histogram",
            EMetricType.SUMMARY: "summary"  # Not implemented yet
        }
        return type_mapping.get(metric_type, "untyped")

    def _export_metric(self, name: str, metric: MetricValue) -> List[str]:
        """
        Export a single metric in Prometheus format.

        Args:
            name: Metric name
            metric: Metric to export

        Returns:
            List of Prometheus format lines
        """
        lines = []

        # Format labels
        labels_str = self._format_labels(metric.metadata.labels)

        if isinstance(metric, CounterValue):
            # Counter format: <name>{<labels>} <value>
            lines.append(f"{name}{labels_str} {metric.value}")

        elif isinstance(metric, GaugeValue):
            # Gauge format: <name>{<labels>} <value>
            lines.append(f"{name}{labels_str} {metric.value}")

        elif isinstance(metric, HistogramValue):
            # Histogram format requires special handling
            lines.extend(self._export_histogram(name, metric, labels_str))

        else:
            # Generic format for other metric types
            if hasattr(metric, 'value'):
                lines.append(f"{name}{labels_str} {metric.value}")

        return lines

    def _export_histogram(self, name: str, histogram: Any, base_labels_str: str) -> List[str]:
        """
        Export histogram in Prometheus format.

        Args:
            name: Histogram name
            histogram: HistogramValue instance
            base_labels_str: Formatted base labels string (without le)

        Returns:
            List of Prometheus format lines for histogram
        """
        lines = []

        # Parse base labels to add le label
        base_labels = self._parse_labels_str(base_labels_str)

        # Export buckets
        for i, boundary in enumerate(histogram.buckets):
            bucket_count = histogram.bucket_counts[i]
            # Add le label to base labels
            bucket_labels = dict(base_labels)
            bucket_labels['le'] = str(boundary)
            bucket_labels_str = self._format_labels(bucket_labels)
            lines.append(f"{name}_bucket{bucket_labels_str} {bucket_count}")

        # Export +Inf bucket (last bucket count)
        inf_count = histogram.bucket_counts[-1]
        inf_labels = dict(base_labels)
        inf_labels['le'] = "+Inf"
        inf_labels_str = self._format_labels(inf_labels)
        lines.append(f"{name}_bucket{inf_labels_str} {inf_count}")

        # Export count
        lines.append(f"{name}_count{base_labels_str} {histogram.count}")

        # Export sum
        lines.append(f"{name}_sum{base_labels_str} {histogram.sum}")

        return lines

    def _parse_labels_str(self, labels_str: str) -> Dict[str, str]:
        """
        Parse a formatted labels string back into a dictionary.

        Args:
            labels_str: Formatted labels string like {key1="value1",key2="value2"}

        Returns:
            Dictionary of labels
        """
        if not labels_str or labels_str == "{}":
            return {}

        # Remove braces and split by comma
        inner = labels_str[1:-1]  # Remove { and }
        if not inner:
            return {}

        labels = {}
        for part in inner.split(','):
            if '=' in part:
                key, value = part.split('=', 1)
                # Remove quotes from value
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                # Unescape quotes and backslashes
                value = value.replace('\\"', '"').replace('\\\\', '\\')
                labels[key] = value

        return labels

    def _format_labels(self, labels: Dict[str, str]) -> str:
        """
        Format labels dictionary into Prometheus label string.

        Args:
            labels: Dictionary of label key-value pairs

        Returns:
            Formatted label string like {key1="value1",key2="value2"}
        """
        if not labels:
            return ""

        label_parts = []
        for key, value in sorted(labels.items()):  # Sort for consistent output
            # Escape quotes and backslashes in label values
            escaped_value = str(value).replace('\\', '\\\\').replace('"', '\\"')
            label_parts.append(f'{key}="{escaped_value}"')

        return "{" + ",".join(label_parts) + "}"