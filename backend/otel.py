"""
OpenTelemetry setup for VFR Outlook backend.

Exports traces, metrics, and logs to the OTLP gRPC endpoint configured via
OTEL_EXPORTER_OTLP_ENDPOINT (default: http://otel-collector.monitoring:4317).

Call configure_otel() once at startup before the FastAPI app is created.
"""

import logging
import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

_DEFAULT_OTLP_ENDPOINT = "http://otel-collector.monitoring:4317"


def configure_otel() -> None:
    """Initialize and register the global TracerProvider, MeterProvider, and LoggerProvider."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", _DEFAULT_OTLP_ENDPOINT)

    resource = Resource.create(
        {
            SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME", "vfr-outlook-backend"),
            SERVICE_VERSION: os.environ.get("OTEL_SERVICE_VERSION", "0.1.0"),
            "deployment.environment": os.environ.get("OTEL_DEPLOYMENT_ENV", "production"),
        }
    )

    # ── Traces ──────────────────────────────────────────────────────────────
    span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # ── Metrics ─────────────────────────────────────────────────────────────
    metric_exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter,
        export_interval_millis=int(os.environ.get("OTEL_METRIC_EXPORT_INTERVAL_MS", "15000")),
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # ── Logs ────────────────────────────────────────────────────────────────
    # Ship WARNING+ records to the OTel collector (→ Loki) and also write
    # them to stdout so they appear in pod logs.
    log_exporter = OTLPLogExporter(endpoint=endpoint, insecure=True)
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

    otel_handler = LoggingHandler(level=logging.WARNING, logger_provider=logger_provider)
    stdout_handler = logging.StreamHandler()
    stdout_handler.setLevel(logging.WARNING)
    stdout_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))

    logging.basicConfig(level=logging.WARNING, handlers=[stdout_handler, otel_handler])


def get_tracer(name: str = "vfr-outlook") -> trace.Tracer:
    return trace.get_tracer(name)


def get_meter(name: str = "vfr-outlook") -> metrics.Meter:
    return metrics.get_meter(name)
