# Referensi Field Nutanix SOC Sandbox

Berikut adalah daftar field yang dihasilkan oleh pipeline. Seluruh field bertipe **teks biasa** di OpenSearch dan tidak memiliki subfield `.keyword`.

## Field dari api_audit

| Field | Contoh | Dihasilkan oleh |
|-------|--------|-----------------|
| `nutanix_log_type` | `api_audit` | Parse API Audit |
| `nutanix_client_type` | `External` atau `ui` | Parse API Audit |
| `nutanix_user` | `admin`, `andi.pratama`, atau `<uuid>` | Parse API Audit |
| `nutanix_http_method` | `GET` atau `POST` | Parse API Audit |
| `nutanix_api_version` | `1.0`, `2.0`, atau `0.8` | Parse API Audit |
| `nutanix_endpoint` | `/v1/users/details` | Parse API Audit |
| `nutanix_entity_uuid` | `<uuid>` atau kosong | Parse API Audit |

## Field Penanda Keamanan

| Field | Nilai | Dihasilkan oleh | Arti |
|-------|-------|-----------------|------|
| `nutanix_external_access` | `true` | Flag External Access | akses berasal dari clientType External |
| `nutanix_critical_operation` | `true` | Flag Critical Operations | method POST, PUT, atau DELETE |
| `nutanix_api_error` | `true` | Flag API Error Response | responseCode selain 200 |
| `nutanix_response_code` | `401`, `403`, `404`, atau `500` | Flag API Error Response | kode kesalahan API |
| `nutanix_alert_type` | `external_api_access`, `critical_operation`, atau `api_error` | berbagai aturan penanda | jenis alert |

## Field dari flow_service

| Field | Contoh | Dihasilkan oleh |
|-------|--------|-----------------|
| `nutanix_log_type` | `flow_service` | Parse Flow Service Logs |
| `nutanix_flow_level` | `INFO` | Parse Flow Service Logs |
| `nutanix_flow_message` | teks peristiwa IDF | Parse Flow Service Logs |

## Field dari consolidated_audit (JSON)

| Field | Contoh | Dihasilkan oleh |
|-------|--------|-----------------|
| `nutanix_log_type` | `audit` | Parse Audit JSON |
| `nutanix_user` | `andi.pratama@sandbox.local` | Parse Audit JSON |
| `nutanix_operation` | `Login`, `Create`, atau `Delete` | Parse Audit JSON |
| `nutanix_record_type` | `Audit` | Parse Audit JSON |
| `nutanix_severity` | `Audit` | Parse Audit JSON |
| `nutanix_message` | `VM deleted` | Parse Audit JSON |
| `nutanix_entity` | `SANDBOX-VM-01` | Parse Audit JSON |
| `nutanix_entity_type` | `vm` atau `cluster` | Parse Audit JSON |

## Field dari cvm_audit (OS Internal)

| Field | Contoh | Dihasilkan oleh |
|-------|--------|-----------------|
| `nutanix_log_type` | `cvm_audit` | CVM Extract Fields |
| `ntnx_node` | `ntnx-sandbox0000001-a-cvm` | CVM Extract Fields |
| `ntnx_type` | `USER_AUTH` atau `USER_CMD` | CVM Extract Fields |
| `ntnx_acct` | `nutanix` | CVM Extract Fields |
| `ntnx_exe` | `/usr/bin/su` | CVM Extract Fields |
| `ntnx_result` | `success` | CVM Extract Fields |

## Kueri Graylog yang Bermanfaat

```
nutanix_user:*                       # seluruh akses yang berlabel pengguna
nutanix_client_type:External         # akses melalui API eksternal
nutanix_client_type:ui               # login melalui antarmuka web
nutanix_api_error:true               # panggilan API yang gagal
nutanix_critical_operation:true      # operasi tulis (POST, PUT, atau DELETE)
nutanix_endpoint:"/v1/users/details" # akses menuju endpoint tertentu
nutanix_log_type:flow_service        # peristiwa flow atau microsegmentation
nutanix_log_type:audit               # consolidated_audit (login, logout, perubahan)
nutanix_operation:Delete             # operasi delete dari audit JSON
```
