# Nutanix SOC Sandbox Detection Rules

This document maps each pipeline rule to the security use case it addresses.

## Pipeline Summary

| Pipeline | Stage | Rule | Function |
|----------|-------|------|----------|
| Prism Central Parser | 0 | Parse API Audit | extracts fields from api_audit (key-value) |
| Prism Central Parser | 0 | Parse Flow Service Logs | flags and extracts flow or IDF events |
| Prism Central Parser | 0 | Parse Audit JSON | extracts fields from consolidated_audit (JSON) |
| Prism Central Parser | 0 | Flag API Error Response | flags responseCode other than 200 |
| Prism Central Parser | 1 | Flag External Access | flags access with clientType External |
| Prism Central Parser | 1 | Flag Critical Operations | flags write operations (POST/PUT/DELETE or Create/Update/Delete) |
| OS Audit Parser | 0 | CVM Drop Broken | discards broken messages of the letter "o" caused by RELP mismatch |
| OS Audit Parser | 1 | CVM Extract Fields | extracts CVM internal auditd fields |

## Use Cases Per Rule

### Parse API Audit

This rule answers the question of who accesses Nutanix, through what, and toward which resource. The rule produces the fields `nutanix_user`, `nutanix_client_type`, `nutanix_http_method`, `nutanix_endpoint`, and `nutanix_entity_uuid`. These fields form the foundation of access visibility.

### Flag External Access

This rule answers the question of which access originates from outside rather than from the internal interface. The rule flags `nutanix_external_access` as true for clientType External. This flagging helps separate service or API traffic from human logins through the interface.

### Flag Critical Operations

This rule answers the question of whether an operation modifies data rather than merely reading it. The GET method is a safe read operation. Meanwhile POST, PUT, DELETE, as well as the operationType values Create, Update, and Delete are considered changes and are therefore flagged with `nutanix_critical_operation` as true. Such operations are high priority for review.

### Flag API Error Response

This rule answers the question of whether there is a failed or denied access attempt. A responseCode other than 200 produces `nutanix_api_error` as true along with `nutanix_response_code`. For example, codes 401 or 403 that indicate unauthorized or forbidden may signal scanning activity or problematic credentials.

### Parse Audit JSON

This rule answers the question of login, logout, and entity change events from the structured audit. The rule parses `consolidated_audit` (JSON) into `nutanix_operation`, `nutanix_entity`, and `nutanix_message`. In many deployments this format appears less frequently than api_audit, so the rule may remain idle, and that condition is normal.

### CVM Drop Broken and CVM Extract Fields

These two rules answer the question of CVM internal OS activity such as su, sudo, and authentication. The rules discard the artifact of the letter "o" caused by RELP mismatch, then extract `ntnx_type`, `ntnx_acct`, `ntnx_exe`, and `ntnx_result`. The goal is to monitor privilege usage at the CVM OS level, which differs from Prism Central API access.

## Alerting Ideas for Further Development

This section is not yet implemented and is provided as development material.

| Alert | Graylog Condition | Rationale |
|-------|-------------------|-----------|
| External API access spike | `nutanix_external_access:true` exceeds a certain threshold | detects API abuse or scraping |
| Failed access spike | `nutanix_api_error:true` (401 or 403) repeated | detects brute force or scanning attempts |
| Critical operation by a non admin user | `nutanix_critical_operation:true` and not admin | detects unexpected changes |
| Interface login by a new user | `nutanix_client_type:ui` with a user outside the known list | detects new or unknown accounts |

Alert implementation can be done through Graylog Alerts and Events together with Notification, for example a webhook to SOAR or Shuffle, or through Grafana Alerting on the NUTANIX datasource.
