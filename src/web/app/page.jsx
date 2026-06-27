"use client";
import { useState } from "react";
import Map from "@/app/components/Map";
import Ranking from "@/app/components/Ranking";
import MunicipioCard from "@/app/components/MunicipioCard";

export default function Home() {
  const [selected, setSelected] = useState(null);

  return (
    <main>
      <div className="map-hero">
        <Map onSelect={setSelected} />
        {selected && (
          <div className="panel-overlay" onClick={() => setSelected(null)}>
            <div className="panel" onClick={(e) => e.stopPropagation()}>
              <button className="panel-close" onClick={() => setSelected(null)}>✕</button>
              <MunicipioCard codigo={selected.codigo} cultivo={selected.cultivo} />
            </div>
          </div>
        )}
      </div>
      <div className="ranking-section">
        <Ranking onSelect={setSelected} />
      </div>
    </main>
  );
}
