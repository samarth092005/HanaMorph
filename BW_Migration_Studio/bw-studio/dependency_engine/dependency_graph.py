"""
HANAMORPH BW Migration & Modernization Studio
Dependency Graph & Cycle Analysis Engine
Milestone M1.6
"""

import sqlite3
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple, Optional, Any

class DependencyGraph:
    """
    Builds a directed dependency graph of SAP BW objects.
    Implements:
    - Tarjan's Strongly Connected Components (SCC) for exact cycle identification.
    - Classification of Hard ETL vs. Soft Lookup dependencies.
    - Strict preservation of all original dependency edges.
    - Deterministic cycle classification (Self-loop, Lookup-induced, Mutual ETL).
    - Flagging genuine cyclic migration dependencies for manual architectural redesign.
    - Kahn's topological sort for wave sequencing.
    """
    HARD_DEPENDENCY_TYPES = {
        "EXTRACTS_INTO",
        "PART_PROVIDER",
        "REPORTING_PROVIDER",
        "DATA_FLOW",
        "TRFN_RULE",
        "PRIMARY_DATA_FLOW",
        "UNION_ELEMENT",
        "JOIN_ELEMENT"
    }

    SOFT_DEPENDENCY_TYPES = {
        "LOOKUP_ROUTINE",
        "MASTER_DATA_READ",
        "SEMANTIC_LINK",
        "SOFT_LOOKUP",
        "EXTERNAL_TRIGGER"
    }

    def __init__(self, db_path: str):
        self.db_path = db_path

    def load_edges_from_db(self, selected_objects: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Loads all dependency edges from bw_object_dependencies or canonical_dependencies,
        preserving original edges completely.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Check if canonical_dependencies exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='canonical_dependencies'")
        has_canonical = cur.fetchone() is not None

        edges = []
        if has_canonical:
            cur.execute("SELECT source_urn, target_urn, dependency_type, is_hard_dependency, mapping_details FROM canonical_dependencies")
            for src, dst, dep_type, is_hard, mapping in cur.fetchall():
                if selected_objects and (src not in selected_objects and dst not in selected_objects):
                    continue
                edges.append({
                    "source": src,
                    "target": dst,
                    "dependency_type": dep_type.upper(),
                    "is_hard": bool(is_hard),
                    "mapping_details": mapping or ""
                })

        # Also load from legacy bw_object_dependencies for complete backward compatibility
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bw_object_dependencies'")
        if cur.fetchone():
            cur.execute("SELECT source_object, dependent_object, dependency_type, mapping_details FROM bw_object_dependencies")
            for src, dst, dep_type, mapping in cur.fetchall():
                if selected_objects and (src not in selected_objects and dst not in selected_objects):
                    continue
                dep_type_upper = dep_type.upper()
                is_hard = dep_type_upper in self.HARD_DEPENDENCY_TYPES or "LOOKUP" not in dep_type_upper
                edges.append({
                    "source": src,
                    "target": dst,
                    "dependency_type": dep_type_upper,
                    "is_hard": is_hard,
                    "mapping_details": mapping or ""
                })

        conn.close()
        return edges

    def find_strongly_connected_components(
        self,
        adj: Dict[str, List[str]],
        all_nodes: Set[str]
    ) -> List[List[str]]:
        """
        Executes Tarjan's Strongly Connected Components (SCC) algorithm.
        Returns all maximal SCCs in linear time O(|V| + |E|).
        """
        index = 0
        indices: Dict[str, int] = {}
        lowlink: Dict[str, int] = {}
        on_stack: Dict[str, bool] = {n: False for n in all_nodes}
        stack: List[str] = []
        sccs: List[List[str]] = []

        def strongconnect(v: str):
            nonlocal index
            indices[v] = index
            lowlink[v] = index
            index += 1
            stack.append(v)
            on_stack[v] = True

            for w in adj.get(v, []):
                if w not in indices:
                    # Successor w has not yet been visited; recurse on it
                    strongconnect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif on_stack.get(w, False):
                    # Successor w is in stack and hence in the current SCC
                    lowlink[v] = min(lowlink[v], indices[w])

            # If v is a root node, pop the stack and generate an SCC
            if lowlink[v] == indices[v]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    scc.append(w)
                    if w == v:
                        break
                sccs.append(scc)

        for node in sorted(all_nodes):
            if node not in indices:
                strongconnect(node)

        return sccs

    def analyze_dependencies(
        self,
        selected_objects: Optional[List[str]] = None,
        custom_edges: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Performs full dependency analysis:
        1. Preserves all raw edges.
        2. Classifies edges into hard ETL and soft lookup dependencies.
        3. Runs Tarjan's SCC to detect cycles.
        4. Classifies cycle types (Self-loop, Lookup-induced, Mutual ETL).
        5. Performs topological sequencing respecting hard dependencies.
        6. Flags genuine circular dependencies for manual redesign.
        """
        raw_edges = custom_edges if custom_edges is not None else self.load_edges_from_db(selected_objects)

        all_nodes = set()
        adj_full = defaultdict(list)
        adj_hard = defaultdict(list)
        edge_map = defaultdict(list)

        for edge in raw_edges:
            src = edge["source"]
            dst = edge["target"]
            dep_type = edge.get("dependency_type", "DATA_FLOW").upper()
            is_hard = edge.get("is_hard", dep_type in self.HARD_DEPENDENCY_TYPES)

            all_nodes.add(src)
            all_nodes.add(dst)
            adj_full[src].append(dst)
            edge_map[(src, dst)].append(edge)

            if is_hard:
                adj_hard[src].append(dst)

        # Detect SCCs on full graph
        sccs = self.find_strongly_connected_components(adj_full, all_nodes)
        
        # Identify non-trivial cyclical SCCs
        cyclic_sccs = []
        for scc in sccs:
            if len(scc) > 1:
                cyclic_sccs.append(scc)
            elif len(scc) == 1:
                # Check for self-loop
                node = scc[0]
                if node in adj_full.get(node, []):
                    cyclic_sccs.append(scc)

        # Classify each cyclical SCC
        cycle_reports = []
        sequencing_exceptions = []
        has_unresolvable_cycle = False

        for scc in cyclic_sccs:
            scc_set = set(scc)
            scc_edges = []
            for u in scc:
                for v in adj_full.get(u, []):
                    if v in scc_set:
                        scc_edges.extend(edge_map.get((u, v), []))

            # Determine cycle category
            if len(scc) == 1:
                cycle_type = "TYPE_1_SELF_LOOP"
                resolution = "Bypass self-referential edge in sequencing; retain in-memory state."
                requires_redesign = False
            else:
                # Check if cycle contains soft lookup dependencies
                soft_edges_in_cycle = [e for e in scc_edges if not e.get("is_hard", True)]
                hard_edges_in_cycle = [e for e in scc_edges if e.get("is_hard", True)]

                if soft_edges_in_cycle:
                    cycle_type = "TYPE_2_LOOKUP_INDUCED"
                    resolution = "Decoupled soft lookup edge for topological wave sequencing. Requires runtime late-binding or two-pass execution."
                    requires_redesign = False
                    for se in soft_edges_in_cycle:
                        sequencing_exceptions.append({
                            "source": se["source"],
                            "target": se["target"],
                            "dependency_type": se["dependency_type"],
                            "rationale": "Soft routine lookup decoupled from primary ETL staging sequence."
                        })
                else:
                    cycle_type = "TYPE_3_MUTUAL_ETL"
                    resolution = "HARD RE-ENGINEERING REQUIRED. Mutual ETL feed cannot be topologically sequenced. Requires architect restructuring."
                    requires_redesign = True
                    has_unresolvable_cycle = True

            cycle_reports.append({
                "nodes": sorted(scc),
                "cycle_type": cycle_type,
                "edges_involved": scc_edges,
                "resolution_strategy": resolution,
                "manual_redesign_required": requires_redesign
            })

        # Compute Topological Sort on Hard Dependency DAG
        in_degree_hard = defaultdict(int)
        for n in all_nodes:
            in_degree_hard[n] = 0
        for src in adj_hard:
            for dst in adj_hard[src]:
                in_degree_hard[dst] += 1

        queue = deque([n for n in all_nodes if in_degree_hard[n] == 0])
        topological_order = []

        while queue:
            curr = queue.popleft()
            topological_order.append(curr)
            for neighbor in adj_hard.get(curr, []):
                in_degree_hard[neighbor] -= 1
                if in_degree_hard[neighbor] == 0:
                    queue.append(neighbor)

        # If hard dependencies still form cycles, append remaining nodes with warning
        if len(topological_order) < len(all_nodes):
            remaining = sorted(all_nodes - set(topological_order))
            topological_order.extend(remaining)

        return {
            "all_nodes": sorted(all_nodes),
            "total_nodes": len(all_nodes),
            "total_edges": len(raw_edges),
            "preserved_edges": raw_edges,
            "has_cycles": len(cyclic_sccs) > 0,
            "has_unresolvable_cycles": has_unresolvable_cycle,
            "strongly_connected_components": sccs,
            "cyclic_sccs_count": len(cyclic_sccs),
            "cycle_reports": cycle_reports,
            "sequencing_exceptions": sequencing_exceptions,
            "topological_sequence": topological_order
        }

    # Backward-compatibility adapter for legacy tests
    def get_topological_order(self, selected_objects: Optional[List[str]] = None) -> Dict[str, Any]:
        analysis = self.analyze_dependencies(selected_objects)
        return {
            "sequence": analysis["topological_sequence"],
            "has_cycle": analysis["has_cycles"],
            "cycles": [item["nodes"] for item in analysis["cycle_reports"]]
        }

    def get_upstream_lineage(self, target_node: str, max_depth: int = 10) -> List[Dict[str, Any]]:
        """
        Traverses backwards from target_node to find all upstream data sources and feeding providers.
        """
        edges = self.load_edges_from_db()
        parent_map = defaultdict(list)
        for e in edges:
            parent_map[e["target"]].append(e)

        visited = set()
        queue = deque([(target_node, 0)])
        lineage = []

        while queue:
            curr, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for e in parent_map.get(curr, []):
                src = e["source"]
                if src not in visited:
                    visited.add(src)
                    lineage.append({
                        "node": src,
                        "dependency_type": e["dependency_type"],
                        "depth": depth + 1,
                        "feeds_into": curr
                    })
                    queue.append((src, depth + 1))
        return sorted(lineage, key=lambda x: x["depth"])

    def get_downstream_lineage(self, source_node: str, max_depth: int = 10) -> List[Dict[str, Any]]:
        """
        Traverses forward from source_node to find all downstream consumers, views, and queries.
        """
        edges = self.load_edges_from_db()
        child_map = defaultdict(list)
        for e in edges:
            child_map[e["source"]].append(e)

        visited = set()
        queue = deque([(source_node, 0)])
        lineage = []

        while queue:
            curr, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for e in child_map.get(curr, []):
                dst = e["target"]
                if dst not in visited:
                    visited.add(dst)
                    lineage.append({
                        "node": dst,
                        "dependency_type": e["dependency_type"],
                        "depth": depth + 1,
                        "fed_by": curr
                    })
                    queue.append((dst, depth + 1))
        return sorted(lineage, key=lambda x: x["depth"])

    def get_missing_dependencies(self, known_nodes: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
        """
        Detects missing dependencies: edges referencing sources or targets not present in known_nodes catalog.
        """
        if known_nodes is None:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("SELECT technical_name FROM bw_objects")
            known_nodes = {row[0] for row in cur.fetchall()}
            conn.close()

        edges = self.load_edges_from_db()
        missing = []
        seen = set()

        for e in edges:
            src = e["source"]
            dst = e["target"]
            if src not in known_nodes and src not in seen:
                seen.add(src)
                missing.append({
                    "missing_node": src,
                    "referenced_by": dst,
                    "direction": "UPSTREAM_SOURCE",
                    "dependency_type": e["dependency_type"]
                })
            if dst not in known_nodes and dst not in seen:
                seen.add(dst)
                missing.append({
                    "missing_node": dst,
                    "referenced_by": src,
                    "direction": "DOWNSTREAM_CONSUMER",
                    "dependency_type": e["dependency_type"]
                })
        return missing

    def get_impact_analysis(self, object_name: str) -> Dict[str, Any]:
        """
        Computes the complete blast radius of altering or migrating object_name.
        """
        downstream = self.get_downstream_lineage(object_name)
        upstream = self.get_upstream_lineage(object_name)

        affected_consumers = [item["node"] for item in downstream]
        direct_consumers = [item["node"] for item in downstream if item["depth"] == 1]
        transitive_consumers = [item["node"] for item in downstream if item["depth"] > 1]

        # Calculate blast radius risk tier
        if len(affected_consumers) >= 5 or any("Q" in c or "COMPOSITE" in c for c in affected_consumers):
            blast_radius = "HIGH"
        elif len(affected_consumers) >= 1:
            blast_radius = "MEDIUM"
        else:
            blast_radius = "LOW"

        return {
            "target_object": object_name,
            "blast_radius_tier": blast_radius,
            "total_downstream_consumers": len(affected_consumers),
            "direct_consumers": direct_consumers,
            "transitive_consumers": transitive_consumers,
            "total_upstream_providers": len(upstream),
            "downstream_details": downstream,
            "upstream_details": upstream
        }
