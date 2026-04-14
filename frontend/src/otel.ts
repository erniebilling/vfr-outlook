/**
 * OpenTelemetry browser instrumentation for VFR Outlook.
 *
 * Sends traces and metrics to the OTLP HTTP endpoint on the OTel collector.
 * The collector URL is read from VITE_OTEL_COLLECTOR_URL at build time
 * (default: http://otel-collector.monitoring:4318).
 *
 * Call initOtel() once before rendering the React tree.
 */

import { WebTracerProvider } from '@opentelemetry/sdk-trace-web'
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-web'
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http'
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http'
import { MeterProvider, PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics'
import { FetchInstrumentation } from '@opentelemetry/instrumentation-fetch'
import { registerInstrumentations } from '@opentelemetry/instrumentation'
import { Resource } from '@opentelemetry/resources'
import { ZoneContextManager } from '@opentelemetry/context-zone'
import {
  SEMRESATTRS_SERVICE_NAME,
  SEMRESATTRS_SERVICE_VERSION,
} from '@opentelemetry/semantic-conventions'
import { metrics, trace } from '@opentelemetry/api'

const COLLECTOR_URL =
  (import.meta.env.VITE_OTEL_COLLECTOR_URL as string | undefined) ??
  'http://otel-collector.monitoring:4318'

const resource = new Resource({
  [SEMRESATTRS_SERVICE_NAME]: 'vfr-outlook-frontend',
  [SEMRESATTRS_SERVICE_VERSION]: '0.1.0',
})

let _initialized = false

export function initOtel(): void {
  if (_initialized) return
  _initialized = true

  // ── Traces ────────────────────────────────────────────────────────────────
  const traceExporter = new OTLPTraceExporter({
    url: `${COLLECTOR_URL}/v1/traces`,
  })

  const tracerProvider = new WebTracerProvider({
    resource,
    spanProcessors: [new BatchSpanProcessor(traceExporter)],
  })

  tracerProvider.register({
    contextManager: new ZoneContextManager(),
  })

  trace.setGlobalTracerProvider(tracerProvider)

  // ── Metrics ───────────────────────────────────────────────────────────────
  const metricExporter = new OTLPMetricExporter({
    url: `${COLLECTOR_URL}/v1/metrics`,
  })

  const meterProvider = new MeterProvider({
    resource,
    readers: [
      new PeriodicExportingMetricReader({
        exporter: metricExporter,
        exportIntervalMillis: 15_000,
      }),
    ],
  })

  metrics.setGlobalMeterProvider(meterProvider)

  // ── Auto-instrument fetch (picks up all /api calls) ───────────────────────
  registerInstrumentations({
    instrumentations: [
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: [/.*/],
        clearTimingResources: true,
      }),
    ],
  })
}

/** Tracer for manual spans (e.g. scoring, map render). */
export function getTracer() {
  return trace.getTracer('vfr-outlook-frontend')
}

/** Meter for custom counters / histograms. */
export function getMeter() {
  return metrics.getMeter('vfr-outlook-frontend')
}
