import subprocess
import time
import urllib.request
import json
import os
import sys

server_script = r"C:\Users\samarth\BW-hanamorph\BW_Migration_Studio\bw-studio\backend\server.py"

print("Starting server process...")
proc = subprocess.Popen([sys.executable, server_script])
try:
    time.sleep(2)
    print("Testing http://localhost:4004/health...")
    with urllib.request.urlopen("http://localhost:4004/health", timeout=5) as resp:
        health_data = json.loads(resp.read().decode('utf-8'))
        print("HEALTH CHECK RESULT:", json.dumps(health_data, indent=2))
        assert health_data["status"] == "HEALTHY"

    print("\nTesting http://localhost:4004/api/overview...")
    with urllib.request.urlopen("http://localhost:4004/api/overview", timeout=5) as resp:
        overview_data = json.loads(resp.read().decode('utf-8'))
        print("OVERVIEW RESULT:", json.dumps(overview_data, indent=2))
        assert overview_data["totalSourceObjects"] >= 5

    print("\nTesting http://localhost:4004/api/assess...")
    req = urllib.request.Request(
        "http://localhost:4004/api/assess",
        data=json.dumps({"objectName": "ZSAM_SO01"}).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        assess_data = json.loads(resp.read().decode('utf-8'))
        print("ASSESSMENT RESULT:", json.dumps(assess_data, indent=2))
        assert assess_data["recommendedRoute"] == "Native Datasphere"

    print("\nALL BACKEND API HEALTH CHECKS VERIFIED SUCCESSFULLY!")
finally:
    print("Terminating server process...")
    proc.terminate()
    proc.wait()
    print("Server cleanly stopped.")
