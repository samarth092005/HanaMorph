"""
Test live extraction of VIEW/DV objects from S21 ADT.
Strictly Read-Only.
"""
import os
import sys

studio_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if studio_dir not in sys.path:
    sys.path.insert(0, studio_dir)

from connectors.connection_hub import ConnectionHub

def main():
    mgr = ConnectionHub.get_instance().managers['bw_s21']

    for uri in [
        '/sap/bc/adt/vit/wb/object_type/viewdv/object_name/%2fBIC%2fAZSAM_PR016?sap-client=200',
        '/sap/bc/adt/vit/wb/object_type/viewdv/object_name/ZSAMPLE_SQL_09?sap-client=200'
    ]:
        res = mgr.execute_sap_http('GET', uri)
        print(f"\nURI: {uri} -> Status: {res['status_code']} Length: {len(res['data'])}")
        if res['status_code'] == 200:
            print("Snippet:")
            print(res['data'][:400].decode('utf-8', errors='ignore'))

if __name__ == "__main__":
    main()
