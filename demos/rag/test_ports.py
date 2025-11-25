#!/usr/bin/env python3
"""Test connectivity to all RAG demo services"""
import requests
import sys

services = [
    ("Data Store", 8001, "/v1/datastore/namespaces"),
    ("Entity Store", 8002, "/health"),
    ("Guardrails", 8005, "/health"),
    ("Chat NIM", 8006, "/v1/models"),
    ("Embedding NIM", 8007, "/v1/models"),
    ("LlamaStack", 8321, "/health"),
]

print("Testing service connectivity...")
print("=" * 60)

all_ok = True
for name, port, path in services:
    try:
        url = f"http://localhost:{port}{path}"
        response = requests.get(url, timeout=3)
        status = response.status_code
        if status in [200, 401, 404]:  # 200 OK, 401 Unauthorized, 404 Not Found all indicate service is up
            print(f"✅ {name:20} (port {port:4}): OK (HTTP {status})")
        else:
            print(f"⚠️  {name:20} (port {port:4}): Unexpected status {status}")
            all_ok = False
    except requests.exceptions.ConnectionError:
        print(f"❌ {name:20} (port {port:4}): Connection refused")
        all_ok = False
    except requests.exceptions.Timeout:
        print(f"⏱️  {name:20} (port {port:4}): Timeout")
        all_ok = False
    except Exception as e:
        print(f"❌ {name:20} (port {port:4}): Error - {type(e).__name__}: {str(e)[:50]}")
        all_ok = False

print("=" * 60)
if all_ok:
    print("✅ All services are reachable! Ready to run the notebook.")
    sys.exit(0)
else:
    print("⚠️  Some services are not reachable. Check port-forwards.")
    sys.exit(1)

