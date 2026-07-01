#!/usr/bin/env python3
"""
Nutanix SOC Sandbox: Validation and Self Test
=============================================
This script checks the consistency and validity of all project components,
namely:
  JSON and YAML syntax
  consistency between rules and pipeline references
  matching of the .grok regex against the sample data format
  alignment of fields produced by the simulator with those promised in the docs
  readability of the JSON in consolidated_audit

An exit code of 0 means all checks passed, while 1 means a check failed.

Example usage:
  python3 validate.py           # run from the scripts folder
  python3 scripts/validate.py   # run from the project root
"""

import json
import os
import re
import sys
import csv

# ---- Project root location (go up one level when run from scripts/) ----
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
section("1. JSON Validity")
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
section("2. YAML Validity")
try:
    import yaml
    for yf in ["docker-compose.yml", "grafana/datasources/nutanix-datasource.yaml"]:
        try:
            yaml.safe_load(open(p(yf)))
            check(yf, True)
        except Exception as e:
            check(yf, False, str(e))
except ImportError:
    print("  [SKIP] pyyaml is not installed (optional)")

# ---------------------------------------------------------------------------
section("3. Rule to Pipeline Consistency")
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

check("All rules referenced by pipelines have a definition",
      referenced.issubset(rule_titles),
      f"missing: {referenced - rule_titles}")
check("No orphan rules (defined but unused)",
      rule_titles == referenced,
      f"unused: {rule_titles - referenced}")

# ---------------------------------------------------------------------------
section("4. Datasource uid Matches the Dashboard Reference")
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
check(f"datasource uid '{ds_uid}' is referenced by the dashboard",
      ds_uid in dash_uids, f"dashboard refer: {dash_uids}")

# ---------------------------------------------------------------------------
section("5. Regex .grok Matches the Sample Data")
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
    check("an api_audit sample exists", False)

# error regex
if samples["error"]:
    check("responseCode regex", re.search(r".*responseCode=([0-9]+).*", samples["error"]) is not None)
else:
    check("an error sample exists (responseCode!=200)", False, "not present in the data (rare, regenerate more)")

# flow
if samples["flow"]:
    check("flow_service level regex", re.search(r".*Z\s+([A-Z]+)\s+.*", samples["flow"]) is not None)
else:
    check("a flow_service sample exists", False)

# cvm
if samples["cvm"]:
    check("cvm audit type regex", re.search(r".*type=([^ ]+).*", samples["cvm"]) is not None)
else:
    check("a cvm_audit sample exists", False)

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
    check("consolidated_audit JSON is parseable", ok)
else:
    check("a consolidated_audit sample exists", False, "the generator has not created any, check the weights")

# ---------------------------------------------------------------------------
section("6. No Leftover Word 'lab'")
leftover = []
SELF = os.path.abspath(__file__)
for dirpath, _, files in os.walk(ROOT):
    if "__pycache__" in dirpath:
        continue
    for fn in files:
        fp = os.path.join(dirpath, fn)
        if os.path.abspath(fp) == SELF:
            continue  # skip the validator itself (it contains the word 'lab' in its check messages)
        try:
            txt = open(fp, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        # look for 'lab' as a substring, except within legitimate common words
        for m in re.finditer(r"lab", txt, re.IGNORECASE):
            ctx = txt[max(0, m.start()-6):m.start()+6].lower()
            # legitimate words containing "lab": sandbox, global, available,
            # syllabus, label, collaboration, elaboration, laboratory
            if any(w in ctx for w in ["sandbox", "global", "availab", "syllab",
                                       "label", "kolab", "elab", "laborat"]):
                continue
            snippet = txt[max(0, m.start()-12):m.start()+12].replace("\n", " ")
            leftover.append(f"{os.path.relpath(fp, ROOT)}: ...{snippet}...")
            break
check("no leftover word 'lab'", len(leftover) == 0,
      "; ".join(leftover[:3]))

# ---------------------------------------------------------------------------
section("7. Documentation Consistency (fields in docs exist in rules)")
# Collect nutanix_* fields set by the .grok rules
produced = set()
for rf in os.listdir(p("graylog/rules")):
    src = open(p("graylog/rules", rf)).read()
    for m in re.finditer(r'set_field\("(nutanix_[a-z_]+)"', src):
        produced.add(m.group(1))
    for m in re.finditer(r'set_field\("(ntnx_[a-z_]+)"', src):
        produced.add(m.group(1))

# Collect fields mentioned in FIELD-REFERENCE.md (inside backticks `nutanix_...`)
documented = set()
fr = open(p("docs/FIELD-REFERENCE.md")).read()
for m in re.finditer(r"`(nutanix_[a-z_]+)`", fr):
    documented.add(m.group(1))
for m in re.finditer(r"`(ntnx_[a-z_]+)`", fr):
    documented.add(m.group(1))

# Every documented field must actually be produced by a rule
missing_in_code = documented - produced
check("All fields in FIELD-REFERENCE.md are produced by a rule",
      len(missing_in_code) == 0,
      f"documented but not present in any rule: {sorted(missing_in_code)}")

# Every produced field should ideally be documented (a warning, not fatal)
undoc = produced - documented
check("All produced fields are documented",
      len(undoc) == 0,
      f"present in a rule but undocumented: {sorted(undoc)}")

# ---------------------------------------------------------------------------
section("8. All Log Types Covered by the Simulator")
# Ensure the generator produces all four types and the simulator parses them all
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
    check("All four log types are parsed (no 'unparsed')",
          "unparsed" not in seen_types and expected.issubset(seen_types),
          f"observed: {sorted(seen_types)}")
except Exception as e:
    check("the simulator can be imported and run", False, str(e))

# ---------------------------------------------------------------------------
section("9. Dashboard Fields Are Produced by Rules")
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
check("All nutanix_* fields in the dashboard are produced by rules",
      dash_nutanix.issubset(produced),
      f"not produced: {sorted(dash_nutanix - produced)}")
check("The dashboard does NOT use .keyword (an important lesson)",
      not any(".keyword" in f for f in dash_fields),
      f"uses keyword: {[f for f in dash_fields if '.keyword' in f]}")

# ---------------------------------------------------------------------------
section("10. Sample Data CSV Integrity")
with open(csv_path) as f:
    header = f.readline().strip()
check("CSV header = timestamp;source;message",
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
check(f"All {total} lines have >=2 ';' delimiters", bad == 0, f"{bad} broken lines")

# ---------------------------------------------------------------------------
section("11. Mermaid Diagram Validity")
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
        check(f"{md} mermaid #{i+1}: declaration, balance, and arrow",
              valid_start and n_sub == n_end and has_arrow,
              f"start={valid_start}, subgraph={n_sub}/end={n_end}, arrow={has_arrow}")

# ---------------------------------------------------------------------------
section("12. No Em Dash or En Dash")
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
check("No em dash or en dash characters", len(dash_files) == 0,
      f"found in: {dash_files}")

# ---------------------------------------------------------------------------
section("RESULT")
print(f"  PASS: {PASS}   FAIL: {FAIL}")
if FAIL == 0:
    print("\n  [SUCCESS] All validations passed.")
    sys.exit(0)
else:
    print(f"\n  [ATTENTION] {FAIL} checks failed, see above.")
    sys.exit(1)
