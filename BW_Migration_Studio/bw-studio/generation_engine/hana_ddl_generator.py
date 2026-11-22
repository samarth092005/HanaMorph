class HANASQLGenerator:
    """
    Generates SAP HANA Cloud Column Table DDL and SQL Views.
    """
    HANA_TYPE_MAP = {
        "CHAR": "NVARCHAR",
        "NUMC": "NVARCHAR",
        "DATS": "DATE",
        "TIMS": "TIME",
        "CURR": "DECIMAL",
        "QUAN": "DECIMAL",
        "DEC": "DECIMAL",
        "INT4": "INTEGER",
        "INT2": "SMALLINT",
        "CUKY": "NVARCHAR",
        "UNIT": "NVARCHAR"
    }

    def generate_column_table_ddl(self, schema_or_space: str, table_name: str, fields: list) -> str:
        col_defs = []
        pk_fields = []

        for f in fields:
            f_name = f["field_name"]
            raw_type = f.get("data_type", "CHAR").upper()
            hdb_type = self.HANA_TYPE_MAP.get(raw_type, "NVARCHAR")
            length = f.get("length", 10)
            decimals = f.get("decimals", 0)

            if hdb_type == "NVARCHAR":
                type_str = f"NVARCHAR({length})"
            elif hdb_type == "DECIMAL":
                type_str = f"DECIMAL({length},{decimals})"
            else:
                type_str = hdb_type

            is_key = f.get("is_key")
            null_str = "NOT NULL" if is_key else ""
            col_defs.append(f'    "{f_name}" {type_str} {null_str}'.strip())

            if is_key:
                pk_fields.append(f'"{f_name}"')

        pk_clause = f',\n    PRIMARY KEY ({", ".join(pk_fields)})' if pk_fields else ""
        cols_joined = ",\n".join(col_defs)

        return f'CREATE COLUMN TABLE "{schema_or_space}"."{table_name}" (\n{cols_joined}{pk_clause}\n);'

    def generate_sql_view_ddl(self, schema_or_space: str, view_name: str, base_table: str, fields: list) -> str:
        col_list = ",\n".join([f'    "{f["field_name"]}"' for f in fields])
        return f'CREATE VIEW "{schema_or_space}"."{view_name}" AS\nSELECT\n{col_list}\nFROM "{schema_or_space}"."{base_table}";'
