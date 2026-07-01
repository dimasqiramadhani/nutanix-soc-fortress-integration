#!/usr/bin/env python3
"""
Nutanix SOC Sandbox : Validasi dan Uji Mandiri
==============================================
Skrip ini memeriksa konsistensi dan validitas seluruh komponen proyek, yaitu:
  sintaks JSON dan YAML
  konsistensi antara aturan dan referensi pipeline
  kecocokan regex .grok dengan format data contoh
  kesesuaian field yang dihasilkan simulator dengan yang dijanjikan dokumentasi
  keterbacaan JSON pada consolidated_audit

Kode keluaran 0 berarti seluruh pemeriksaan lolos, sedangkan 1 berarti ada
pemeriksaan yang gagal.

Contoh penggunaan:
  python3 validate.py           # dijalankan dari folder scripts
  python3 scripts/validate.py   # dijalankan dari akar proyek
"""

import json
import os
import re
import sys
import csv

# ---- Lokasi root project (naik satu level kalau dijalankan dari scripts/) ----
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE if os.path.basename(HERE) != "scripts" else os.path.dirname(HERE)

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    mark = "OK  " if cond else "FAIL"
    if cond:
        PASS += 1
    else:
        FAIL += 1
    line = f"  [{mark}] {name}"
    if detail and not cond:
        line += f"  -> {detail}"
    print(line)


def p(*parts):
    return os.path.join(ROOT, *parts)


def section(t):
    print("\n" + "=" * 58 + f"\n{t}\n" + "=" * 58)


# ---------------------------------------------------------------------------
section("1. Validitas JSON")
for jf in [
    "grafana/dashboards/nutanix-monitoring-dashboard.json",
    "graylog/inputs/nutanix-syslog-tcp-input.json",
    "graylog/content-pack/nutanix-soc-content-pack.json",
]:
    try:
        json.load(open(p(jf)))
        check(jf, True)
    except Exception as e:
        check(jf, False, str(e))

# ---------------------------------------------------------------------------
section("2. Validitas YAML")
try:
    import yaml
    for yf in ["docker-compose.yml", "grafana/datasources/nutanix-datasource.yaml"]:
        try:
            yaml.safe_load(open(p(yf)))
            check(yf, True)
        except Exception as e:
            check(yf, False, str(e))
except ImportError:
    print("  [SKIP] pyyaml tidak terinstall (opsional)")

# ---------------------------------------------------------------------------
section("3. Konsistensi rule <-> pipeline")
rule_titles = set()
for rf in os.listdir(p("graylog/rules")):
    src = open(p("graylog/rules", rf)).read()
    m = re.search(r'rule\s+"([^"]+)"', src)
    if m:
        rule_titles.add(m.group(1))

referenced = set()
for pf in os.listdir(p("graylog/pipelines")):
    src = open(p("graylog/pipelines", pf)).read()
    for m in re.finditer(r'rule\s+"([^"]+)"', src):
        referenced.add(m.group(1))

check("Semua rule yang direferensikan pipeline punya definisi",
      referenced.issubset(rule_titles),
      f"missing: {referenced - rule_titles}")
check("Tidak ada rule yatim (didefinisikan tapi tak dipakai)",
      rule_titles == referenced,
      f"unused: {rule_titles - referenced}")

# ---------------------------------------------------------------------------
section("4. Datasource uid cocok dengan referensi dashboard")
ds_uid = None
for line in open(p("grafana/datasources/nutanix-datasource.yaml")):
    m = re.search(r"uid:\s*(\S+)", line)
    if m:
        ds_uid = m.group(1)
        break
dash = json.load(open(p("grafana/dashboards/nutanix-monitoring-dashboard.json")))
dash_uids = set()
def walk(o):
    if isinstance(o, dict):
        if o.get("type") == "grafana-opensearch-datasource" and "uid" in o:
            dash_uids.add(o["uid"])
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)
walk(dash)
check(f"datasource uid '{ds_uid}' direferensikan dashboard",
      ds_uid in dash_uids, f"dashboard refer: {dash_uids}")

# ---------------------------------------------------------------------------
section("5. Regex .grok match sample data")
csv_path = p("sample-data/sandbox_nutanix_logs.csv")
samples = {"api": None, "flow": None, "cvm": None, "consolidated": None, "error": None}
with open(csv_path) as f:
    rd = csv.reader(f, delimiter=";")
    next(rd)
    for row in rd:
        if len(row) < 3:
            continue
        msg = row[2]
        if "api_audit:" in msg:
            if samples["api"] is None:
                samples["api"] = msg
            if "responseCode=" in msg and "responseCode=200" not in msg and samples["error"] is None:
                samples["error"] = msg
        elif "flow_service_logs" in msg and samples["flow"] is None:
            samples["flow"] = msg
        elif "audispd" in msg and samples["cvm"] is None:
            samples["cvm"] = msg
        elif "consolidated_audit:" in msg and samples["consolidated"] is None:
            samples["consolidated"] = msg

# api_audit regexes
if samples["api"]:
    for field, pat in {
        "clientType": r".*clientType=([^|]+)\|\|.*",
        "userName": r".*userName=([^|]+)\|\|.*",
        "httpMethod": r".*httpMethod=([^|]+)\|\|.*",
        "restEndpoint": r".*restEndpoint=([^|]*)\|\|.*",
    }.items():
        check(f"api_audit regex {field}", re.match(pat, samples["api"]) is not None)
else:
    check("ada sample api_audit", False)

# error regex
if samples["error"]:
    check("responseCode regex", re.search(r".*responseCode=([0-9]+).*", samples["error"]) is not None)
else:
    check("ada sample error (responseCode!=200)", False, "tidak ada di data (jarang - regenerate lebih banyak)")

# flow
if samples["flow"]:
    check("flow_service level regex", re.search(r".*Z\s+([A-Z]+)\s+.*", samples["flow"]) is not None)
else:
    check("ada sample flow_service", False)

# cvm
if samples["cvm"]:
    check("cvm audit type regex", re.search(r".*type=([^ ]+).*", samples["cvm"]) is not None)
else:
    check("ada sample cvm_audit", False)

# consolidated
if samples["consolidated"]:
    m = re.search(r"consolidated_audit:\s*(\{.*\})", samples["consolidated"])
    ok = False
    if m:
        try:
            json.loads(m.group(1))
            ok = True
        except Exception:
            ok = False
    check("consolidated_audit JSON parseable", ok)
else:
    check("ada sample consolidated_audit", False, "generator belum bikin - cek weights")

# ---------------------------------------------------------------------------
section("6. Tidak ada sisa kata 'lab'")
leftover = []
SELF = os.path.abspath(__file__)
for dirpath, _, files in os.walk(ROOT):
    if "__pycache__" in dirpath:
        continue
    for fn in files:
        fp = os.path.join(dirpath, fn)
        if os.path.abspath(fp) == SELF:
            continue  # skip validator sendiri (mengandung kata 'lab' di pesan cek)
        try:
            txt = open(fp, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        # cari 'lab' sebagai substring, kecuali dalam kata umum yang sah
        for m in re.finditer(r"lab", txt, re.IGNORECASE):
            ctx = txt[max(0, m.start()-6):m.start()+6].lower()
            # kata sah yang mengandung "lab": sandbox, global, available,
            # syllabus, label/berlabel, kolaborasi, elaborasi, laboratorium
            if any(w in ctx for w in ["sandbox", "global", "availab", "syllab",
                                       "label", "kolab", "elab", "laborat"]):
                continue
            snippet = txt[max(0, m.start()-12):m.start()+12].replace("\n", " ")
            leftover.append(f"{os.path.relpath(fp, ROOT)}: ...{snippet}...")
            break
check("tidak ada sisa kata 'lab'", len(leftover) == 0,
      "; ".join(leftover[:3]))

# ---------------------------------------------------------------------------
section("7. Konsistensi dokumentasi (field di docs ada di rule)")
# Ambil field nutanix_* yang di-set oleh rule .grok
produced = set()
for rf in os.listdir(p("graylog/rules")):
    src = open(p("graylog/rules", rf)).read()
    for m in re.finditer(r'set_field\("(nutanix_[a-z_]+)"', src):
        produced.add(m.group(1))
    for m in re.finditer(r'set_field\("(ntnx_[a-z_]+)"', src):
        produced.add(m.group(1))

# Ambil field yang disebut di FIELD-REFERENCE.md (dalam backtick `nutanix_...`)
documented = set()
fr = open(p("docs/FIELD-REFERENCE.md")).read()
for m in re.finditer(r"`(nutanix_[a-z_]+)`", fr):
    documented.add(m.group(1))
for m in re.finditer(r"`(ntnx_[a-z_]+)`", fr):
    documented.add(m.group(1))

# Setiap field terdokumentasi harus benar-benar diproduksi rule
missing_in_code = documented - produced
check("Semua field di FIELD-REFERENCE.md diproduksi oleh rule",
      len(missing_in_code) == 0,
      f"didokumentasikan tapi tak ada di rule: {sorted(missing_in_code)}")

# Setiap field yang diproduksi sebaiknya terdokumentasi (warning, bukan fatal)
undoc = produced - documented
check("Semua field yang diproduksi terdokumentasi",
      len(undoc) == 0,
      f"ada di rule tapi tak terdokumentasi: {sorted(undoc)}")

# ---------------------------------------------------------------------------
section("8. Semua tipe log ter-cover simulator")
# Pastikan generator menghasilkan keempat tipe & simulator memparse semua
try:
    sys.path.insert(0, p("scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("simpipe", p("scripts/simulate_pipeline.py"))
    simpipe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(simpipe)

    seen_types = set()
    with open(csv_path) as f:
        rd = csv.reader(f, delimiter=";")
        next(rd)
        for row in rd:
            if len(row) < 3:
                continue
            out = simpipe.process(row[2])
            seen_types.add(out.get("nutanix_log_type", "unparsed"))
    expected = {"api_audit", "cvm_audit", "flow_service", "audit"}
    check("Keempat tipe log ter-parse (tidak ada 'unparsed')",
          "unparsed" not in seen_types and expected.issubset(seen_types),
          f"terlihat: {sorted(seen_types)}")
except Exception as e:
    check("simulator dapat di-import & jalan", False, str(e))

# ---------------------------------------------------------------------------
section("9. Field dashboard diproduksi oleh rule")
dash2 = json.load(open(p("grafana/dashboards/nutanix-monitoring-dashboard.json")))
dash_fields = set()
def walk2(o):
    if isinstance(o, dict):
        if o.get("type") == "terms" and "field" in o:
            dash_fields.add(o["field"])
        if isinstance(o.get("query"), str):
            for mm in re.finditer(r"(nutanix_[a-z_]+)", o["query"]):
                dash_fields.add(mm.group(1))
        for v in o.values():
            walk2(v)
    elif isinstance(o, list):
        for v in o:
            walk2(v)
walk2(dash2)
dash_nutanix = {f for f in dash_fields if f.startswith(("nutanix_", "ntnx_"))}
check("Semua field nutanix_* di dashboard diproduksi rule",
      dash_nutanix.issubset(produced),
      f"tidak diproduksi: {sorted(dash_nutanix - produced)}")
check("Dashboard TIDAK memakai .keyword (pelajaran penting)",
      not any(".keyword" in f for f in dash_fields),
      f"pakai keyword: {[f for f in dash_fields if '.keyword' in f]}")

# ---------------------------------------------------------------------------
section("10. Integritas CSV sample data")
with open(csv_path) as f:
    header = f.readline().strip()
check("Header CSV = timestamp;source;message",
      header == "timestamp;source;message", f"header: {header}")
bad = 0
total = 0
with open(csv_path) as f:
    next(f)
    for line in f:
        if not line.strip():
            continue
        total += 1
        if line.count(";") < 2:
            bad += 1
check(f"Semua {total} baris punya >=2 delimiter ';'", bad == 0, f"{bad} baris rusak")

# ---------------------------------------------------------------------------
section("11. Diagram Mermaid valid")
for md in ["README.md", "docs/ARCHITECTURE.md"]:
    txt = open(p(md)).read()
    blocks = re.findall(r"```mermaid\n(.*?)```", txt, re.DOTALL)
    if not blocks:
        continue
    for i, b in enumerate(blocks):
        lines = [l for l in b.strip().split("\n") if l.strip()]
        first = lines[0].strip()
        valid_start = first.startswith(("flowchart", "graph"))
        n_sub = sum(1 for l in lines if l.strip().startswith("subgraph"))
        n_end = sum(1 for l in lines if l.strip() == "end")
        has_arrow = any("-->" in l for l in lines)
        check(f"{md} mermaid #{i+1}: deklarasi & balance & arrow",
              valid_start and n_sub == n_end and has_arrow,
              f"start={valid_start}, subgraph={n_sub}/end={n_end}, arrow={has_arrow}")

# ---------------------------------------------------------------------------
section("12. Tidak ada em dash atau en dash")
dash_files = []
for dirpath, _, files in os.walk(ROOT):
    if "__pycache__" in dirpath:
        continue
    for fn in files:
        fp = os.path.join(dirpath, fn)
        try:
            txt = open(fp, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if "\u2014" in txt or "\u2013" in txt:  # em dash / en dash
            dash_files.append(os.path.relpath(fp, ROOT))
check("Tidak ada karakter em dash atau en dash", len(dash_files) == 0,
      f"ditemukan di: {dash_files}")

# ---------------------------------------------------------------------------
section("HASIL")
print(f"  PASS: {PASS}   FAIL: {FAIL}")
if FAIL == 0:
    print("\n  [SUCCESS] Semua validasi lolos.")
    sys.exit(0)
else:
    print(f"\n  [ATTENTION] {FAIL} pemeriksaan gagal - lihat di atas.")
    sys.exit(1)
