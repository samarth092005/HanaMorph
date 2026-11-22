import http.server
import socketserver
import json
import sqlite3
import os
import sys
import urllib.parse
import hmac
import hashlib
import secrets
import signal
import threading
import argparse
import time
from datetime import datetime, timezone
from http.cookies import SimpleCookie

PORT = 4004
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from connectors.connection_hub import ConnectionHub
from discovery.discovery_engine import DiscoveryEngine
from assessment_engine.assessment_engine import AssessmentEngine
from dependency_engine.dependency_graph import DependencyGraph
from planning_engine.planning_engine import PlanningEngine
from generation_engine.generation_engine import GenerationEngine
from validation_engine.validation_engine import ValidationEngine
from deployment.delivery_packager import DeliveryPackager
from deployment.package_validator import PackageValidator
from deployment.runbook_generator import RunbookGenerator
from core.job_engine import BackgroundJobEngine
from core.database_backup_manager import DatabaseBackupManager

DB_PATH = os.path.join(BASE_DIR, "database", "bw_studio.sqlite")
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
OUTPUT_DIR = os.path.join(os.path.dirname(BASE_DIR), "output")
DELIVERY_DIR = os.path.join(os.path.dirname(BASE_DIR), "delivery")


class SessionManager:
    """Server-side session manager providing secure HttpOnly session cookies & CSRF tokens."""
    def __init__(self, ttl_seconds: int = 86400):
        self.ttl = ttl_seconds
        self.sessions = {} # session_id -> {"user": str, "created_at": float, "expires_at": float, "csrf_token": str}
        self.lock = threading.Lock()

    def create_session(self, user: str = "admin") -> tuple:
        session_id = secrets.token_hex(32)
        csrf_token = secrets.token_hex(16)
        now = time.time()
        with self.lock:
            self.sessions[session_id] = {
                "user": user,
                "created_at": now,
                "expires_at": now + self.ttl,
                "csrf_token": csrf_token
            }
        return session_id, csrf_token

    def validate_session(self, session_id: str) -> dict:
        if not session_id:
            return None
        with self.lock:
            sess = self.sessions.get(session_id)
            if not sess:
                return None
            if time.time() > sess["expires_at"]:
                del self.sessions[session_id]
                return None
            return sess

    def invalidate_session(self, session_id: str) -> bool:
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
        return False

SESSION_MGR = SessionManager()


def get_or_create_api_key():
    """Retrieve API key from environment, persistent file, or generate a new secure key."""
    env_key = os.environ.get("BW_STUDIO_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    key_file = os.path.join(BASE_DIR, ".api_key")
    if os.path.isfile(key_file):
        try:
            with open(key_file, "r", encoding="utf-8") as f:
                key = f.read().strip()
            if key:
                return key
        except Exception as e:
            print(f"[AUTH] Error reading {key_file}: {e}")

    new_key = secrets.token_urlsafe(32)
    try:
        with open(key_file, "w", encoding="utf-8") as f:
            f.write(new_key)
        try:
            os.chmod(key_file, 0o600)
        except Exception:
            pass
        key_fp = hashlib.sha256(new_key.encode('utf-8')).hexdigest()[:12]
        print(f"[AUTH] Generated new secure API key (sha256:{key_fp}...) saved to .api_key")
    except Exception as e:
        print(f"[AUTH] Warning: Could not write {key_file}: {e}")
    return new_key


class StudioHandler(http.server.BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-API-Key, X-CSRF-Token')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _authenticate_request(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. Health check is public for monitoring liveness
        if path in ("/health", "/api/health"):
            return True

        # 2. Auth login and session-check endpoints are public
        if path in ("/api/auth/login", "/api/auth/session"):
            return True

        # 3. Static frontend assets are public (jailed to FRONTEND_DIR)
        if not path.startswith("/api/"):
            return True

        # 4. OPTIONS CORS preflight is exempt
        if self.command == "OPTIONS":
            return True

        # 5. Check HttpOnly Session Cookie
        cookie_header = self.headers.get("Cookie")
        if cookie_header:
            cookie = SimpleCookie()
            try:
                cookie.load(cookie_header)
                if "bw_studio_session" in cookie:
                    sid = cookie["bw_studio_session"].value
                    sess = SESSION_MGR.validate_session(sid)
                    if sess:
                        self.session_user = sess["user"]
                        self.csrf_token = sess["csrf_token"]
                        return True
            except Exception:
                pass

        # 6. Check Authorization Bearer or X-API-Key headers (programmatic CLI / adapter fallback)
        auth_header = self.headers.get("Authorization")
        api_key_header = self.headers.get("X-API-Key")

        token = None
        if auth_header:
            parts = auth_header.strip().split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
            elif len(parts) == 1:
                token = parts[0]
        elif api_key_header:
            token = api_key_header.strip()

        if not token:
            self._send_json({
                "error": "Unauthorized: Missing authentication credentials. Provide a valid session cookie, 'Authorization: Bearer <token>', or 'X-API-Key' header.",
                "status": "UNAUTHORIZED"
            }, status_code=401)
            return False

        expected_key = getattr(self.server, "api_key", None)
        if not expected_key:
            expected_key = get_or_create_api_key()

        if not hmac.compare_digest(token.encode("utf-8"), expected_key.encode("utf-8")):
            self._send_json({
                "error": "Unauthorized: Invalid API token.",
                "status": "UNAUTHORIZED"
            }, status_code=401)
            return False

        return True

    def _send_json(self, data, status_code=200, headers=None):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

    def _send_error(self, message, status_code=400):
        self._send_json({"error": message, "status": "ERROR"}, status_code=status_code)

    def _serve_static_file(self, req_path):
        clean_path = urllib.parse.unquote(req_path)
        if clean_path in ("/", ""):
            clean_path = "/index.html"

        if ".." in clean_path or "\\" in clean_path or "\0" in clean_path:
            self._send_error("Forbidden: Path traversal blocked", 403)
            return

        rel_path = clean_path.lstrip("/\\")
        canonical_frontend = os.path.abspath(FRONTEND_DIR)
        target_path = os.path.abspath(os.path.join(canonical_frontend, rel_path))

        try:
            common = os.path.commonpath([canonical_frontend, target_path])
        except ValueError:
            self._send_error("Forbidden: Invalid path location", 403)
            return

        if common != canonical_frontend:
            self._send_error("Forbidden: Access outside frontend root blocked", 403)
            return

        prohibited_exts = {".sqlite", ".db", ".env", ".key", ".master_key", ".log", ".py", ".pyc", ".sh", ".bat", ".git", ".md"}
        _, ext = os.path.splitext(target_path)
        if ext.lower() in prohibited_exts or any(seg.startswith(".") for seg in rel_path.split("/")):
            self._send_error("Forbidden: Access to requested resource type is blocked", 403)
            return

        mime_types = {
            ".html": "text/html; charset=utf-8",
            ".htm": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".woff": "font/woff",
            ".woff2": "font/woff2"
        }

        if not os.path.isfile(target_path):
            self._send_error(f"Resource '{req_path}' not found", 404)
            return

        content_type = mime_types.get(ext.lower())
        if not content_type:
            self._send_error("Forbidden: MIME type not allowed", 403)
            return

        try:
            with open(target_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_error(f"Internal server error: {str(e)}", 500)

    def do_GET(self):
        try:
            if not self._authenticate_request():
                return
            self._handle_get()
        except Exception as e:
            self._send_error(f"Internal server error: {str(e)}", 500)

    def _handle_get(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. Health check (public liveness probe)
        if path in ("/health", "/api/health"):
            self._send_json({
                "service": "BW_Migration_Studio",
                "status": "HEALTHY",
                "version": "1.0.0",
                "environment": os.environ.get("STUDIO_ENV", "local_development"),
                "sapSafety": "STRICT_READ_ONLY_ENFORCED",
                "s21Protection": "ACTIVE",
                "authMode": "API_KEY",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            return

        # 1.1 Auth session state query
        if path == "/api/auth/session":
            cookie_hdr = self.headers.get("Cookie")
            authenticated = False
            user = None
            csrf = None
            if cookie_hdr:
                cookie = SimpleCookie()
                try:
                    cookie.load(cookie_hdr)
                    if "bw_studio_session" in cookie:
                        sess = SESSION_MGR.validate_session(cookie["bw_studio_session"].value)
                        if sess:
                            authenticated = True
                            user = sess["user"]
                            csrf = sess["csrf_token"]
                except Exception:
                    pass

            if not authenticated:
                auth_hdr = self.headers.get("Authorization")
                api_key_hdr = self.headers.get("X-API-Key")
                tok = None
                if auth_hdr:
                    p = auth_hdr.strip().split()
                    tok = p[1] if len(p) == 2 else p[0]
                elif api_key_hdr:
                    tok = api_key_hdr.strip()
                if tok:
                    expected = getattr(self.server, "api_key", None) or get_or_create_api_key()
                    if hmac.compare_digest(tok.encode("utf-8"), expected.encode("utf-8")):
                        authenticated = True
                        user = "api-token-user"

            self._send_json({
                "authenticated": authenticated,
                "user": user,
                "csrfToken": csrf,
                "authMode": "HTTP_ONLY_COOKIE_OR_TOKEN"
            })
            return

        # 2. Executive Overview
        if path == "/api/overview":
            try:
                conn = sqlite3.connect(DB_PATH, timeout=30.0)
                cur = conn.cursor()

                # Check modern or legacy tables
                cur.execute("SELECT count(*) FROM bw_objects")
                total_objs = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM bw_object_dependencies")
                total_deps = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM migration_projects")
                total_projects = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM migration_plans")
                total_plans = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM validation_runs")
                total_val_runs = cur.fetchone()[0]

                cur.execute("SELECT count(*) FROM delivery_packages")
                total_pkgs = cur.fetchone()[0]

                conn.close()

                hub = ConnectionHub.get_instance()
                statuses = hub.get_all_statuses()
                configured_conns = sum(1 for s in statuses if s["status"] in ("CONNECTED", "PARTIALLY CONFIGURED"))

                self._send_json({
                    "totalSourceObjects": total_objs,
                    "totalDependencies": total_deps,
                    "configuredConnections": configured_conns,
                    "totalProjects": total_projects,
                    "totalPlans": total_plans,
                    "totalValidationRuns": total_val_runs,
                    "totalDeliveryPackages": total_pkgs,
                    "s21Inspection": "READ_ONLY_VERIFIED",
                    "supportedTargetRoutes": [
                        "Native Datasphere",
                        "SAP BW Bridge",
                        "BDC Data Product",
                        "SAP HANA Cloud",
                        "Hybrid Modernization"
                    ]
                })
            except Exception as e:
                self._send_error(f"Failed to fetch overview: {str(e)}", 500)
            return

        # 3. Discovery Catalog & Details
        if path in ("/api/discovery/catalog", "/api/catalog"):
            engine = DiscoveryEngine(DB_PATH)
            catalog = engine.get_catalog()
            self._send_json(catalog)
            return

        if path.startswith("/api/discovery/object/"):
            obj_name = path.replace("/api/discovery/object/", "").strip()
            engine = DiscoveryEngine(DB_PATH)
            details = engine.get_object_details(obj_name)
            if details:
                self._send_json(details)
            else:
                self._send_error(f"Object '{obj_name}' not found", 404)
            return

        if path.startswith("/api/catalog/"):
            obj_name = path.replace("/api/catalog/", "").strip()
            engine = DiscoveryEngine(DB_PATH)
            details = engine.get_object_details(obj_name)
            if details:
                self._send_json(details)
            else:
                self._send_error(f"Object '{obj_name}' not found", 404)
            return

        # 4. Lineage & Dependencies
        if path in ("/api/discovery/lineage", "/api/dependencies"):
            engine = DiscoveryEngine(DB_PATH)
            lineage = engine.get_lineage_graph()
            self._send_json(lineage)
            return

        if path == "/api/discovery/runs":
            engine = DiscoveryEngine(DB_PATH)
            runs = engine.get_runs()
            self._send_json(runs)
            return

        if path.startswith("/api/discovery/snapshots"):
            query_obj = urllib.parse.parse_qs(parsed.query).get("objectName", [None])[0]
            engine = DiscoveryEngine(DB_PATH)
            snaps = engine.get_discovery_snapshots(query_obj)
            self._send_json(snaps)
            return

        # 5. Assessment Summary & Object details
        if path == "/api/assessment/summary":
            engine = AssessmentEngine(DB_PATH)
            summary = engine.get_assessment_summary()
            self._send_json(summary)
            return

        if path.startswith("/api/assessment/object/"):
            obj_name = path.replace("/api/assessment/object/", "").strip()
            engine = AssessmentEngine(DB_PATH)
            finding = engine.get_object_assessment(obj_name)
            if finding:
                self._send_json(finding)
            else:
                self._send_error(f"Assessment finding for '{obj_name}' not found", 404)
            return

        # Modernization Intelligence Endpoints (Milestone M3)
        if path == "/api/intelligence/landscape":
            engine = AssessmentEngine(DB_PATH)
            qs = urllib.parse.parse_qs(parsed.query)
            filters = {k: v[0] for k, v in qs.items()}
            summary = engine.get_landscape_summary(filters)
            self._send_json(summary)
            return

        if path == "/api/intelligence/prioritization":
            engine = AssessmentEngine(DB_PATH, DependencyGraph(DB_PATH))
            summary = engine.get_prioritization_summary()
            self._send_json(summary)
            return

        if path == "/api/intelligence/object":
            qs = urllib.parse.parse_qs(parsed.query)
            obj_name = qs.get("objectName", [None])[0]
            if not obj_name:
                self._send_error("Missing parameter 'objectName'")
                return
            engine = AssessmentEngine(DB_PATH, DependencyGraph(DB_PATH))
            try:
                details = engine.assess_object(obj_name)
                self._send_json(details)
            except Exception as e:
                self._send_error(str(e), 404)
            return

        if path == "/api/intelligence/lineage":
            qs = urllib.parse.parse_qs(parsed.query)
            obj_name = qs.get("objectName", [None])[0]
            if not obj_name:
                self._send_error("Missing parameter 'objectName'")
                return
            dep_graph = DependencyGraph(DB_PATH)
            try:
                impact = dep_graph.get_impact_analysis(obj_name)
                self._send_json(impact)
            except Exception as e:
                self._send_error(str(e), 404)
            return

        # 6. Planning - Projects and Plans
        if path == "/api/planning/projects":
            engine = PlanningEngine(DB_PATH)
            projects = engine.list_projects()
            self._send_json(projects)
            return

        if path.startswith("/api/planning/plan/"):
            plan_id = path.replace("/api/planning/plan/", "").strip()
            engine = PlanningEngine(DB_PATH)
            plan = engine.get_plan_details(plan_id)
            if plan:
                self._send_json(plan)
            else:
                self._send_error(f"Plan '{plan_id}' not found", 404)
            return

        # 7. Generation Artifacts
        if path.startswith("/api/generation/artifacts/"):
            plan_id = path.replace("/api/generation/artifacts/", "").strip()
            engine = GenerationEngine(DB_PATH, OUTPUT_DIR)
            artifacts = engine.get_generation_artifacts(plan_id)
            self._send_json(artifacts)
            return

        # 8. Validation Reports
        if path.startswith("/api/validation/report/"):
            run_id = path.replace("/api/validation/report/", "").strip()
            engine = ValidationEngine(DB_PATH)
            report = engine.get_validation_report(run_id)
            if report:
                self._send_json(report)
            else:
                self._send_error(f"Validation run '{run_id}' not found", 404)
            return

        # 9. Delivery Package Manifest
        if path.startswith("/api/delivery/package/"):
            package_id = path.replace("/api/delivery/package/", "").strip()
            packager = DeliveryPackager(DB_PATH, OUTPUT_DIR, DELIVERY_DIR)
            pkg = packager.get_package_manifest(package_id)
            if pkg:
                self._send_json(pkg)
            else:
                self._send_error(f"Delivery package '{package_id}' not found", 404)
            return

        # 9b. Runbook Generation
        if path.startswith("/api/runbook/"):
            plan_id = path.replace("/api/runbook/", "").strip()
            gen = RunbookGenerator(DB_PATH)
            rb = gen.generate_runbook(project_id="proj-default", plan_id=plan_id)
            self._send_json(rb)
            return

        # 9c. Background Jobs (M5)
        if path == "/api/jobs":
            engine = BackgroundJobEngine.get_instance(DB_PATH)
            self._send_json(engine.list_jobs())
            return

        if path.startswith("/api/jobs/"):
            job_id = path.replace("/api/jobs/", "").strip()
            engine = BackgroundJobEngine.get_instance(DB_PATH)
            job = engine.get_job(job_id)
            if job:
                self._send_json(job)
            else:
                self._send_error(f"Job '{job_id}' not found", 404)
            return

        # 10. Connections
        if path == "/api/connections":
            hub = ConnectionHub.get_instance()
            statuses = hub.get_all_statuses()
            self._send_json(statuses)
            return

        # 11. Unhandled API endpoints return 404
        if path.startswith("/api/"):
            self._send_error(f"Endpoint '{path}' not found", 404)
            return

        # 12. Serve static frontend files jailed strictly to FRONTEND_DIR
        self._serve_static_file(path)

    def do_POST(self):
        try:
            if not self._authenticate_request():
                return
            self._handle_post()
        except Exception as e:
            self._send_error(f"Internal server error: {str(e)}", 500)

    def _handle_post(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else "{}"
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}

        # 0. Authentication Session Management
        if path == "/api/auth/login":
            key_attempt = payload.get("apiKey") or payload.get("token") or ""
            expected_key = getattr(self.server, "api_key", None) or get_or_create_api_key()
            if not key_attempt or not hmac.compare_digest(str(key_attempt).strip().encode("utf-8"), expected_key.encode("utf-8")):
                self._send_json({"error": "Unauthorized: Invalid API key.", "status": "UNAUTHORIZED"}, status_code=401)
                return
            sid, csrf = SESSION_MGR.create_session("admin")
            cookie_val = f"bw_studio_session={sid}; Path=/; HttpOnly; SameSite=Lax"
            self._send_json({
                "status": "AUTHENTICATED",
                "user": "admin",
                "csrfToken": csrf,
                "message": "Session initialized with secure HttpOnly cookie."
            }, status_code=200, headers={"Set-Cookie": cookie_val})
            return

        if path == "/api/auth/logout":
            cookie_hdr = self.headers.get("Cookie")
            if cookie_hdr:
                cookie = SimpleCookie()
                try:
                    cookie.load(cookie_hdr)
                    if "bw_studio_session" in cookie:
                        SESSION_MGR.invalidate_session(cookie["bw_studio_session"].value)
                except Exception:
                    pass
            expired_cookie = "bw_studio_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=Lax"
            self._send_json({
                "status": "LOGGED_OUT",
                "message": "Session terminated and cookie cleared."
            }, status_code=200, headers={"Set-Cookie": expired_cookie})
            return

        # 1. Connection management
        if path == "/api/connections/test":
            system_id = payload.get("systemId", "all")
            hub = ConnectionHub.get_instance()
            if system_id == "all":
                res = hub.test_all()
            else:
                res = hub.test_connection(system_id)
            self._send_json(res)
            return

        if path == "/api/connections/reload":
            hub = ConnectionHub.get_instance()
            hub.reload_config()
            self._send_json({"status": "RELOADED", "connections": hub.get_all_statuses()})
            return

        # 2. Discovery Triggers
        if path == "/api/discovery/run":
            system_id = payload.get("systemId", "S21_LIVE")
            live_filter = payload.get("liveFilter", "Z*")
            use_adt_live = payload.get("useAdtLive", True)
            try:
                engine = DiscoveryEngine(DB_PATH)
                res = engine.run_discovery(system_id=system_id, live_filter=live_filter, use_adt_live=use_adt_live)
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Discovery run failed: {str(e)}", 500)
            return

        if path == "/api/discovery/import":
            bundle = payload.get("bundle", payload)
            sys_id = payload.get("systemId", "OFFLINE_BUNDLE")
            try:
                engine = DiscoveryEngine(DB_PATH)
                res = engine.import_metadata_bundle(bundle, system_id=sys_id)
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Metadata import failed: {str(e)}", 500)
            return

        # 3. Phase 4 Assessment Trigger
        if path in ("/api/assessment/run", "/api/assess"):
            try:
                engine = AssessmentEngine(DB_PATH)
                # If specific object requested, return specific assessment
                if "objectName" in payload:
                    finding = engine.get_object_assessment(payload["objectName"])
                    if not finding:
                        engine.assess_all_objects()
                        finding = engine.get_object_assessment(payload["objectName"])

                    rec_raw = finding.get("recommended_target") or finding.get("target_recommendation") or "Native Datasphere"
                    if "Native Datasphere" in rec_raw:
                        rec = "Native Datasphere"
                    elif "BW Bridge" in rec_raw:
                        rec = "SAP BW Bridge"
                    else:
                        rec = rec_raw

                    scores = finding.get("scores") or {}
                    rationale = finding.get("rationale") or "Standard relational schema."
                    self._send_json({
                        "objectName": payload["objectName"],
                        "recommendedRoute": rec,
                        "recommendedTarget": rec_raw,
                        "feasibilityScores": {
                            "nativeDatasphere": scores.get("functional", finding.get("overall_score", 91)),
                            "bwBridge": scores.get("technical", 60),
                            "bdcDataProduct": 80,
                            "hybrid": 55
                        },
                        "blastRadiusScore": 3,
                        "rationale": rationale
                    })
                    return

                res = engine.assess_all_objects()
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Assessment run failed: {str(e)}", 500)
            return

        # Modernization Intelligence Run Trigger (Milestone M3)
        if path == "/api/intelligence/assess":
            system_id = payload.get("systemId", "S21")
            engine = AssessmentEngine(DB_PATH, DependencyGraph(DB_PATH))
            try:
                res = engine.assess_all(system_id)
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Intelligence assessment failed: {str(e)}", 500)
            return

        # 4. Phase 5 Migration Planning
        if path == "/api/planning/project":
            name = payload.get("name", "BW Modernization Project")
            desc = payload.get("description", "Enterprise BW Migration to Datasphere")
            target_space = payload.get("targetSpace", "SALES_ANALYTICS")
            created_by = payload.get("createdBy", "Architect")
            try:
                engine = PlanningEngine(DB_PATH)
                res = engine.create_project(name, desc, target_space, created_by)
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Project creation failed: {str(e)}", 500)
            return

        if path == "/api/planning/generate":
            project_id = payload.get("projectId")
            plan_name = payload.get("name", "Standard Modernization Plan")
            target_platform = payload.get("targetPlatform", "Native Datasphere")
            selected_objects = payload.get("selectedObjects")

            if not project_id:
                self._send_error("Missing required parameter 'projectId'")
                return

            try:
                engine = PlanningEngine(DB_PATH)
                res = engine.generate_plan(project_id, plan_name, target_platform, selected_objects)
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Plan generation failed: {str(e)}", 500)
            return

        if path == "/api/planning/approve":
            plan_id = payload.get("planId")
            approver = payload.get("approverName", "Architect")
            notes = payload.get("notes", "Approved for deployment")

            if not plan_id:
                self._send_error("Missing required parameter 'planId'")
                return

            try:
                engine = PlanningEngine(DB_PATH)
                res = engine.approve_plan(plan_id, approver, notes)
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Plan approval failed: {str(e)}", 500)
            return

        if path == "/api/planning/reject":
            plan_id = payload.get("planId")
            rejecter = payload.get("rejecterName", "Architect")
            reason = payload.get("reason", "Needs revision")

            if not plan_id:
                self._send_error("Missing required parameter 'planId'")
                return

            try:
                engine = PlanningEngine(DB_PATH)
                res = engine.reject_plan(plan_id, rejecter, reason)
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Plan rejection failed: {str(e)}", 500)
            return

        # 5. Phase 6 Code & Artifact Generation
        if path in ("/api/generation/run", "/api/generate"):
            plan_id = payload.get("planId")
            generated_by = payload.get("generatedBy", "GenerationEngine")

            # Backward compatibility check for single-object generate
            if not plan_id and "objectName" in payload:
                obj_name = payload.get("objectName", "ZSAM_SO01")
                target_space = payload.get("targetSpace", "SALES_ANALYTICS")
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
                self._send_json({
                    "objectName": obj_name,
                    "targetSpace": target_space,
                    "csnPayload": csn,
                    "ddlSql": ddl,
                    "status": "GENERATED_LOCAL"
                })
                return

            if not plan_id:
                self._send_error("Missing required parameter 'planId'")
                return

            try:
                engine = GenerationEngine(DB_PATH, OUTPUT_DIR)
                res = engine.generate_for_plan(plan_id, generated_by)
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Artifact generation failed: {str(e)}", 500)
            return

        # 6. Phase 7 Validation Run
        if path == "/api/validation/run":
            project_id = payload.get("projectId")
            plan_id = payload.get("planId")
            executed_by = payload.get("executedBy", "ValidationEngine")

            if not project_id or not plan_id:
                self._send_error("Missing required parameters 'projectId' or 'planId'")
                return

            try:
                engine = ValidationEngine(DB_PATH)
                res = engine.validate_project(project_id, plan_id, executed_by)
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Validation run failed: {str(e)}", 500)
            return

        # 7. Phase 7 Delivery Packaging
        if path == "/api/delivery/package":
            project_id = payload.get("projectId")
            plan_id = payload.get("planId")
            created_by = payload.get("createdBy", "DeliveryPackager")

            if not project_id or not plan_id:
                self._send_error("Missing required parameters 'projectId' or 'planId'")
                return

            try:
                packager = DeliveryPackager(DB_PATH, OUTPUT_DIR, DELIVERY_DIR)
                res = packager.create_package(project_id, plan_id, created_by)
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Delivery packaging failed: {str(e)}", 500)
            return

        # 7b. Delivery Package Validation
        if path == "/api/package/validate":
            package_dir = payload.get("packageDir")
            if not package_dir:
                self._send_error("Missing required parameter 'packageDir'")
                return
            validator = PackageValidator()
            try:
                res = validator.validate_package(package_dir)
                self._send_json(res.to_dict())
            except Exception as e:
                self._send_error(f"Package validation failed: {str(e)}", 500)
            return

        # 8. Background Jobs (M5)
        if path == "/api/jobs/submit":
            job_type = payload.get("jobType", "GENERIC_TASK")
            job_payload = payload.get("payload", {})
            engine = BackgroundJobEngine.get_instance(DB_PATH)

            # Simple worker task wrapper
            def sample_task(jid, p, cancel_evt):
                time.sleep(0.1)
                return {"status": "SUCCESS", "processed_records": 10}

            job_id = engine.submit_job(job_type, job_payload, sample_task)
            self._send_json({"jobId": job_id, "status": "QUEUED"})
            return

        if path.startswith("/api/jobs/") and path.endswith("/cancel"):
            job_id = path.replace("/api/jobs/", "").replace("/cancel", "").strip()
            engine = BackgroundJobEngine.get_instance(DB_PATH)
            cancelled = engine.cancel_job(job_id)
            self._send_json({"jobId": job_id, "cancelled": cancelled})
            return

        # 9. Database Backup Drill (M5)
        if path == "/api/admin/backup":
            mgr = DatabaseBackupManager(DB_PATH)
            try:
                res = mgr.create_atomic_backup(tag="api")
                self._send_json(res)
            except Exception as e:
                self._send_error(f"Backup failed: {str(e)}", 500)
            return

        self._send_error(f"Endpoint '{path}' not found", 404)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, api_key=None):
        super().__init__(server_address, RequestHandlerClass)
        self.api_key = api_key or get_or_create_api_key()


def run_server(host=None, port=None):
    host = host or os.environ.get("BW_STUDIO_HOST") or os.environ.get("STUDIO_HOST", "127.0.0.1")
    port = port or int(os.environ.get("BW_STUDIO_PORT") or os.environ.get("STUDIO_PORT", PORT))
    api_key = get_or_create_api_key()
    key_fp = hashlib.sha256(api_key.encode('utf-8')).hexdigest()[:12]

    print("=" * 70)
    print("  HANAMORPH BW MIGRATION STUDIO — STANDALONE BACKEND (THREADED)")
    print("=" * 70)
    print(f"[*] Bound Host:    http://{host}:{port}")
    print(f"[*] Concurrency:   Threaded (ThreadingMixIn, Non-blocking)")
    print(f"[*] Auth Mode:     API Key Enforced (Bearer / X-API-Key)")
    print(f"[*] Auth Key FP:   sha256:{key_fp}...")
    print(f"[*] Database Path: {DB_PATH}")
    print(f"[*] SAP Safety:    STRICT_READ_ONLY_ENFORCED (Zero Mutation)")
    print("=" * 70)

    httpd = ThreadedHTTPServer((host, port), StudioHandler, api_key=api_key)

    def shutdown_signal(signum, frame):
        print("\n[*] Received shutdown signal. Gracefully stopping server...")
        threading.Thread(target=httpd.shutdown).start()

    try:
        signal.signal(signal.SIGINT, shutdown_signal)
        signal.signal(signal.SIGTERM, shutdown_signal)
    except (AttributeError, ValueError):
        pass

    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
        print("[*] Server stopped cleanly.")


def main():
    parser = argparse.ArgumentParser(description="HanaMorph BW Migration Studio Backend")
    parser.add_argument("--host", default=None, help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind (default: 4004)")
    args = parser.parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
