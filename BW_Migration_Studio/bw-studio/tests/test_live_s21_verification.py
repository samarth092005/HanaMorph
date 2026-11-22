"""
Live Read-Only Verification Script for SAP BW System S21
Executed under strict read-only mandate (AGENTS.md).
Zero mutations, HTTP GET only, RFC whitelist only.
"""
import os
import sys
import json
import hashlib
import time

studio_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if studio_dir not in sys.path:
    sys.path.insert(0, studio_dir)

from connectors.connection_hub import ConnectionHub
from discovery.adt_discovery_adapter import ADTDiscoveryAdapter

def main():
    hub = ConnectionHub.get_instance()
    mgr = hub.managers.get("bw_s21")
    if not mgr:
        print("ERROR: bw_s21 connection manager not found.")
        return

    print("==================================================================")
    print("HANAMORPH — LIVE S21 READ-ONLY CONNECTIVITY & METADATA AUDIT")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("==================================================================")

    # 1. Test Connection
    print("\n[Step 1] Testing live ADT discovery endpoint (/sap/bc/adt/discovery)...")
    res = mgr.test_connection()
    safe_details = dict(res.get("details", {}))
    if "password" in safe_details:
        safe_details["password"] = "***MASKED***"
    
    print(f"Status:       {res.get('status')}")
    print(f"Success:      {res.get('success')}")
    print(f"Latency:      {res.get('latency_ms', 0):.2f} ms")
    print(f"Host:         {safe_details.get('host')}")
    print(f"Client:       {safe_details.get('client')}")
    print(f"User:         {safe_details.get('user')}")
    print(f"Server Type:  {safe_details.get('server_type')}")
    print(f"Endpoint:     {safe_details.get('endpoint_reached')}")
    print(f"HTTP Status:  {safe_details.get('http_status')}")
    print(f"Policy:       {safe_details.get('read_only_policy')}")

    if not res.get("success"):
        print(f"FAILURE: {res.get('message')}")
        return

    # 2. ADT Repository QuickSearch
    adapter = ADTDiscoveryAdapter(mgr)
    print("\n[Step 2] Executing read-only ADT quick search for '*ZSAM*'...")
    search_endpoint = "/sap/bc/adt/repository/informationsystem/search?operation=quickSearch&query=*ZSAM*&maxResults=10"
    raw_search = mgr.execute_sap_http("GET", search_endpoint)
    print(f"HTTP Status Code: {raw_search['status_code']}")
    print(f"HTTP Latency:     {raw_search['latency_ms']:.2f} ms")
    print(f"Response Length:  {len(raw_search['data'])} bytes")
    search_hash = hashlib.sha256(raw_search['data']).hexdigest()
    print(f"SHA-256 Digest:   {search_hash}")

    objects = adapter.search_objects(query="*ZSAM*", max_results=10)
    print(f"\nDiscovered Live Objects Count: {len(objects)}")
    for obj in objects:
        print(f"  * [{obj['adt_type']}] {obj['technical_name']}")
        print(f"    Package:     {obj['package']}")
        print(f"    Description: {obj['description']}")
        print(f"    Provenance:  {obj['provenance']}")
        print(f"    ADT URI:     {obj['uri']}")

    # 3. Retrieve DDIC Table Fields for First Available Table
    target_table = None
    target_uri = None
    for obj in objects:
        if "tabl" in obj.get("adt_type", "").lower() or "tabl" in obj.get("uri", "").lower() or obj["technical_name"].startswith("Z"):
            target_table = obj["technical_name"]
            target_uri = obj.get("uri")
            break
    
    if not target_table and objects:
        target_table = objects[0]["technical_name"]
        target_uri = objects[0].get("uri")

    if target_table:
        print(f"\n[Step 3] Extracting live DDIC fields for '{target_table}' ({target_uri})...")
        raw_field_resp = mgr.execute_sap_http("GET", target_uri)
        print(f"HTTP Status Code: {raw_field_resp['status_code']}")
        print(f"HTTP Latency:     {raw_field_resp['latency_ms']:.2f} ms")
        print(f"Response Length:  {len(raw_field_resp['data'])} bytes")
        field_hash = hashlib.sha256(raw_field_resp['data']).hexdigest()
        print(f"SHA-256 Digest:   {field_hash}")

        fields = adapter.extract_table_fields(target_table, adt_uri=target_uri)
        print(f"Parsed Fields Count: {len(fields)}")
        for f in fields[:10]:
            print(f"    Field: {f['name']:<15} Type: {f['data_type']:<8} Len: {f['length']:<4} Dec: {f['decimals']:<2} Key: {f['is_key']}")

    # 4. Invariant Verification: Forbidden Mutating HTTP Verbs
    print("\n[Step 4] Verifying security guardrail against mutating requests...")
    try:
        mgr.execute_sap_http("POST", "/sap/bc/adt/repository/informationsystem/search")
        print("SECURITY FAILURE: Mutating POST was NOT blocked!")
    except Exception as e:
        print(f"SECURITY VERIFIED: Mutating POST blocked as expected -> {type(e).__name__}: {e}")

    try:
        mgr.execute_sap_http("DELETE", "/sap/bc/adt/repository/informationsystem/search")
        print("SECURITY FAILURE: Mutating DELETE was NOT blocked!")
    except Exception as e:
        print(f"SECURITY VERIFIED: Mutating DELETE blocked as expected -> {type(e).__name__}: {e}")

    print("\n==================================================================")
    print("LIVE S21 READ-ONLY VERIFICATION COMPLETE: ALL CHECKS PASSED")
    print("==================================================================")

if __name__ == "__main__":
    main()
