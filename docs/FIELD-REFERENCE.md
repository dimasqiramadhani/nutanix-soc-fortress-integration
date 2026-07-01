# Nutanix SOC Sandbox Field Reference

The following is a list of fields produced by the pipeline. All fields are of the **plain text** type in OpenSearch and do not have a `.keyword` subfield.

## Fields From api_audit

| Field | Example | Produced By |
|-------|---------|-------------|
| `nutanix_log_type` | `api_audit` | Parse API Audit |
| `nutanix_client_type` | `External` or `ui` | Parse API Audit |
| `nutanix_user` | `admin`, `andi.pratama`, or `<uuid>` | Parse API Audit |
| `nutanix_http_method` | `GET` or `POST` | Parse API Audit |
| `nutanix_api_version` | `1.0`, `2.0`, or `0.8` | Parse API Audit |
| `nutanix_endpoint` | `/v1/users/details` | Parse API Audit |
| `nutanix_entity_uuid` | `<uuid>` or empty | Parse API Audit |

## Security Flag Fields

| Field | Value | Produced By | Meaning |
|-------|-------|-------------|---------|
| `nutanix_external_access` | `true` | Flag External Access | access originates from clientType External |
| `nutanix_critical_operation` | `true` | Flag Critical Operations | POST, PUT, or DELETE method |
| `nutanix_api_error` | `true` | Flag API Error Response | responseCode other than 200 |
| `nutanix_response_code` | `401`, `403`, `404`, or `500` | Flag API Error Response | API error code |
| `nutanix_alert_type` | `external_api_access`, `critical_operation`, or `api_error` | various flag rules | alert type |

## Fields From flow_service

| Field | Example | Produced By |
|-------|---------|-------------|
| `nutanix_log_type` | `flow_service` | Parse Flow Service Logs |
| `nutanix_flow_level` | `INFO` | Parse Flow Service Logs |
| `nutanix_flow_message` | IDF event text | Parse Flow Service Logs |

## Fields From consolidated_audit (JSON)

| Field | Example | Produced By |
|-------|---------|-------------|
| `nutanix_log_type` | `audit` | Parse Audit JSON |
| `nutanix_user` | `andi.pratama@sandbox.local` | Parse Audit JSON |
| `nutanix_operation` | `Login`, `Create`, or `Delete` | Parse Audit JSON |
| `nutanix_record_type` | `Audit` | Parse Audit JSON |
| `nutanix_severity` | `Audit` | Parse Audit JSON |
| `nutanix_message` | `VM deleted` | Parse Audit JSON |
| `nutanix_entity` | `SANDBOX-VM-01` | Parse Audit JSON |
| `nutanix_entity_type` | `vm` or `cluster` | Parse Audit JSON |

## Fields From cvm_audit (OS Internal)

| Field | Example | Produced By |
|-------|---------|-------------|
| `nutanix_log_type` | `cvm_audit` | CVM Extract Fields |
| `ntnx_node` | `ntnx-sandbox0000001-a-cvm` | CVM Extract Fields |
| `ntnx_type` | `USER_AUTH` or `USER_CMD` | CVM Extract Fields |
| `ntnx_acct` | `nutanix` | CVM Extract Fields |
| `ntnx_exe` | `/usr/bin/su` | CVM Extract Fields |
| `ntnx_result` | `success` | CVM Extract Fields |

## Useful Graylog Queries

```
nutanix_user:*                       # all access labeled with a user
nutanix_client_type:External         # access through the external API
nutanix_client_type:ui               # login through the web interface
nutanix_api_error:true               # failed API calls
nutanix_critical_operation:true      # write operations (POST, PUT, or DELETE)
nutanix_endpoint:"/v1/users/details" # access to a specific endpoint
nutanix_log_type:flow_service        # flow or microsegmentation events
nutanix_log_type:audit               # consolidated_audit (login, logout, changes)
nutanix_operation:Delete             # delete operations from the JSON audit
```
