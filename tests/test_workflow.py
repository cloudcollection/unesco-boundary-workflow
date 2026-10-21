import copy
import json
from pathlib import Path

import pytest
import shapefile
from pyproj import Geod

from unesco_boundary.cli import main
from unesco_boundary.evidence import ArchiveClient, sha256, write_json
from unesco_boundary.geometry import area_ha, explicit_osm_ids, validate_collection
from unesco_boundary.maps import document_extension, download_maps, map_links
from unesco_boundary.package import build_package
from unesco_boundary.retrieve import load_sites, probe_site, whc_url


@pytest.fixture
def collection():
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"name": "测试岛"}, "geometry": {
        "type": "MultiPolygon", "coordinates": [
            [[[110, 30], [110.02, 30], [110.02, 30.02], [110, 30.02], [110, 30]],
             [[110.005, 30.005], [110.005, 30.01], [110.01, 30.01], [110.01, 30.005], [110.005, 30.005]]],
            [[[110.03, 30], [110.04, 30], [110.04, 30.01], [110.03, 30.01], [110.03, 30]]]]}}]}


@pytest.fixture
def source_review(tmp_path, collection):
    source = tmp_path / "source.geojson"
    write_json(source, collection)
    review = {"local_id": 1, "unesco_id": 1, "site_name": "St. 测试岛", "reviewer": "offline test",
              "reviewed_at": "2026-10-21T00:00:00Z", "source_url": "urn:synthetic:test", "source_kind": "synthetic",
              "source_sha256": sha256(source.read_bytes()), "status": "review_needed", "scope_note": "Synthetic test, not a UNESCO boundary",
              "caveats": ["Synthetic geometry"], "official_check": {"url": whc_url(1, 1), "outcome": "not_applicable", "note": "Offline synthetic test"}}
    path = tmp_path / "review.json"
    write_json(path, review)
    return source, path, review


def archive(run, url, data, content_type="application/json", status=200):
    raw = Path(run) / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    body = data if isinstance(data, bytes) else json.dumps(data).encode()
    key = sha256(url.encode())
    (raw / (key + ".body")).write_bytes(body)
    write_json(raw / (key + ".json"), {"url": url, "final_url": url, "status_code": status, "content_type": content_type,
                                       "retrieved_at": "2026-10-21T00:00:00Z", "sha256": sha256(body), "bytes": len(body)})


def test_multipolygon_holes_unicode_and_dotted_names(tmp_path, source_review):
    source, review, _ = source_review
    result = build_package(source, review, tmp_path / "out")
    folder = Path(result["path"])
    assert (folder / "1_St. 测试岛.geojson").exists()
    with shapefile.Reader(str(folder / "1_St. 测试岛.shp"), encoding="utf-8") as reader:
        assert len(reader.shapes()) == len(reader.records()) == 1
        assert len(reader.shape(0).parts) == 3  # two exteriors, one hole
        assert reader.record(0)["NAME"] == "测试岛"
    checksums = json.loads((folder / "checksums.json").read_text(encoding="utf-8"))
    assert all(sha256((folder / name).read_bytes()) == value for name, value in checksums.items())


def test_review_is_bound_to_source_bytes(tmp_path, source_review):
    source, review, _ = source_review
    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        build_package(source, review, tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_existing_output_is_not_overwritten(tmp_path, source_review):
    source, review, _ = source_review
    result = build_package(source, review, tmp_path / "out")
    with pytest.raises(FileExistsError):
        build_package(source, review, tmp_path / "out")
    assert Path(result["path"]).exists()


def test_incomplete_components_cannot_be_correct(tmp_path, source_review):
    source, path, review = source_review
    review.update({"source_kind": "official_whc", "status": "correct", "expected_components": ["a", "b"], "covered_components": ["a"],
                   "checks": dict.fromkeys(["authority", "property_core", "location", "component_coverage", "area"], True)})
    write_json(path, review)
    with pytest.raises(ValueError, match="component"):
        build_package(source, path, tmp_path / "out")


@pytest.mark.parametrize("kind", ["synthetic", "scale_anchor"])
def test_scale_only_and_synthetic_never_correct(tmp_path, source_review, kind):
    source, path, review = source_review
    review.update(status="correct", source_kind=kind)
    write_json(path, review)
    with pytest.raises(ValueError, match="cannot be marked correct"):
        build_package(source, path, tmp_path / "out")


def test_hole_area_matches_ellipsoidal_reference(collection):
    polygon = collection["features"][0]["geometry"]["coordinates"][0]
    geod = Geod(ellps="WGS84")
    ring_areas = [abs(geod.polygon_area_perimeter(*zip(*ring))[0]) for ring in polygon]
    single = {"type": "Polygon", "coordinates": polygon}
    assert area_ha(single) == pytest.approx((ring_areas[0] - ring_areas[1]) / 10000, rel=1e-10)


@pytest.mark.parametrize("change", ["unclosed", "self_intersection", "not_wgs84", "point", "nan"])
def test_invalid_geometry_rejected(collection, change):
    data = copy.deepcopy(collection)
    geometry = data["features"][0]["geometry"]
    if change == "point":
        data["features"][0]["geometry"] = {"type": "Point", "coordinates": [110, 30]}
    elif change == "unclosed":
        geometry["coordinates"][0][0].pop()
    elif change == "not_wgs84":
        geometry["coordinates"][0][0][1] = [1000000, 2000000]
    elif change == "nan":
        geometry["coordinates"][0][0][1] = [float("nan"), 30]
    else:
        geometry["coordinates"][0] = [[[110, 30], [111, 31], [110, 31], [111, 30], [110, 30]]]
    with pytest.raises(ValueError):
        validate_collection(data)


def test_ids_keep_relation_way_types_and_ignore_other_numbers():
    assert explicit_osm_ids("UNESCO 870, Q123456, 2026; way 123456; relation: 77; https://www.openstreetmap.org/way/123456") == ["R77", "W123456"]
    assert explicit_osm_ids("OSM nearby 123456, lat 30.123456") == []


def test_html_is_not_saved_as_a_map():
    with pytest.raises(ValueError, match="not a recognized"):
        document_extension(b"<!DOCTYPE html><title>Access denied</title>")


def test_map_links_are_official_and_deduplicated():
    html = '<a href="/document/123">Map</a><a href="/document/123#x">Duplicate</a><a href="https://other.example/document/99">Other</a>'
    assert len(map_links(html, "https://whc.unesco.org/en/list/1/maps/")) == 1


def test_offline_archive_integrity_and_missing(tmp_path):
    client = ArchiveClient(tmp_path, offline=True)
    with pytest.raises(FileNotFoundError):
        client.fetch("https://example.org/missing")
    url = "https://example.org/data"
    archive(tmp_path, url, {"ok": True})
    assert client.json(url) == {"ok": True}
    (tmp_path / "raw" / (sha256(url.encode()) + ".body")).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        client.fetch(url)


def test_core_error_is_not_absence_or_osm_permission(tmp_path):
    empty = {"type": "FeatureCollection", "features": []}
    for layer in (0, 2):
        archive(tmp_path, whc_url(1, layer), empty)
    archive(tmp_path, whc_url(1, 1), {"error": {"code": 400, "message": "Bad query"}})
    result = probe_site({"id": 1, "unesco_id": 1, "site_name": "Test"}, tmp_path, ArchiveClient(tmp_path, offline=True))
    assert result["status"] == "source_error"
    assert not result["candidates"]


def test_official_candidate_is_not_auto_accepted(tmp_path, collection):
    for layer in (0, 1, 2):
        archive(tmp_path, whc_url(1, layer), collection if layer == 1 else {"type": "FeatureCollection", "features": []})
    result = probe_site({"id": 1, "unesco_id": 1, "site_name": "Test"}, tmp_path, ArchiveClient(tmp_path, offline=True))
    assert result["status"] == "review_needed"
    assert len(result["candidates"]) == 1


def test_offline_map_download_rejects_html(tmp_path):
    page = "https://whc.unesco.org/en/list/1/maps/"
    doc = "https://whc.unesco.org/document/123"
    archive(tmp_path, page, b'<a href="/document/123">Map</a>', "text/html")
    archive(tmp_path, doc, b"<html>Login</html>", "text/html")
    result = download_maps(1, tmp_path, ArchiveClient(tmp_path, offline=True))
    assert result["documents"][0]["status"] == "document_error"
    assert not list((tmp_path / "maps").rglob("*.jpg"))


def test_input_columns_and_verified_skip(tmp_path):
    source = tmp_path / "sites.csv"
    source.write_text('site_name,unesco_id,id,right or not\nTest,870,615,1\n', encoding="utf-8")
    assert load_sites(source)[0]["skip"] is True
    assert load_sites(source, override=True)[0]["skip"] is False


def test_cli_failure_exit_code(tmp_path):
    assert main(["validate", str(tmp_path / "missing.geojson")]) == 2


def test_complete_review_can_be_exported_correct(tmp_path, source_review):
    source, path, review = source_review
    review.update({"source_kind": "official_whc", "status": "correct", "expected_components": ["a"], "covered_components": ["a"],
                   "official_area_ha": 100, "area_comparison_note": "Synthetic assertion for testing the review gate only",
                   "checks": dict.fromkeys(["authority", "property_core", "location", "component_coverage", "area"], True)})
    write_json(path, review)
    assert Path(build_package(source, path, tmp_path / "out")["path"]).parent.name == "correct"


def test_offline_probe_cli_writes_summary(tmp_path, collection):
    for layer in (0, 1, 2):
        archive(tmp_path, whc_url(1, layer), collection if layer == 1 else {"type": "FeatureCollection", "features": []})
    sites = tmp_path / "sites.csv"
    sites.write_text("id,unesco_id,site_name\n7,1,Offline fixture\n", encoding="utf-8")
    assert main(["probe", "--input", str(sites), "--run", str(tmp_path), "--offline"]) == 0
    summary = json.loads((tmp_path / "retrieval.json").read_text(encoding="utf-8"))
    assert summary["records"][0]["status"] == "review_needed"
    assert (tmp_path / "candidates" / "7" / "whc_layer1.geojson").exists()


def test_offline_valid_pdf_download(tmp_path):
    page = "https://whc.unesco.org/en/list/1/maps/"
    doc = "https://whc.unesco.org/document/123"
    archive(tmp_path, page, b'<a href="/document/123">Map</a>', "text/html")
    archive(tmp_path, doc, b"%PDF-1.7\nSynthetic signature fixture, not a complete PDF", "application/pdf")
    result = download_maps(1, tmp_path, ArchiveClient(tmp_path, offline=True))
    assert result["documents"][0]["status"] == "downloaded_document"
    assert (tmp_path / "maps" / "1" / "123.pdf").exists()
