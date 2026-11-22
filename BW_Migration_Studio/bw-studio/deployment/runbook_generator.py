"""
HANAMORPH BW Migration & Modernization Studio
Migration Execution Runbook Generator
Milestone M4.3
"""

import json
import os
import time
from typing import Dict, Any, List, Optional

class RunbookGenerator:
    """
    Generates human-readable Markdown and machine-executable JSON runbooks
    guiding deployment of migrated artifacts into SAP Datasphere and SAC.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def generate_runbook(
        self,
        project_id: str,
        plan_id: str,
        space: str = "SALES_ANALYTICS",
        artifacts: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Creates a structured multi-phase execution runbook.
        """
        runbook_id = f"rb-{plan_id}"
        generation_time = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        
        phases = [
            {
                "phase_id": "PHASE_01_PREREQUISITES",
                "name": "Phase 1: Prerequisites & Environment Readiness",
                "estimated_minutes": 15,
                "steps": [
                    {
                        "step_id": "STEP_1_1",
                        "title": "Verify Target Space Provisioning",
                        "command": f"datasphere space show --space {space}",
                        "description": f"Confirm Datasphere space '{space}' is active with sufficient memory quota.",
                        "validation": "Status must be ACTIVE"
                    },
                    {
                        "step_id": "STEP_1_2",
                        "title": "Test SAP BW Source Connection",
                        "command": "datasphere connection test --connection BW_S21_CONNECTION",
                        "description": "Validate network reachability and ODP metadata catalog connectivity.",
                        "validation": "Connection check returns HTTP 200 / Success"
                    },
                    {
                        "step_id": "STEP_1_3",
                        "title": "Validate Currency & Unit Reference Tables",
                        "command": f"datasphere table show --space {space} --table TCURR",
                        "description": "Ensure TCURR and T006 are present in space for currency conversion.",
                        "validation": "Table exists with active status"
                    }
                ]
            },
            {
                "phase_id": "PHASE_02_PHYSICAL_INGESTION",
                "name": "Phase 2: Physical Schema & Ingestion Setup",
                "estimated_minutes": 30,
                "steps": [
                    {
                        "step_id": "STEP_2_1",
                        "title": "Deploy Local Table CSN Definitions",
                        "command": f"datasphere csn import --space {space} --file *.csn.json",
                        "description": "Deploy generated CSN 2.0 Local Table entities.",
                        "validation": "CSN entities created with status DEPLOYED"
                    },
                    {
                        "step_id": "STEP_2_2",
                        "title": "Deploy & Configure Replication Flows",
                        "command": f"datasphere replication-flow import --space {space} --file *_repl_flow.json",
                        "description": "Configure automated delta replication from SAP BW source.",
                        "validation": "Replication Flow status is CONFIGURED"
                    },
                    {
                        "step_id": "STEP_2_3",
                        "title": "Trigger Initial Data Replication Load",
                        "command": f"datasphere replication-flow start --space {space} --load INITIAL",
                        "description": "Initiate initial full data replication batch.",
                        "validation": "Load completes with 0 errors"
                    }
                ]
            },
            {
                "phase_id": "PHASE_03_SEMANTIC_LAYER",
                "name": "Phase 3: Semantic Layer Deployment",
                "estimated_minutes": 25,
                "steps": [
                    {
                        "step_id": "STEP_3_1",
                        "title": "Deploy Transformation & Dimension Views",
                        "command": f"datasphere view deploy --space {space} --file TV_*.sql",
                        "description": "Compile calculated column expressions and business views.",
                        "validation": "Views deployed without syntax errors"
                    },
                    {
                        "step_id": "STEP_3_2",
                        "title": "Deploy Consumption Views & Analytic Models",
                        "command": f"datasphere analytic-model deploy --space {space} --file AM_*.csn.json",
                        "description": "Activate analytic models for multi-dimensional consumption.",
                        "validation": "Analytic Models active and queryable"
                    }
                ]
            },
            {
                "phase_id": "PHASE_04_SAC_CONSUMPTION",
                "name": "Phase 4: SAP Analytics Cloud Integration",
                "estimated_minutes": 20,
                "steps": [
                    {
                        "step_id": "STEP_4_1",
                        "title": "Import SAC Analytical Models",
                        "command": "sac model import --file SAC_*_model.json",
                        "description": "Create analytical datasets in SAP Analytics Cloud.",
                        "validation": "Model imports successfully"
                    },
                    {
                        "step_id": "STEP_4_2",
                        "title": "Verify Input Variables and Hierarchy Prompts",
                        "command": "sac model validate-prompts --model SAC_*",
                        "description": "Confirm variable prompts bind properly to CALDAY/FISCPER.",
                        "validation": "Prompts return expected default selections"
                    }
                ]
            },
            {
                "phase_id": "PHASE_05_RECONCILIATION",
                "name": "Phase 5: Post-Migration Data Reconciliation",
                "estimated_minutes": 30,
                "steps": [
                    {
                        "step_id": "STEP_5_1",
                        "title": "Execute Row Count Reconciliation",
                        "command": "hanamorph reconcile count --source BW_S21 --target DATASPHERE",
                        "description": "Verify source record counts match target Local Tables within 0% discrepancy.",
                        "validation": "Source and target row counts match identically"
                    },
                    {
                        "step_id": "STEP_5_2",
                        "title": "Execute Financial KPI Aggregation Reconciliation",
                        "command": "hanamorph reconcile aggregate --metric NETWR --tolerance 0.0001",
                        "description": "Compare aggregate sums of revenue and quantities between BW and SAC.",
                        "validation": "Delta below tolerance threshold"
                    }
                ]
            }
        ]

        # Generate Markdown version
        md_lines = [
            f"# SAP BW Modernization Execution Runbook",
            f"**Project ID:** `{project_id}`  ",
            f"**Plan ID:** `{plan_id}`  ",
            f"**Runbook ID:** `{runbook_id}`  ",
            f"**Target Space:** `{space}`  ",
            f"**Generated:** {generation_time}  ",
            f"",
            f"---",
            f"",
            f"## Executive Overview",
            f"This runbook outlines the strict sequential execution order for deploying modernized artifacts",
            f"into SAP Datasphere and SAP Analytics Cloud (SAC) with continuous validation checkpoints.",
            f"",
            f"> [!IMPORTANT]",
            f"> Every phase includes explicit verification criteria. Do not proceed to the next phase",
            f"> until all validation checkpoints in the current phase have passed.",
            f""
        ]

        for p in phases:
            md_lines.append(f"### {p['name']} (Est. {p['estimated_minutes']} mins)")
            for s in p["steps"]:
                md_lines.append(f"#### {s['step_id']}: {s['title']}")
                md_lines.append(f"- **Description:** {s['description']}")
                md_lines.append(f"- **Execution Command:**")
                md_lines.append(f"  ```bash\n  {s['command']}\n  ```")
                md_lines.append(f"- **Validation Gate:** `{s['validation']}`")
                md_lines.append("")

        md_text = "\n".join(md_lines)

        return {
            "runbook_id": runbook_id,
            "project_id": project_id,
            "plan_id": plan_id,
            "target_space": space,
            "generated_at": generation_time,
            "phases": phases,
            "markdown_content": md_text
        }
