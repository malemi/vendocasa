"""KML zone geometry (scripts/import_omi_zones.py): holes stay holes, parts stay parts."""

from __future__ import annotations

from pathlib import Path

from shapely.geometry import Point

from scripts.import_omi_zones import parse_kml_placemarks

KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
  <Placemark>
    <name>ZONA CON BUCO</name>
    <ExtendedData><Data name="LINKZONA"><value>MI00000001</value></Data></ExtendedData>
    <Polygon>
      <outerBoundaryIs><LinearRing><coordinates>0,0,0 10,0,0 10,10,0 0,10,0 0,0,0</coordinates></LinearRing></outerBoundaryIs>
      <innerBoundaryIs><LinearRing><coordinates>4,4,0 6,4,0 6,6,0 4,6,0 4,4,0</coordinates></LinearRing></innerBoundaryIs>
    </Polygon>
  </Placemark>
  <Placemark>
    <name>ZONA IN DUE PARTI</name>
    <ExtendedData><Data name="LINKZONA"><value>MI00000002</value></Data></ExtendedData>
    <MultiGeometry>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>20,0 23,0 23,3 20,3</coordinates></LinearRing></outerBoundaryIs></Polygon>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>30,0 32,0 32,2 30,2 30,0</coordinates></LinearRing></outerBoundaryIs></Polygon>
    </MultiGeometry>
  </Placemark>
</Document></kml>
"""


def _zones(tmp_path: Path) -> dict[str, object]:
    path = tmp_path / "F205.kml"
    path.write_text(KML, encoding="utf-8")
    return {z["link_zona"]: z["geometry"] for z in parse_kml_placemarks(str(path))}


def test_an_inner_boundary_is_a_hole(tmp_path):
    zone = _zones(tmp_path)["MI00000001"]
    assert len(zone.geoms) == 1
    assert zone.area == 100 - 4
    assert not zone.contains(Point(5, 5))  # inside the hole
    assert zone.contains(Point(1, 1))


def test_several_polygons_are_one_multipart_zone(tmp_path):
    zone = _zones(tmp_path)["MI00000002"]
    assert len(zone.geoms) == 2
    assert zone.area == 9 + 4  # the open ring is closed when parsed
    assert zone.contains(Point(21.5, 1.5)) and zone.contains(Point(31, 1))
