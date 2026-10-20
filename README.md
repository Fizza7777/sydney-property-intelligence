# Sydney Property Intelligence
Standalone static GitHub Pages dashboard. Completely independent of FC27. No GitHub Actions workflows, secrets, scheduled tasks, shared database, or shared APIs.

## Deploy
GitHub repository Settings → Pages → Build and deployment → Deploy from a branch → main / (root) → Save.

## Data accuracy
The map loads genuine NSW Spatial Services suburb polygons from https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme_multiCRS/FeatureServer/2 .
Data layer data/metrics.json initially contains []: **no property pricing figures are invented.**

NSW Valuer General **assessed land values** are distinct from sold house transactions; bedrooms are not attributes of land valuations. Public sale records may not include bedroom counts. Bedroom-filtered sales medians should remain unavailable until independently licensed, sourced transactions with eligible bedroom counts are imported.

To import a suitably licensed CSV: `python scripts/aggregate.py source.csv --output data/metrics.json`. Required fields: suburb, metric (land/house), year, value, source; optional bedrooms (house only). Verify eligibility, NSW sales treatment, missing values, duplicates and suburb naming before import. This minimal script is an ingestion starting point, **not** a turnkey government ETL.

Map geographic bounding rectangle approximates Greater Sydney; regional assignments are approximate geographic buckets based on suburb polygon centres, not government statistical regions. The service returns up to 2,000 features per request. If a future request is truncated, implement paginated querying.

## Limitations
Price filters exclude suburbs without verified prices, clearly indicating missing coverage. Historical trend chart awaits multiple years. All figures require documented provenance. Users must obey source license terms.

## Security
No secrets in this public repository. No persistent tracking, GitHub Actions, or dynamic backend. Browser loads external Leaflet, CARTO map tiles, and NSW Spatial Services.
