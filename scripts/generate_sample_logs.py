#!/usr/bin/env python3
"""
Nutanix SOC Sandbox: Sample Log Generator
=========================================
This script generates synthetic and fictional Nutanix Prism Central logs for
sandbox purposes. All hostnames, users, UUIDs, and IP addresses within it are
examples for learning and demonstration. No production or real data is
included.

The generated formats mirror the real Prism Central log structure, namely:
  api_audit          (key-value)
  cvm_audit          (auditd or audispd)
  flow_service       (microsegmentation)
  consolidated_audit (JSON)

Example usage:
  python3 generate_sample_logs.py --count 2000 --out ../sample-data/sandbox_nutanix_logs.csv
"""

import argparse
import random
import uuid
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# SAMPLE INVENTORY (all fictional for the sandbox)
# ---------------------------------------------------------------------------
PCVM = "NTNX-10-0-0-45-A-PCVM"          # Prism Central VM (sandbox)
CVMS = [
    "NTNX-SANDBOX0000001-A-CVM",
    "NTNX-SANDBOX0000001-B-CVM",
    "NTNX-SANDBOX0000002-A-CVM",
    "NTNX-SANDBOX0000002-B-CVM",
]

# Fictional users: a mix of human UI users, admin, service accounts, and a backup account
HUMAN_USERS = ["andi.pratama", "budi.santoso", "citra.dewi"]
SERVICE_UUIDS = [
    "0000aaaa-1111-2222-3333-444455556666",
    "0000bbbb-7777-8888-9999-aaaabbbbcccc",
]
ADMIN_USER = "admin"
BACKUP_USER = "sandboxbackupadmin"

SANDBOX_VM_UUID = "11111111-2222-3333-4444-555555555555"

# Endpoint umum (GET dominan seperti di dunia nyata)
GET_ENDPOINTS = [
    "/v1/users/details",
    "/v1/multicluster/cluster_external_state",
    f"/v1/vms/{SANDBOX_VM_UUID}/stats",
    f"/v2.0/vms/{SANDBOX_VM_UUID}",
    "/v2.0/cluster",
    "/v1/containers",
    "/v0.8/networks",
    "/v1/progress_monitors",
    "/v1/clusters",
    "/v2.0/hosts",
]
WRITE_ENDPOINTS = [
    "/v1/groups",
    f"/v1/vms/{SANDBOX_VM_UUID}",
    "/v1/multicluster/data/send_data",
]

FLOW_MESSAGES = [
    "PublishLearnedIp: VIRTUAL_NIC {uuid} updated in IDF",
    "PublishLearnedIp: VM {uuid} updated in IDF",
    "Forwarding 1 requests to {uuid}",
]


def rand_uuid():
    return str(uuid.uuid4())


def ts_iso(dt, tz="+07:00"):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond//1000:03d}{tz}"


def ts_inner(dt):
    # inner timestamp gaya "2026-06-30 03:18:17,424Z"
    return dt.strftime("%Y-%m-%d %H:%M:%S,") + f"{dt.microsecond//1000:03d}Z"


def make_api_audit(dt):
    """Generate a single api_audit key-value line."""
    host = random.choice(CVMS + [PCVM])

    # Pilih profil user
    roll = random.random()
    if roll < 0.45:
        client_type = "External"
        user = random.choice(SERVICE_UUIDS)
        method = "GET"
        endpoint = "/v1/users/details"
    elif roll < 0.65:
        client_type = "External"
        user = ADMIN_USER
        method = "GET"
        endpoint = "/v1/multicluster/cluster_external_state"
    elif roll < 0.72:
        client_type = "External"
        user = BACKUP_USER
        method = "GET"
        endpoint = random.choice(["/v2.0/cluster", "/v2.0/hosts"])
    else:
        client_type = "ui"
        user = random.choice(HUMAN_USERS)
        # human via UI kadang melakukan write (POST)
        if random.random() < 0.1:
            method = "POST"
            endpoint = random.choice(WRITE_ENDPOINTS)
        else:
            method = "GET"
            endpoint = random.choice(GET_ENDPOINTS)

    api_ver = random.choice(["1.0", "2.0", "0.8"])
    entity = SANDBOX_VM_UUID if "vms" in endpoint else ""

    # Occasionally inject a response error (to exercise the Flag API Error rule)
    resp = ""
    if random.random() < 0.03:
        code = random.choice(["401", "403", "404", "500"])
        resp = f"||responseCode={code}"

    msg = (
        f"{host} api_audit: INFO  {ts_inner(dt)} "
        f"clientType={client_type}||userName={user}||NutanixApiVersion={api_ver}||"
        f"httpMethod={method}||restEndpoint={endpoint}||entityUuid={entity}||"
        f"queryParams=||payload={resp}"
    )
    return host, msg


def make_cvm_audit(dt):
    """Generate a single cvm audit (audispd) line, which is OS internal."""
    host = random.choice(CVMS)
    node = host.lower()
    session = random.randint(10000000, 99999999)
    pid = random.randint(1000, 60000)
    audit_id = random.randint(100000000, 999999999)
    epoch = dt.timestamp()

    templates = [
        # su authentication (privilege)
        (f"type=USER_AUTH msg=audit({epoch:.3f}:{audit_id}): pid={pid} uid=0 auid=0 "
         f"ses={session} subj=sysadm_u:sysadm_r:sysadm_su_t:s0-s0:c0.c1023 "
         f"msg='op=PAM:authentication grantors=pam_rootok acct=\"nutanix\" "
         f"exe=\"/usr/bin/su\" hostname=? addr=? terminal=? res=success'"),
        # sudo command (privilege)
        (f"type=USER_CMD msg=audit({epoch:.3f}:{audit_id}): pid={pid} uid=0 auid=0 "
         f"ses={session} subj=sysadm_u:sysadm_r:sysadm_sudo_t:s0-s0:c0.c1023 "
         f"msg='cwd=\"/root\" cmd=6c73202d6c202f746d70 "
         f"terminal=? res=success'"),
        # service start (noise-ish)
        (f"type=SERVICE_START msg=audit({epoch:.3f}:{audit_id}): pid=1 uid=0 "
         f"auid=4294967295 ses=4294967295 subj=system_u:system_r:init_t:s0 "
         f"msg='unit=rsyslog comm=\"systemd\" exe=\"/usr/lib/systemd/systemd\" "
         f"hostname=? addr=? terminal=? res=success'"),
    ]
    body = random.choice(templates)
    msg = f"{host} audispd[{random.randint(10000,40000)}]: node={node} {body}"
    return host, msg


def make_flow_service(dt):
    host = random.choice(CVMS)
    tmpl = random.choice(FLOW_MESSAGES).format(uuid=rand_uuid())
    msg = (f"{host} flow_service_logs-acropolis: {ts_inner(dt)} INFO "
           f"vm_idf_entity.py:{random.randint(100,999)} {tmpl}")
    return host, msg


# consolidated_audit (JSON), used to test the Parse Audit JSON rule
AUDIT_OPS = [
    ("Login", "User logged in to Prism Central", "cluster", "SANDBOX-CLUSTER"),
    ("Logout", "User logged out from Prism Central", "cluster", "SANDBOX-CLUSTER"),
    ("Create", "VM created", "vm", "SANDBOX-VM-01"),
    ("Update", "VM configuration updated", "vm", "SANDBOX-VM-02"),
    ("Delete", "VM deleted", "vm", "SANDBOX-VM-03"),
]


def make_consolidated_audit(dt):
    import json as _json
    host = PCVM
    op, msg_text, etype, ename = random.choice(AUDIT_OPS)
    user = random.choice(HUMAN_USERS) + "@sandbox.local"
    payload = {
        "affectedEntityList": [
            {"entityType": etype, "name": ename, "uuid": rand_uuid()}
        ],
        "defaultMsg": msg_text,
        "operationType": op,
        "recordType": "Audit",
        "severity": "Audit",
        "userName": user,
        "userUuid": rand_uuid(),
        "uuid": rand_uuid(),
    }
    msg = f"{host} consolidated_audit: {_json.dumps(payload, separators=(',', ':'))}"
    return host, msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=2000)
    ap.add_argument("--out", default="../sample-data/sandbox_nutanix_logs.csv")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)

    # Distribution similar to real data: api_audit dominant, cvm audit frequent,
    # with flow and consolidated_audit being few
    weights = [("api", 0.55), ("cvm", 0.38), ("flow", 0.03), ("consolidated", 0.04)]

    start = datetime.now() - timedelta(hours=6)
    rows = []
    for i in range(args.count):
        dt = start + timedelta(seconds=i * (6 * 3600 / args.count),
                               microseconds=random.randint(0, 999000))
        r = random.random()
        cum = 0
        kind = "api"
        for k, w in weights:
            cum += w
            if r <= cum:
                kind = k
                break

        if kind == "api":
            host, msg = make_api_audit(dt)
        elif kind == "cvm":
            host, msg = make_cvm_audit(dt)
        elif kind == "flow":
            host, msg = make_flow_service(dt)
        else:
            host, msg = make_consolidated_audit(dt)

        # CSV line: timestamp;source;message (semicolon delimited, mirroring a Graylog export)
        full = f"{host} {msg}" if not msg.startswith(host) else msg
        rows.append(f"{ts_iso(dt)};{host};{full}")

    with open(args.out, "w") as f:
        f.write("timestamp;source;message\n")
        f.write("\n".join(rows) + "\n")

    print(f"[+] {len(rows)} sandbox log lines written to {args.out}")


if __name__ == "__main__":
    main()
