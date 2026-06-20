# Lab 5 - Accelerated AI: Event-driven cybersecurity pipeline

**Course:** Introduction to AI for Cybersecurity (HIT)
**Student:** Stav Hefetz
**Lab spec:** [course repo / lab5 Accelerated AI](https://github.com/melofon/HIT-ai-cybersecurity-labs/tree/main/labs/lab5%20Accelerated%20AI)

The course README puts it like this: *"In cybersecurity, pipelines matter more than models."* That's the framing for this whole lab.

## 1. What this lab is about

This is the only lab in the course that is architectural rather than ML-focused. The point is to build a small but realistic SOC analytics pipeline so the *shape* of real SOC platforms (Splunk, Sentinel, Chronicle, Panther) becomes obvious. They are all built on message queues plus distributed tracing rather than monolithic scripts, and once you've wired one up by hand you understand why.

The pipeline:

```
                ┌─────────────────────┐
                │  Producer notebook  │  simulates Windows process
                │ windows-log-producer│  + login telemetry
                └──────────┬──────────┘
                           │ JSON event
                           ▼
                  ┌─────────────────┐
                  │   Apache Kafka  │  topic: raw-events
                  │  (KRaft mode)   │  (no Zookeeper)
                  └────────┬────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
    ┌──────────────────────┐  ┌────────────────────┐
    │ Consumer / Classifier│  │ Redpanda Console   │
    │ + MITRE ATT&CK rules │  │  (Kafka inspect UI)│
    │  -> classified.csv   │  └────────────────────┘
    └──────────┬───────────┘
               │ OTLP spans
               ▼
       ┌───────────────┐
       │   Jaeger UI   │  end-to-end traces
       └───────────────┘

               (offline)
               ▼
    ┌──────────────────────┐
    │  Statistics notebook │  pandas + matplotlib
    │  reads CSV → charts  │
    └──────────────────────┘
```

The trick worth pointing out is how trace IDs are wired. The producer derives the OpenTelemetry `trace_id` directly from the event UUID, so the consumer can rebuild the parent span context from the event ID alone, without the producer having to inject trace headers into the Kafka message body. Jaeger then shows the producer span and the consumer span as a single trace per event, which is what makes the "what data flows" vs "how the pipeline executes" split work cleanly.

## 2. Files

```
Lab5-Accelerated-AI/
├── README.md
├── compose.yml                  Kafka KRaft + Redpanda Console + Jaeger + Jupyter
└── notebooks/
    └── 1. Mittre classification/
        ├── 1. Producer.ipynb            emits events to Kafka topic raw-events
        ├── 2. Consumer_Classifier.ipynb consumes, classifies, writes CSV, emits traces
        ├── 3. Statistics.ipynb          offline analysis of classified_packets.csv
        └── classified_packets.csv       a sample run, so notebook 3 is plottable as-is
```

## 3. How to run

You need Docker Desktop (or Docker Engine + Compose v2), about 4 GB of free RAM (Kafka and Jaeger are not light), and ports 8080, 8888, 9092, 16686, 29092, 4317, and 4318 free.

Bring the stack up:

```bash
cd Labs/Lab5-Accelerated-AI
docker compose up -d
```

Kafka takes about 20 seconds to elect itself controller in KRaft mode. After that:

| Service          | URL                                |
|------------------|------------------------------------|
| JupyterLab       | http://localhost:8888 (no token)   |
| Redpanda Console | http://localhost:8080              |
| Jaeger UI        | http://localhost:16686             |

The Kafka broker is also reachable from the host on `localhost:29092` if you want to attach a CLI client (`kcat`, `kafka-console-consumer`) from outside the compose network.

To actually run the pipeline:

1. Open `1. Producer.ipynb`, run all cells. The last cell is an infinite loop emitting events every 1 to 5 seconds. Leave it running.
2. In a separate Jupyter tab open `2. Consumer_Classifier.ipynb` and run all cells. The consume loop is also infinite. You'll see lines like `Processed <uuid> → TA0002 / T1059.001`.
3. Let both run for 2 to 5 minutes so the CSV grows enough to be interesting.
4. Interrupt both (Kernel → Interrupt) and open `3. Statistics.ipynb`. Run all cells. You'll get a stacked bar chart of MITRE tactics over time.

Tear down with `docker compose down -v`.

## 4. What you can see in each UI

In Redpanda Console (port 8080), the topic `raw-events` appears as soon as the producer publishes its first message. Click into the topic, then the Messages tab, and you'll see the JSON payloads streaming live. That's the "what data flows" view.

In Jaeger (port 16686), pick `windows-log-producer` or `packet-classifier` from the service dropdown and hit Find Traces. Each event becomes one trace. Open one and you see a tree of spans:

* `produce_event` (PRODUCER kind)
  * `kafka_produce`
* `consume_event` (CONSUMER kind) - sharing the same trace_id because of the UUID-to-trace-id mapping
  * `classify_event`
  * `write_csv`

That tree is the "how the pipeline executes" view. Same event, two completely different lenses on it.

## 5. Conceptual questions the course README asks

### a) Why does Kafka replace a direct function call?

A direct call like `classify(event)` couples the producer and the classifier in three ways at once: in code, in time, and in capacity. If the classifier crashes, the producer crashes. If the classifier is slow, the producer blocks. If you want a second consumer (say an LLM-based deep classifier alongside the rule-based one) you have to refactor the producer to fan out to both.

Kafka decouples all three. The producer only knows the topic name. Events are persisted, so the classifier can be down for an hour and still catch up. Kafka absorbs bursts, so the classifier sees a smoothed stream instead of a spike.

This matters in cyber specifically because attacks come in bursts. Port scans, brute-force, lateral movement waves - they all generate event spikes, and dropping events during a spike is exactly what you cannot afford if you're trying to detect the burst itself.

### b) Where would bottlenecks appear?

In this lab the bottleneck is the classifier, because the producer is artificially slowed down with a 1 to 5 second sleep. If you remove that sleep, the producer can flood Kafka faster than the classifier reads. You'd see two symptoms:

* Consumer group lag on `raw-events` grows, visible in Redpanda Console under Consumer Groups.
* The `write_csv` span in Jaeger becomes the slowest span in the trace, because `csv_file.flush()` is synchronous on every event.

The real fixes look like: replace the CSV sink with a batched DB writer, or stop flushing on every event and flush every N events instead; partition the Kafka topic and run more classifier replicas in the same consumer group (Kafka auto-balances partitions across consumers); or move the classifier to a real worker pool (Faust, Ray, Spark Structured Streaming).

### c) Why is distributed tracing useful here?

Without Jaeger the producer and the classifier are two black boxes that both happen to log to stdout. With Jaeger you see the lifetime of each event end-to-end: when the producer emitted it, how long it sat in Kafka before the classifier picked it up, how long classification took, how long the CSV write took. You also see where time actually goes - `classify_event` is microseconds, but `kafka_produce` and `write_csv` are not, and that's only obvious from the trace.

In a real SOC this is the difference between "we have a brute-force alert at 03:14" and "we have a brute-force alert at 03:14 and here are the 47 failed logins from 185.243.115.84 that produced it, with timestamps to the millisecond." The second one is useful for IR. The first one is just an alert.

### d) Where would you scale independently?

This is the whole point of the architecture. Each stage scales on its own axis:

* Producer scales with the number of monitored hosts (one producer per agent).
* Kafka scales with partitions and brokers. Partitions set the max parallelism downstream.
* The classifier scales with attack volume. Multiple classifier pods in the same consumer group, Kafka load-balances partitions across them.
* The analytics sink scales with retention and query load. It doesn't affect detection latency at all because it's reading persisted data.

You can scale any of these independently of the others, which you cannot do when everything is one Python process.

### e) How does this differ from a real SOC?

Things this lab deliberately doesn't do that a real SOC would:

* **Schema management** - no schema registry, no Avro/Protobuf. A typo in a field name would silently break downstream parsing here, which is unacceptable in production.
* **Auth** - Kafka runs PLAINTEXT, Jupyter has a dev token. Real systems use mTLS and SASL/SCRAM with per-topic ACLs.
* **Persistence** - a CSV is fine for a lab. Real SOCs write to OpenSearch, ClickHouse, or a proper SIEM index.
* **Dedup and ordering** - if the consumer crashes after `write_csv` but before committing the Kafka offset, the next consumer will reprocess that event and double-write it. Real systems use idempotent producers, exactly-once semantics, or downstream `event_id` dedup.
* **Detection logic** - the rule set here is 4 lines. A real SOC has Sigma rules, YARA rules, ML detectors, and correlation across multiple events.
* **Alerting and response** - we only classify. There's no fan-out to PagerDuty, no SOAR playbook, no IR pager. A real pipeline has another stage past the classifier that does that.

The architecture is right. The contents are kept deliberately small so the lab fits in a Friday afternoon.

## 6. A note on the name "Accelerated AI"

The folder is named *Accelerated AI* but the README is explicit that no GPU is required for this lab. The naming refers to the *next* labs that will layer on top of this one (the course README mentions GPU-accelerated classifiers and advanced monitoring as future extensions). What this lab teaches is the substrate a GPU classifier would plug into - Kafka in, Kafka out, traced end-to-end - not the GPU bit itself.

## 7. How this connects to my final project

My final project (`Project/` - SOC-Copilot) is essentially the smart-classifier slot in this pipeline filled out properly. Instead of the 4-line rule function in the consumer notebook, it has an Isolation Forest anomaly detector, a deterministic MITRE ATT&CK mapper with the full technique catalogue, and an AG2 LLM agent that explains each alert in plain English.

If I were to merge the two, the consumer cell in this lab would import `Project.src.detector` and `Project.src.mitre_mapper` instead of calling `classify_event`. The Kafka topic, the trace structure, and the CSV sink would not change. That's the architecture working as intended.
