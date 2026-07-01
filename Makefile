# Nutanix SOC Sandbox: Makefile
# Shortcut commands for common operations.

.PHONY: help validate generate simulate feed up down clean

help:
	@echo "Nutanix SOC Sandbox: available commands"
	@echo "  make validate   run the validity and consistency self test"
	@echo "  make generate   regenerate the sample data (2500 lines)"
	@echo "  make simulate   display the parsing results offline without Docker"
	@echo "  make feed       send sample logs to Graylog at localhost:5141"
	@echo "  make up         start the Docker stack"
	@echo "  make down       stop the Docker stack"
	@echo "  make clean      remove the Python cache"

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
