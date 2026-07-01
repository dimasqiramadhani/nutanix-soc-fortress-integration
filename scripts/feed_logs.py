#!/usr/bin/env python3
"""
Nutanix SOC Sandbox: Log Feeder
===============================
This script reads the sandbox_nutanix_logs.csv file and sends each line to the
Graylog Syslog TCP input (default localhost:5141), mirroring Nutanix forwarding
syslog. As a result, a real Nutanix device is not required.

Example usage:
  python3 feed_logs.py --host localhost --port 5141 \
      --file ../sample-data/sandbox_nutanix_logs.csv --rate 20

  --rate means the number of messages per second (a value of 0 means as fast as possible)
  --loop means repeating continuously to simulate a live stream
"""

import argparse
import csv
import socket
import time
from datetime import datetime


def syslog_frame(source, message, ts=None):
    """Wrap into an RFC style syslog frame understood by Graylog Syslog TCP."""
    if ts is None:
        ts = datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")
        # sisipkan colon di offset tz: +0700 -> +07:00
        ts = ts[:-2] + ":" + ts[-2:]
    # PRI 134 = facility local0 (16) severity info (6)
    return f"<134>{ts} {source} {message}\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=5141)
    ap.add_argument("--file", default="../sample-data/sandbox_nutanix_logs.csv")
    ap.add_argument("--rate", type=float, default=20.0,
                    help="messages per second (0 = no delay)")
    ap.add_argument("--loop", action="store_true")
    args = ap.parse_args()

    def load_rows():
        rows = []
        with open(args.file) as f:
            reader = csv.reader(f, delimiter=";")
            next(reader, None)  # skip the header
            for r in reader:
                if len(r) < 3:
                    continue
                # r = [timestamp, source, message]
                rows.append((r[1], r[2]))
        return rows

    rows = load_rows()
    print(f"[+] {len(rows)} lines loaded from {args.file}")
    delay = (1.0 / args.rate) if args.rate > 0 else 0

    sent = 0
    try:
        while True:
            with socket.create_connection((args.host, args.port), timeout=5) as sock:
                for source, message in rows:
                    frame = syslog_frame(source, message)
                    sock.sendall(frame.encode("utf-8"))
                    sent += 1
                    if sent % 100 == 0:
                        print(f"    sent {sent} messages...")
                    if delay:
                        time.sleep(delay)
            if not args.loop:
                break
            print("[*] loop: starting again from the beginning")
    except ConnectionRefusedError:
        print(f"[!] Unable to connect to {args.host}:{args.port}. "
              f"Ensure the Graylog Syslog TCP input is running on that port.")
        return
    except KeyboardInterrupt:
        print("\n[*] stopped by the user")

    print(f"[+] Done. Total sent: {sent} messages")


if __name__ == "__main__":
    main()
