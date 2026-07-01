#!/usr/bin/env python3
"""
Nutanix SOC Sandbox - Offline Pipeline Simulator
============================================
Menerapkan LOGIKA pipeline rule (versi Python) ke sample CSV, lalu
menampilkan ringkasan field hasil parsing + statistik - TANPA perlu
Graylog/OpenSearch. Berguna untuk cepat memverifikasi bahwa rule
menghasilkan field yang benar (mirror dari rule .grok).

Usage:
  python3 simulate_pipeline.py --file ../sample-data/sandbox_nutanix_logs.csv
"""

import argparse
import csv
import re
from collections import Counter


def parse_api_audit(msg, out):
    if "api_audit:" not in msg:
        return False
    def g(pat):
        m = re.search(pat, msg)
        return m.group(1) if m else ""
    out["nutanix_client_type"] = g(r"clientType=([^|]+)\|\|")
    out["nutanix_user"] = g(r"userName=([^|]+)\|\|")
    out["nutanix_http_method"] = g(r"httpMethod=([^|]+)\|\|")
    out["nutanix_api_version"] = g(r"NutanixApiVersion=([^|]+)\|\|")
    out["nutanix_endpoint"] = g(r"restEndpoint=([^|]*)\|\|")
    out["nutanix_entity_uuid"] = g(r"entityUuid=([^|]*)\|\|")
    out["nutanix_log_type"] = "api_audit"
    return True


def parse_flow(msg, out):
    if "flow_service_logs" not in msg:
        return False
    out["nutanix_log_type"] = "flow_service"
    m = re.search(r"Z\s+([A-Z]+)\s+", msg)
    out["nutanix_flow_level"] = m.group(1) if m else ""
    return True


def parse_cvm(msg, out):
    if "audispd" not in msg:
        return False
    def g(pat):
        m = re.search(pat, msg)
        return m.group(1) if m else ""
    out["nutanix_log_type"] = "cvm_audit"
    out["ntnx_node"] = g(r"node=([^ ]+)")
    out["ntnx_type"] = g(r"type=([^ ]+)")
    out["ntnx_acct"] = g(r'acct="([^"]+)"')
    out["ntnx_exe"] = g(r'exe="([^"]+)"')
    out["ntnx_result"] = g(r"res=([^ ']+)")
    return True


def flag_api_error(msg, out):
    if "responseCode=" in msg and "responseCode=200" not in msg:
        m = re.search(r"responseCode=([0-9]+)", msg)
        out["nutanix_response_code"] = m.group(1) if m else ""
        out["nutanix_api_error"] = "true"
        out["nutanix_alert_type"] = "api_error"


def flag_external(out):
    if out.get("nutanix_client_type") == "External":
        out["nutanix_external_access"] = "true"
        out.setdefault("nutanix_alert_type", "external_api_access")


def flag_critical(out):
    if out.get("nutanix_http_method") in ("DELETE", "PUT", "POST"):
        out["nutanix_critical_operation"] = "true"
        out.setdefault("nutanix_alert_type", "critical_operation")


def process(msg):
    out = {}
    if not (parse_api_audit(msg, out) or parse_flow(msg, out) or parse_cvm(msg, out)):
        out["nutanix_log_type"] = "unparsed"
    flag_api_error(msg, out)
    flag_external(out)
    flag_critical(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="../sample-data/sandbox_nutanix_logs.csv")
    ap.add_argument("--show", type=int, default=3, help="berapa contoh per tipe")
    args = ap.parse_args()

    log_types = Counter()
    users = Counter()
    client_types = Counter()
    methods = Counter()
    endpoints = Counter()
    alerts = Counter()
    examples = {}

    with open(args.file) as f:
        reader = csv.reader(f, delimiter=";")
        next(reader, None)
        for r in reader:
            if len(r) < 3:
                continue
            msg = r[2]
            parsed = process(msg)
            lt = parsed.get("nutanix_log_type", "unparsed")
            log_types[lt] += 1
            if parsed.get("nutanix_user"):
                users[parsed["nutanix_user"]] += 1
            if parsed.get("nutanix_client_type"):
                client_types[parsed["nutanix_client_type"]] += 1
            if parsed.get("nutanix_http_method"):
                methods[parsed["nutanix_http_method"]] += 1
            if parsed.get("nutanix_endpoint"):
                endpoints[parsed["nutanix_endpoint"]] += 1
            if parsed.get("nutanix_alert_type"):
                alerts[parsed["nutanix_alert_type"]] += 1
            examples.setdefault(lt, []).append(parsed)

    def section(title):
        print("\n" + "=" * 60)
        print(title)
        print("=" * 60)

    section("LOG TYPES")
    for k, v in log_types.most_common():
        print(f"  {k:15} : {v}")

    section("CLIENT TYPES (External vs UI)")
    for k, v in client_types.most_common():
        print(f"  {k:15} : {v}")

    section("TOP USERS (siapa akses Nutanix)")
    for k, v in users.most_common(10):
        print(f"  {k:45} : {v}")

    section("HTTP METHODS")
    for k, v in methods.most_common():
        print(f"  {k:8} : {v}")

    section("TOP ENDPOINTS")
    for k, v in endpoints.most_common(10):
        print(f"  {k:55} : {v}")

    section("ALERT TYPES (hasil flag rules)")
    for k, v in alerts.most_common():
        print(f"  {k:25} : {v}")

    section(f"CONTOH FIELD PER TIPE (maks {args.show})")
    for lt, items in examples.items():
        print(f"\n--- {lt} ---")
        for ex in items[:args.show]:
            for key in sorted(ex):
                print(f"    {key} = {ex[key]}")
            print("    " + "-" * 30)


if __name__ == "__main__":
    main()
