# Arsitektur — Nutanix SOC Sandbox

## Alur data end-to-end

```
┌────────────────────────┐
│  Sample Log Generator  │  generate_sample_logs.py
│  (pengganti CVM/PCVM)  │  → sandbox_nutanix_logs.csv
└───────────┬────────────┘
            │  feed_logs.py  (syslog TCP :5141)
            ▼
┌────────────────────────┐
│        GRAYLOG         │
│  Input: Syslog TCP 5141│
│  Stream: Nutanix -     │
│          Network Logs  │
│  ┌──────────────────┐  │
│  │ Pipeline: Prism  │  │  Stage 0: parse (api_audit / flow / json)
│  │ Central Parser   │  │           + flag api error
│  │                  │  │  Stage 1: flag external / critical
│  ├──────────────────┤  │
│  │ Pipeline: OS     │  │  Stage 0: drop broken
│  │ Audit Parser     │  │  Stage 1: extract cvm fields
│  └──────────────────┘  │
└───────────┬────────────┘
            │  index: nutanix_network_*
            ▼
┌────────────────────────┐
│      OPENSEARCH        │  penyimpanan + agregasi
│  (Wazuh Indexer di     │
│   lingkungan asli)     │
└───────────┬────────────┘
            │  datasource OpenSearch (PPL enabled)
            ▼
┌────────────────────────┐
│        GRAFANA         │  Dashboard: Nutanix - Network Logs Monitoring
│  Panels: timeline,     │
│  user activity, top    │
│  endpoints, external   │
│  vs ui, http methods,  │
│  api errors            │
└────────────────────────┘
```

## Keputusan desain

### Kenapa Graylog di tengah (bukan langsung ke Wazuh Manager)?
Use case-nya adalah **visibilitas akses** ("siapa login/akses ke Nutanix"), bukan korelasi MITRE per-event. Graylog menangani ingest, normalisasi, dan filtering, lalu menulis ke OpenSearch. Grafana membaca langsung dari OpenSearch untuk visualisasi. Alur ini lebih ringan daripada memaksa semua lewat Wazuh Manager.

### Kenapa dua pipeline terpisah?
- **Prism Central Parser** menangani `api_audit`, `flow_service`, dan `consolidated_audit` (JSON).
- **OS Audit Parser** menangani `audispd` (auditd internal CVM) — struktur log-nya beda total (key `type=`, `acct=`, `exe=`), jadi dipisah agar rule tetap rapi.

Keduanya terhubung ke stream yang sama (`Nutanix - Network Logs`) dan berjalan paralel.

### Kenapa field tanpa `.keyword`?
Field yang dibuat via `set_field()` di pipeline masuk sebagai text biasa di OpenSearch. Tidak ada mapping otomatis ke sub-field `keyword`. Karena itu:
- **Benar:** Group By Terms → `nutanix_client_type`
- **Salah:** Group By Terms → `nutanix_client_type.keyword` (tidak ada → agregasi gagal / hasil aneh)

Ini penyebab umum pie/bar chart "kosong" atau "1 slice 100% time" di Grafana.

## Format log yang direplikasi

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
