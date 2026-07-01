# Nutanix SOC Sandbox : Makefile
# Perintah singkat untuk operasi umum.

.PHONY: help validate generate simulate feed up down clean

help:
	@echo "Nutanix SOC Sandbox : perintah yang tersedia"
	@echo "  make validate   menjalankan uji mandiri validitas dan konsistensi"
	@echo "  make generate   membangkitkan ulang data contoh (2500 baris)"
	@echo "  make simulate   menampilkan hasil parsing secara luring tanpa Docker"
	@echo "  make feed       mengirim log contoh ke Graylog pada localhost:5141"
	@echo "  make up         menjalankan tumpukan Docker"
	@echo "  make down       menghentikan tumpukan Docker"
	@echo "  make clean      menghapus cache Python"

validate:
	python3 scripts/validate.py

generate:
	cd scripts && python3 generate_sample_logs.py --count 2500 --out ../sample-data/sandbox_nutanix_logs.csv

simulate:
	cd scripts && python3 simulate_pipeline.py --file ../sample-data/sandbox_nutanix_logs.csv

feed:
	cd scripts && python3 feed_logs.py --host localhost --port 5141 --file ../sample-data/sandbox_nutanix_logs.csv --rate 30

up:
	docker compose up -d

down:
	docker compose down

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
