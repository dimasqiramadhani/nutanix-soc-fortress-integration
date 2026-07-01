# Aturan Deteksi Nutanix SOC Sandbox

Dokumen ini memetakan setiap aturan pipeline terhadap kasus penggunaan keamanan yang ditanganinya.

## Ringkasan Pipeline

| Pipeline | Stage | Aturan | Fungsi |
|----------|-------|--------|--------|
| Prism Central Parser | 0 | Parse API Audit | mengekstrak field dari api_audit (key-value) |
| Prism Central Parser | 0 | Parse Flow Service Logs | menandai dan mengekstrak peristiwa flow atau IDF |
| Prism Central Parser | 0 | Parse Audit JSON | mengekstrak field dari consolidated_audit (JSON) |
| Prism Central Parser | 0 | Flag API Error Response | menandai responseCode selain 200 |
| Prism Central Parser | 1 | Flag External Access | menandai akses berclientType External |
| Prism Central Parser | 1 | Flag Critical Operations | menandai operasi tulis (POST/PUT/DELETE atau Create/Update/Delete) |
| OS Audit Parser | 0 | CVM Drop Broken | membuang pesan rusak berupa huruf "o" akibat ketidaksesuaian RELP |
| OS Audit Parser | 1 | CVM Extract Fields | mengekstrak field auditd internal CVM |

## Kasus Penggunaan per Aturan

### Parse API Audit

Aturan ini menjawab pertanyaan mengenai siapa yang mengakses Nutanix, melalui apa, dan menuju sumber daya mana. Aturan menghasilkan field `nutanix_user`, `nutanix_client_type`, `nutanix_http_method`, `nutanix_endpoint`, dan `nutanix_entity_uuid`. Field tersebut menjadi fondasi visibilitas akses.

### Flag External Access

Aturan ini menjawab pertanyaan mengenai akses mana yang berasal dari luar dan bukan dari antarmuka internal. Aturan menandai `nutanix_external_access` bernilai true untuk clientType External. Penandaan ini bermanfaat untuk memisahkan lalu lintas layanan atau API dari login manusia melalui antarmuka.

### Flag Critical Operations

Aturan ini menjawab pertanyaan mengenai ada tidaknya operasi yang mengubah data, bukan sekadar membaca. Method GET tergolong operasi baca yang aman. Adapun POST, PUT, DELETE, maupun operationType Create, Update, dan Delete tergolong perubahan sehingga ditandai dengan `nutanix_critical_operation` bernilai true. Operasi semacam ini berprioritas tinggi untuk ditinjau.

### Flag API Error Response

Aturan ini menjawab pertanyaan mengenai ada tidaknya percobaan akses yang gagal atau ditolak. responseCode selain 200 akan menghasilkan `nutanix_api_error` bernilai true beserta `nutanix_response_code`. Sebagai contoh, kode 401 atau 403 yang menandakan unauthorized atau forbidden dapat mengindikasikan aktivitas pemindaian atau kredensial yang bermasalah.

### Parse Audit JSON

Aturan ini menjawab pertanyaan mengenai peristiwa login, logout, dan perubahan entity dari audit terstruktur. Aturan mengurai `consolidated_audit` (JSON) menjadi `nutanix_operation`, `nutanix_entity`, dan `nutanix_message`. Pada banyak penerapan, format ini lebih jarang muncul dibandingkan api_audit sehingga aturan dapat menganggur, dan kondisi tersebut wajar.

### CVM Drop Broken dan CVM Extract Fields

Kedua aturan ini menjawab pertanyaan mengenai aktivitas OS internal CVM seperti su, sudo, maupun autentikasi. Aturan membuang artefak berupa huruf "o" akibat ketidaksesuaian RELP, kemudian mengekstrak `ntnx_type`, `ntnx_acct`, `ntnx_exe`, dan `ntnx_result`. Tujuannya adalah memantau penggunaan privilese pada tingkat OS CVM yang berbeda dari akses API Prism Central.

## Gagasan Alerting untuk Pengembangan Lanjutan

Bagian ini belum diimplementasikan dan disediakan sebagai bahan pengembangan.

| Alert | Kondisi Graylog | Alasan |
|-------|-----------------|--------|
| Lonjakan akses API eksternal | `nutanix_external_access:true` melampaui ambang tertentu | mendeteksi penyalahgunaan atau scraping API |
| Lonjakan akses gagal | `nutanix_api_error:true` (401 atau 403) berulang | mendeteksi upaya brute force atau pemindaian |
| Operasi kritis oleh pengguna non-admin | `nutanix_critical_operation:true` dan bukan admin | mendeteksi perubahan yang tidak diharapkan |
| Login antarmuka oleh pengguna baru | `nutanix_client_type:ui` dengan pengguna di luar daftar dikenal | mendeteksi akun baru atau tidak dikenal |

Implementasi alert dapat dilakukan melalui Graylog Alerts and Events beserta Notification, misalnya webhook menuju SOAR atau Shuffle, maupun melalui Grafana Alerting pada datasource NUTANIX.
