# HANAMORPH — Mapping Engine Engineering Guide

## 1. PURPOSE & ARCHITECTURE
The Mapping Engine is responsible for translating SAP BW data structures, field definitions, transformation logic, and ABAP expressions into SAP Datasphere CSN entity schemas and ANSI/HANA SQL expressions.

---

## 2. DATA TYPE TRANSLATION MATRIX

The mapping engine normalizes SAP Data Dictionary (DDIC) data types into Core Schema Notation (CSN) primitive types and SAP HANA SQL types:

| SAP BW / DDIC Type | Description | CSN Primitive Type | SAP HANA SQL Type |
|---|---|---|---|
| `CHAR` / `SSTR` | Character String | `cds.String(length)` | `NVARCHAR(length)` |
| `NUMC` | Numeric String | `cds.String(length)` | `NVARCHAR(length)` |
| `DATS` | Date (YYYYMMDD) | `cds.Date` | `DATE` |
| `TIMS` | Time (HHMMSS) | `cds.Time` | `TIME` |
| `DEC` / `CURR` / `QUAN` | Decimal Number | `cds.Decimal(p, s)` | `DECIMAL(p, s)` |
| `FLTP` | Floating Point | `cds.Double` | `DOUBLE` |
| `INT4` | 32-bit Integer | `cds.Integer` | `INTEGER` |
| `INT8` | 64-bit Integer | `cds.Integer64` | `BIGINT` |
| `CUKY` | Currency Key | `cds.String(5)` | `NVARCHAR(5)` |
| `UNIT` | Measurement Unit | `cds.String(3)` | `NVARCHAR(3)` |

---

## 3. ABAP ROUTINE TRANSLATION TO SQL

The engine incorporates a deterministic expression converter for standard SAP BW formulas and common ABAP routines:

### 3.1 String Concatenation & Manipulation
- **ABAP**: `CONCATENATE src-field1 src-field2 INTO result SEPARATED BY space.`
- **Target SQL**: `CONCAT(CONCAT("field1", ' '), "field2")` or `"field1" || ' ' || "field2"`

### 3.2 Conditional Logic
- **ABAP**:
  ```abap
  IF src-amount > 0.
    result = src-amount.
  ELSE.
    result = 0.
  ENDIF.
  ```
- **Target SQL**:
  ```sql
  CASE WHEN "amount" > 0 THEN "amount" ELSE 0 END
  ```

### 3.3 Null Value & Initial Value Handling
- **ABAP**: `IF src-country IS INITIAL. result = 'UNKNOWN'. ENDIF.`
- **Target SQL**: `COALESCE(NULLIF("country", ''), 'UNKNOWN')`

---

## 4. MAPPING DOCUMENT GENERATION
For every converted object, the engine produces a human-auditable markdown mapping document (`<technical_name>_mapping.md`):
- Source object details (TLOGO, package, system).
- Target object specification (CSN entity name, Datasphere space).
- 1:1 field mapping table with types, lengths, keys, and descriptions.
- Complex transformation annotations with original ABAP routine snippets and translated SQL equivalents.
