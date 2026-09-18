from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# --- OpenTelemetry setup ---
resource = Resource.create({"service.name": "gitops-demo-app"})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger.observability.svc.cluster.local:4318/v1/traces")
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)

app = FastAPI()

# Auto-instrument all FastAPI routes (no manual span code needed per-route)
FastAPIInstrumentor.instrument_app(app)

APP_VERSION = "2.0.0"

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {"version": APP_VERSION, "message": "Hello from GitOps demo app v2 - UPDATED"}

@app.get("/")
def root():
    return {"service": "gitops-demo-app", "status": "running"}
