import http.server
import socketserver
import json
import sqlite3
import os
import urllib.parse

PORT = 4004
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "bw_studio.sqlite")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

class StudioHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "service": "BW_Migration_Studio",
                "status": "HEALTHY",
                "version": "1.0.0",
                "environment": "LOCAL_DEVELOPMENT",
                "sapSafety": "STRICT_READ_ONLY_ENFORCED",
                "s21Protection": "ACTIVE"
            }).encode('utf-8'))
            return

        if path == "/api/overview":
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT count(*) FROM source_catalog")
            total_objs = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM dependencies")
            total_deps = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM connection_profiles")
            total_conns = cur.fetchone()[0]
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "totalSourceObjects": total_objs,
                "totalDependencies": total_deps,
                "configuredConnections": total_conns,
                "s21Inspection": "READ_ONLY_VERIFIED",
                "supportedTargetRoutes": ["Native Datasphere", "SAP BW Bridge", "BDC Data Product", "Hybrid"]
            }).encode('utf-8'))
            return

        if path == "/api/catalog":
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM source_catalog")
            rows = [dict(r) for r in cur.fetchall()]
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(rows).encode('utf-8'))
            return

        if path.startswith("/api/catalog/"):
            obj_name = path.split("/")[3]
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM source_catalog WHERE name = ?", (obj_name,))
            obj = cur.fetchone()
            if not obj:
                self.send_response(404)
                self.end_headers()
                return
            cur.execute("SELECT * FROM object_fields WHERE object_name = ?", (obj_name,))
            fields = [dict(r) for r in cur.fetchall()]
            cur.execute("SELECT * FROM dependencies WHERE source_object = ? OR dependent_object = ?", (obj_name, obj_name))
            deps = [dict(r) for r in cur.fetchall()]
            conn.close()

            res = dict(obj)
            res['fields'] = fields
            res['dependencies'] = deps

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
            return

        if path == "/api/dependencies":
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM dependencies")
            deps = [dict(r) for r in cur.fetchall()]
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(deps).encode('utf-8'))
            return

        if path == "/api/connections":
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM connection_profiles")
            conns = [dict(r) for r in cur.fetchall()]
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(conns).encode('utf-8'))
            return

        # Serve frontend index.html for root or UI files
        if path == "/" or path == "/index.html":
            index_path = os.path.join(FRONTEND_DIR, "index.html")
            if os.path.exists(index_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                with open(index_path, "rb") as f:
                    self.wfile.write(f.read())
                return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
        payload = json.loads(body)

        if path == "/api/assess":
            obj_name = payload.get("objectName", "ZSAM_SO01")
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM source_catalog WHERE name = ?", (obj_name,))
            obj = cur.fetchone()
            conn.close()

            if not obj:
                self.send_response(404)
                self.end_headers()
                return

            has_abap = obj['has_custom_abap']
            obj_type = obj['type']

            if has_abap:
                recommended = "SAP BW Bridge"
                scores = {"nativeDatasphere": 45, "bwBridge": 90, "bdcDataProduct": 50, "hybrid": 70}
                rationale = "Object contains procedural ABAP routines requiring BTP ABAP runtime preservation."
            elif obj_type == "COMPOSITE_PROVIDER":
                recommended = "Native Datasphere (Analytic Model)"
                scores = {"nativeDatasphere": 92, "bwBridge": 65, "bdcDataProduct": 75, "hybrid": 60}
                rationale = "CompositeProvider maps directly to modern Datasphere Analytic Model with star join."
            else:
                recommended = "Native Datasphere"
                scores = {"nativeDatasphere": 88, "bwBridge": 60, "bdcDataProduct": 80, "hybrid": 55}
                rationale = "Standard relational schema maps directly to Datasphere Local Table and push-down SQL."

            result = {
                "objectName": obj_name,
                "recommendedRoute": recommended,
                "feasibilityScores": scores,
                "blastRadiusScore": 3,
                "rationale": rationale
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))
            return

        if path == "/api/generate":
            obj_name = payload.get("objectName", "ZSAM_SO01")
            target_space = payload.get("targetSpace", "SALES_ANALYTICS")

            # Generate sample CSN artifact
            csn = {
                "$schema": "https://help.sap.com/doc/csn-v2.0.json",
                "definitions": {
                    f"{target_space}.LT_{obj_name}": {
                        "kind": "entity",
                        "@EndUserText.label": f"Modernized {obj_name} Local Table",
                        "elements": {
                            "SALES_DOC": {"type": "cds.String", "length": 10, "key": True},
                            "ITEM_NUM": {"type": "cds.Integer", "key": True},
                            "NET_VALUE": {"type": "cds.Decimal", "precision": 15, "scale": 2},
                            "CURRENCY": {"type": "cds.String", "length": 5}
                        }
                    }
                }
            }

            ddl = f'CREATE COLUMN TABLE "{target_space}"."LT_{obj_name}" (\n' \
                  f'    "SALES_DOC" NVARCHAR(10) NOT NULL,\n' \
                  f'    "ITEM_NUM" INTEGER NOT NULL,\n' \
                  f'    "NET_VALUE" DECIMAL(15,2),\n' \
                  f'    "CURRENCY" NVARCHAR(5),\n' \
                  f'    PRIMARY KEY ("SALES_DOC", "ITEM_NUM")\n' \
                  f');'

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "objectName": obj_name,
                "targetSpace": target_space,
                "csnPayload": csn,
                "ddlSql": ddl,
                "status": "GENERATED_LOCAL"
            }).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), StudioHandler) as httpd:
        print(f"HanaMorph BW Migration Studio Backend running at http://localhost:{PORT}")
        httpd.serve_forever()
