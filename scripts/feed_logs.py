#!/usr/bin/env python3
"""
Nutanix SOC Sandbox : Pengirim Log
==================================
Skrip ini membaca berkas sandbox_nutanix_logs.csv dan mengirim tiap baris ke
input Graylog Syslog TCP (bawaan localhost:5141), meniru Nutanix yang
meneruskan syslog. Dengan demikian, perangkat Nutanix nyata tidak diperlukan.

Contoh penggunaan:
  python3 feed_logs.py --host localhost --port 5141 \
      --file ../sample-data/sandbox_nutanix_logs.csv --rate 20

  --rate berarti jumlah pesan per detik (nilai 0 berarti secepat mungkin)
  --loop berarti mengulang terus untuk menyimulasikan aliran langsung
"""

import argparse
import csv
import socket
import time
from datetime import datetime


def syslog_frame(source, message, ts=None):
    """Bungkus jadi frame syslog RFC-ish yang dimengerti Graylog Syslog TCP."""
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
                    help="pesan per detik (0 = tanpa jeda)")
    ap.add_argument("--loop", action="store_true")
    args = ap.parse_args()

    def load_rows():
        rows = []
        with open(args.file) as f:
            reader = csv.reader(f, delimiter=";")
            next(reader, None)  # skip header
            for r in reader:
                if len(r) < 3:
                    continue
                # r = [timestamp, source, message]
                rows.append((r[1], r[2]))
        return rows

    rows = load_rows()
    print(f"[+] {len(rows)} baris dimuat dari {args.file}")
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
                        print(f"    terkirim {sent} pesan...")
                    if delay:
                        time.sleep(delay)
            if not args.loop:
                break
            print("[*] loop: mulai lagi dari awal")
    except ConnectionRefusedError:
        print(f"[!] Tidak bisa connect ke {args.host}:{args.port}. "
              f"Pastikan Graylog input Syslog TCP jalan di port itu.")
        return
    except KeyboardInterrupt:
        print("\n[*] dihentikan user")

    print(f"[+] Selesai. Total terkirim: {sent} pesan")


if __name__ == "__main__":
    main()
