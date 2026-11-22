# HANAMORPH BW Migration & Modernization Studio
# Milestone M1.2: Canonical Metadata Model & URN Specification

**Document Reference:** `BW-MIG-M1-CANONICAL`  
**Status:** Implemented & Verified (7/7 Tests Passing)  
**Target Studio:** `BW_Migration_Studio/bw-studio/models/canonical_model.py`  
**Classification:** SAP Enterprise Modernization Engineering Deliverable  
**Date:** November 21, 2026  

---

## 1. Overview & Verification

Milestone M1.2 implements the unified **Canonical Metadata Model and URN Identity Engine**, providing a standardized, collision-proof representation for SAP BW metadata across multi-client, namespaced, and versioned SAP environments.

### Core Architectural Guarantees:
1. **Collision-Proof URNs:** Unambiguously namespaces objects across system IDs, 3-digit zero-padded SAP clients, object types, URL-encoded partner/customer namespaces, and lifecycle versions.
2. **Deterministic Content Fingerprinting:** Generates SHA-256 digests strictly over normalized structural/semantic content, guaranteeing that changes in field metadata are detected even if extraction timestamps remain identical.
3. **Lossless Semantic Typing:** Preserves ABAP data dictionary types, lengths, decimal precision, primary keys, aggregation types, currency/unit linkages (`0CURRENCY`, `0UNIT`), and compounding parents.
4. **Provenance & Confidence Boundaries:** Restricts confidence and completeness scores to $[0.0, 1.0]$ and tracks origin metadata (`LIVE_VERIFIED`, `OFFLINE_FIXTURE`, `ADT_EXTRACTED`).

---

## 2. Canonical URN Grammar & Normalization Rules

The canonical URN grammar is defined as:
$$\mathbf{URN} = \mathbf{urn:sap:bw:}\langle \text{system\_id} \rangle \mathbf{:}\langle \text{client} \rangle \mathbf{:}\langle \text{object\_type} \rangle \mathbf{:}\langle \text{escaped\_name} \rangle [\mathbf{:}\langle \text{version} \rangle]$$

### 2.1 Normalization Invariants
- **`system_id`:** Lowercased and whitespace-trimmed (e.g., `S21` $\rightarrow$ `s21`, `P01` $\rightarrow$ `p01`).
- **`client`:** Zero-padded to 3 numeric digits (e.g., `1` $\rightarrow$ `001`, `20` $\rightarrow$ `020`, `200` $\rightarrow$ `200`). Non-numeric clients are preserved trimmed.
- **`object_type`:** Lowercased and mapped to canonical codes (`adso`, `hcpr`, `iobj`, `trfn`, `dtpa`, `elem`, `isrc`, `osrc`).
- **`escaped_name`:** Slashes and special characters in SAP customer/partner namespaces are URL percent-encoded (e.g., `/COMPANY/SALES_01` $\rightarrow$ `%2FCOMPANY%2FSALES_01`, `/BI0/0CUSTOMER` $\rightarrow$ `%2FBI0%2F0CUSTOMER`).
- **`version`:** Uppercased lifecycle indicator (`A` = Active, `M` = Revised, `D` = Decommissioned, `T` = Transport). Defaults to `A`.

### 2.2 Stable vs. Versioned Identity
- **Versioned URN:** Uniquely addresses an exact snapshot version:  
  `urn:sap:bw:s21:200:adso:%2FCOMPANY%2FSALES_01:A`
- **Stable URN:** Identifies the conceptual entity across lifecycle transitions:  
  `urn:sap:bw:s21:200:adso:%2FCOMPANY%2FSALES_01`

---

## 3. Deterministic SHA-256 Content Fingerprint

The content fingerprint is calculated by sorting dictionary keys, serializing to a compact JSON string without whitespace separators (`("," , ":")`), and hashing via SHA-256:

$$\text{Fingerprint} = \text{SHA256}\Big(\text{JSON}_{\text{sorted}}\big(\text{system}, \text{client}, \text{type}, \text{name}, \text{version}, \text{fields}_{\text{sorted}}, \text{dependencies}_{\text{sorted}}\big)\Big)$$

### Verified Test Evidence:
1. **Timestamp Invariance:** Two objects with identical fields and properties but extraction timestamps hours apart produce bit-for-bit identical fingerprints (`test_content_fingerprint_deterministic_and_timestamp_agnostic`).
2. **Mutation Detection:** Mutating a single field attribute (e.g., field length from 15 to 17) with the exact same timestamp instantly produces a differing fingerprint (`test_content_fingerprint_detects_mutation_with_same_timestamp`).
