"use client";
import { useState } from "react";
import RiskBadge from "./RiskBadge";

const LEVELS = [
  {
    nivel: "Bajo",
    range: "0 a 0,25",
    meaning: "Las condiciones se ven estables. Conviene seguir atento, pero no hay señal de alerta fuerte.",
  },
  {
    nivel: "Medio",
    range: "0,25 a 0,50",
    meaning: "Hay señales de cuidado. Revise clima, cultivo y costos para no llevarse sorpresas.",
  },
  {
    nivel: "Alto",
    range: "0,50 a 0,75",
    meaning: "El riesgo es importante. Priorice este municipio o cultivo y prepare medidas de prevención.",
  },
  {
    nivel: "Crítico",
    range: "0,75 a 1",
    meaning: "Alerta alta. Es momento de actuar con urgencia y pedir apoyo técnico si es posible.",
  },
];

const PARTS = [
  {
    code: "SPC",
    name: "Peligro climático",
    weight: "50%",
    plain: "¿Qué tan duro está el clima ahora frente a lo normal de ese municipio? (lluvia, calor, sequía).",
  },
  {
    code: "SEP",
    name: "Exposición productiva",
    weight: "30%",
    plain: "¿Cuánto depende el municipio de ese cultivo? Si es muy importante, un mal clima afecta más.",
  },
  {
    code: "SVE",
    name: "Vulnerabilidad económica",
    weight: "20%",
    plain: "¿Qué tan difícil es resistir un golpe? Mira precios de insumos y condiciones sociales del territorio.",
  },
];

export default function RiskGuide() {
  const [open, setOpen] = useState(false);

  return (
    <section className="risk-guide" aria-labelledby="risk-guide-title">
      <div className="risk-guide-header">
        <div>
          <h2 id="risk-guide-title" className="risk-guide-title">
            ¿Cómo leer el riesgo?
          </h2>
          <p className="risk-guide-lead">
            El <strong>IRA</strong> (Índice de Riesgo Agrícola) es un número de 0 a 1.
            Mientras más alto, más riesgo tiene el cultivo en ese municipio.
            Se arma con tres partes: clima, importancia del cultivo y capacidad económica del territorio.
          </p>
        </div>
        <button
          type="button"
          className="risk-guide-toggle"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
        >
          {open ? "Ocultar explicación" : "Ver explicación completa"}
        </button>
      </div>

      <div className="risk-guide-levels" role="list">
        {LEVELS.map((level) => (
          <div key={level.nivel} className="risk-guide-level" role="listitem">
            <div className="risk-guide-level-top">
              <RiskBadge nivel={level.nivel} />
              <span className="risk-guide-range">{level.range}</span>
            </div>
            <p>{level.meaning}</p>
          </div>
        ))}
      </div>

      {open && (
        <div className="risk-guide-details">
          <h3 className="risk-guide-subtitle">Las 3 partes del IRA</h3>
          <ul className="risk-guide-parts">
            {PARTS.map((part) => (
              <li key={part.code}>
                <strong>{part.code} — {part.name}</strong>
                <span className="risk-guide-weight">Pesa {part.weight} del total</span>
                <p>{part.plain}</p>
              </li>
            ))}
          </ul>
          <p className="risk-guide-formula">
            En corto: <strong>IRA = clima (mitad) + importancia del cultivo + vulnerabilidad económica</strong>.
            El mapa y la tabla muestran el riesgo del período más reciente de cada cultivo.
          </p>
          <ol className="risk-guide-steps">
            <li>Elija un cultivo o departamento, o busque un municipio.</li>
            <li>Haga clic en el mapa o en una fila de la tabla.</li>
            <li>En la ficha verá el mismo número, explicado paso a paso.</li>
          </ol>
        </div>
      )}
    </section>
  );
}
