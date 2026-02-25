# Data Pipeline

## Data Directory Layout

```
./data/
+-- QIP1337269_LMAMRA70L29F839Z.zip    # Each zip contains:
+-- QIP1337270_LMAMRA70L29F839Z.zip    #   - 2 CSVs (VALORI + ZONE)
+-- ...                                 #   - ~7,900 KML files (one per municipality)
+-- QIP1337298_LMAMRA70L29F839Z.zip
```

24 zip files covering semesters from 2013_S2 to 2025_S1, total ~2.4 GB.

## Zip File Naming

Convention from the Agenzia: `QIP[progressive]_[CodiceFiscale].zip`

The zip filename does NOT encode the semester. The semester is determined from the files inside:
- CSV filenames: `QI_[YYYY][S]_VALORI.csv` where YYYY=year, S=1 or 2
- KML `<Document><name>`: contains `Anno/Semestre YYYY/S`

## Import Flow

The unified import script (`backend/scripts/import_omi.py`) orchestrates the entire pipeline:

```
discover_and_import_all("./data/", DATABASE_URL)
    |
    +-- 1. Scan ./data/ for *.zip files
    |
    +-- 2. For each zip:
    |       Extract to temp directory
    |       Identify files by pattern:
    |         *VALORI*.csv  -> quotation data
    |         *ZONE*.csv    -> zone descriptions
    |         *.kml         -> zone polygons
    |
    +-- 3. Parse semester from CSV filename
    |       Pattern: QI_[YYYY][S]_VALORI.csv
    |       Result: "YYYY_S1" or "YYYY_S2"
    |
    +-- 4. Import ZONE CSVs first
    |       (needed to build LinkZona lookup for KMLs)
    |
    +-- 5. Import KML polygons
    |       Parse each KML with lxml
    |       Extract CODCOM + CODZONA per Placemark
    |       Look up LinkZona from ZONE CSV data
    |       Build geometry from coordinates
    |       Insert into omi.zones
    |
    +-- 6. Import VALORI CSVs
    |       Clean data (decimal separators, whitespace, quotes)
    |       Map columns to DB schema
    |       Insert into omi.quotations
    |
    +-- 7. Post-import: VACUUM ANALYZE
```

## Semester Detection

From CSV filenames:
```python
# Pattern: QI_[RequestID]_[YYYY][S]_VALORI.csv
# Example: QI_20242_VALORI.csv -> 2024, S2 -> "2024_S2"
match = re.search(r'(\d{4})([12])_(?:VALORI|ZONE)', filename, re.IGNORECASE)
semester = f"{match.group(1)}_S{match.group(2)}"
```

Note: The `RequestID` part can look like a year+semester (e.g. `20242`), but it IS the year+semester encoding. `20242` = year 2024, semester 2.

From KML Document name:
```python
# Pattern: "AGRIGENTO (AG) Anno/Semestre 2025/1 generato il ..."
match = re.search(r'Anno/Semestre\s+(\d{4})/(\d)', doc_name)
semester = f"{match.group(1)}_S{match.group(2)}"
```

## CSV Cleaning Steps

1. **Skip title line** -- first line is descriptive text, not headers. Use `skiprows=1` with pandas
2. **Strip whitespace** -- all string fields get `.str.strip()`
3. **Decimal separators** -- replace comma with period in numeric fields: `str.replace(",", ".")`
4. **Spurious quotes** -- `Zona_Descr` field has wrapping single quotes: strip them
5. **Empty trailing column** -- rows end with `;` creating an extra column; ignore it
6. **NaN handling** -- some zones have purchase prices but no rent data; leave as NULL
7. **Stato_prev** -- convert `"P"` to boolean `True`, anything else to `False`
8. **LinkZona validation** -- must match `^[A-Z]{2}\d{8}$`; warn on invalid values

## KML Import Process

Each KML file is one municipality. Processing:

1. Parse with `lxml.etree` (GeoPandas/Fiona cannot reliably extract ExtendedData from these KMLs)
2. For each `<Placemark>`:
   - Extract `CODCOM` and `CODZONA` from `<Data>` elements
   - Parse coordinates from `<Polygon>` or `<MultiGeometry>`
   - Build Shapely geometry
3. Construct `link_zona` by looking up the ZONE CSV where `Comune_amm == CODCOM` and `Zona == CODZONA`
4. Write to PostGIS via GeoAlchemy2 or raw `ST_GeomFromText`

**Fallback for missing LinkZona:** If a KML zone has no match in the ZONE CSV, construct a synthetic key from `province_code + CODZONA` for internal use, and log a warning.

## Deduplication

UNIQUE constraints handle duplicates:
- `omi.zones`: `UNIQUE(link_zona, semester)` -- same zone in same semester is skipped
- `omi.quotations`: duplicate rows are caught by the foreign key + combination of fields

The import uses `ON CONFLICT DO NOTHING` (or pandas `if_exists="append"` with try/except on IntegrityError) to skip existing data.

## Post-Import

After bulk import:
```sql
VACUUM ANALYZE omi.zones;
VACUUM ANALYZE omi.quotations;
```

This updates query planner statistics and reclaims dead tuple space.

## Semiannual Update Workflow

Every 6 months when new OMI data is published:

1. Log in to the Agenzia delle Entrate portal with SPID
2. Download the new semester's zip file
3. Drop it into `./data/`
4. Run: `python -m backend.scripts.import_omi ./data/ $DATABASE_URL`
5. The script detects the new semester and imports only new data (existing semesters are skipped via UNIQUE constraints)
6. The frontend automatically picks up the new semester via the `/api/semesters` endpoint
