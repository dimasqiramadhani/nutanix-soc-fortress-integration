# Nutanix SOC Sandbox Architecture

## End to End Data Flow

The following diagram illustrates the journey of data from the log generator through to visualization in Grafana.

```mermaid
flowchart TD
    subgraph SRC["Log Source"]
        GEN["Sample Log Generator<br/>(replaces Nutanix CVM/PCVM)<br/>produces sandbox_nutanix_logs.csv"]
    end

    GEN -->|"feed_logs.py<br/>syslog TCP :5141"| GL

    subgraph GL["Graylog"]
        IN["Syslog TCP Input 5141"]
        STR["Stream<br/>Nutanix Network Logs"]
        subgraph PCP["Pipeline: Prism Central Parser"]
            PCP0["Stage 0<br/>Parse api_audit, flow, JSON<br/>Flag API Error"]
            PCP1["Stage 1<br/>Flag External, Flag Critical"]
        end
        subgraph OSP["Pipeline: OS Audit Parser"]
            OSP0["Stage 0<br/>Drop Broken"]
            OSP1["Stage 1<br/>Extract CVM Fields"]
        end
        IN --> STR
        STR --> PCP0 --> PCP1
        STR --> OSP0 --> OSP1
    end

    PCP1 -->|"index nutanix_network_*"| OS
    OSP1 -->|"index nutanix_network_*"| OS

    subgraph STORE["Storage"]
        OS["OpenSearch<br/>(Wazuh Indexer in a real environment)"]
    end

    OS -->|"OpenSearch datasource, PPL enabled"| GRF

    subgraph VIZ["Visualization"]
        GRF["Grafana<br/>Nutanix Network Logs Monitoring Dashboard<br/>Panels: timeline, user activity, top endpoints,<br/>external vs ui, http methods, api errors"]
    end
```

## Design Decisions

### Why Graylog Is Placed in the Middle Instead of Feeding Directly to Wazuh Manager

The primary use case is access visibility, namely answering the question of who logs in to or accesses Nutanix, rather than per event MITRE correlation. Graylog handles the ingest, normalization, and filtering process, then writes the results to OpenSearch. Grafana then reads directly from OpenSearch for visualization. This flow is lighter than forcing all data through Wazuh Manager.

### Why Two Separate Pipelines Are Used

The **Prism Central Parser** pipeline handles `api_audit`, `flow_service`, and `consolidated_audit` (JSON). The **OS Audit Parser** pipeline handles `audispd`, namely the CVM internal auditd whose log structure is entirely different because it uses keys such as `type=`, `acct=`, and `exe=`. This separation keeps the rules clean and easy to maintain.

Both pipelines connect to the same stream, namely `Nutanix Network Logs`, and run in parallel.

### Why Fields Do Not Use `.keyword`

Fields created through `set_field()` in the pipeline are stored as plain text in OpenSearch. There is no automatic mapping to a keyword subfield. Therefore, the grouping rules in Grafana are as follows.

The correct configuration uses Group By Terms on the `nutanix_client_type` field. Conversely, the incorrect configuration uses `nutanix_client_type.keyword` which is unavailable and therefore causes aggregation to fail or to produce unexpected output.

This is a common cause of pie or bar panels in Grafana appearing empty or showing only a single full slice.

## Replicated Log Formats

### api_audit (key-value)

```
<HOST> api_audit: INFO  <ts>Z clientType=External||userName=admin||
NutanixApiVersion=1.0||httpMethod=GET||restEndpoint=/v1/...||
entityUuid=||queryParams=||payload=
```

### cvm_audit (audispd)

```
<HOST> audispd[PID]: node=<node> type=USER_AUTH msg=audit(...): ...
acct="nutanix" exe="/usr/bin/su" ... res=success
```

### flow_service

```
<HOST> flow_service_logs-acropolis: <ts>Z INFO vm_idf_entity.py:NNN
PublishLearnedIp: VM <uuid> updated in IDF
```

### consolidated_audit (JSON)

```
<HOST> consolidated_audit: {"affectedEntityList":[{"entityType":"vm",
"name":"SANDBOX-VM-01","uuid":"..."}],"defaultMsg":"VM deleted",
"operationType":"Delete","recordType":"Audit","severity":"Audit",
"userName":"budi.santoso@sandbox.local"}
```
