"use client";
import { useEffect, useRef } from "react";
import useAPI from "../hooks/useAPI";

const COLORS = { Bajo: "#22c55e", Medio: "#eab308", Alto: "#f97316", Crítico: "#ef4444" };

export default function Map({ onSelect }) {
  const { data } = useAPI("/api/municipios");
  const ref = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);

  useEffect(() => {
    if (!data?.features?.length) return;
    import("leaflet/dist/leaflet.css");
    import("leaflet").then((L) => {
      if (!mapRef.current) {
        mapRef.current = L.map(ref.current, { zoomControl: true }).setView([4.5, -74], 6);
        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 18,
          attribution: "© OpenStreetMap",
        }).addTo(mapRef.current);
      }
      if (layerRef.current) mapRef.current.removeLayer(layerRef.current);
      layerRef.current = L.geoJSON(data, {
        style: (f) => ({
          fillColor: COLORS[f.properties.ira_nivel] || "#888",
          weight: 1,
          color: "#333",
          fillOpacity: 0.7,
        }),
        onEachFeature: (f, layer) => {
          layer.bindTooltip(
            `<b>${f.properties.municipio}</b><br/>` +
            `<span style="font-size:11px">Máximo IRA: ${f.properties.ira_nivel} (${f.properties.ira_score?.toFixed(3)}) — ${f.properties.cultivo}</span>`
          );
          layer.on("click", () => onSelect?.({ codigo: f.properties.codigo_municipio, cultivo: f.properties.cultivo }));
        },
      }).addTo(mapRef.current);
    });
    return () => { mapRef.current?.remove(); mapRef.current = null; layerRef.current = null; };
  }, [data, onSelect]);

  return <div ref={ref} className="map-container" />;
}
