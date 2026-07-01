# Panduan Pemasangan Nutanix SOC Sandbox

Tersedia dua jalur pemasangan, yaitu pemeriksaan cepat secara luring dan tumpukan penuh menggunakan Docker.

## Validasi Cepat Sebelum Memulai

```bash
python3 scripts/validate.py
```

Perintah tersebut memastikan seluruh berkas JSON dan YAML valid, aturan dan pipeline konsisten, serta regex cocok dengan data contoh. Kode keluaran nol menandakan proyek siap digunakan.

## Jalur 1: Luring (Paling Cepat)

Jalur ini hanya membutuhkan Python 3.

```bash
cd scripts
python3 simulate_pipeline.py --file ../sample-data/sandbox_nutanix_logs.csv
```

Perintah tersebut menerapkan logika seluruh aturan terhadap data contoh dan menampilkan ringkasannya. Jalur ini cocok untuk memahami keluaran pipeline tanpa menjalankan komponen apa pun.

## Jalur 2: Tumpukan Penuh (Docker)

### Prasyarat

Jalur ini membutuhkan Docker beserta Docker Compose, RAM minimal sekitar 4 GB, serta ketersediaan port 9000 untuk Graylog, 3000 untuk Grafana, 9200 untuk OpenSearch, dan 5141 untuk syslog.

### 1. Menjalankan Tumpukan

```bash
docker compose up -d
docker compose ps        # memastikan seluruh layanan running atau healthy
```

Tunggu sekitar 1 hingga 2 menit sampai Graylog siap pada http://localhost:9000 dengan kredensial admin dan admin.

### 2. Membuat Input Syslog TCP

Pada antarmuka Graylog, buka System, lalu Inputs, lalu pilih Syslog TCP, kemudian Launch new input. Isi sesuai `graylog/inputs/nutanix-syslog-tcp-input.json` dengan Bind 0.0.0.0, Port 5141, opsi Store full message aktif, serta static field `syslog_type=network` dan `syslog_customer=sandbox`.

### 3. Membuat Stream

Buka Streams, lalu Create Stream, dengan nama Nutanix Network Logs. Tambahkan aturan stream `syslog_type` bernilai `network`. Aktifkan opsi Remove matches from Default Stream, kemudian jalankan stream.

### 4. Mengimpor Aturan dan Pipeline

**Opsi cepat (Content Pack):** buka System, lalu Content Packs, lalu Upload, kemudian pilih `graylog/content-pack/nutanix-soc-content-pack.json`, lalu Install. Seluruh 8 aturan dan 2 pipeline langsung terpasang. Lanjutkan ke langkah 5 untuk menghubungkan ke stream dan lewati langkah manual di bawah.

**Opsi manual untuk mengimpor aturan:** buka System, lalu Pipelines, lalu Manage rules, lalu Create Rule dengan Use Source Code Editor. Salin dan tempel isi tiap berkas berikut satu per satu.

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

### 5. Membuat Pipeline

Buka Manage pipelines, lalu Add new pipeline.

Pipeline **Nutanix Prism Central Parser** sesuai `graylog/pipelines/nutanix-prism-central-parser.pipeline` memiliki Stage 0 dengan match either yang berisi Parse API Audit, Parse Flow Service Logs, Parse Audit JSON, dan Flag API Error Response, serta Stage 1 dengan match either yang berisi Flag External Access dan Flag Critical Operations.

Pipeline **Nutanix OS Audit Parser** sesuai `graylog/pipelines/nutanix-os-audit-parser.pipeline` memiliki Stage 0 berisi CVM Drop Broken dan Stage 1 berisi CVM Extract Fields.

Hubungkan **kedua pipeline** ke stream Nutanix Network Logs. Pastikan Message Processor bernama Pipeline Processor telah aktif melalui System, lalu Configurations.

### 6. Mengirim Log

```bash
cd scripts
python3 feed_logs.py --host localhost --port 5141 \
    --file ../sample-data/sandbox_nutanix_logs.csv --rate 30
# untuk aliran langsung, tambahkan --loop
```

### 7. Verifikasi pada Graylog

Lakukan pencarian dengan rentang waktu satu jam terakhir menggunakan kueri berikut.

```
nutanix_user:*
nutanix_client_type:External
nutanix_api_error:true
```

### 8. Grafana

Buka http://localhost:3000 dengan kredensial admin dan admin. Datasource NUTANIX beserta dashboard Nutanix Network Logs Monitoring telah ter-provisioning secara otomatis melalui folder `grafana/`.

Apabila dashboard belum muncul, lakukan impor manual melalui Dashboards, lalu New, lalu Import, kemudian unggah `grafana/dashboards/nutanix-monitoring-dashboard.json`.

## Penanganan Masalah

| Gejala | Kemungkinan Penyebab | Solusi |
|--------|----------------------|--------|
| Log masuk sebagai huruf "o" | ketidaksesuaian RELP pada lingkungan nyata | pastikan pengirim menggunakan plain syslog TCP dan bukan RELP |
| Field `nutanix_*` tidak muncul | pipeline belum terhubung ke stream atau processor tidak aktif | periksa koneksi pipeline dan Message Processors |
| Panel pie atau bar pada Grafana kosong | menggunakan `.keyword` | ganti dengan field tanpa `.keyword` |
| OpenSearch gagal dijalankan | keterbatasan memlock atau RAM | pastikan ulimit memlock dan RAM mencukupi |
