# Official maps to reviewed geometry

The `maps` command only downloads documents linked from the official maps page.
It recognizes file signatures and keeps HTML/error responses in the raw archive.
It neither identifies the right boundary legend nor converts PDFs to polygons.

1. Establish the map date/version, official provenance, page number and exact
   property/core legend symbol. Separate buffers and proposed extensions.
2. Inspect geospatial-PDF metadata (`VP`, `Measure`, `LPTS`, `GPTS`, `WKT`,
   `LGIDict`). Extract vector linework before raster masking when possible.
3. Test coordinate orientation, including page-height Y flips. Verify against
   component positions and map labels. Keep curve IDs and transform parameters.
4. Without an embedded transform, use graticule/ticks or well-spread GCPs in
   QGIS. Save the GCP table, CRS, model, residuals and overlay. Use enough points
   for the chosen model and independent check points; fitting residuals alone
   do not establish positional accuracy.
5. Trace only visible target linework. For color masks, record ROI, thresholds,
   masks, overlays, rejected masks and any manual changes. Do not tune a mask
   solely to reproduce the published area or invent missing boundary segments.
6. Check component coverage and area before exporting EPSG:4326 GeoJSON. Keep
   the original PDF/image and all process files in the run directory.

Scale bar + a WHC point gives an approximate placement, not a full georeference.
Its status remains `review_needed`; the exporter prevents `scale_anchor` from
entering `correct`. A geospatial transform or residual-tested control solution
still needs visual/scope checks. Unclear symbols or missing components justify
`review_needed`, `partial`, or no output. A point buffer is never a substitute.

Record map URL and checksum, page/legend, transform and control evidence,
component assignments, measured area, official reference and caveats in review
JSON. For `geospatial_pdf` or `digitized_map` marked `correct`, include a
`georeference_evidence` field pointing to the preserved calibration/residual
files. The exporter checks that this evidence is declared; the reviewer checks it.
