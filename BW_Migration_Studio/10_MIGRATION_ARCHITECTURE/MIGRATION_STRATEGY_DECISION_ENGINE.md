# Migration Strategy Decision Engine

## 1. Decision Matrix & Scoring Algorithm
The HanaMorph Assessment Engine evaluates every source BW object against a multi-factor scoring rubric:

$$	ext{Score} = w_1 S_{	ext{structure}} + w_2 S_{	ext{abap}} + w_3 S_{	ext{lineage}} + w_4 S_{	ext{volume}}$$

| Route | Criteria | Score Threshold | Output Action |
|---|---|---|---|
| **Route 1: Native Datasphere** | Standard ADSO, direct formulas, standard measures | $\ge 80$ | Generate Local Table + Analytic Model |
| **Route 2: BW Bridge** | Complex ABAP routines, custom function modules | $\ge 75$ | Generate BW Bridge Shell / Remote specs |
| **Route 3: BDC Data Product** | Certified business content, existing BW/4HANA DPG | $\ge 70$ | Generate Data Product Subscription plan |
| **Route 4: Hybrid / Redesign** | MultiProviders with heterogeneous unions, legacy PSA | N/A | Flag for architectural manual redesign |
