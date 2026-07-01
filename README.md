# Nutanix SOC Sandbox — Prism Central → Graylog → OpenSearch → Grafana

Sandbox environment untuk mempelajari & mendemonstrasikan integrasi log **Nutanix Prism Central** ke stack SIEM (Graylog + OpenSearch + Grafana), lengkap dengan pipeline parsing, detection rules, dan dashboard.

> **Catatan penting:** Seluruh data, hostname, username, UUID, dan IP di sandbox ini **fiktif** dan dibuat untuk keperluan belajar. Tidak ada data produksi/nyata. Kredensial yang tercantum hanya untuk sandbox lokal — jangan dipakai di lingkungan nyata.

---

## Apa yang disimulasikan

Alur end-to-end yang direplikasi:

```
[Sample Log Generator]                (pengganti CVM/PCVM Nutanix asli)
        │  syslog TCP 5141
        ▼
    Graylog  ── Stream "Nutanix - Network Logs"
        │       └── Pipeline "Nutanix - Prism Central Parser"
        │       └── Pipeline "Nutanix - OS Audit Parser"
        ▼
    OpenSearch (index: nutanix_network_*)
        ▼
     Grafana  ── Dashboard "Nutanix - Network Logs Monitoring"
```

Tipe log yang di-cover (meniru format asli Prism Central):

| Tipe | Contoh | Rule terkait |
|------|--------|-------------|
| `api_audit` | siapa akses API/UI, endpoint, method | Parse API Audit, Flag External, Flag Critical, Flag API Error |
| `cvm_audit` | auditd/audispd internal CVM (su/sudo) | CVM Extract Fields, Drop Broken |
| `flow_service` | microsegmentation / IDF events | Parse Flow Service Logs |

---

## Struktur folder

```
nutanix-soc-sandbox/
├── docker-compose.yml            # stack lengkap (Graylog+OpenSearch+Grafana+Mongo)
├── README.md
├── docs/
│   ├── ARCHITECTURE.md           # penjelasan arsitektur & alur data
│   ├── SETUP.md                  # langkah setup detail
│   └── FIELD-REFERENCE.md        # daftar field hasil parsing
├── graylog/
│   ├── inputs/                   # config input Syslog TCP 5141
│   ├── rules/                    # 8 pipeline rule (.grok)
│   └── pipelines/                # 2 definisi pipeline
├── grafana/
│   ├── datasources/              # provisioning datasource NUTANIX (OpenSearch)
│   └── dashboards/               # dashboard JSON (Terms+Count, tanpa .keyword)
├── sample-data/
│   └── sandbox_nutanix_logs.csv      # 2500 baris log sintetis
└── scripts/
    ├── generate_sample_logs.py   # generator data sandbox
    ├── feed_logs.py              # kirim CSV -> Graylog syslog TCP
    └── simulate_pipeline.py      # cek hasil parsing offline (tanpa Docker)
```

---

## Cara pakai — 2 opsi

### Opsi A — Cepat, tanpa Docker (cek logika parsing)

Cukup Python 3. Tidak perlu Graylog/OpenSearch.

```bash
cd scripts
python3 simulate_pipeline.py --file ../sample-data/sandbox_nutanix_logs.csv
```

Output: ringkasan log types, top users, client types, endpoints, dan alert types — hasil dari menerapkan logika rule ke sample data. Berguna untuk memahami apa yang dihasilkan tiap rule.

Regenerate data (jumlah/seed berbeda):

```bash
python3 generate_sample_logs.py --count 5000 --seed 7 --out ../sample-data/sandbox_nutanix_logs.csv
```

### Opsi B — Full stack (Docker)

Butuh Docker + Docker Compose, RAM ~4GB.

```bash
# 1. Naikkan stack
docker compose up -d

# 2. Tunggu Graylog siap (~1-2 menit), buka http://localhost:9000  (admin/admin)

# 3. Di Graylog UI, import manual:
#    - Input     : lihat graylog/inputs/nutanix-syslog-tcp-input.json
#    - Rules     : copy-paste tiap file di graylog/rules/*.grok
#    - Pipelines : buat 2 pipeline sesuai graylog/pipelines/*.pipeline
#      lalu connect ke stream "Nutanix - Network Logs"

# 4. Feed log sandbox ke Graylog
cd scripts
python3 feed_logs.py --host localhost --port 5141 \
    --file ../sample-data/sandbox_nutanix_logs.csv --rate 30

# 5. Buka Grafana http://localhost:3000 (admin/admin)
#    Datasource NUTANIX & dashboard sudah otomatis ter-provision.
```

Untuk simulasi stream live (log mengalir terus), tambahkan `--loop`:

```bash
python3 feed_logs.py --loop --rate 20
```

---

## Pelajaran penting dari sandbox ini

1. **Field text TIDAK punya sub-field `.keyword`.** Field hasil `set_field()` di Graylog pipeline masuk ke OpenSearch sebagai text biasa. Di Grafana, Group By harus pakai `nutanix_client_type` — **bukan** `nutanix_client_type.keyword` (yang tidak ada dan bikin agregasi gagal).

2. **Grafana panel breakdown** = metric `Count` + bucket aggregation `Terms` pada field kategori. Lihat `grafana/dashboards/nutanix-monitoring-dashboard.json` untuk konfigurasi yang benar.

3. **`api_audit` (key-value) dominan**, bukan `consolidated_audit` (JSON). Rule Parse Audit JSON disertakan tapi biasanya idle — normal.

4. **Critical operation jarang** (GET dominan). Sedikit POST/PUT/DELETE itu wajar untuk environment stabil, bukan bug.

Lihat `docs/` untuk detail lebih lanjut.
