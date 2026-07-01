# Field Reference — Nutanix SOC Sandbox

Daftar field yang dihasilkan pipeline. Semua field bertipe **text biasa** di OpenSearch (tidak ada sub-field `.keyword`).

## Field dari api_audit

| Field | Contoh | Dihasilkan oleh |
|-------|--------|-----------------|
| `nutanix_log_type` | `api_audit` | Parse API Audit |
| `nutanix_client_type` | `External` / `ui` | Parse API Audit |
| `nutanix_user` | `admin`, `andi.pratama`, `<uuid>` | Parse API Audit |
| `nutanix_http_method` | `GET`, `POST` | Parse API Audit |
| `nutanix_api_version` | `1.0`, `2.0`, `0.8` | Parse API Audit |
| `nutanix_endpoint` | `/v1/users/details` | Parse API Audit |
| `nutanix_entity_uuid` | `<uuid>` atau kosong | Parse API Audit |

## Field flag (security)

| Field | Nilai | Dihasilkan oleh | Arti |
|-------|-------|-----------------|------|
| `nutanix_external_access` | `true` | Flag External Access | akses dari clientType External |
| `nutanix_critical_operation` | `true` | Flag Critical Operations | method POST/PUT/DELETE |
| `nutanix_api_error` | `true` | Flag API Error Response | responseCode != 200 |
| `nutanix_response_code` | `401`,`403`,`404`,`500` | Flag API Error Response | kode error API |
| `nutanix_alert_type` | `external_api_access` / `critical_operation` / `api_error` | berbagai flag rule | jenis alert |

## Field dari flow_service

| Field | Contoh | Dihasilkan oleh |
|-------|--------|-----------------|
| `nutanix_log_type` | `flow_service` | Parse Flow Service Logs |
| `nutanix_flow_level` | `INFO` | Parse Flow Service Logs |
| `nutanix_flow_message` | teks event IDF | Parse Flow Service Logs |

## Field dari cvm_audit (OS internal)

| Field | Contoh | Dihasilkan oleh |
|-------|--------|-----------------|
| `nutanix_log_type` | `cvm_audit` | CVM Extract Fields |
| `ntnx_node` | `ntnx-sandbox0000001-a-cvm` | CVM Extract Fields |
| `ntnx_type` | `USER_AUTH`, `USER_CMD` | CVM Extract Fields |
| `ntnx_acct` | `nutanix` | CVM Extract Fields |
| `ntnx_exe` | `/usr/bin/su` | CVM Extract Fields |
| `ntnx_result` | `success` | CVM Extract Fields |

## Query Graylog berguna

```
nutanix_user:*                       # semua akses bersandboxel user
nutanix_client_type:External         # akses via API eksternal
nutanix_client_type:ui               # login via web UI
nutanix_api_error:true               # API call gagal
nutanix_critical_operation:true      # operasi write (POST/PUT/DELETE)
nutanix_endpoint:"/v1/users/details" # akses ke endpoint tertentu
nutanix_log_type:flow_service        # event flow/microsegmentation
```
