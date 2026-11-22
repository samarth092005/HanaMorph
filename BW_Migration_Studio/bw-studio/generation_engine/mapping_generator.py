class MappingSpecGenerator:
    """
    Generates Source-to-Target Field Mapping Specification for migration verification.
    """
    def generate_mapping_markdown(self, source_object: str, target_artifact: str, fields: list) -> str:
        lines = [
            f"# Source-to-Target Field Mapping Specification",
            f"**Source SAP BW Object**: `{source_object}`  ",
            f"**Target Modernized Artifact**: `{target_artifact}`  ",
            f"**Total Fields Mapped**: {len(fields)}  \n",
            "| Source Field | Source Type | Target Field | Target Type | Key? | Semantics | Transformation Rule |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        for f in fields:
            name = f["field_name"]
            stype = f"{f.get('data_type')}({f.get('length')})" if f.get('length') else f.get('data_type', 'CHAR')
            key_str = "YES" if f.get("is_key") else "NO"
            sem = f.get("semantics") or "-"
            rule = "DIRECT_1_TO_1"
            lines.append(f"| `{name}` | `{stype}` | `{name}` | `{stype}` | {key_str} | {sem} | `{rule}` |")

        return "\n".join(lines) + "\n"
