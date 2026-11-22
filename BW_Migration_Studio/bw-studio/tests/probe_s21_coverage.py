"""
Probe script to evaluate S21 ADT endpoint coverage for BW object types.
Strictly Read-Only (HTTP GET only).
"""
import os
import sys
import xml.etree.ElementTree as ET

studio_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if studio_dir not in sys.path:
    sys.path.insert(0, studio_dir)

from connectors.connection_hub import ConnectionHub

def main():
    mgr = ConnectionHub.get_instance().managers['bw_s21']

    types_to_probe = [
        ('TABL/DT', '*ZSAM*', 'TABL/DT'),
        ('VIEW/DV', '*ZSAM*', 'VIEW/DV'),
        ('ADSO', '*ZSAM*', 'ADSO'),
        ('IOBJ', '*0*', 'IOBJ'),
        ('HCPR', '*ZSAM*', 'HCPR'),
        ('CUBE', '*ZSAM*', 'CUBE'),
        ('ODSO', '*ZSAM*', 'ODSO'),
        ('MPRO', '*ZSAM*', 'MPRO'),
        ('TRFN', '*ZSAM*', 'TRFN'),
        ('DTPA', '*ZSAM*', 'DTPA'),
        ('RSDS', '*ZSAM*', 'RSDS'),
        ('RSPC', '*ZSAM*', 'RSPC'),
        ('ELEM/Query', '*ZSAM*', 'ELEM'),
        ('ODSV', '*ZSAM*', 'ODSV')
    ]

    print("======================================================================")
    print("S21 ADT ENDPOINT COVERAGE PROBE")
    print("======================================================================")

    for label, query, otype in types_to_probe:
        endpoint = f"/sap/bc/adt/repository/informationsystem/search?operation=quickSearch&query={query}&maxResults=10&sap-client=200"
        if otype:
            endpoint += f"&objectType={otype}"
        try:
            res = mgr.execute_sap_http("GET", endpoint)
            print(f"\nProbe [{label:<12}] -> HTTP Status: {res['status_code']}")
            if res['status_code'] == 200:
                root = ET.fromstring(res['data'])
                items = root.findall('.//{*}objectReference')
                print(f"   Items Found: {len(items)}")
                for it in items[:4]:
                    name = it.attrib.get('{http://www.sap.com/adt/core}name')
                    t = it.attrib.get('{http://www.sap.com/adt/core}type')
                    uri = it.attrib.get('{http://www.sap.com/adt/core}uri')
                    desc = it.attrib.get('{http://www.sap.com/adt/core}description', '')
                    print(f"   * {name:<20} Type: {t:<10} URI: {uri} ({desc})")
            else:
                print(f"   Error: HTTP {res['status_code']}")
        except Exception as e:
            print(f"\nProbe [{label:<12}] -> FAILED: {e}")

if __name__ == "__main__":
    main()
