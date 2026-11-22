"""
Independent Verification Runner for S21 Live Verification Sign-Off
Strict Read-Only Mandate. Masks all sensitive credentials.
"""
import socket
import time
import hashlib
import urllib.request
import os
import sys

studio_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if studio_dir not in sys.path:
    sys.path.insert(0, studio_dir)

from connectors.connection_hub import ConnectionHub
from discovery.adt_discovery_adapter import ADTDiscoveryAdapter

def main():
    print("--- 1. TCP PORT VERIFICATION ---")
    for port in [8000, 3300]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        start = time.time()
        try:
            s.connect(("192.168.1.55", port))
            dur = (time.time() - start) * 1000
            print(f"TCP 192.168.1.55:{port} -> SUCCESS (Latency: {dur:.2f} ms)")
            s.close()
        except Exception as e:
            print(f"TCP 192.168.1.55:{port} -> FAILED: {e}")

    print("\n--- 2. GET /sap/public/ping ---")
    try:
        t0 = time.time()
        req = urllib.request.Request("http://192.168.1.55:8000/sap/public/ping")
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            content = resp.read()
            lat = (time.time() - t0) * 1000
            print(f"Status:   {resp.status} {resp.reason}")
            print(f"Latency:  {lat:.2f} ms")
            print(f"Server:   {resp.headers.get('server')}")
            print(f"Content:  {resp.headers.get('content-type')}")
            print(f"Length:   {len(content)} bytes")
            print(f"SHA-256:  {hashlib.sha256(content).hexdigest()}")
    except Exception as e:
        print(f"Ping failed: {e}")

    print("\n--- 3. ADT DISCOVERY (/sap/bc/adt/discovery?sap-client=200) ---")
    hub = ConnectionHub.get_instance()
    mgr = hub.managers["bw_s21"]

    disco_resp = mgr.execute_sap_http("GET", "/sap/bc/adt/discovery?sap-client=200")
    disco_hash = hashlib.sha256(disco_resp["data"]).hexdigest()
    print(f"Status:   {disco_resp['status_code']}")
    print(f"Latency:  {disco_resp['latency_ms']:.2f} ms")
    print(f"Length:   {len(disco_resp['data'])} bytes")
    print(f"SHA-256:  {disco_hash}")

    print("\n--- 4. ADT QUICKSEARCH (*ZSAM*) ---")
    search_endpoint = "/sap/bc/adt/repository/informationsystem/search?operation=quickSearch&query=*ZSAM*&maxResults=10&sap-client=200"
    search_resp = mgr.execute_sap_http("GET", search_endpoint)
    search_hash = hashlib.sha256(search_resp["data"]).hexdigest()
    print(f"Status:   {search_resp['status_code']}")
    print(f"Latency:  {search_resp['latency_ms']:.2f} ms")
    print(f"Length:   {len(search_resp['data'])} bytes")
    print(f"SHA-256:  {search_hash}")

    adapter = ADTDiscoveryAdapter(mgr)
    objects = adapter.search_objects(query="*ZSAM*", max_results=10)
    print(f"Objects Discovered ({len(objects)} items):")
    for idx, obj in enumerate(objects, 1):
        # Calculate object entry hash
        raw_repr = f"{obj['technical_name']}|{obj['adt_type']}|{obj['uri']}".encode('utf-8')
        h = hashlib.sha256(raw_repr).hexdigest()
        print(f"  [{idx:02d}] {obj['technical_name']:<25} Type: {obj['adt_type']:<10} Provenance: {obj['provenance']} SHA256: {h[:16]}... URI: {obj['uri']}")

    print("\n--- 5. DDIC TABLE METADATA (/BIC/AZSAM_PR011) ---")
    target_uri = "/sap/bc/adt/ddic/tables/%2fbic%2fazsam_pr011?sap-client=200"
    tbl_resp = mgr.execute_sap_http("GET", target_uri)
    tbl_hash = hashlib.sha256(tbl_resp["data"]).hexdigest()
    print(f"Status:   {tbl_resp['status_code']}")
    print(f"Latency:  {tbl_resp['latency_ms']:.2f} ms")
    print(f"Length:   {len(tbl_resp['data'])} bytes")
    print(f"SHA-256:  {tbl_hash}")

    fields = adapter.extract_table_fields("/BIC/AZSAM_PR011", adt_uri=target_uri)
    print(f"Extracted Fields ({len(fields)} fields):")
    for f in fields:
        print(f"  Field: {f['name']:<18} Type: {f['data_type']:<10} Length: {f['length']:<5} Decimals: {f['decimals']:<3} Key: {f['is_key']}")

if __name__ == "__main__":
    main()
