# Data Pipeline

## Data Directory Layout

```
./data/
+-- QIP1337269_LMAMRA70L29F839Z.zip    # Each zip contains:
+-- QIP1337270_LMAMRA70L29F839Z.zip    #   - 2 CSVs (VALORI + ZONE)
+-- ...                                 #   - ~7,900 KML files (one per municipality)
+-- QIP1337298_LMAMRA70L29F839Z.zip
```

25 zip files covering 23 semesters from 2010_S2 to 2025_S1, total ~2.4 GB. Some semesters appear in multiple zips (duplicates with identical data -- handled via UNIQUE constraints).

## Zip File Naming

Convention from the Agenzia: `QIP[progressive]_[CodiceFiscale].zip`

The zip filename does NOT encode the semester. The semester is determined from the files inside:
- CSV filenames: `QI_[YYYY][S]_VALORI.csv` where YYYY=year, S=1 or 2
- KML `<Document><name>`: contains `Anno/Semestre YYYY/S`

## Import Flow

The unified import script (`backend/scripts/import_omi.py`) orchestrates the entire pipeline. Run from the `backend/` directory:

```bash
cd backend
python -m scripts.import_omi           # reads DATA_DIR and DATABASE_URL from .env
python -m scripts.import_omi --reset   # drop and recreate all OMI tables first
```

```
discover_and_import_all(DATA_DIR, DATABASE_URL)
    |
    +-- 1. Scan data dir for *.zip files
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
    +-- 4. Check idempotency: skip if semester exists in BOTH omi.zones AND omi.quotations
    |
    +-- 5. Import ZONE CSV first
    |       (builds a lookup dict for KML -> LinkZona resolution)
    |
    +-- 6. Import KML polygons (handles 3 different formats, see below)
    |       Parse each KML with lxml
    |       Build Shapely geometry
    |       Insert into omi.zones via batch INSERT with SAVEPOINTs
    |       Geometry safety: ST_Multi(ST_CollectionExtract(ST_MakeValid(...), 3))
    |
    +-- 7. Import VALORI CSV via PostgreSQL COPY FROM STDIN
    |       Clean data (decimal separators, encoding, types)
    |       Deduplicate on UNIQUE key
    |       Pre-delete existing rows for the semester (safe retry)
    |       Bulk-load via psycopg3 COPY protocol
    |
    +-- 8. Post-import: VACUUM ANALYZE
```

## Semester Detection

From CSV filenames:
```python
# Pattern: QI_[YYYY][S]_VALORI.csv or QI_[YYYY][S]_ZONE.csv
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
2. **Encoding fallback** -- try UTF-8 first, fall back to Latin-1 if decode fails (some older semesters use ISO-8859-1)
3. **Read as `dtype=str`** -- parse all columns as strings initially to avoid float coercion on integer codes
4. **Strip whitespace** -- all string fields get `.str.strip()`
5. **Decimal separators** -- replace comma with period in numeric fields: `str.replace(",", ".")`
6. **Spurious quotes** -- `Zona_Descr` field has wrapping single quotes: strip them
7. **Empty trailing column** -- rows end with `;` creating an extra column; drop it
8. **NaN handling** -- some zones have purchase prices but no rent data; leave as NULL
9. **Stato_prev** -- convert `"P"` to boolean `True` -> `"t"` for COPY (anything else -> `"f"`)
10. **Property type code** -- use pandas `Int64` nullable integer to avoid `20.0` in COPY output
11. **Empty strings** -- replace with `None` so they serialize as `\N` (NULL) in COPY
12. **Tab/newline sanitization** -- replace embedded `\t`, `\n`, `\r` with spaces (would corrupt TSV format)
13. **LinkZona validation** -- must match `^[A-Z]{2}\d{8}$`; drop invalid rows with warning

## Quotation Bulk Loading (COPY Protocol)

The import uses PostgreSQL's `COPY FROM STDIN` protocol via psycopg3 for maximum throughput. This avoids the parameter limits of SQL INSERT (PostgreSQL's 65,535 parameter cap makes large multi-row INSERTs impossible for 150K+ rows).

Steps:
1. Delete any existing rows for the semester (safe re-import on retry)
2. Deduplicate DataFrame on UNIQUE key `(link_zona, semester, property_type_code, conservation_state)`
3. Serialize to TSV in a `StringIO` buffer with `\N` as NULL representation
4. Stream to PostgreSQL via `cursor.copy("COPY ... FROM STDIN")`

```python
buf = io.StringIO()
output.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
buf.seek(0)
with cursor.copy("COPY omi.quotations (...) FROM STDIN") as copy:
    while data := buf.read(8192):
        copy.write(data.encode("utf-8"))
```

## Three KML Formats

The KML structure changed across semesters. The import handles all 3 formats:

### Format 1: Direct LINKZONA (2010_S2, 2013_S2)

Older semesters have `LINKZONA` populated directly in `<Data>` elements. `CODCOM` and `CODZONA` may be absent.

```xml
<Data name="LINKZONA"><value>MI00000290</value></Data>
```

Resolution: use `LINKZONA` directly. Build a reverse index from the ZONE CSV (`link_zona -> zone_info`) to get metadata.

### Format 2: Filename + `<name>` tag (2014_S1)

This transitional semester has `LINKZONA` present but **empty**, and `CODCOM`/`CODZONA` are also missing. The zone code must be extracted from the Placemark `<name>` element.

```xml
<name>ALESSANDRIA - Zona OMI B01</name>
```

Resolution: extract Belfiore code from the KML filename (e.g. `A182.kml` -> `A182`) and zone code via regex `Zona\s+OMI\s+(\S+)`. Then look up `(belfiore_code, zone_code)` in the ZONE CSV.

### Format 3: CODCOM + CODZONA (2014_S2+)

Current format. `LINKZONA` is empty; `CODCOM` and `CODZONA` are populated.

```xml
<Data name="LINKZONA"><value></value></Data>
<Data name="CODCOM"><value>A089</value></Data>
<Data name="CODZONA"><value>R1</value></Data>
```

Resolution: look up `(CODCOM, CODZONA)` in the ZONE CSV to get `LinkZona`.

## KML Geometry Processing

Each KML Placemark contains one or more `<Polygon>` elements (possibly wrapped in `<MultiGeometry>`):

1. Parse `<coordinates>` text: `lng,lat,alt` triplets separated by whitespace
2. Build Shapely `Polygon` objects, ensuring ring closure
3. Combine into a `MultiPolygon`
4. On INSERT, wrap with PostGIS safety functions:
   ```sql
   ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_GeomFromText(:wkt, 4326)), 3))
   ```
   - `ST_MakeValid` fixes self-intersections and other topology errors
   - `ST_CollectionExtract(..., 3)` extracts only Polygon components (discards points/lines)
   - `ST_Multi` ensures the result is always a MultiPolygon (matches column type)

## KML Encoding Handling

Some KMLs (notably Bolzano/South Tyrol municipalities with German characters) contain non-UTF-8 bytes. The parser:

1. Reads the file as raw bytes
2. Attempts `etree.fromstring(raw_bytes)` (lxml auto-detects encoding)
3. On `XMLSyntaxError`, decodes as UTF-8 with `errors="replace"` and re-parses

## Zone Batch Insert with SAVEPOINTs

Zones are inserted in batches of 500 using SAVEPOINTs for error isolation. If one row fails (e.g. invalid geometry), the SAVEPOINT is rolled back and the batch continues without aborting the entire transaction.

```python
for row in batch:
    conn.execute(text("SAVEPOINT sp"))
    try:
        conn.execute(text("INSERT INTO omi.zones ..."), row)
        conn.execute(text("RELEASE SAVEPOINT sp"))
    except Exception:
        conn.execute(text("ROLLBACK TO SAVEPOINT sp"))
```

## Idempotency

- **Semester check**: before importing, check if the semester exists in **both** `omi.zones` AND `omi.quotations`. A semester is considered imported only if it appears in both tables.
- **Quotations**: pre-delete all rows for the semester before COPY (safe retry on failure).
- **Zones**: `ON CONFLICT (link_zona, semester) DO NOTHING` skips duplicates.
- **Duplicate zips**: some semesters appear in multiple zip files; only the first zip is processed.

## Post-Import

After all semesters are loaded:
```sql
VACUUM ANALYZE omi.zones;
VACUUM ANALYZE omi.quotations;
```

This updates query planner statistics and reclaims dead tuple space.

## Production Stats

Full import (23 semesters, 2010_S2 to 2025_S1):
- ~620,000 zone polygons
- ~3,750,000 quotation rows
- Import time: ~45 minutes on Apple Silicon

## Semiannual Update Workflow

Every 6 months when new OMI data is published:

1. Log in to the Agenzia delle Entrate portal with SPID
2. Download the new semester's zip file
3. Drop it into the data directory (configured via `DATA_DIR` in `.env`)
4. Run: `cd backend && python -m scripts.import_omi`
5. The script detects the new semester and imports only new data (existing semesters are skipped)
6. The frontend automatically picks up the new semester via the `/api/semesters` endpoint
