# Nutanix SOC Sandbox Setup Guide

Two setup paths are available, namely a quick offline check and a full stack using Docker.

## Quick Validation Before Starting

```bash
python3 scripts/validate.py
```

This command ensures that all JSON and YAML files are valid, that rules and pipelines are consistent, and that the regex matches the sample data. An exit code of zero indicates that the project is ready to use.

## Path 1: Offline (Fastest)

This path requires only Python 3.

```bash
cd scripts
python3 simulate_pipeline.py --file ../sample-data/sandbox_nutanix_logs.csv
```

This command applies the logic of all rules to the sample data and displays a summary. This path is suitable for understanding the pipeline output without running any components.

## Path 2: Full Stack (Docker)

### Prerequisites

This path requires Docker with Docker Compose, a minimum of approximately 4 GB of RAM, and the availability of port 9000 for Graylog, 3000 for Grafana, 9200 for OpenSearch, and 5141 for syslog.

### 1. Start the Stack

```bash
docker compose up -d
docker compose ps        # ensure all services are running or healthy
```

Wait approximately 1 to 2 minutes until Graylog is ready at http://localhost:9000 with the credentials admin and admin.

### 2. Create the Syslog TCP Input

In the Graylog interface, open System, then Inputs, then select Syslog TCP, then Launch new input. Fill it according to `graylog/inputs/nutanix-syslog-tcp-input.json` with Bind 0.0.0.0, Port 5141, the Store full message option enabled, and the static fields `syslog_type=network` and `syslog_customer=sandbox`.

### 3. Create the Stream

Open Streams, then Create Stream, with the name Nutanix Network Logs. Add the stream rule `syslog_type` with the value `network`. Enable the Remove matches from Default Stream option, then start the stream.

### 4. Import Rules and Pipelines

**Quick option (Content Pack):** open System, then Content Packs, then Upload, then select `graylog/content-pack/nutanix-soc-content-pack.json`, then Install. All 8 rules and 2 pipelines are installed immediately. Continue to step 5 to connect to the stream and skip the manual steps below.

**Manual option to import rules:** open System, then Pipelines, then Manage rules, then Create Rule with Use Source Code Editor. Copy and paste the contents of each file below one at a time.

```
graylog/rules/01-parse-api-audit.grok
graylog/rules/02-parse-flow-service-logs.grok
graylog/rules/03-flag-api-error-response.grok
graylog/rules/04-flag-external-access.grok
graylog/rules/05-flag-critical-operations.grok
graylog/rules/06-parse-audit-json.grok
graylog/rules/07-cvm-drop-broken.grok
graylog/rules/08-cvm-extract-fields.grok
```

### 5. Create the Pipelines

Open Manage pipelines, then Add new pipeline.

The **Nutanix Prism Central Parser** pipeline according to `graylog/pipelines/nutanix-prism-central-parser.pipeline` has Stage 0 with match either containing Parse API Audit, Parse Flow Service Logs, Parse Audit JSON, and Flag API Error Response, and Stage 1 with match either containing Flag External Access and Flag Critical Operations.

The **Nutanix OS Audit Parser** pipeline according to `graylog/pipelines/nutanix-os-audit-parser.pipeline` has Stage 0 containing CVM Drop Broken and Stage 1 containing CVM Extract Fields.

Connect **both pipelines** to the Nutanix Network Logs stream. Ensure that the Message Processor named Pipeline Processor is enabled through System, then Configurations.

### 6. Send the Logs

```bash
cd scripts
python3 feed_logs.py --host localhost --port 5141 \
    --file ../sample-data/sandbox_nutanix_logs.csv --rate 30
# for a live stream, add --loop
```

### 7. Verify in Graylog

Perform a search with a time range of the last one hour using the following queries.

```
nutanix_user:*
nutanix_client_type:External
nutanix_api_error:true
```

### 8. Grafana

Open http://localhost:3000 with the credentials admin and admin. The NUTANIX datasource and the Nutanix Network Logs Monitoring dashboard are provisioned automatically through the `grafana/` folder.

If the dashboard does not appear, import it manually through Dashboards, then New, then Import, then upload `grafana/dashboards/nutanix-monitoring-dashboard.json`.

## Troubleshooting

| Symptom | Possible Cause | Solution |
|---------|----------------|----------|
| Logs arrive as the letter "o" | RELP mismatch in a real environment | ensure the sender uses plain syslog TCP and not RELP |
| The `nutanix_*` fields do not appear | the pipeline is not connected to the stream or the processor is not enabled | check the pipeline connection and Message Processors |
| The pie or bar panels in Grafana are empty | using `.keyword` | replace with the field without `.keyword` |
| OpenSearch fails to start | memlock or RAM limitations | ensure the memlock ulimit and RAM are sufficient |
