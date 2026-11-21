# NexusOps: Workload, Telemetry, and Event Processing (Sections B & C)

This guide explains how information travels from an application to the NexusOps monitoring platform, how that information is processed, and how it can become an incident.

## 1. The big picture

Imagine NexusOps is monitoring three independently running applications:

- Order Service
- Payment Service
- Notification Service

If the Payment Service starts failing, NexusOps needs information about what is happening inside it. That information is called **telemetry**.

The architecture has two major responsibilities:

- **B. Workload and Telemetry Collection:** Collect information from applications and infrastructure.
- **C. Event Backbone and Stream Processing:** Process that information, detect problems, and create incidents.

The high-level event flow is:

```text
Payment Service
    -> OpenTelemetry instrumentation and Collector
    -> Kafka
    -> Telemetry Worker
    -> NexusOps Incident Management
```

The application generates logs, metrics, and traces. The Collector receives and routes telemetry, Kafka buffers events, and the Telemetry Worker processes events and detects failures.

## 2. What is telemetry?

Telemetry is information that describes what is happening inside an application.
For example, when someone uses the Payment Service, we might want to know:

- Did the API request succeed?
- How long did it take?
- Did an exception occur?
- Which database query failed?
- How much memory is the application consuming?

There are three major types of telemetry.

### Logs

Logs tell us **what happened**. For example:

```text
10:30:01 INFO Payment request received
10:30:02 INFO Connecting to database
10:30:03 ERROR Database connection timeout
10:30:03 ERROR Payment processing failed
```

Logs help engineers understand individual events and errors.

### Metrics

Metrics tell us **how much, how often, or how well something is performing**.
Examples include:

| Metric | Example value |
| --- | ---: |
| CPU usage | 85% |
| Memory usage | 78% |
| API latency | 2.4 seconds |
| Error rate | 35% |
| Requests per second | 500 |

Unlike logs, metrics are generally numerical measurements collected over time.
For example, we can calculate average API latency over the last five minutes.

### Traces

Traces tell us **how a request travels through multiple services**. Suppose a customer places an order:

| Step | Component | Activity | Duration |
| ---: | --- | --- | ---: |
| 1 | Order Service | Request received | 20 ms |
| 2 | Payment Service | Payment processing | 180 ms |
| 3 | Database | Database query | 2,000 ms |
| 4 | Order Service | Request failed; timeout returned to caller | — |

A trace helps us identify where a request spent its time and where it failed.

In short:

| Telemetry type | Main question |
| --- | --- |
| Logs | What happened? |
| Metrics | How much or how often? |
| Traces | Where did the request go? |

All three are useful when investigating incidents.

## 3. What is OpenTelemetry?

[OpenTelemetry](https://opentelemetry.io/) (OTel) is an open-source observability framework that helps applications generate, collect, and export telemetry. It provides a common approach for instrumenting services written in different languages.

For example, an organization might run:

- Order Service in Python
- Payment Service in Java
- Notification Service in Node.js
- Inventory Service in Python

OpenTelemetry instrumentation allows these services to produce telemetry in a standardized way.

### Instrumentation and the Collector

**Instrumentation** adds the capability to an application to generate telemetry. For example, FastAPI instrumentation can automatically capture incoming HTTP requests, request durations, status codes, exceptions, and trace information. Applications can also add custom instrumentation.

The **OpenTelemetry Collector** is a separate process that receives and routes telemetry. Its main components are:

| Component | Responsibility |
| --- | --- |
| Receiver | Receives telemetry |
| Processor | Processes or transforms telemetry |
| Exporter | Sends telemetry to a destination |

For example, a receiver can accept telemetry from the Payment Service, a processor can filter, batch, or enrich it, and an exporter can send it to Kafka or another observability backend.

Applications can send telemetry to the Collector without knowing where it will eventually be stored. The Collector handles routing according to its configuration.

## 4. What are Prometheus and Grafana?

Prometheus and Grafana are often used together, but they have different responsibilities.

### Prometheus

[Prometheus](https://prometheus.io/) is a monitoring and time-series database system. Its primary job is to collect and store numerical metrics over time.

| Time | CPU usage |
| --- | ---: |
| 10:00 | 40% |
| 10:01 | 45% |
| 10:02 | 65% |
| 10:03 | 85% |
| 10:04 | 95% |

Prometheus provides a query language called **PromQL**. For example:

```promql
rate(http_requests_total[5m])
```

This calculates the per-second rate of HTTP requests over the last five minutes.

To calculate the rate of HTTP 500 responses:

```promql
rate(http_requests_total{status="500"}[5m])
```

Prometheus commonly collects metrics using **scraping**. A service might expose a metrics endpoint such as `/payment-service/metrics`:

```text
http_requests_total 1200
http_errors_total 45
cpu_usage 85
```

Prometheus periodically calls the endpoint and collects the metrics. This is called **pull-based monitoring**: Prometheus pulls metrics from targets instead of waiting for each application to push them.

### Grafana

[Grafana](https://grafana.com/) is a visualization and dashboard platform. It connects to data sources such as Prometheus and displays their data through graphs, charts, tables, gauges, and dashboards.

In NexusOps, Grafana can display:

- CPU usage over time
- Memory utilization
- API latency
- Requests per second
- Error rates

The simplest distinction is:

- **Prometheus** collects and stores metrics.
- **Grafana** queries and visualizes data from Prometheus.

Grafana is not the database storing those metrics.

## 5. What is Kafka?

[Apache Kafka](https://kafka.apache.org/) is a distributed event-streaming platform. It allows one application to publish events and another application to consume them without communicating directly.

| Term | Meaning |
| --- | --- |
| Producer | Sends events |
| Topic | Category in which events are stored |
| Broker | Kafka server that stores events |
| Consumer | Reads and processes events |

### Example in NexusOps

Suppose the Payment Service generates this error:

```json
{
  "service": "payment-service",
  "event_type": "database_error",
  "severity": "critical",
  "message": "Database connection timeout",
  "timestamp": "2026-11-16T10:30:00Z"
}
```

The event can be sent to a Kafka topic named `telemetry.events`. The Telemetry Worker subscribes to that topic and processes the event.

The Payment Service does not need to know what the Telemetry Worker will do with the event. It publishes the event, and the worker consumes it independently. This is called **decoupling**.

## 6. How the tools work together

Prometheus and Kafka are **not the same pipeline**. They serve different purposes, and the connections between components must be explicitly configured.

### Flow 1: Monitoring and visualization

```text
Payment Service metrics
    -> OpenTelemetry Collector (if configured for this route)
    -> Prometheus
    -> Grafana dashboards
```

Prometheus stores time-series metrics, and Grafana visualizes them.

### Flow 2: Event processing and incident detection

```text
Application telemetry
    -> OpenTelemetry instrumentation and Collector
    -> Kafka: telemetry.events
    -> Telemetry Worker
    -> NexusOps Incident Management
```

The Collector can route different telemetry signals to different destinations through exporters. For example:

- Metrics can be made available to Prometheus.
- Logs and traces can be exported to Kafka.
- Grafana can visualize Prometheus metrics.

These routes do not happen automatically; they require configuration.

## 7. What happens inside the Telemetry Worker?

The `telemetry-worker` is a NexusOps application that consumes telemetry events from Kafka and decides whether something requires attention.

### Step 1: The Payment Service starts failing

The service begins generating errors:

```text
ERROR: Database connection timeout
ERROR: Payment processing failed
ERROR: Database connection timeout
```

OpenTelemetry instrumentation captures relevant telemetry, and the configured pipeline exports it.

### Step 2: Kafka receives events

The Collector sends normalized events to the `telemetry.events` topic. Kafka stores the events until consumers process them.

If 10,000 events arrive in a short period, Kafka can buffer them so that the backend does not have to process everything immediately.

### Step 3: The Telemetry Worker consumes events

The worker subscribes to the Kafka topic and processes incoming events. Conceptually:

```python
for event in kafka_consumer:
    process_event(event)
```

Processing might include:

- Validating the event
- Checking whether it is a duplicate
- Identifying the associated service
- Updating relevant metrics or health information
- Evaluating monitoring rules

### Step 4: Redis helps with deduplication and caching

Kafka may deliver the same event more than once. An **idempotency key** can identify events that have already been processed so the same operation is not repeated.

Redis can help store these keys and frequently accessed service-health information, for example:

```text
payment-service = UNHEALTHY
order-service = DEGRADED
notification-service = HEALTHY
```

Caching this information can make dashboard reads faster.

### Step 5: Monitoring thresholds are evaluated

For example, NexusOps might configure a rule such as:

```text
IF error_rate > 5%
DURING 60 seconds

THEN create incident
```

The worker evaluates relevant telemetry against configured rules. If a condition is satisfied, it creates an incident.

### Step 6: An incident is created

The worker saves the incident in PostgreSQL. For example:

```json
{
  "incident_id": "INC-1042",
  "service": "payment-service",
  "severity": "critical",
  "status": "open",
  "description": "Payment service error rate exceeded threshold"
}
```

It can also publish an `incident.created` event to another Kafka topic.

### Step 7: Other components react

Different components can react independently:

- FastAPI sends real-time updates to the frontend.
- The AI Worker starts investigating the incident.
- The notification system sends alerts.
- PostgreSQL maintains the incident record.

This is the benefit of an event-driven architecture: components can react to events without being tightly coupled to one another.

## 8. Dead Letter Queues and idempotency

### Idempotency

Suppose the same event arrives three times. Without idempotency, the system might create three incidents. With idempotency, it recognizes that the event has already been processed and avoids repeating the operation.

### Dead Letter Queue (DLQ)

Suppose Kafka delivers a malformed event that the worker cannot process. Repeatedly retrying that event could prevent progress.

After a configured number of retries, the event can be sent to a Dead Letter Queue, for example `telemetry.dlq`. An engineer can inspect it later, diagnose the issue, and decide whether it can be corrected and replayed.

## 9. Storage responsibilities

The original blueprint mentions storing logs and metrics in PostgreSQL. PostgreSQL is useful for structured application data, but storing every raw metric there duplicates work better handled by a time-series system.

A clearer division of responsibilities is:

| Storage system | Responsibility |
| --- | --- |
| Prometheus | Time-series metrics |
| PostgreSQL | Services, incidents, configurations, and investigation reports |
| Redis | Cache, idempotency keys, and Pub/Sub |
| S3 | Archived logs and investigation artifacts |
| pgvector | Embeddings and semantic retrieval |
| Kafka | Durable event stream and replayable events |

For traces, plan for a dedicated trace backend or an archival strategy such as S3. There is generally no need to build a trace storage system from scratch.

## 10. Knowledge check

### 1. What is the primary purpose of OpenTelemetry?

- Store application data
- **Generate, collect, and export telemetry**
- Visualize dashboards

OpenTelemetry provides instrumentation and collection pipelines for logs, metrics, and traces.

### 2. Which tool stores time-series metrics?

- Grafana
- Kafka
- **Prometheus**

Prometheus collects and stores numerical metrics over time.

### 3. What is Grafana responsible for?

- **Visualizing monitoring data**
- Processing Kafka events
- Creating database records

Grafana queries data sources such as Prometheus and displays dashboards.

### 4. Why use Kafka?

- Replace PostgreSQL
- **Buffer and distribute events between independent components**
- Generate application logs

Kafka decouples event producers and consumers and supports durable event processing.

### 5. Who consumes `telemetry.events` in NexusOps?

- Grafana
- **Telemetry Worker**
- React frontend

The Telemetry Worker consumes events, evaluates monitoring rules, and creates incidents.

## Key takeaway

Keep this event-processing flow in mind:

```text
Application -> OpenTelemetry -> Kafka -> Telemetry Worker -> Incident
```

Once this flow is clear, the rest of the NexusOps architecture becomes easier to understand.
