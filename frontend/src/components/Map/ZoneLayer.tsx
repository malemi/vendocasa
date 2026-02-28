import { GeoJSON } from "react-leaflet";
import type { Layer, PathOptions } from "leaflet";
import type { ZoneGeoJSON } from "../../types";

interface ZoneLayerProps {
  data: ZoneGeoJSON;
}

function priceToColor(priceMin: number | null, priceMax: number | null): string {
  if (priceMin == null || priceMax == null) return "#cbd5e0";
  const avg = (priceMin + priceMax) / 2;
  // Gradient: green (low) -> yellow (mid) -> red (high)
  // Range: 500 - 8000 EUR/m2
  const t = Math.min(1, Math.max(0, (avg - 500) / 7500));
  if (t < 0.5) {
    // green to yellow
    const r = Math.round(t * 2 * 255);
    return `rgb(${r}, 200, 50)`;
  } else {
    // yellow to red
    const g = Math.round((1 - (t - 0.5) * 2) * 200);
    return `rgb(255, ${g}, 50)`;
  }
}

export function ZoneLayer({ data }: ZoneLayerProps) {
  const style = (feature: GeoJSON.Feature | undefined): PathOptions => {
    const props = feature?.properties;
    const color = priceToColor(props?.price_min, props?.price_max);
    return {
      fillColor: color,
      fillOpacity: 0.4,
      color: "#4a5568",
      weight: 1,
      opacity: 0.6,
    };
  };

  const onEachFeature = (feature: GeoJSON.Feature, layer: Layer) => {
    if (feature.properties) {
      layer.bindPopup(() => {
        const div = document.createElement("div");
        const props = feature.properties!;
        const fasciaLabel: Record<string, string> = {
          B: "Centrale",
          C: "Semicentrale",
          D: "Periferica",
          E: "Suburbana",
          R: "Rurale",
        };
        const fascia = props.fascia ? fasciaLabel[props.fascia] || props.fascia : "";
        div.innerHTML = `
          <div style="font-size:0.85rem;line-height:1.5">
            <strong>${props.municipality || ""} - ${props.zone_code || ""}</strong>
            ${fascia ? `<span> (${fascia})</span>` : ""}
            <br/>
            ${props.description ? `<span style="color:#718096;font-size:0.75rem">${props.description}</span>` : ""}
            ${
              props.price_min != null && props.price_max != null
                ? `<div style="margin-top:4px;font-weight:600">${props.price_min.toLocaleString("it-IT")} - ${props.price_max.toLocaleString("it-IT")} EUR/m2</div>`
                : ""
            }
          </div>
        `;
        return div;
      });
    }
  };

  return (
    <GeoJSON
      key={JSON.stringify(data).length}
      data={data}
      style={style}
      onEachFeature={onEachFeature}
    />
  );
}
