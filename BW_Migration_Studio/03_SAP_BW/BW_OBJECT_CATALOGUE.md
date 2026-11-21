# SAP BW Object Catalogue (S21 Verified Baseline)

## 1. Observed Objects in S21 Client 200
Based on verified RSA1 modeling workspace inspection:

| Object Name | Object Type | Description | Parent InfoArea | Target Modernization Recommendation |
|---|---|---|---|---|
| `ZSAM_SO_IA` | INFOAREA | Sales Order InfoArea | Root | Datasphere Space: `SALES_ANALYTICS` |
| `ZSAM_SO01` | ADSO (Standard) | Sales Order Header & Item ADSO | `ZSAM_SO_IA` | Local Table `LT_SALES_ORDER` + Transformation Flow |
| `ZSAM_SO_CP` | COMPOSITE_PROVIDER | Sales Order CompositeProvider | `ZSAM_SO_IA` | Analytic Model `AM_SALES_ORDER` (Star Join) |
| `ZSAM_MM_PR` | ADSO (Standard) | MM Purchase Requisition | `ZAIS_BW` | Local Table `LT_PURCHASE_REQ` + View `V_PURCHASE_REQ` |
| `ZAIS_BW` | INFOAREA | BW Common Object InfoArea | Root | Datasphere Space: `PROCUREMENT_ANALYTICS` |

## 2. Field Schema Detail: `ZSAM_SO01`
- `SALES_DOC` (CHAR 10, Key): Sales Document Number
- `ITEM_NUM` (NUMC 6, Key): Sales Document Item Number
- `DOC_TYPE` (CHAR 4): Order Type
- `SALES_ORG` (CHAR 4): Sales Organization
- `DISTR_CHAN` (CHAR 2): Distribution Channel
- `DIVISION` (CHAR 2): Division
- `CUSTOMER` (CHAR 10): Sold-to Party
- `MATERIAL` (CHAR 18): Material Number
- `DOC_DATE` (DATS 8): Creation Date
- `NET_VALUE` (CURR 15,2): Net Value in Document Currency
- `CURRENCY` (CUKY 5): Document Currency
- `ORDER_QTY` (QUAN 13,3): Order Quantity
- `SALES_UNIT` (UNIT 3): Sales Unit of Measure
