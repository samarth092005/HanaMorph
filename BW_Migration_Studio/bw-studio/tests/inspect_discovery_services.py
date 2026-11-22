"""
Inspect advertised ADT discovery services for BW and DDIC endpoints.
Strictly Read-Only.
"""
import os
import sys
import re

studio_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if studio_dir not in sys.path:
    sys.path.insert(0, studio_dir)

from connectors.connection_hub import ConnectionHub

def main():
    mgr = ConnectionHub.get_instance().managers['bw_s21']
    disco = mgr.execute_sap_http('GET', '/sap/bc/adt/discovery?sap-client=200')
    text = disco['data'].decode('utf-8', errors='ignore')

    all_hrefs = re.findall(r'href="([^"]+)"', text)
    bw_hrefs = [h for h in all_hrefs if 'bw' in h.lower()]
    ddic_hrefs = [h for h in all_hrefs if any(k in h.lower() for k in ['ddic', 'table', 'search', 'core'])]

    print(f"Total hrefs in ADT discovery: {len(all_hrefs)}")
    print(f"BW-specific hrefs: {len(bw_hrefs)}")
    for h in sorted(set(bw_hrefs)):
        print(f"  * {h}")

    print("\n--- Testing BW-specific ICF service nodes ---")
    for ep in [
        '/sap/bc/adt/bw/discovery',
        '/sap/bc/adt/bw',
        '/sap/bc/adt/bw/adso',
        '/sap/bw/cpi',
        '/sap/bc/bwc',
        '/sap/bw/doc',
        '/sap/bc/adt/bw/modeling',
        '/sap/bc/adt/bw/repository'
    ]:
        try:
            res = mgr.execute_sap_http('GET', f'{ep}?sap-client=200')
            print(f"{ep:<30} -> Status: {res['status_code']} Length: {len(res['data'])}")
        except Exception as e:
            print(f"{ep:<30} -> Error: {e}")

if __name__ == "__main__":
    main()
