#!/usr/bin/env python3
"""One-shot GitHub Actions network probe for official market-document hosts.

Diagnostics only: never archives or interprets market evidence. Each HTTP method
gets three attempts, bounded connect/read timeouts, and structured timing output.
"""
from __future__ import annotations

import json
import pathlib
import socket
import ssl
import subprocess
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit

import requests

OUT = pathlib.Path("data/reports/market_source_transport_probe.json")
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 25
ATTEMPTS = 3
BACKOFF = (2, 5)
MAX_BODY_BYTES = 256 * 1024
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/pdf,application/octet-stream,text/html,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}
URLS = [
    {"label": "niftyindices_pdf", "url": "https://www.niftyindices.com/Factsheet/ind_nifty50.pdf"},
    {"label": "nsearchives_pdf", "url": "https://nsearchives.nseindia.com/content/indices/ind_nifty50.pdf"},
    {"label": "nsearchives_inline_pdf", "url": "https://nsearchives.nseindia.com/web/sites/default/files/inline-files/Nifty%2050%20whitepaper.pdf"},
    {"label": "nse_homepage", "url": "https://www.nseindia.com/"},
]

def network_probe(host: str) -> dict:
    result = {"host": host}
    started = time.monotonic()
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        result["dns_seconds"] = round(time.monotonic() - started, 3)
        result["resolved_ips"] = sorted({x[4][0] for x in infos})
        ip = infos[0][4][0]
        family = infos[0][0]
        t = time.monotonic()
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(CONNECT_TIMEOUT)
            sock.connect((ip, 443))
            result["tcp_seconds"] = round(time.monotonic() - t, 3)
            t = time.monotonic()
            context = ssl.create_default_context()
            with context.wrap_socket(sock, server_hostname=host) as tls:
                result["tls_seconds"] = round(time.monotonic() - t, 3)
                result["tls_version"] = tls.version()
                result["cipher"] = tls.cipher()[0] if tls.cipher() else None
    except Exception as exc:
        result["network_error"] = f"{type(exc).__name__}: {exc}"[:500]
    return result

def record_attempt(method, url, attempt, operation):
    started = time.monotonic()
    record = {"method": method, "url": url, "attempt": attempt}
    try:
        details = operation()
        record.update(details)
        record["ok"] = True
    except Exception as exc:
        record["ok"] = False
        record["error"] = f"{type(exc).__name__}: {exc}"[:700]
    record["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return record

def retry(method, url, operation):
    records = []
    for attempt in range(1, ATTEMPTS + 1):
        records.append(record_attempt(method, url, attempt, operation))
        if records[-1]["ok"]:
            break
        if attempt < ATTEMPTS:
            time.sleep(BACKOFF[attempt - 1])
    return records

def requests_once(url):
    def run():
        with requests.get(url, headers=HEADERS, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                          stream=True, allow_redirects=True) as response:
            ttfb = response.elapsed.total_seconds()
            count = 0
            for chunk in response.iter_content(16384):
                if chunk:
                    count += len(chunk)
                    if count >= MAX_BODY_BYTES:
                        break
            return {"status_code": response.status_code, "final_url": response.url,
                    "content_type": response.headers.get("Content-Type"),
                    "content_length": response.headers.get("Content-Length"),
                    "ttfb_seconds": round(ttfb, 3), "bytes_received": count}
    return run

def curl_once(url):
    def run():
        cmd = ["curl", "--silent", "--show-error", "--location", "--http1.1",
               "--connect-timeout", str(CONNECT_TIMEOUT), "--max-time", str(READ_TIMEOUT + CONNECT_TIMEOUT),
               "--max-filesize", str(MAX_BODY_BYTES), "-A", HEADERS["User-Agent"],
               "-H", "Accept: " + HEADERS["Accept"],
               "-H", "Accept-Language: " + HEADERS["Accept-Language"],
               "-H", "Referer: " + HEADERS["Referer"],
               "-o", "/dev/null", "-w",
               "http_code=%{http_code}\\nurl_effective=%{url_effective}\\ntime_namelookup=%{time_namelookup}\\ntime_connect=%{time_connect}\\ntime_appconnect=%{time_appconnect}\\ntime_starttransfer=%{time_starttransfer}\\nsize_download=%{size_download}\\ncontent_type=%{content_type}\\n",
               url]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=READ_TIMEOUT + CONNECT_TIMEOUT + 5)
        parsed = {}
        for line in p.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                parsed[k] = v
        if p.returncode:
            raise RuntimeError(f"curl exit {p.returncode}: {p.stderr[-500:]} ; metrics={parsed}")
        return {"curl_metrics": parsed, "bytes_received": int(float(parsed.get("size_download", 0)))}
    return run

def curl_cffi_once(url):
    def run():
        from curl_cffi import requests as c_requests
        with c_requests.Session(impersonate="chrome") as session:
            response = session.get(url, headers=HEADERS,
                                   timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
                                   stream=True, allow_redirects=True)
            count = 0
            for chunk in response.iter_content(16384):
                if chunk:
                    count += len(chunk)
                    if count >= MAX_BODY_BYTES:
                        break
            return {"status_code": response.status_code, "final_url": response.url,
                    "content_type": response.headers.get("Content-Type"),
                    "content_length": response.headers.get("Content-Length"),
                    "bytes_received": count}
    return run


def main():
    hosts = sorted({urlsplit(x["url"]).hostname for x in URLS if urlsplit(x["url"]).hostname})
    report = {"schema_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "runner": {"os": "GitHub Actions ubuntu-latest", "python": __import__("sys").version},
              "timeouts_seconds": {"connect": CONNECT_TIMEOUT, "read": READ_TIMEOUT},
              "attempts_per_method": ATTEMPTS, "network": [network_probe(h) for h in hosts],
              "http_probes": []}
    for target in URLS:
        url = target["url"]
        for method, factory in (("requests", requests_once), ("curl_http1_1_browser_headers", curl_once),
                                ("curl_cffi_chrome_impersonation", curl_cffi_once)):
            report["http_probes"].append({"label": target["label"], "method": method,
                                         "attempts": retry(method, url, factory(url))})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"network": report["network"], "http_probes": report["http_probes"]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
