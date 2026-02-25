import { MapContainer as LeafletMap, TileLayer, Marker, useMap } from "react-leaflet";
import { useEffect } from "react";
import type { Coordinates, ZoneGeoJSON } from "../../types";
import { ZoneLayer } from "./ZoneLayer";

interface MapViewProps {
  center?: Coordinates;
  zones?: ZoneGeoJSON;
}

function FlyToPoint({ coords }: { coords: Coordinates }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([coords.lat, coords.lng], 15, { duration: 1.5 });
  }, [coords.lat, coords.lng, map]);
  return null;
}

export function MapView({ center, zones }: MapViewProps) {
  // Default center: Italy
  const defaultCenter: [number, number] = [42.0, 12.5];
  const defaultZoom = 6;

  return (
    <LeafletMap
      center={defaultCenter}
      zoom={defaultZoom}
      style={{ width: "100%", height: "100%" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {zones && <ZoneLayer data={zones} />}
      {center && (
        <>
          <FlyToPoint coords={center} />
          <Marker position={[center.lat, center.lng]} />
        </>
      )}
    </LeafletMap>
  );
}
