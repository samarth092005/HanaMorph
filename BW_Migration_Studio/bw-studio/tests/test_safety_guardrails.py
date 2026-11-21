import unittest

class SecurityViolationError(Exception):
    pass

def execute_sap_request(method, endpoint):
    allowed_methods = ["GET", "HEAD"]
    if method.upper() not in allowed_methods:
        raise SecurityViolationError(f"Prohibited mutating HTTP verb: {method} to SAP endpoint {endpoint}")
    return {"status": 200, "message": "Read-only operation permitted"}

class TestSafetyGuardrails(unittest.TestCase):
    def test_read_operations_permitted(self):
        res = execute_sap_request("GET", "/sap/opu/odata/IWFND/CATALOGSERVICE;v=2/CatalogCollection")
        self.assertEqual(res["status"], 200)

    def test_mutating_post_blocked(self):
        with self.assertRaises(SecurityViolationError):
            execute_sap_request("POST", "/sap/bc/adt/ddic/structures")

    def test_mutating_delete_blocked(self):
        with self.assertRaises(SecurityViolationError):
            execute_sap_request("DELETE", "/sap/bc/adt/repository/nodestructure")

    def test_transport_request_creation_blocked(self):
        with self.assertRaises(SecurityViolationError):
            execute_sap_request("PUT", "/sap/bc/adt/cts/transports")

if __name__ == "__main__":
    unittest.main()
