# SPDX-License-Identifier: Apache-2.0
# Adapted from cloudcollection/unesco-whc-osm-boundary-retriever; see NOTICE.
"""Collect candidates. Acceptance remains an explicit, hash-bound review."""

from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlencode

from .evidence import utc_now, write_json
from .geometry import explicit_osm_ids, validate_collection

WHC = "https://services6.arcgis.com/eMd5K6XXEvJETxfQ/arcgis/rest/services/prd_whc_sites_dossiers_elements_v2_view/FeatureServer"


def load_sites(path, override=False):
    path = Path(path)
    if path.suffix.lower() == ".xlsx":
        import openpyxl
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet = book.active
        values = sheet.iter_rows(values_only=True)
        headers = [str(v).strip() if v is not None else "" for v in next(values)]
        rows = [dict(zip(headers, row)) for row in values]
        book.close()
    elif path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
    else:
        raise ValueError("Input must be CSV or XLSX")
    result, seen = [], set()
    for row in rows:
        if not any(v not in (None, "") for v in row.values()):
            continue
        for field in ("id", "unesco_id", "site_name"):
            if row.get(field) in (None, ""):
                raise ValueError("Missing named input column/value: " + field)
        for field in ("id", "unesco_id"):
            value = float(row[field])
            if value <= 0 or not value.is_integer():
                raise ValueError("Require positive integer " + field)
            row[field] = int(value)
        if row["id"] in seen:
            raise ValueError("Duplicate local ID: " + str(row["id"]))
        seen.add(row["id"])
        row["site_name"] = str(row["site_name"]).strip()
        row["skip"] = str(row.get("right or not", "")).strip() in {"1", "1.0"} and not override
        result.append(row)
    return result


def whc_url(pid, layer):
    return WHC + f"/{layer}/query?" + urlencode({"where": f"property_id={pid}", "outFields": "*", "returnGeometry": "true", "f": "geojson", "outSR": 4326})


def check_fc(data):
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        raise ValueError("WHC did not return a FeatureCollection")
    if data.get("exceededTransferLimit") or data.get("properties", {}).get("exceededTransferLimit"):
        raise ValueError("WHC response truncated; paginate or export explicitly before review")


def probe_site(row, run, client, no_osm=False, max_queries=5):
    pid, rid = row["unesco_id"], row["id"]
    record = {"id": rid, "unesco_id": pid, "site_name": row["site_name"], "generated_at": utc_now(),
              "official_page": f"https://whc.unesco.org/en/list/{pid}/", "maps_page": f"https://whc.unesco.org/en/list/{pid}/maps/",
              "status": "review_needed", "layers": {}, "candidates": [], "errors": []}
    if row.get("skip"):
        record["status"] = "skipped_verified_row"
        return record
    work = Path(run) / "candidates" / str(rid)
    work.mkdir(parents=True, exist_ok=True)
    layers = {}
    for layer in (0, 1, 2):
        url = whc_url(pid, layer)
        try:
            data = client.json(url)
            check_fc(data)
            layers[layer] = data
            write_json(work / f"whc_layer{layer}.geojson", data)
            record["layers"][str(layer)] = {"url": url, "feature_count": len(data["features"])}
        except Exception as exc:
            record["errors"].append({"source": f"whc_layer{layer}", "url": url, "error": str(exc)})
    if 1 not in layers:
        record["status"] = "source_error"
        return record  # An API failure is not evidence that official geometry is absent.
    core = layers[1]
    if core["features"]:
        try:
            validation = validate_collection(core)
            record["candidates"].append({"source_kind": "official_whc", "path": f"candidates/{rid}/whc_layer1.geojson", "url": whc_url(pid, 1), **validation})
            record["note"] = "Official candidate found. Check property identity, core scope, components and area before acceptance."
        except ValueError as exc:
            record["errors"].append({"source": "whc_core_geometry", "error": str(exc)})
            record["status"] = "source_error"
        return record
    if no_osm:
        record["status"] = "official_core_empty"
        return record
    ids = explicit_osm_ids(str(row.get("remarks") or ""))
    queries = [row["site_name"]]
    # Keep exact component attributes for review; avoid guessing area fields or summing repeated totals.
    for feature in layers.get(0, {}).get("features", []):
        props = feature.get("properties") or {}
        for key in ("name", "NAME", "component_name", "name_en"):
            if props.get(key) and props[key] not in queries:
                queries.append(str(props[key]))
    urls = []
    if ids:
        urls.append("https://nominatim.openstreetmap.org/lookup?" + urlencode({"format": "jsonv2", "osm_ids": ",".join(ids), "polygon_geojson": 1, "extratags": 1}))
    for query in queries[:max_queries]:
        urls.append("https://nominatim.openstreetmap.org/search?" + urlencode({"format": "jsonv2", "q": query, "polygon_geojson": 1, "extratags": 1, "limit": 5}))
    seen = set()
    for url in urls:
        try:
            items = client.json(url)
            if not isinstance(items, list):
                raise ValueError("Nominatim response must be a list")
            for item in items:
                key = (item.get("osm_type"), item.get("osm_id"))
                if key in seen or (item.get("geojson") or {}).get("type") not in {"Polygon", "MultiPolygon"}:
                    continue
                seen.add(key)
                fc = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {k: v for k, v in item.items() if k != "geojson"}, "geometry": item["geojson"]}]}
                validation = validate_collection(fc)
                filename = f"osm_{key[0]}_{key[1]}.geojson"
                write_json(work / filename, fc)
                record["candidates"].append({"source_kind": "osm", "path": f"candidates/{rid}/{filename}", "url": url,
                                              "osm_type": key[0], "osm_id": key[1], "name": item.get("display_name"), "tags": item.get("extratags", {}), **validation})
        except Exception as exc:
            record["errors"].append({"source": "osm", "url": url, "error": str(exc)})
    if not record["candidates"]:
        record["status"] = "source_error" if record["errors"] else "no_boundary_found_yet"
    return record


def probe(rows, run, client, no_osm=False):
    records = []
    for row in rows:
        record = probe_site(row, run, client, no_osm)
        write_json(Path(run) / "reviews" / f"{row['id']}_retrieval.json", record)
        records.append(record)
    write_json(Path(run) / "retrieval.json", {"generated_at": utc_now(), "records": records})
    lines = ["# Retrieval", "", "| Local ID | UNESCO ID | Site | Status | Candidates |", "|---|---|---|---|---|"]
    for r in records:
        name = r["site_name"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {r['id']} | {r['unesco_id']} | {name} | {r['status']} | {len(r['candidates'])} |")
    (Path(run) / "retrieval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return records
