"""Synthetic OMI archives: zone and quotation CSVs and a KML with a hole.

Shared by the import tests (tests/integration/test_import_publication.py) and
the browser journeys' seed (tests/e2e/seed.py). Zone MI00000001 is a square
with a hole; MI00000002 has two parts; MI00000003 has no perimeter.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

SEMESTER = "2024_S2"

ZONE_CSV = (
    "Zone OMI semestre 2024/2\n"
    "Prov;Comune_ISTAT;Comune_amm;Comune_descrizione;Fascia;Zona;Zona_Descr;LinkZona\n"
    "MI;015146;F205;MILANO;B;B01;'CENTRO CON BUCO';MI00000001\n"
    "MI;015146;F205;MILANO;C;C01;'SEMICENTRO IN DUE PARTI';MI00000002\n"
    "MI;015146;F205;MILANO;D;D01;'ZONA SENZA PERIMETRO';MI00000003\n"
)


def valori_csv(price_scale: int = 1) -> str:
    rows = [
        ("MI", "MI00000001", "20", "Abitazioni civili", "NORMALE", "P", 2100, 2800),
        ("MI", "MI00000002", "20", "Abitazioni civili", "NORMALE", "P", 1500, 1900),
        ("MI", "MI00000003", "20", "Abitazioni civili", "NORMALE", "P", 900, 1200),
    ]
    lines = ["Valori OMI semestre 2024/2",
             "Prov;LinkZona;Cod_Tip;Descr_Tipologia;Stato;Stato_prev;Compr_min;Compr_max;Sup_NL_compr;Loc_min;Loc_max;Sup_NL_loc"]
    for prov, lz, tip, desc, stato, prev, low, high in rows:
        lines.append(f"{prov};{lz};{tip};{desc};{stato};{prev};{low * price_scale};{high * price_scale};L;7;10;L")
    return "\n".join(lines) + "\n"


def kml(extra_placemark: str = "") -> str:
    def placemark(link_zona, polygons):
        return (f"<Placemark><ExtendedData><Data name=\"LINKZONA\"><value>{link_zona}</value></Data>"
                f"</ExtendedData><MultiGeometry>{polygons}</MultiGeometry></Placemark>")

    def polygon(outer, inner=None):
        inner_xml = (f"<innerBoundaryIs><LinearRing><coordinates>{inner}</coordinates></LinearRing>"
                     f"</innerBoundaryIs>") if inner else ""
        return (f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{outer}</coordinates></LinearRing>"
                f"</outerBoundaryIs>{inner_xml}</Polygon>")

    holed = placemark("MI00000001", polygon("9.10,45.40 9.20,45.40 9.20,45.50 9.10,45.50 9.10,45.40",
                                             "9.14,45.44 9.16,45.44 9.16,45.46 9.14,45.46 9.14,45.44"))
    two_parts = placemark("MI00000002", polygon("9.30,45.40 9.33,45.40 9.33,45.43 9.30,45.43 9.30,45.40")
                          + polygon("9.40,45.40 9.42,45.40 9.42,45.42 9.40,45.42 9.40,45.40"))
    return ('<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f"{holed}{two_parts}{extra_placemark}</Document></kml>")


def make_archive(directory: Path, name: str = "omi_2024_2.zip", valori: str | None = None,
                 kml_text: str | None = None) -> Path:
    path = directory / name
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("QI_20242_ZONE.csv", ZONE_CSV)
        z.writestr("QI_20242_VALORI.csv", valori if valori is not None else valori_csv())
        z.writestr("F205.kml", kml_text if kml_text is not None else kml())
    return path
