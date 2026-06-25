"use client";
import { useEffect, useRef } from "react";
import useAPI from "../hooks/useAPI";

const COLORS = { Bajo: "#22c55e", Medio: "#eab308", Alto: "#f97316", Crítico: "#ef4444" };

export default function Map({ onSelect }) {
  const { data } = useAPI("/api/municipios");
  const ref = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    if (!data?.features?.length || mapRef.current) return;

    import("leaflet/dist/leaflet.css");
    import("leaflet").then((L) => {
      mapRef.current = L.map(ref.current, { zoomControl: true }).setView([4.5, -74], 6);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: "© OpenStreetMap",
      }).addTo(mapRef.current);

      L.geoJSON(data, {
        style: (f) => ({
          fillColor: COLORS[f.properties.ira_nivel] || "#888",
          weight: 1,
          color: "#333",
          fillOpacity: 0.7,
        }),
        onEachFeature: (f, layer) => {
          layer.bindTooltip(
            `<b>${f.properties.municipio}</b><br/>IRA: ${f.properties.ira_nivel} (${f.properties.ira_score?.toFixed(3)})`
          );
          layer.on("click", () => onSelect?.(f.properties.codigo_municipio));
        },
      }).addTo(mapRef.current);
    });

    return () => { mapRef.current?.remove(); mapRef.current = null; };
  }, [data, onSelect]);

  return <div ref={ref} style={{ width: "100%", height: 500, borderRadius: 8 }} />;
}
