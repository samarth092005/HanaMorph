import xml.etree.ElementTree as ET
import re

class ADTDiscoveryAdapter:
    """
    Extracts live SAP BW metadata via authenticated NetWeaver ADT REST interfaces.
    Operates strictly within read-only HTTP GET boundaries.
    """
    def __init__(self, bw_connection_manager):
        self.bw_manager = bw_connection_manager

    def search_objects(self, query: str = "*ZSAM*", max_results: int = 50) -> list:
        endpoint = f"/sap/bc/adt/repository/informationsystem/search?operation=quickSearch&query={query}&maxResults={max_results}"
        res = self.bw_manager.execute_sap_http("GET", endpoint)
        if res["status_code"] != 200:
            raise RuntimeError(f"ADT search failed with HTTP {res['status_code']}")

        root = ET.fromstring(res["data"])
        objects = []
        for ref in root.findall(".//{http://www.sap.com/adt/core}objectReference"):
            name = ref.attrib.get("{http://www.sap.com/adt/core}name", "")
            uri = ref.attrib.get("{http://www.sap.com/adt/core}uri", "")
            otype = ref.attrib.get("{http://www.sap.com/adt/core}type", "")
            pkg = ref.attrib.get("{http://www.sap.com/adt/core}packageName", "$TMP")
            desc = ref.attrib.get("{http://www.sap.com/adt/core}description", "")

            # Group into conceptual BW objects
            objects.append({
                "technical_name": name,
                "uri": uri,
                "adt_type": otype,
                "package": pkg,
                "description": desc,
                "provenance": "LIVE_VERIFIED"
            })
        return objects

    def extract_table_fields(self, table_name: str, adt_uri: str = None) -> list:
        """
        Reads DDIC table source code over ADT and parses field definitions.
        Tries raw ABAP DDL (/source/main) first, then falls back to base endpoint HTML.
        """
        if adt_uri:
            endpoint = adt_uri
        else:
            clean_name = table_name.lower().replace("/", "%2f")
            endpoint = f"/sap/bc/adt/ddic/tables/{clean_name}"

        # Clean endpoint of any query params to construct /source/main URI
        base_path = endpoint.split("?")[0]
        source_main_endpoint = f"{base_path}/source/main"

        # Try /source/main with Accept: text/plain
        try:
            res = self.bw_manager.execute_sap_http("GET", source_main_endpoint, headers={"Accept": "text/plain, */*"})
        except TypeError:
            res = self.bw_manager.execute_sap_http("GET", source_main_endpoint)
        except Exception:
            res = {"status_code": 404, "data": b""}

        if not res or res.get("status_code") != 200:
            try:
                res = self.bw_manager.execute_sap_http("GET", endpoint)
            except Exception:
                return []
            if not res or res.get("status_code") != 200:
                return []

        text_content = res["data"].decode('utf-8', errors='ignore')
        fields = []

        # 1. Try parsing raw ABAP DDL
        pattern_ddl = re.compile(
            r'^\s*(?:(?P<is_key>key)\s+)?'
            r'(?P<name>[a-zA-Z0-9_]+)\s*:\s*'
            r'(?:abap\.)?(?P<type>[a-zA-Z0-9_]+)'
            r'(?:\s*\(\s*(?P<len>[0-9]+)(?:\s*,\s*(?P<scale>[0-9]+))?\s*\))?',
            re.MULTILINE | re.IGNORECASE
        )
        for match in pattern_ddl.finditer(text_content):
            f_name = match.group("name")
            dtype = match.group("type")
            length = match.group("len")
            scale = match.group("scale")
            has_key = match.group("is_key") is not None
            f_name_upper = f_name.upper()
            if f_name_upper in ["MANDT", ".INCLUDE", "RECORDMODE", "DEFINE", "TABLE"]:
                continue
            fields.append({
                "name": f_name_upper,
                "data_type": dtype.upper(),
                "length": int(length) if length else 10,
                "decimals": int(scale) if scale else 0,
                "is_key": 1 if has_key else 0,
                "description": f_name_upper
            })

        if fields:
            return fields

        # 2. Fallback to HTML-formatted table definition
        pattern_html = re.compile(
            r'(?:(?P<is_key><span class="keyword">key</span>)\s+)?'
            r'<span class="identifier">(?P<name>[a-zA-Z0-9_]+)</span>\s*'
            r'<span class="keyword">:</span>\s*'
            r'<span class="identifier">abap</span><span class="keyword">\.</span><span class="identifier">(?P<type>[a-zA-Z0-9_]+)</span>'
            r'(?:\s*<span class="keyword">\(</span>\s*<span class="number">(?P<len>[0-9]+)</span>(?:\s*<span class="keyword">,</span>\s*<span class="number">(?P<scale>[0-9]+)</span>)?\s*<span class="keyword">\)</span>)?',
            re.IGNORECASE
        )
        for match in pattern_html.finditer(text_content):
            f_name = match.group("name")
            dtype = match.group("type")
            length = match.group("len")
            scale = match.group("scale")
            has_key_keyword = match.group("is_key") is not None
            f_name_upper = f_name.upper()
            if f_name_upper in ["MANDT", ".INCLUDE"]:
                continue
            fields.append({
                "name": f_name_upper,
                "data_type": dtype.upper(),
                "length": int(length) if length else 10,
                "decimals": int(scale) if scale else 0,
                "is_key": 1 if has_key_keyword else 0,
                "description": f_name_upper
            })
        return fields
