"""Offline integration demo. All polygons are synthetic, never real UNESCO boundaries."""

import argparse
import json
from pathlib import Path

from unesco_boundary.evidence import sha256, write_json
from unesco_boundary.package import build_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    source = root / "synthetic.geojson"
    data = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"name": "Synthetic island / 合成示例"}, "geometry": {
        "type": "MultiPolygon", "coordinates": [
            [[[110, 30], [110.02, 30], [110.02, 30.02], [110, 30.02], [110, 30]],
             [[110.005, 30.005], [110.005, 30.01], [110.01, 30.01], [110.01, 30.005], [110.005, 30.005]]],
            [[[110.03, 30], [110.04, 30], [110.04, 30.01], [110.03, 30.01], [110.03, 30]]]]}}]}
    write_json(source, data)
    review = {"local_id": 1, "unesco_id": 1, "site_name": "Synthetic demo", "reviewer": "offline-demo",
              "reviewed_at": "2026-10-21T00:00:00Z", "source_url": "urn:synthetic:demo", "source_kind": "synthetic",
              "source_sha256": sha256(source.read_bytes()), "status": "review_needed", "scope_note": "Software verification only; unrelated to UNESCO property 1",
              "caveats": ["Invented test geometry, not a heritage boundary"],
              "official_check": {"url": "https://whc.unesco.org/en/list/1/maps/", "outcome": "not_applicable", "note": "Synthetic offline test"}}
    write_json(root / "review.json", review)
    print(json.dumps(build_package(source, root / "review.json", root / "packages"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
