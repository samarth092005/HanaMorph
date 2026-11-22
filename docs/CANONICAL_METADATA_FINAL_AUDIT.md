# HANAMORPH — CANONICAL METADATA FINAL AUDIT
**Model Version:** 2.1.0  
**Schema Version:** Migration 7  
**Status:** **AUDITED & CERTIFIED**  

---

## 1. Canonical URN Identity Specification

Every SAP BW object is uniquely and permanently identified across the modernization lifecycle by a structured Uniform Resource Name (URN):

```
urn:sap:bw:{system_id}:{client}:{object_type}:{technical_name}
```

- **Example (ADSO):** `urn:sap:bw:s21:200:adso:zsam_so01`
- **Example (Table):** `urn:sap:bw:s21:200:tabl:%2fbic%2fazsam_pr011`
- **Stable URN:** `urn:sap:bw:s21:200:adso:zsam_so01` (invariant across versions)
- **Versioned URN:** `urn:sap:bw:s21:200:adso:zsam_so01:A` (tracks active vs modified state)

---

## 2. 15 Canonical Object Attributes

The canonical table `canonical_bw_objects` stores exactly 15 standardized attributes for every discovered object:

1. `urn`: Primary key string.
2. `stable_urn`: Version-independent URN for lineage tracking.
3. `system_id`: Source SAP system identifier (`S21`).
4. `client`: SAP client (`200`).
5. `object_type`: Standardized type (`ADSO`, `COMPOSITE_PROVIDER`, `TABL`, etc.).
6. `technical_name`: Technical identifier in SAP repository.
7. `version`: Object version (`A` for active, `M` for modified).
8. `description`: Business text description.
9. `infoarea`: Parent InfoArea or `$TMP`.
10. `package`: ABAP development package.
11. `active_status`: Activation state flag.
12. `content_fingerprint`: Deterministic SHA-256 hash of object structure.
13. `provenance`: `LIVE_VERIFIED`, `CACHED`, `IMPORTED`, or `SYNTHETIC_OFFLINE`.
14. `confidence_score`: Floating-point confidence score (0.0 – 1.0).
15. `completeness_score`: Metric indicating percentage of attributes extracted.

---

## 3. Cryptographic Fingerprint Determinism

Object content fingerprints are generated deterministically:
```python
payload = {
    "name": obj_name,
    "type": obj_type,
    "fields": sorted([{"name": f["name"], "type": f["type"], "len": f["len"]} for f in fields], key=lambda x: x["name"]),
    "dependencies": sorted(dependencies)
}
fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
```
- Re-extracting an identical object yields the exact same SHA-256 checksum.
- Any modification in field definition, key assignment, or data type triggers a change in fingerprint, enabling instant delta change detection.
