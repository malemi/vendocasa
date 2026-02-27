# OMI Data Sources

## Overview

The Osservatorio del Mercato Immobiliare (OMI) is part of the Agenzia delle Entrate. It publishes semiannual real estate market data for the entire Italian territory, organized by "OMI zones" -- micro-areas with homogeneous market characteristics.

Two types of data are available:

1. **OMI Quotations** -- expert-assessed EUR/m2 price ranges by zone, property type, and conservation state. Published as downloadable CSVs + KML zone polygons.
2. **Declared Transaction Values** -- actual prices paid in individual sales. Accessible only through a SPID-gated web viewer (no API, no export).

## Quotation CSVs

### VALORI CSV (Quotations)

Filename pattern: `QI_[RequestID]_VALORI.csv` (inside zip files named `QIP[ID]_[CF].zip`)

- Delimiter: semicolon (`;`)
- Encoding: UTF-8 (some older semesters use Latin-1/ISO-8859-1 -- the import script auto-detects)
- Decimal separator: **comma** (`,`) -- e.g. `5,1` means 5.1
- First line: descriptive title (not a header) -- e.g. `Quotazioni Immobiliari : Valori di Mercato - Semestre 2024/2 - elaborazione del 18-MAR-25`
- Second line: column headers
- ~158,000 rows per semester (national)

#### Column Schema (22 columns)

| # | Column | Type | Example | Description |
|---|--------|------|---------|-------------|
| 1 | Area_territoriale | text | NORD-OVEST | Macro-area (skip) |
| 2 | Regione | text | PIEMONTE | Region name (skip) |
| 3 | Prov | text | AL | Province code (2 letters) |
| 4 | Comune_ISTAT | text | 1006003 | ISTAT municipality code |
| 5 | Comune_cat | text | A2AA | Cadastral office code (skip) |
| 6 | Sez | text | (blank) | Cadastral section (usually empty) |
| 7 | Comune_amm | text | A182 | Belfiore code (skip) |
| 8 | Comune_descrizione | text | ALESSANDRIA | Municipality name |
| 9 | Fascia | text | B | Zone band: B/C/D/E/R |
| 10 | Zona | text | B1 | Zone code within municipality |
| 11 | LinkZona | text | AL00000001 | **JOIN KEY** to KML polygons |
| 12 | Cod_Tip | int | 20 | Property type code |
| 13 | Descr_Tipologia | text | Abitazioni civili | Property type description |
| 14 | Stato | text | NORMALE | Conservation state |
| 15 | Stato_prev | text | P | "P" = prevalent state for this zone |
| 16 | Compr_min | decimal | 540 | EUR/m2 purchase price minimum |
| 17 | Compr_max | decimal | 810 | EUR/m2 purchase price maximum |
| 18 | Sup_NL_compr | char | L | Surface type: L=Lorda (gross), N=Netta (net) |
| 19 | Loc_min | decimal | 5,1 | EUR/m2/month rent minimum |
| 20 | Loc_max | decimal | 7,6 | EUR/m2/month rent maximum |
| 21 | Sup_NL_loc | char | L | Surface type for rent |

Note: column 22 is an empty trailing field due to the trailing semicolon in each row.

### ZONE CSV (Zone Descriptions)

Filename pattern: `QI_[RequestID]_ZONE.csv`

- Same format as VALORI (semicolon, comma decimals, title line)
- ~27,000 rows per semester

#### Column Schema (16 columns)

| # | Column | Type | Example | Description |
|---|--------|------|---------|-------------|
| 1 | Area_territoriale | text | ISOLE | Macro-area |
| 2 | Regione | text | SICILIA | Region |
| 3 | Prov | text | AG | Province code |
| 4 | Comune_ISTAT | text | 19084001 | ISTAT code |
| 5 | Comune_cat | text | U2AA | Cadastral office |
| 6 | Sez | text | (blank) | Section |
| 7 | Comune_amm | text | A089 | Belfiore code |
| 8 | Comune_descrizione | text | AGRIGENTO | Municipality name |
| 9 | Fascia | text | B | Zone band |
| 10 | Zona_Descr | text | 'CENTRO URBANO' | Zone description (has spurious quotes) |
| 11 | Zona | text | B1 | Zone code |
| 12 | LinkZona | text | AG00000027 | Join key |
| 13 | Cod_tip_prev | int | 20 | Prevalent property type code |
| 14 | Descr_tip_prev | text | Abitazioni civili | Prevalent type description |
| 15 | Stato_prev | text | N | Prevalent conservation state |
| 16 | Microzona | int | 0 | Microzone number |

## KML Perimeters

Each zip contains ~7,900 KML files, one per municipality (named by Belfiore code, e.g. `A089.kml` = Agrigento).

### Three KML Formats Across Semesters

The KML structure changed over time. The import script handles all 3 variants:

#### Format 1: Direct LINKZONA (2010_S2, 2013_S2)

Older semesters have `LINKZONA` populated directly. `CODCOM` and `CODZONA` may be absent or empty.

```xml
<ExtendedData>
  <Data name="LINKZONA"><value>MI00000290</value></Data>
</ExtendedData>
```

#### Format 2: Neither LINKZONA nor CODCOM/CODZONA (2014_S1)

A transitional semester where `LINKZONA` is present but **empty**, and `CODCOM`/`CODZONA` are also missing. The zone code must be extracted from the `<name>` element:

```xml
<Placemark>
  <name>ALESSANDRIA - Zona OMI B01</name>
  <ExtendedData>
    <Data name="LINKZONA"><value></value></Data>
  </ExtendedData>
  ...
</Placemark>
```

Resolution: Belfiore code from filename (`A182.kml` -> `A182`), zone code via regex on `<name>`.

#### Format 3: CODCOM + CODZONA (2014_S2 onward)

Current format. `LINKZONA` is empty; zone identification is via `CODCOM` (Belfiore code) and `CODZONA`.

```xml
<ExtendedData>
  <Data name="LINKZONA"><value></value></Data>
  <Data name="CODCOM"><value>A089</value></Data>
  <Data name="CODZONA"><value>R1</value></Data>
</ExtendedData>
```

### KML Structure (Format 3 example)

```xml
<Document>
  <name>AGRIGENTO (AG) Anno/Semestre 2025/1 generato il 13/10/2025</name>
  <!-- Styles... -->
  <Placemark>
    <name>AGRIGENTO - Zona OMI R1</name>
    <description><!-- HTML table with zone info --></description>
    <ExtendedData>
      <Data name="LINKZONA"><value></value></Data>
      <Data name="CODCOM"><value>A089</value></Data>
      <Data name="CODZONA"><value>R1</value></Data>
    </ExtendedData>
    <MultiGeometry>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>lng,lat,0 lng,lat,0 ...</coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </MultiGeometry>
  </Placemark>
</Document>
```

Note: KMLs use `<Data>` elements (not `<SimpleData>` as in some KML schemas).

### Semester Detection from KML

The `<Document><name>` element contains: `"AGRIGENTO (AG) Anno/Semestre 2025/1 generato il ..."`

Parse with regex: `Anno/Semestre\s+(\d{4})/(\d)` -> year, semester number.

### Encoding

Most KMLs are UTF-8, but some (notably Bolzano/South Tyrol municipalities with German characters like umlauts) contain non-UTF-8 bytes. The parser handles this with a fallback decode using `errors="replace"`.

## The LinkZona Join Key

Format: `[Province 2-letter code][8-digit zero-padded number]`

Examples:
- `AL00000001` -- Alessandria, zone B1
- `MI00000290` -- Milano, zone B01
- `AG00000027` -- Agrigento, zone B1

This key connects:
- VALORI CSV (quotations) -> `LinkZona` column
- ZONE CSV (descriptions) -> `LinkZona` column
- KML (polygons) -> resolved differently depending on the semester format (see above)

## Property Type Codes

| Code | Description |
|------|-------------|
| 20 | Abitazioni civili |
| 21 | Abitazioni di tipo economico |
| 1 | Ville e villini |
| 2 | Abitazioni signorili |
| 13 | Box |
| 11 | Negozi |
| 6 | Uffici |

## Fascia (Zone Band) Codes

| Code | Description |
|------|-------------|
| B | Centrale (central) |
| C | Semicentrale (semi-central) |
| D | Periferica (peripheral) |
| E | Suburbana (suburban) |
| R | Rurale (rural) |

## Declared Transaction Values

The "Consultazione Valori Immobiliari Dichiarati" service shows actual prices paid in real estate transactions since 2019.

**Access:** Requires SPID authentication at the Agenzia delle Entrate portal.

**Fields visible per transaction:**
- Month/year of the deed
- Transaction type (Residenziale, Commerciale, Produttivo, etc.)
- Declared price (corrispettivo dichiarato, EUR)
- Cadastral category (e.g. A/2, A/3, C/6)
- Consistenza (in vani for cat. A, m2 for cat. C, m3 for cat. B)

**Why it cannot be automated:**
- No API exists
- No CSV/PDF export
- The viewer uses a proprietary SVG map renderer (GEOPOI)
- Minimum 5 transactions per area shown (privacy threshold)

For this tool, transactions are entered manually via a form in the frontend.

## Known Data Quirks

1. **Three KML formats** -- the ExtendedData structure changed across semesters (2010-2013: direct LINKZONA, 2014_S1: extract from filename+name, 2014_S2+: CODCOM+CODZONA). See "Three KML Formats" above.
2. **Encoding issues in Bolzano KMLs** -- some Bolzano/Alto Adige KML files have non-UTF-8 bytes (German characters)
3. **Spurious quotes in Zona_Descr** -- the ZONE CSV wraps zone descriptions in single quotes: `'CENTRO URBANO'`
4. **Decimal separator** -- raw Agenzia CSVs use comma (`,`) as decimal separator
5. **CSV encoding** -- most CSVs are UTF-8, but some older semesters use Latin-1/ISO-8859-1
6. **Trailing semicolons** -- CSV rows end with `;` creating an empty final column
7. **Duplicate zip files** -- some semesters appear in multiple zips; handled via UNIQUE constraints on import
8. **Duplicate CSV rows** -- some semesters (e.g. 2014_S2) have ~46 duplicate quotation rows; handled via deduplication before COPY
9. **Quotations without zones** -- not every LinkZona in the VALORI CSV has a corresponding KML polygon (no FK constraint enforced)
