"""Strict WGS84 polygon checks; no silent repairs or invented boundaries."""

import math

from pyproj import Geod
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from shapely.validation import explain_validity

GEOD = Geod(ellps="WGS84")


def checked_geometry(geometry):
    if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Only Polygon or MultiPolygon is supported")
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    if not polygons:
        raise ValueError("Empty polygon")
    for polygon in polygons:
        if not polygon:
            raise ValueError("Empty polygon rings")
        for ring in polygon:
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError("Rings must be explicitly closed with at least four positions")
            for point in ring:
                if len(point) != 2 or not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in point):
                    raise ValueError("Require finite two-dimensional longitude/latitude positions")
                if not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                    raise ValueError("Coordinates outside EPSG:4326 longitude/latitude range")
            if any(abs(a[0] - b[0]) > 180 for a, b in zip(ring, ring[1:])):
                raise ValueError("Split antimeridian-crossing polygons before packaging")
    result = shape(geometry)
    if result.is_empty or not result.is_valid or result.area == 0:
        raise ValueError("Invalid polygon: " + explain_validity(result))
    return result


def area_ha(geometry):
    geom = checked_geometry(geometry)
    polys = [geom] if geom.geom_type == "Polygon" else geom.geoms
    # CCW exterior + CW holes gives the signed ellipsoidal area with holes removed.
    return sum(abs(GEOD.geometry_area_perimeter(orient(p, sign=1))[0]) for p in polys) / 10000


def validate_collection(data):
    if data.get("type") != "FeatureCollection" or not data.get("features"):
        raise ValueError("Require a nonempty FeatureCollection")
    if data.get("crs"):
        raise ValueError("Remove legacy CRS only after explicitly transforming to RFC 7946 WGS84")
    geoms = []
    for feature in data["features"]:
        if feature.get("type") != "Feature":
            raise ValueError("FeatureCollection contains a non-Feature entry")
        geoms.append(checked_geometry(feature.get("geometry")))
    return {"feature_count": len(geoms), "geometry_types": sorted({g.geom_type for g in geoms}),
            "area_ha": sum(area_ha(f["geometry"]) for f in data["features"]),
            "crs": "EPSG:4326 (RFC 7946 longitude, latitude)"}


def explicit_osm_ids(text):
    import re

    result = []
    patterns = [
        (r"(?:\brelation\b|关系)\s*[:/#：]?\s*(\d+)\b", "R"),
        (r"(?:\bway\b|路径)\s*[:/#：]?\s*(\d+)\b", "W"),
    ]
    for pattern, kind in patterns:
        for value in re.findall(pattern, text or "", re.I):
            item = kind + value
            if item not in result:
                result.append(item)
    return result
