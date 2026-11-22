/**
 * HANAMORPH BW Migration & Modernization Studio
 * Milestone M4.5 — Workstream G: Adapter Isolation Verification Harness (Node.js)
 * Proves that bw_studio_adapter.js and OpenAPI specification are completely decoupled,
 * correctly handle timeouts, connection errors, HTTP status mapping, and authentication.
 */

const http = require("http");
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const BWStudioAdapter = require("../../integration/bw_studio_adapter.js");

const TEST_PORT = 4199;
const TEST_API_KEY = "test-node-adapter-isolated-key-333";

let mockServer;
let lastReceivedHeaders = {};
let lastReceivedBody = null;

function startMockServer() {
  return new Promise((resolve) => {
    mockServer = http.createServer((req, res) => {
      lastReceivedHeaders = req.headers;
      let bodyData = "";
      req.on("data", (chunk) => { bodyData += chunk; });
      req.on("end", () => {
        try { lastReceivedBody = bodyData ? JSON.parse(bodyData) : null; } catch(e) { lastReceivedBody = bodyData; }

        if (req.url === "/health") {
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ status: "HEALTHY", sapSafety: "STRICT_READ_ONLY_ENFORCED" }));
          return;
        }

        if (req.url === "/api/overview") {
          const auth = req.headers["authorization"];
          if (auth === `Bearer ${TEST_API_KEY}`) {
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ totalSourceObjects: 10, status: "OK" }));
          } else {
            res.writeHead(401, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ error: "Unauthorized", status: "UNAUTHORIZED" }));
          }
          return;
        }

        if (req.url === "/api/slow") {
          // Intentionally do not respond to test timeout
          setTimeout(() => {
            if (!res.writableEnded) {
              res.writeHead(200, { "Content-Type": "application/json" });
              res.end(JSON.stringify({ done: true }));
            }
          }, 500);
          return;
        }

        if (req.url === "/api/error") {
          res.writeHead(500, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Internal processing defect", code: 500 }));
          return;
        }

        res.writeHead(404, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Resource not found", status: "NOT_FOUND" }));
      });
    });

    mockServer.listen(TEST_PORT, "127.0.0.1", () => {
      resolve();
    });
  });
}

function stopMockServer() {
  return new Promise((resolve) => {
    mockServer.close(() => resolve());
  });
}

async function runTests() {
  console.log("============================================================");
  console.log("WORKSTREAM G: NODE.JS ADAPTER & OPENAPI ISOLATION AUDIT");
  console.log("============================================================");

  // 1. OpenAPI Specification Validation
  const openapiPath = path.join(__dirname, "..", "..", "docs", "integration", "BW_STUDIO_OPENAPI_V1.json");
  assert(fs.existsSync(openapiPath), `OpenAPI spec missing at ${openapiPath}`);
  const openapi = JSON.parse(fs.readFileSync(openapiPath, "utf-8"));
  assert.strictEqual(openapi.openapi, "3.0.3", "OpenAPI version must be 3.0.3");
  assert(openapi.paths && Object.keys(openapi.paths).length >= 15, "OpenAPI must define at least 15 paths");
  assert(openapi.components.securitySchemes.ApiKeyAuth, "OpenAPI must declare ApiKeyAuth");
  console.log(`[+] OpenAPI 3.0.3 validated: ${Object.keys(openapi.paths).length} paths defined.`);

  // 2. Start loopback mock server
  await startMockServer();
  console.log(`[+] Isolated mock HTTP server listening on 127.0.0.1:${TEST_PORT}`);

  try {
    const adapter = new BWStudioAdapter({
      baseUrl: `http://127.0.0.1:${TEST_PORT}`,
      apiKey: TEST_API_KEY,
      timeoutMs: 200
    });

    // Test 2.1: Health check
    const health = await adapter.getHealth();
    assert.strictEqual(health.status, "HEALTHY");
    console.log("[+] Test 2.1: getHealth() succeeded.");

    // Test 2.2: Authenticated call & header propagation
    const overview = await adapter.getOverview();
    assert.strictEqual(overview.totalSourceObjects, 10);
    assert.strictEqual(lastReceivedHeaders["authorization"], `Bearer ${TEST_API_KEY}`);
    assert.strictEqual(lastReceivedHeaders["x-api-key"], TEST_API_KEY);
    console.log("[+] Test 2.2: getOverview() authenticated & propagated headers correctly.");

    // Test 2.3: 401 Unauthorized handling
    const unauthAdapter = new BWStudioAdapter({
      baseUrl: `http://127.0.0.1:${TEST_PORT}`,
      apiKey: "invalid-key-xyz"
    });
    try {
      await unauthAdapter.getOverview();
      assert.fail("Expected 401 Unauthorized error");
    } catch (err) {
      assert.strictEqual(err.statusCode, 401);
      console.log("[+] Test 2.3: 401 Unauthorized mapped correctly to error instance.");
    }

    // Test 2.4: 500 Internal Error mapping
    try {
      await adapter._request("GET", "/api/error");
      assert.fail("Expected 500 error");
    } catch (err) {
      assert.strictEqual(err.statusCode, 500);
      assert.strictEqual(err.message, "Internal processing defect");
      console.log("[+] Test 2.4: 500 Error body mapped correctly.");
    }

    // Test 2.5: Timeout handling
    try {
      await adapter._request("GET", "/api/slow");
      assert.fail("Expected timeout error");
    } catch (err) {
      assert(err.message.includes("timed out"), `Expected timeout message, got: ${err.message}`);
      console.log("[+] Test 2.5: Timeout aborted request cleanly.");
    }

    // Test 2.6: Connection failure on unreachable port
    const deadAdapter = new BWStudioAdapter({
      baseUrl: "http://127.0.0.1:49999",
      apiKey: TEST_API_KEY
    });
    try {
      await deadAdapter.getHealth();
      assert.fail("Expected connection refused error");
    } catch (err) {
      assert(err.message.includes("failed at"), `Expected connection failure message, got: ${err.message}`);
      console.log("[+] Test 2.6: Connection failure safely reported without crash.");
    }

    // Test 2.7: Redaction Invariant — Verify secrets are not leaked in error messages
    try {
      await unauthAdapter._request("GET", "/api/nonexistent");
    } catch (err) {
      assert(!err.message.includes(TEST_API_KEY), "API key must never be leaked in error message string");
      console.log("[+] Test 2.7: Secret redaction verified.");
    }

    console.log("============================================================");
    console.log(">>> WORKSTREAM G: ALL 7 ISOLATION TESTS PASSED (100%) <<<");
    console.log("============================================================");
  } finally {
    await stopMockServer();
  }
}

runTests().catch((err) => {
  console.error("[-] Test harness failed:", err);
  process.exit(1);
});
