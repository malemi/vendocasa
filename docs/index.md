# Documentation Index

| File | Topic |
|------|-------|
| [architecture.md](architecture.md) | System architecture: tech stack, service topology, database schema, request flow |
| [data-sources.md](data-sources.md) | OMI data ecosystem: CSV column schemas, KML structure, LinkZona join key, download procedures from Agenzia delle Entrate |
| [data-pipeline.md](data-pipeline.md) | Import scripts: zip scanning, CSV parsing, KML-to-PostGIS ingestion, semester detection, semiannual update workflow |
| [api.md](api.md) | Backend REST API: all endpoints, request/response schemas, geocoding flow, spatial query details |
| [valuation-methodology.md](valuation-methodology.md) | How address-to-valuation works: geocoding -> zone lookup -> quotation retrieval -> estimate calculation. Limitations and caveats |
| [legal.md](legal.md) | Data licensing analysis: OMI quotations vs declared transaction values, personal use scope, what cannot be done commercially |
| [deployment.md](deployment.md) | Railway deployment: PostGIS template, Docker setup, environment variables, CI/CD, semiannual data refresh |
