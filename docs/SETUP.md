# Setup Guide — Nutanix SOC Sandbox

Dua jalur: **cek cepat offline** atau **full stack Docker**.

---

## Jalur 1 — Offline (paling cepat)

Hanya butuh Python 3.

```bash
cd scripts
python3 simulate_pipeline.py --file ../sample-data/sandbox_nutanix_logs.csv
```

Ini menerapkan logika semua rule ke sample data dan menampilkan ringkasan. Cocok untuk memahami output pipeline tanpa menjalankan apa pun.

---

## Jalur 2 — Full Stack (Docker)

### Prasyarat
- Docker & Docker Compose
- RAM minimal ~4 GB
- Port bebas: 9000 (Graylog), 3000 (Grafana), 9200 (OpenSearch), 5141 (syslog)

### 1. Naikkan stack
```bash
docker compose up -d
docker compose ps        # pastikan semua "running"/"healthy"
```
Tunggu ~1–2 menit sampai Graylog siap di http://localhost:9000 (admin / admin).

### 2. Buat Input Syslog TCP
Graylog UI → **System → Inputs** → pilih **Syslog TCP** → Launch new input.
Isi sesuai `graylog/inputs/nutanix-syslog-tcp-input.json`:
- Bind: `0.0.0.0`, Port: `5141`
- Store full message: on
- Static fields: `syslog_type=network`, `syslog_customer=sandbox`

### 3. Buat Stream
**Streams → Create Stream**: `Nutanix - Network Logs`.
Tambahkan rule stream: `syslog_type` = `network`. Aktifkan **Remove matches from Default Stream**. Start stream.

### 4. Import Rules
**System → Pipelines → Manage rules → Create Rule** (Use Source Code Editor).
Copy-paste isi tiap file berikut, satu per satu:
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

### 5. Buat Pipelines
**Manage pipelines → Add new pipeline**:

**Nutanix - Prism Central Parser** — sesuai `graylog/pipelines/nutanix-prism-central-parser.pipeline`:
- Stage 0 (match either): Parse API Audit, Parse Flow Service Logs, Parse Audit JSON, Flag API Error Response
- Stage 1 (match either): Flag External Access, Flag Critical Operations

**Nutanix - OS Audit Parser** — sesuai `graylog/pipelines/nutanix-os-audit-parser.pipeline`:
- Stage 0: CVM Drop Broken
- Stage 1: CVM Extract Fields

Connect **kedua pipeline** ke stream `Nutanix - Network Logs`.
Pastikan **Message Processor "Pipeline Processor"** aktif (System → Configurations).

### 6. Feed log
```bash
cd scripts
python3 feed_logs.py --host localhost --port 5141 \
    --file ../sample-data/sandbox_nutanix_logs.csv --rate 30
# stream live: tambahkan --loop
```

### 7. Verifikasi di Graylog
Search (Last 1 hour):
```
nutanix_user:*
nutanix_client_type:External
nutanix_api_error:true
```

### 8. Grafana
http://localhost:3000 (admin / admin). Datasource **NUTANIX** dan dashboard **Nutanix - Network Logs Monitoring** sudah ter-provision otomatis via folder `grafana/`.

Jika dashboard tidak muncul, import manual: **Dashboards → New → Import** → upload `grafana/dashboards/nutanix-monitoring-dashboard.json`.

---

## Troubleshooting

| Gejala | Kemungkinan sebab | Solusi |
|--------|-------------------|--------|
| Log masuk sebagai `o` | RELP mismatch (di dunia nyata) | pastikan pengirim pakai plain syslog TCP, bukan RELP |
| Field `nutanix_*` tidak muncul | pipeline belum connect ke stream / processor mati | cek koneksi pipeline & Message Processors |
| Pie/bar chart Grafana kosong | pakai `.keyword` | ganti ke field tanpa `.keyword` |
| OpenSearch tak mau start | memlock / RAM | pastikan ulimit memlock & RAM cukup |
