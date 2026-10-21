"""Review-gated export with one Shapefile record per GeoJSON feature."""

from __future__ import annotations

import json
import math
import re
import shutil
from datetime import datetime
from pathlib import Path

import shapefile
from pyproj import CRS
from shapely.geometry import shape
from shapely.geometry.polygon import orient

from . import __version__
from .evidence import sha256, utc_now, write_json
from .geometry import validate_collection

KINDS = {"official_whc", "official_vector", "osm", "geospatial_pdf", "digitized_map", "scale_anchor", "synthetic"}
STATUSES = {"correct", "partial", "review_needed"}


def review_check(review, source_bytes):
    for field in ("local_id", "unesco_id", "site_name", "reviewer", "reviewed_at", "source_url", "source_kind", "status", "scope_note", "caveats"):
        if field not in review or review[field] in (None, ""):
            raise ValueError("Review is missing: " + field)
    for field in ("local_id", "unesco_id"):
        if not isinstance(review[field], int) or isinstance(review[field], bool) or review[field] <= 0:
            raise ValueError("Review requires positive integer " + field)
    if review.get("source_sha256") != sha256(source_bytes):
        raise ValueError("Review SHA-256 does not match the exact source file")
    if review["status"] not in STATUSES or review["source_kind"] not in KINDS:
        raise ValueError("Unknown status or source kind")
    if not isinstance(review["caveats"], list):
        raise ValueError("caveats must be a list (use [] if none)")
    if any(isinstance(review[k], str) and review[k].startswith("REPLACE_") for k in review):
        raise ValueError("Complete the review template before packaging")
    stamp = datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("reviewed_at requires an ISO 8601 timezone")
    official = review.get("official_check", {})
    if not all(official.get(k) for k in ("url", "outcome", "note")):
        raise ValueError("Record the WHC core check URL, outcome and note")
    if review["status"] == "correct":
        if review["source_kind"] in {"scale_anchor", "synthetic"}:
            raise ValueError("Scale-only or synthetic data cannot be marked correct")
        checks = review.get("checks", {})
        if not all(checks.get(k) is True for k in ("authority", "property_core", "location", "component_coverage", "area")):
            raise ValueError("correct requires explicit authority/core/location/components/area review")
        expected = review.get("expected_components", [])
        covered = review.get("covered_components", [])
        if not expected or len(expected) != len(set(expected)) or set(expected) != set(covered):
            raise ValueError("correct requires the complete explicit component ID list")
        if not isinstance(review.get("official_area_ha"), (int, float)) or not math.isfinite(review["official_area_ha"]) or review["official_area_ha"] <= 0 or not review.get("area_comparison_note"):
            raise ValueError("correct requires a positive official area and comparison explanation")
        if review["source_kind"] != "official_whc" and official["outcome"] not in {"empty", "unusable"}:
            raise ValueError("Fallback acceptance must explain why WHC core geometry was unusable")
        if review["source_kind"] in {"geospatial_pdf", "digitized_map"} and not review.get("georeference_evidence"):
            raise ValueError("Map-derived correct output requires georeference/residual evidence")


def package_name(review):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", review["site_name"]).strip(" .")
    if not name:
        raise ValueError("Empty site name")
    return f"{review['local_id']}_{name[:100]}"


def base_file(folder, name, suffix):
    # Do not use with_suffix: dots in actual site names are part of the basename.
    return folder / (name + suffix)


def verify_roundtrip(folder, name, source):
    with shapefile.Reader(str(base_file(folder, name, ".shp")), encoding="utf-8") as reader:
        if len(reader) != len(source["features"]) or len(reader.shapes()) != len(source["features"]):
            raise RuntimeError("Shapefile feature/attribute count mismatch")
        for i, feature in enumerate(source["features"]):
            actual = shape(reader.shape(i).__geo_interface__)
            expected = shape(feature["geometry"])
            if not expected.equals(actual):
                raise RuntimeError("Shapefile round-trip changed geometry or holes")
    readback = json.loads(base_file(folder, name, ".geojson").read_text(encoding="utf-8"))
    if readback != source:
        raise RuntimeError("GeoJSON round-trip changed data")


def build_package(source_path, review_path, out_root):
    source_bytes = Path(source_path).read_bytes()
    data = json.loads(source_bytes.decode("utf-8-sig"))
    review = json.loads(Path(review_path).read_text(encoding="utf-8-sig"))
    validation = validate_collection(data)
    review_check(review, source_bytes)
    name = package_name(review)
    parent = Path(out_root) / review["status"]
    final = parent / name
    stage = parent / ("." + name + ".staging")
    if final.exists() or stage.exists():
        raise FileExistsError("Output exists; use a new output root or archive the prior package explicitly")
    parent.mkdir(parents=True, exist_ok=True)
    stage.mkdir()
    try:
        write_json(base_file(stage, name, ".geojson"), data)
        with shapefile.Writer(shp=str(base_file(stage, name, ".shp")),
                              shx=str(base_file(stage, name, ".shx")),
                              dbf=str(base_file(stage, name, ".dbf")),
                              shapeType=shapefile.POLYGON, encoding="utf-8") as writer:
            writer.field("FID", "N", size=10, decimal=0)
            writer.field("LOCAL_ID", "N", size=10, decimal=0)
            writer.field("UNESCO_ID", "N", size=10, decimal=0)
            writer.field("NAME", "C", size=240)
            writer.field("STATUS", "C", size=20)
            writer.field("SOURCE", "C", size=32)
            for index, feature in enumerate(data["features"], 1):
                geom = shape(feature["geometry"])
                polys = [geom] if geom.geom_type == "Polygon" else geom.geoms
                rings = []
                for poly in polys:
                    # ESRI Shapefile: clockwise exterior, counterclockwise holes.
                    poly = orient(poly, sign=-1)
                    rings.append(list(poly.exterior.coords))
                    rings.extend(list(ring.coords) for ring in poly.interiors)
                writer.poly(rings)  # All parts of one feature in exactly one shape.
                label = str((feature.get("properties") or {}).get("name") or review["site_name"])
                label = label.encode("utf-8")[:240].decode("utf-8", errors="ignore")
                writer.record(index, review["local_id"], review["unesco_id"], label, review["status"], review["source_kind"])
        base_file(stage, name, ".prj").write_text(CRS.from_epsg(4326).to_wkt(version="WKT1_ESRI"), encoding="ascii")
        base_file(stage, name, ".cpg").write_text("UTF-8", encoding="ascii")
        write_json(stage / "review.json", review)
        if review.get("official_area_ha"):
            validation["area_difference_percent"] = 100 * (validation["area_ha"] / review["official_area_ha"] - 1)
        validation.update({"checked_at": utc_now(), "tool_version": __version__, "source_sha256": sha256(source_bytes),
                           "status": review["status"], "scope": "Geometry and export checks; scientific acceptance is recorded in review.json"})
        write_json(stage / "validation.json", validation)
        md = [f"# {name}", "", f"- Status: `{review['status']}`", f"- UNESCO property: {review['unesco_id']}",
              f"- Source: {review['source_url']}", f"- Method: {review['source_kind']}", f"- Reviewed by: {review['reviewer']} ({review['reviewed_at']})",
              f"- Scope: {review['scope_note']}", f"- Features: {validation['feature_count']}; area: {validation['area_ha']:.6f} ha (WGS84 ellipsoid)",
              "", "## Evidence", "", "See review.json for source checks, component coverage, official area, rejected candidates and caveats.",
              "See validation.json for geometry checks and SHA-256. Full original attributes remain in GeoJSON; DBF keeps a compact index.", "", "## Caveats", ""]
        md.extend("- " + str(c) for c in review["caveats"])
        if not review["caveats"]:
            md.append("None recorded by the reviewer.")
        base_file(stage, name, ".md").write_text("\n".join(md) + "\n", encoding="utf-8")
        verify_roundtrip(stage, name, data)
        checksums = {p.name: sha256(p.read_bytes()) for p in stage.iterdir() if p.is_file()}
        write_json(stage / "checksums.json", checksums)
        stage.rename(final)
    except Exception:
        # stage is a new, tool-owned sibling; never remove an existing final package.
        if stage.resolve().parent != parent.resolve():
            raise RuntimeError("Refusing cleanup outside staging parent")
        shutil.rmtree(stage)
        raise
    return {"path": str(final), **validation}
