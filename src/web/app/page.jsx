"use client";
import { useState } from "react";
import Map from "@/app/components/Map";
import Ranking from "@/app/components/Ranking";
import MunicipioCard from "@/app/components/MunicipioCard";
import RiskGuide from "@/app/components/RiskGuide";

export default function Home() {
  const [selected, setSelected] = useState(null);

  return (
    <main>
      <div className="map-hero">
        <Map onSelect={setSelected} />
        <div className="map-intro">
          <p className="map-intro-text">
            El color del mapa muestra el riesgo más alto entre los cultivos del período reciente de cada municipio.
            Haga clic en un municipio o use la tabla de abajo para ver el detalle.
          </p>
        </div>
        {selected && (
          <div className="panel-overlay" onClick={() => setSelected(null)}>
            <div className="panel" onClick={(e) => e.stopPropagation()}>
              <button className="panel-close" onClick={() => setSelected(null)} aria-label="Cerrar ficha">✕</button>
              <MunicipioCard
                key={`${selected.codigo}|${selected.cultivo}|${String(selected.periodo || "").slice(0, 10)}`}
                codigo={selected.codigo}
                cultivo={selected.cultivo}
                periodo={selected.periodo}
              />
            </div>
          </div>
        )}
      </div>
      <div className="ranking-section">
        <RiskGuide />
        <Ranking onSelect={setSelected} selected={selected} />
      </div>
    </main>
  );
}
