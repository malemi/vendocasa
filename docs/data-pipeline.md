# Data Pipeline

## Data Directory Layout

```
backend/data/                           # DATA_DIR: ./data, relative to backend/
+-- QIP1337269_LMAMRA70L29F839Z.zip    # Each zip contains:
+-- QIP1337270_LMAMRA70L29F839Z.zip    #   - 2 CSVs (VALORI + ZONE)
+-- ...                                 #   - ~7,900 KML files (one per municipality)
+-- QIP1337298_LMAMRA70L29F839Z.zip
```

25 zip files covering 23 semesters from 2010_S2 to 2025_S1, total ~2.4 GB. Some semesters appear in more than one zip. Archives with identical content are imported once; if a semester's archives differ, that semester fails and is not imported (`scripts/import_omi.py`).

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
python -m scripts.import_omi --reset   # empty OMI zones, quotations and completion records first
python -m scripts.validate_semesters   # read-only report on the loaded semesters
```

The script first brings the schema up to date with the Alembic migrations. `--reset` empties `omi.zones`, `omi.quotations` and `omi.semester_import` in one transaction. It never drops the schema, `omi.transactions` or anything in the `app` schema.

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
    +-- 4. Skip semesters recorded complete in omi.semester_import
    |       A semester found in several archives with different contents is not imported
    |
    +-- 5. Parse, before touching the database:
    |       ZONE CSV -> lookup dict for KML -> LinkZona resolution
    |       KML polygons (3 formats, see below) -> zone rows with their source file
    |       VALORI CSV -> cleaned COPY text
    |
    +-- 6. ONE transaction per semester:
    |       advisory lock on the semester
    |       delete the semester's zones, quotations and completion record
    |       insert the zones (each row in a savepoint; any rejected row fails the semester)
    |       COPY the quotations (any error fails the semester)
    |       write the completion record: counts, quotations without a zone, archive SHA-256
    |       A failure rolls everything back; the previous data stays current
    |
    +-- 7. Post-import: VACUUM ANALYZE
```

A failed semester is logged with its reason, and every rejected zone row with its file, zone and error. The script exits with status 1 when any semester failed.

## Completion records

`omi.semester_import` holds one row per complete semester. The API, the agent tools and `/api/semesters` use only these semesters, explicitly requested ones included.

Some zones in the quotation CSVs have no KML perimeter. Their quotations are legitimate and are counted as `quotations_without_zone`, not failed. Migration 0005 backfilled records for the semesters loaded before it existed. A loaded semester passes when it has zones and quotations and every geometry is valid. For those semesters, `quotations_without_zone` also counts zone rows that the old importer lost after an insert error; a re-import from the archive tells the two apart. `scripts/validate_semesters.py` prints the same report read-only, and exits with status 1 when the latest loaded semester fails.

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
4. Write the prepared text to PostgreSQL with one `cursor.copy("COPY ... FROM STDIN")`, inside the semester's transaction

```python
buf = io.StringIO()
output.to_csv(buf, sep="\t", header=False, index=False, na_rep="\\N")
copy_text = buf.getvalue()
with cursor.copy("COPY omi.quotations (...) FROM STDIN") as copy:
    copy.write(copy_text.encode("utf-8"))
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

1. For each `<Polygon>`, the `outerBoundaryIs` ring is the shell and every `innerBoundaryIs` ring is a hole. Coordinates are `lng,lat,alt` triplets; rings are closed when needed.
2. Build one Shapely `Polygon(shell, holes)` per `<Polygon>`.
3. Combine the polygons of the placemark into a `MultiPolygon`.
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

## Zone Insert with Savepoints

Inside the semester's transaction, each zone row is inserted in its own savepoint (`insert_zone_rows`). A failing row is rolled back and recorded, so every rejected row is reported at once. Any rejection then fails, and rolls back, the whole semester.

## Idempotency

- **Semester check**: a semester is imported when it has no completion record.
- **Replacement**: the semester's existing zones, quotations and record are deleted in the same transaction that writes the new ones, so a retry never duplicates.
- **Duplicate zips**: a semester found in several archives is imported only when the archives are byte-identical (same SHA-256).

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
5. The script imports semesters that have no completion record, and skips complete ones
6. The new semester becomes the latest complete one for valuations once its transaction commits
