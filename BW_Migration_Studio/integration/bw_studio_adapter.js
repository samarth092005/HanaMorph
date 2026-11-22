/**
 * HANAMORPH Platform Integration Adapter
 * Decoupled Node.js / JavaScript Client for BW Migration Studio
 * Milestone M6
 *
 * Guarantees zero SQLite database coupling. All interactions occur
 * via loopback HTTP REST contracts against http://127.0.0.1:4004.
 */

const http = require("http");

class BWStudioAdapter {
  /**
   * @param {Object} options
   * @param {string} [options.baseUrl='http://127.0.0.1:4004']
   * @param {string} [options.apiKey='']
   * @param {number} [options.timeoutMs=15000]
   */
  constructor(options = {}) {
    this.baseUrl = options.baseUrl || process.env.BW_STUDIO_URL || "http://127.0.0.1:4004";
    this.apiKey = options.apiKey || process.env.BW_STUDIO_API_KEY || "";
    this.timeoutMs = options.timeoutMs || 15000;
  }

  /**
   * Internal HTTP request dispatcher
   */
  async _request(method, path, body = null) {
    const url = new URL(path, this.baseUrl);
    const postData = body ? JSON.stringify(body) : null;

    const headers = {
      "Accept": "application/json",
      "User-Agent": "HANAMORPH-Platform-Adapter/1.0.0"
    };

    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
      headers["X-API-Key"] = this.apiKey;
    }

    if (postData) {
      headers["Content-Type"] = "application/json";
      headers["Content-Length"] = Buffer.byteLength(postData);
    }

    const options = {
      method: method.toUpperCase(),
      hostname: url.hostname,
      port: url.port || 4004,
      path: url.pathname + url.search,
      headers: headers,
      timeout: this.timeoutMs
    };

    return new Promise((resolve, reject) => {
      const req = http.request(options, (res) => {
        let rawData = "";
        res.setEncoding("utf8");

        res.on("data", (chunk) => {
          rawData += chunk;
        });

        res.on("end", () => {
          try {
            const parsed = rawData ? JSON.parse(rawData) : {};
            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve(parsed);
            } else {
              const err = new Error(parsed.error || `HTTP ${res.statusCode}: ${res.statusMessage}`);
              err.statusCode = res.statusCode;
              err.responseBody = parsed;
              reject(err);
            }
          } catch (e) {
            if (res.statusCode >= 200 && res.statusCode < 300) {
              resolve(rawData);
            } else {
              reject(new Error(`HTTP ${res.statusCode} with unparseable body: ${rawData}`));
            }
          }
        });
      });

      req.on("error", (err) => {
        reject(new Error(`Connection to BW Migration Studio failed at ${this.baseUrl}: ${err.message}`));
      });

      req.on("timeout", () => {
        req.destroy();
        reject(new Error(`Request to BW Migration Studio timed out after ${this.timeoutMs}ms`));
      });

      if (postData) {
        req.write(postData);
      }
      req.end();
    });
  }

  // -------------------------------------------------------------
  // Public Client Methods
  // -------------------------------------------------------------

  async getHealth() {
    return this._request("GET", "/health");
  }

  async getOverview() {
    return this._request("GET", "/api/overview");
  }

  async getCatalog() {
    return this._request("GET", "/api/catalog");
  }

  async getObjectDetails(objectName) {
    return this._request("GET", `/api/discovery/object/${encodeURIComponent(objectName)}`);
  }

  async getLineage() {
    return this._request("GET", "/api/discovery/lineage");
  }

  async getAssessmentSummary() {
    return this._request("GET", "/api/assessment/summary");
  }

  async assessObject(objectName) {
    return this._request("POST", "/api/assess", { objectName });
  }

  async getLandscapeIntelligence() {
    return this._request("GET", "/api/intelligence/landscape");
  }

  async listProjects() {
    return this._request("GET", "/api/planning/projects");
  }

  async createProject(name, description, targetSpace = "SALES_ANALYTICS") {
    return this._request("POST", "/api/planning/project", { name, description, targetSpace });
  }

  async generateArtifacts(planId, space = "SALES_ANALYTICS") {
    return this._request("POST", "/api/generation/run", { planId, targetSpace: space });
  }

  async validateProject(projectId, planId) {
    return this._request("POST", "/api/validation/run", { projectId, planId });
  }

  async createDeliveryPackage(projectId, planId, version = "1.0.0") {
    return this._request("POST", "/api/delivery/package", { projectId, planId, version });
  }

  async getRunbook(planId) {
    return this._request("GET", `/api/runbook/${encodeURIComponent(planId)}`);
  }

  async submitJob(jobType, payload) {
    return this._request("POST", "/api/jobs/submit", { jobType, payload });
  }

  async getJob(jobId) {
    return this._request("GET", `/api/jobs/${encodeURIComponent(jobId)}`);
  }
}

module.exports = BWStudioAdapter;
