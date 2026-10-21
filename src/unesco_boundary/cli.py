import argparse
import json
import os
import sys
from pathlib import Path

from .evidence import ArchiveClient
from .geometry import validate_collection
from .maps import download_maps
from .package import build_package
from .retrieve import load_sites, probe


def main(argv=None):
    parser = argparse.ArgumentParser(description="UNESCO boundary sources, map documents and reviewed GIS packages")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("probe", "maps"):
        command = commands.add_parser(name)
        command.add_argument("--run", required=True, help="Evidence directory; reuse only to replay the same snapshot")
        command.add_argument("--offline", action="store_true")
        command.add_argument("--user-agent", default=os.environ.get("UNESCO_USER_AGENT"))
        if name == "probe":
            command.add_argument("--input", required=True)
            command.add_argument("--no-osm", action="store_true")
            command.add_argument("--override-verified", action="store_true")
        else:
            command.add_argument("--unesco-id", required=True, type=int)
    package = commands.add_parser("package")
    package.add_argument("--geojson", required=True)
    package.add_argument("--review", required=True)
    package.add_argument("--out-root", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("geojson")
    args = parser.parse_args(argv)
    try:
        if args.command == "package":
            result = build_package(args.geojson, args.review, args.out_root)
        elif args.command == "validate":
            result = validate_collection(json.loads(Path(args.geojson).read_text(encoding="utf-8-sig")))
        else:
            client = ArchiveClient(args.run, args.user_agent, args.offline)
            if args.command == "probe":
                result = probe(load_sites(args.input, args.override_verified), args.run, client, args.no_osm)
                failed = any(r["status"] == "source_error" for r in result)
            else:
                result = download_maps(args.unesco_id, args.run, client)
                failed = any(r["status"] == "document_error" for r in result["documents"])
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2 if failed else 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
