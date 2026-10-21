# Source review

Prefer WHC property/core geometry, then official national/local vectors. OSM is
a fallback or comparison. Geospatial PDFs can preserve official coordinates;
unreferenced maps require a documented transform. The best source depends on the
property version, component scope and intended use; a successful HTTP request is
not an acceptance decision.

| Check | Evidence to record |
|---|---|
| Identity | UNESCO property ID, full name, boundary revision, component IDs |
| Scope | Property/core versus buffer, proposed extension or administrative area |
| Position | Map overlay and component locations; record a CRS transform if used |
| Geometry | Valid closed Polygon/MultiPolygon, holes, islands and multipart coverage |
| Area | Official field/units/version and geodesic hectares, difference and explanation |
| Coverage | Explicit expected/covered/missing component lists, not just feature count |
| Decision | Source URL, reviewer, date, caveats and rejected alternatives |

WHC layer numbers follow the current endpoint convention;
recheck service metadata if the service changes. The probe rejects reported
transfer-limit truncation; it does not silently accept a first page. Preserve raw
layer-0 attributes instead of choosing the first field whose name contains “area”.
Repeated property totals must not be added as though they were component areas.

An OSM city or protected area can share a name and still be the wrong boundary.
Compare tags, exact object type/ID, map overlap, area and full component coverage.
The CLI retains candidates without scoring a short name fragment into acceptance.
When public Nominatim cannot resolve a candidate, use official sources or a
documented manual Overpass/GIS route. Keep public Nominatim use small and
sequential; sustained batch work needs an appropriate hosted/local service.

Fill `examples/review.template.json` after inspecting the selected source. Use
`python -m unesco_boundary validate PATH` for geometric diagnostics and calculate
the source hash with `python -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('PATH').read_bytes()).hexdigest())"`.
The review timestamp must include a timezone. A `correct` package requires all
five review checks, explicit complete component IDs, official area and a written
comparison. There is no universal area-error threshold: map scale, boundary
revision, rounding and component scope affect what a discrepancy means.

Raw geometry uses longitude/latitude in RFC 7946 WGS84. The checker catches many
coordinate errors, but a small projected coordinate can still look like valid
degrees; inspect source CRS. Antimeridian-crossing rings must be split by a GIS
step first. Area is summed per feature; overlapping features must be resolved or
explained during review. Original GeoJSON attributes are preserved; Shapefile
DBF contains only a compact identity/source/status index.
