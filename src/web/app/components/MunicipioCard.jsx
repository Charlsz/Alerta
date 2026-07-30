"use client";
import { useState, useEffect, useRef, useMemo } from "react";
import useAPI from "../hooks/useAPI";
import RiskBadge from "./RiskBadge";

const GENERAL = "__general__";

/** Compare periods by date only — ignores `T` vs space time suffixes from different APIs. */
function periodKey(value) {
  return String(value || "").slice(0, 10);
}

function samePeriod(a, b) {
  return Boolean(a) && Boolean(b) && periodKey(a) === periodKey(b);
}

function fmtMonth(periodo) {
  const key = periodKey(periodo);
  if (!key || key.length < 7) return "—";
  const [year, month] = key.split("-");
  const names = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const idx = Number(month) - 1;
  if (!year || idx < 0 || idx > 11) return key.slice(0, 7);
  return `${names[idx]} ${year}`;
}

function riskPlain(nivel) {
  const map = {
    Bajo: "condiciones estables por ahora",
    Medio: "hay que prestar atención",
    Alto: "riesgo importante, priorice acciones",
    Crítico: "alerta urgente, actúe lo antes posible",
    "Sin dato": "aún no hay suficiente información",
  };
  return map[nivel] || "revise el detalle abajo";
}

const COMPONENT_HELP = {
  spc: "Mide si el clima (lluvia, calor, sequía) está peor de lo normal en este municipio.",
  sep: "Mide qué tan importante es este cultivo para la producción local. Si pesa mucho, un mal clima duele más.",
  sve: "Mide qué tan difícil es aguantar un golpe económico: precios de insumos y condiciones del territorio.",
};

function Bar({ value, label, help, color }) {
  const pct = Math.round((value ?? 0) * 100);
  return (
    <div className="bar-row">
      <div className="bar-copy">
        <span className="bar-label">{label}</span>
        {help && <span className="bar-help">{help}</span>}
      </div>
      <div className="bar-track">
        <div className="bar-fill" style={{ width: `${pct}%`, background: color || "var(--color-primary)" }} />
      </div>
      <span className="bar-value">{pct}%</span>
    </div>
  );
}

function getScoreColor(v) {
  if (v == null) return "#888";
  if (v >= 0.75) return "#ef4444";
  if (v >= 0.50) return "#f97316";
  if (v >= 0.25) return "#eab308";
  return "#22c55e";
}

function fmtHa(v) {
  if (v == null) return "\u2014";
  return Number(v).toLocaleString("es-CO", { maximumFractionDigits: 0 }) + " ha";
}

function fmtTon(v) {
  if (v == null) return "\u2014";
  return Number(v).toLocaleString("es-CO", { maximumFractionDigits: 1 }) + " t/ha";
}

/** From a list of periods, return the id of the one that should be shown by default. */
function pickDefaultPeriodId(periods, preferId) {
  if (preferId) {
    const match = periods.find((p) => samePeriod(p.periodo, preferId));
    if (match) return match.periodo;
  }
  if (!periods.length) return null;
  const withData = periods.filter(p => p.rendimiento_predicho != null);
  const pool = withData.length > 0 ? withData : periods;
  return pool.reduce((a, b) => (a.periodo > b.periodo ? a : b)).periodo;
}

export default function MunicipioCard({ codigo, cultivo: propCultivo, periodo: propPeriodo }) {
  const { data, loading } = useAPI(codigo ? `/api/municipio/${codigo}` : null);

  // Internal selection state
  const [focusCultivo, setFocusCultivo] = useState(null);
  const [focusPeriodo, setFocusPeriodo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [multiAgent, setMultiAgent] = useState(null);
  const [ndviData, setNdviData] = useState(null);
  const [deforData, setDeforData] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const keyRef = useRef(null);

  // New map/ranking selection must win over leftover tab/chip focus from a prior open.
  useEffect(() => {
    setFocusCultivo(null);
    setFocusPeriodo(null);
    setMessages([]);
  }, [codigo, propCultivo, propPeriodo]);

  const isGeneral = focusCultivo === GENERAL;

  // Latest row per cultivo, sorted by IRA desc
  const cultivoOptions = useMemo(() => {
    if (!data?.data) return [];
    const latest = {};
    for (const d of data.data) {
      const key = d.cultivo;
      if (!latest[key] || d.periodo > latest[key].periodo) {
        latest[key] = d;
      }
    }
    return Object.values(latest).sort((a, b) => (b.ira_score || 0) - (a.ira_score || 0));
  }, [data]);

  // Current selection
  const selectedCultivo = (() => {
    if (isGeneral) return GENERAL;
    if (focusCultivo) return focusCultivo;
    if (propCultivo) return propCultivo;
    return cultivoOptions[0]?.cultivo || null;
  })();

  // All periods for the selected cultivo
  const periodOptions = useMemo(() => {
    if (!data?.data || !selectedCultivo || selectedCultivo === GENERAL) return [];
    return data.data
      .filter(d => d.cultivo === selectedCultivo)
      .sort((a, b) => (a.periodo < b.periodo ? 1 : -1));
  }, [data, selectedCultivo]);

  // Display row — honor map/ranking selection; otherwise prefer non-null rendimiento_predicho
  const displayRow = useMemo(() => {
    if (!periodOptions.length) return null;
    const prefer = focusPeriodo || propPeriodo;
    const id = pickDefaultPeriodId(periodOptions, prefer);
    return periodOptions.find((d) => samePeriod(d.periodo, id)) || periodOptions[0];
  }, [periodOptions, focusPeriodo, propPeriodo]);

  // General summary
  const generalSummary = useMemo(() => {
    if (!data?.data) return null;
    const latest = {};
    for (const d of data.data) {
      const key = d.cultivo;
      if (!latest[key] || d.periodo > latest[key].periodo) latest[key] = d;
    }
    const list = Object.values(latest);
    const scores = list.map(d => d.ira_score).filter(v => v != null);
    const niveles = {};
    for (const d of list) {
      const n = d.ira_nivel || "Sin dato";
      niveles[n] = (niveles[n] || 0) + 1;
    }
    const sorted = [...list].sort((a, b) => (b.ira_score || 0) - (a.ira_score || 0));
    return {
      totalCultivos: list.length,
      avgIRA: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null,
      niveles,
      top3: sorted.slice(0, 3),
      bottom3: sorted.slice(-3).reverse(),
    };
  }, [data]);

  // The exact selection the card is showing — this is what the assistant must analyze
  const selectedPeriodo = isGeneral ? null : displayRow?.periodo ?? null;

  // Municipio-level data (NDVI, deforestation) — same for every cultivo/period
  useEffect(() => {
    if (!codigo) return;
    let vigente = true;
    setNdviData(null); setDeforData(null);
    Promise.all([
      fetch(`/api/municipio/${codigo}/deforestacion`).then(r => r.json()).catch(() => null),
      fetch(`/api/municipio/${codigo}/ndvi`).then(r => r.json()).catch(() => null),
    ]).then(([d, n]) => {
      if (!vigente) return;
      setDeforData(d);
      setNdviData(n);
    });
    return () => { vigente = false; };
  }, [codigo]);

  // Multi-agent analysis — depends on the current selection (general vs cultivo × period).
  // `vigente` descarta respuestas de una selección anterior: sin esto, una respuesta lenta
  // (p.ej. la del primer render, aún sin período) sobreescribe la del período elegido.
  useEffect(() => {
    // En vista de cultivo se espera a conocer el período, para no pedir un análisis que se descarta
    if (!codigo || !selectedCultivo || (!isGeneral && !selectedPeriodo)) return;
    let vigente = true;
    setMultiAgent(null);
    setLoaded(false);
    const params = new URLSearchParams({ scope: isGeneral ? "general" : "cultivo" });
    if (!isGeneral) {
      params.set("cultivo", selectedCultivo);
      if (selectedPeriodo) params.set("periodo", String(selectedPeriodo));
    }
    fetch(`/api/municipio/${codigo}/multiagent?${params}`)
      .then(r => r.json())
      .catch(() => null)
      .then(m => { if (vigente) { setMultiAgent(m); setLoaded(true); } });
    return () => { vigente = false; };
  }, [codigo, selectedCultivo, selectedPeriodo, isGeneral]);

  // Al cambiar de municipio, cultivo o período el contexto del asistente ya no es el mismo:
  // se reinicia la conversación para que no queden respuestas de otra selección.
  useEffect(() => {
    const k = `${codigo}-${selectedCultivo || ""}-${selectedPeriodo || ""}`;
    if (keyRef.current && keyRef.current !== k) setMessages([]);
    keyRef.current = k;
  }, [codigo, selectedCultivo, selectedPeriodo]);

  const ask = async () => {
    const q = question.trim();
    if (!q || asking) return;
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setQuestion("");
    setAsking(true);
    try {
      const body = { question: q, scope: isGeneral ? "general" : "cultivo" };
      if (!isGeneral) { body.cultivo = selectedCultivo; body.periodo = selectedPeriodo; }
      const res = await fetch(`/api/municipio/${codigo}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const json = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", text: json.answer || "Error al obtener respuesta." }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", text: "Error de conexión." }]);
    }
    setAsking(false);
  };

  // ── Empty / Loading states ──
  if (!codigo) return <p className="empty-state">Selecciona un municipio en el mapa o ranking.</p>;
  if (loading) return <p className="empty-state">Cargando...</p>;
  if (!data?.data?.length) return <p className="empty-state">Sin datos para este municipio.</p>;
  if (!cultivoOptions.length) return <p className="empty-state">Sin datos de cultivos para este municipio.</p>;

  const firstRow = data.data[0];

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">{firstRow.nombre_municipio || codigo}</h2>
        <p className="card-subtitle">{firstRow.nombre_departamento}</p>
      </div>

      <div className="scope-banner" role="status">
        {isGeneral ? (
          <>
            <p className="scope-banner-title">Vista general del municipio</p>
            <p className="scope-banner-text">
              Aquí se resume el último período de cada cultivo reportado
              ({generalSummary?.totalCultivos ?? 0} cultivos).
              No hay un solo cultivo seleccionado.
            </p>
          </>
        ) : (
          <>
            <p className="scope-banner-title">
              Estás viendo: <strong>{displayRow?.cultivo || selectedCultivo}</strong>
              {" · "}
              {fmtMonth(displayRow?.periodo)}
            </p>
            <p className="scope-banner-text">
              <RiskBadge nivel={displayRow?.ira_nivel} />
              {" "}
              IRA {displayRow?.ira_score != null ? displayRow.ira_score.toFixed(3) : "—"}
              {" — "}
              {riskPlain(displayRow?.ira_nivel)}.
              Este es el mismo dato que aparece en el mapa y en la tabla.
            </p>
          </>
        )}
      </div>

      {/* Cultivo tabs */}
      <div className="cultivo-tabs">
        <button
          className={`cultivo-tab ${isGeneral ? "cultivo-tab--active" : ""}`}
          onClick={() => { setFocusCultivo(GENERAL); setFocusPeriodo(null); setMessages([]); }}
        >
          General
        </button>
        {cultivoOptions.map(c => (
          <button
            key={c.cultivo}
            className={`cultivo-tab ${c.cultivo === selectedCultivo && !isGeneral ? "cultivo-tab--active" : ""}`}
            onClick={() => { setFocusCultivo(c.cultivo); setFocusPeriodo(c.periodo); setMessages([]); }}
          >
            <span className="cultivo-tab-name">{c.cultivo}</span>
            <RiskBadge nivel={c.ira_nivel} />
          </button>
        ))}
      </div>

      {/* ── GENERAL VIEW ── */}
      {isGeneral && generalSummary && (
        <>
          <div className="card-section">
            <h4 className="section-label">Resumen del municipio</h4>
            <p className="section-help">
              Promedio del último período de cada cultivo. Sirve para ver el panorama completo del municipio.
            </p>
            <div className="metrics-grid">
              <div className="metric-card">
                <span className="metric-value">{generalSummary.totalCultivos}</span>
                <span className="metric-label">Cultivos reportados</span>
              </div>
              <div className="metric-card">
                <span className="metric-value">{generalSummary.avgIRA?.toFixed(3) ?? "\u2014"}</span>
                <span className="metric-label">IRA promedio</span>
                <span className="metric-help">Promedio simple de los cultivos</span>
              </div>
            </div>
          </div>

          {/* Risk distribution */}
          <div className="card-section">
            <h4 className="section-label">¿Cuántos cultivos hay en cada nivel?</h4>
            <div className="metrics-grid">
              {Object.entries(generalSummary.niveles).map(([nivel, count]) => (
                <div key={nivel} className="metric-card" style={{ flex: 1, minWidth: 60 }}>
                  <RiskBadge nivel={nivel} />
                  <span className="metric-value" style={{ fontSize: "1rem" }}>{count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Top 3 */}
          <div className="card-section">
            <h4 className="section-label">Mayor riesgo</h4>
            <p className="section-help">Los cultivos que hoy necesitan más atención en este municipio.</p>
            {generalSummary.top3.map((d, i) => (
              <div key={d.cultivo} className="agent-item" style={{ display: "flex", justifyContent: "space-between" }}>
                <span>{i + 1}. {d.cultivo}</span>
                <span><RiskBadge nivel={d.ira_nivel} /> IRA {d.ira_score?.toFixed(3)}</span>
              </div>
            ))}
          </div>

          {/* Bottom 3 */}
          <div className="card-section">
            <h4 className="section-label">Menor riesgo</h4>
            <p className="section-help">Los cultivos con mejor situación relativa en este momento.</p>
            {generalSummary.bottom3.map((d, i) => (
              <div key={d.cultivo} className="agent-item" style={{ display: "flex", justifyContent: "space-between" }}>
                <span>{i + 1}. {d.cultivo}</span>
                <span><RiskBadge nivel={d.ira_nivel} /> IRA {d.ira_score?.toFixed(3)}</span>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 12, textAlign: "right" }}>
            <a
              href={`/reporte/${codigo}`}
              target="_blank"
              rel="noreferrer"
              className="btn btn--ghost"
              style={{ fontSize: "0.8125rem" }}
            >
              Reporte PDF · vista general →
            </a>
          </div>
        </>
      )}

      {/* ── CULTIVO DETAIL VIEW ── */}
      {!isGeneral && (
        <>
          {/* Period selector */}
          {periodOptions.length > 1 && (
            <div className="period-chips">
              {periodOptions.map(p => (
                <button
                  key={String(p.periodo)}
                  className={`period-chip ${samePeriod(p.periodo, displayRow?.periodo) ? "period-chip--active" : ""} ${p.rendimiento_predicho == null ? "period-chip--incomplete" : ""}`}
                  onClick={() => setFocusPeriodo(p.periodo)}
                  title={p.rendimiento_predicho == null ? "Sin datos de rendimiento para este período" : undefined}
                >
                  {periodKey(p.periodo).slice(0, 7)}
                  <span className="period-chip-ira">{p.ira_score?.toFixed(3)}</span>
                </button>
              ))}
            </div>
          )}

          {displayRow && (
            <>
              <div className="ira-hero">
                <RiskBadge nivel={displayRow.ira_nivel} />
                <span className="ira-hero-score">IRA {displayRow.ira_score?.toFixed(3)}</span>
                <p className="ira-hero-plain">{riskPlain(displayRow.ira_nivel)}</p>
              </div>

              <div className="bars-group">
                <h4 className="section-label">De dónde sale este riesgo</h4>
                <p className="section-help">
                  El IRA mezcla tres partes. Cada barra va de 0% (poco problema) a 100% (mucho problema).
                </p>
                <Bar value={displayRow.spc} label="Peligro climático (SPC)" help={COMPONENT_HELP.spc} color={getScoreColor(displayRow.spc)} />
                <Bar value={displayRow.sep} label="Exposición productiva (SEP)" help={COMPONENT_HELP.sep} color={getScoreColor(displayRow.sep)} />
                <Bar value={displayRow.sve} label="Vulnerabilidad económica (SVE)" help={COMPONENT_HELP.sve} color={getScoreColor(displayRow.sve)} />
              </div>

              <div className="metrics-grid">
                {displayRow.rendimiento_predicho != null && (
                  <div className="metric-card">
                    <span className="metric-value">{fmtTon(displayRow.rendimiento_predicho)}</span>
                    <span className="metric-label">Rendimiento esperado</span>
                    <span className="metric-help">Cuánto se espera cosechar por hectárea</span>
                  </div>
                )}
                <div className="metric-card">
                  <span className="metric-value">{displayRow.anomaly_score != null ? displayRow.anomaly_score.toFixed(2) : "\u2014"}</span>
                  <span className="metric-label">Puntaje de anomalía</span>
                  <span className="metric-help">Qué tan raro se ve este caso frente a otros similares</span>
                </div>
                {displayRow.rendimiento_nnet != null && (
                  <div className="metric-card">
                    <span className="metric-value">{fmtTon(displayRow.rendimiento_nnet)}</span>
                    <span className="metric-label">Rendimiento (modelo avanzado)</span>
                    <span className="metric-help">Otra estimación hecha con inteligencia artificial</span>
                  </div>
                )}
              </div>

              {/* Top-3 features */}
              {(() => {
                try {
                  const top3 = typeof displayRow.importancia_top3 === "string" ? JSON.parse(displayRow.importancia_top3) : displayRow.importancia_top3;
                  if (!Array.isArray(top3) || top3.length === 0) return null;
                  return (
                    <div className="card-section">
                      <h4 className="section-label">Qué más está influyendo en la alerta</h4>
                      <p className="section-help">Estas son las variables que más empujan el resultado de este caso.</p>
                      <div className="top3-grid">
                        {top3.map((item, i) => (
                          <div key={i} className="top3-chip">
                            <span className="top3-rank">{i + 1}</span>
                            <span className="top3-var">{item.var}</span>
                            <span className="top3-shap">{item.shap?.toFixed(4)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                } catch {
                  return null;
                }
              })()}

              <div style={{ marginTop: 12, textAlign: "right" }}>
                <a
                  href={`/reporte/${codigo}?cultivo=${encodeURIComponent(displayRow.cultivo)}&periodo=${encodeURIComponent(displayRow.periodo)}`}
                  target="_blank"
                  className="btn btn--ghost"
                  style={{ fontSize: "0.8125rem" }}
                >
                  Reporte PDF · {displayRow.cultivo} →
                </a>
              </div>
            </>
          )}
        </>
      )}

      {/* Deforestation */}
      {deforData?.data && !deforData?.error && (
        <div className="card-section">
          <h4 className="section-label">Pérdida de bosque</h4>
          <p className="section-help">Hectáreas de bosque perdidas en este municipio (no es solo del cultivo seleccionado).</p>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-value">{(() => { const e = Object.entries(deforData.data).find(([k]) => k.startsWith("deforestacion_") && !k.includes("total") && !k.includes("promedio") && !k.includes("tendencia")); return e ? fmtHa(e[1]) : "\u2014"; })()}</span>
              <span className="metric-label">Último año</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">{fmtHa(deforData.data.deforestacion_total_5y)}</span>
              <span className="metric-label">Últimos 5 años</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">{fmtHa(deforData.data.deforestacion_total_10y)}</span>
              <span className="metric-label">Últimos 10 años</span>
            </div>
            <div className="metric-card">
              <span className="metric-value" style={{ fontSize: "0.75rem" }}>{deforData.data.deforestacion_tendencia_label || "\u2014"}</span>
              <span className="metric-label">Tendencia</span>
            </div>
          </div>
        </div>
      )}

      {/* NDVI */}
      {ndviData?.data?.length > 0 && (
        <div className="card-section">
          <h4 className="section-label">Salud de la vegetación (NDVI satelital)</h4>
          <p className="section-help">
            El NDVI es una medida desde satélite: valores más altos suelen indicar vegetación más verde y sana.
          </p>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-value">{ndviData.data[0].ndvi?.toFixed(3)}</span>
              <span className="metric-label">NDVI actual</span>
            </div>
            {ndviData.data[0].anomalia != null && (
              <div className="metric-card">
                <span className="metric-value" style={{ color: ndviData.data[0].anomalia < 0 ? "#ef4444" : "#22c55e" }}>
                  {ndviData.data[0].anomalia > 0 ? "+" : ""}{ndviData.data[0].anomalia.toFixed(1)}%
                </span>
                <span className="metric-label">vs. histórico</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Multi-Agent */}
      {multiAgent?.agentes?.length > 0 && (
        <div className="card-section">
          <h4 className="section-label">
            Análisis Multi-Agente
            <span className="context-note" style={{ fontWeight: 400 }}>
              {isGeneral
                ? " · promedio de todos los cultivos"
                : ` · ${displayRow?.cultivo || selectedCultivo}, ${String(displayRow?.periodo || "").slice(0, 7)}`}
            </span>
          </h4>
          {multiAgent.agentes.map((a, i) => (
            <div key={i} className="agent-item">
              <strong>{a.agente}:</strong> <RiskBadge nivel={a.nivel} />
              {a.hallazgos?.length > 0 && <ul className="agent-hallazgos">{a.hallazgos.map((h, j) => <li key={j}>{h}</li>)}</ul>}
            </div>
          ))}
          {multiAgent.coordinador && (
            <div className="agent-coordinator">
              <strong>Conclusión ({multiAgent.coordinador.prioridad}):</strong> {multiAgent.coordinador.resumen}
            </div>
          )}
        </div>
      )}

      {loaded && !multiAgent?.agentes?.length && (
        <div className="card-section">
          <p className="empty-state" style={{ padding: 0, fontSize: "0.8125rem" }}>No hay suficientes datos para el análisis multi-agente de este municipio.</p>
        </div>
      )}

      {/* Chat IA */}
      <div className="card-section">
        <h4 className="section-label">Asistente IA</h4>
        <p className="context-note">
          {isGeneral
            ? `El asistente analiza el municipio en general: los ${generalSummary?.totalCultivos ?? 0} cultivos con su último período.`
            : `El asistente analiza únicamente ${displayRow?.cultivo || selectedCultivo} en el período ${String(displayRow?.periodo || "").slice(0, 7)}.`
          }
        </p>
        <div className="chat-messages">
          {messages.map((m, i) => (
            <div key={i} className={`chat-message chat-message--${m.role}`}>
              <strong>{m.role === "user" ? "Tú" : "Asistente"}:</strong> {m.text}
            </div>
          ))}
          {asking && <p className="empty-state" style={{ padding: "4px 0" }}>Pensando...</p>}
          {!messages.length && <p className="empty-state" style={{ padding: "4px 0", fontSize: "0.8125rem" }}>Pregunta sobre el riesgo, los indicadores o qué acciones tomar.</p>}
        </div>
        <div className="chat-input-group">
          <input
            className="chat-input"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
            placeholder="¿Qué significa este nivel de riesgo?"
          />
          <button className="btn btn--primary" onClick={ask} disabled={asking || !question.trim()}>
            {asking ? "..." : "Enviar"}
          </button>
        </div>
      </div>
    </div>
  );
}
