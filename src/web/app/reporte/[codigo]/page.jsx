"use client";
import { use, useEffect, useMemo, useState } from "react";
import RiskBadge from "@/app/components/RiskBadge";

function fmtTon(v) {
  if (v == null) return "—";
  return Number(v).toLocaleString("es-CO", { maximumFractionDigits: 1 }) + " t/ha";
}

function fmtHa(v) {
  if (v == null) return "—";
  return Number(v).toLocaleString("es-CO", { maximumFractionDigits: 0 }) + " ha";
}

function periodLabel(periodo) {
  const key = String(periodo || "").slice(0, 10);
  if (key.length < 7) return "—";
  const [y, m] = key.split("-");
  const names = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const idx = Number(m) - 1;
  if (!y || idx < 0 || idx > 11) return key.slice(0, 7);
  return `${names[idx]} ${y}`;
}

function pct(v) {
  if (v == null) return "—";
  return `${Math.round(Number(v) * 100)}%`;
}

function riskPlain(nivel) {
  const map = {
    Bajo: "condiciones relativamente estables",
    Medio: "hay que prestar atención",
    Alto: "riesgo importante: priorice acciones",
    Crítico: "alerta urgente: actúe lo antes posible",
  };
  return map[nivel] || "revise el detalle con su técnico";
}

function componentPlain(key) {
  const map = {
    spc: "Clima (lluvia, calor, sequía) frente a lo normal del municipio.",
    sep: "Qué tanto depende la zona de este cultivo.",
    sve: "Qué tan difícil es aguantar un golpe económico.",
  };
  return map[key] || "";
}

function splitActions(text) {
  if (!text) return [];
  return text
    .split(/\n+/)
    .map((l) => l.replace(/^\s*[-•\d.)]+\s*/, "").trim())
    .filter(Boolean);
}

export default function ReportePage({ params, searchParams }) {
  const { codigo } = use(params);
  const sp = use(searchParams);
  const cultivoParam = sp?.cultivo || null;
  const periodoParam = sp?.periodo || null;

  const [row, setRow] = useState(null);
  const [defor, setDefor] = useState(null);
  const [ndvi, setNdvi] = useState(null);
  const [multiAgent, setMultiAgent] = useState(null);
  const [ai, setAi] = useState(null);
  const [aiError, setAiError] = useState("");
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!codigo) return;
    let vigente = true;
    setLoading(true);
    setAiLoading(true);
    setAi(null);
    setAiError("");

    const detailParams = new URLSearchParams();
    if (cultivoParam) detailParams.set("cultivo", cultivoParam);
    if (periodoParam) detailParams.set("periodo", periodoParam);
    const qs = detailParams.toString();

    const maParams = new URLSearchParams({
      scope: cultivoParam ? "cultivo" : "general",
    });
    if (cultivoParam) maParams.set("cultivo", cultivoParam);
    if (periodoParam) maParams.set("periodo", periodoParam);

    Promise.all([
      fetch(`/api/municipio/${codigo}${qs ? `?${qs}` : ""}`).then((r) => r.json()),
      fetch(`/api/municipio/${codigo}/deforestacion`).then((r) => r.json()).catch(() => null),
      fetch(`/api/municipio/${codigo}/ndvi`).then((r) => r.json()).catch(() => null),
      fetch(`/api/municipio/${codigo}/multiagent?${maParams}`).then((r) => r.json()).catch(() => null),
    ])
      .then(([d, df, n, m]) => {
        if (!vigente) return;
        const first = d?.data?.[0] || null;
        setRow(first);
        setDefor(df?.data || null);
        setNdvi(n || null);
        setMultiAgent(m?.agentes ? m : null);
      })
      .finally(() => {
        if (vigente) setLoading(false);
      });

    fetch(`/api/municipio/${codigo}/reporte`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scope: cultivoParam ? "cultivo" : "general",
        cultivo: cultivoParam,
        periodo: periodoParam,
      }),
    })
      .then(async (r) => {
        const json = await r.json();
        if (!r.ok) throw new Error(json.message || "No se pudo generar el análisis con IA.");
        return json;
      })
      .then((json) => {
        if (!vigente) return;
        setAi(json);
      })
      .catch((err) => {
        if (!vigente) return;
        setAiError(err.message || "No se pudo generar el análisis con IA.");
      })
      .finally(() => {
        if (vigente) setAiLoading(false);
      });

    return () => {
      vigente = false;
    };
  }, [codigo, cultivoParam, periodoParam]);

  const topComponent = useMemo(() => {
    if (!row) return null;
    const items = [
      { key: "spc", label: "Peligro climático (SPC)", value: row.spc },
      { key: "sep", label: "Exposición productiva (SEP)", value: row.sep },
      { key: "sve", label: "Vulnerabilidad económica (SVE)", value: row.sve },
    ].filter((x) => x.value != null);
    if (!items.length) return null;
    return items.sort((a, b) => b.value - a.value)[0];
  }, [row]);

  const lastDefor = useMemo(() => {
    if (!defor) return null;
    const entry = Object.entries(defor).find(
      ([k]) =>
        k.startsWith("deforestacion_") &&
        !k.includes("total") &&
        !k.includes("promedio") &&
        !k.includes("tendencia"),
    );
    return entry ? { key: entry[0], value: entry[1] } : null;
  }, [defor]);

  const onCopy = async () => {
    const parts = [
      `Reporte Alerta — ${row?.nombre_municipio || codigo}`,
      row?.cultivo ? `Cultivo: ${row.cultivo}` : null,
      row?.periodo ? `Período: ${periodLabel(row.periodo)}` : null,
      row?.ira_nivel ? `IRA ${row.ira_score?.toFixed(3)} (${row.ira_nivel})` : null,
      "",
      ai?.secciones?.resumen || ai?.texto || "",
      ai?.secciones?.acciones || "",
    ].filter((x) => x != null);
    try {
      await navigator.clipboard.writeText(parts.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  };

  if (loading) {
    return (
      <div className="report-page">
        <div className="report-loading">
          <p className="report-loading-title">Preparando su reporte…</p>
          <p className="report-loading-text">
            Estamos cargando los números del municipio y pidiendo a la IA un resumen en lenguaje claro.
          </p>
        </div>
      </div>
    );
  }

  if (!row) {
    return (
      <div className="report-page">
        <p className="empty-state">Sin datos para este municipio con la selección actual.</p>
        <a className="btn btn--ghost no-print" href="/">Volver al mapa</a>
      </div>
    );
  }

  const borderColor =
    row.ira_nivel === "Crítico"
      ? "var(--critico)"
      : row.ira_nivel === "Alto"
        ? "var(--alto)"
        : row.ira_nivel === "Medio"
          ? "var(--medio)"
          : "var(--bajo)";

  const actions = splitActions(ai?.secciones?.acciones);

  return (
    <div className="report-page">
      <div className="report-toolbar no-print">
        <div className="report-toolbar-left">
          <a className="btn btn--ghost" href="/">← Volver</a>
          <p className="report-toolbar-hint">
            Use <strong>Imprimir / Guardar PDF</strong> y elija “Guardar como PDF” en el diálogo del navegador.
          </p>
        </div>
        <div className="report-toolbar-actions">
          <button className="btn btn--ghost" type="button" onClick={onCopy}>
            {copied ? "Copiado" : "Copiar resumen"}
          </button>
          <button className="btn btn--primary" type="button" onClick={() => window.print()}>
            Imprimir / Guardar PDF
          </button>
        </div>
      </div>

      <header className="report-header" style={{ borderBottomColor: borderColor }}>
        <div>
          <p className="report-kicker">Alerta · Reporte de riesgo agrícola</p>
          <h1>{row.nombre_municipio || codigo}</h1>
          <p className="report-meta">
            {row.nombre_departamento}
            {row.cultivo ? ` · Cultivo: ${row.cultivo}` : ""}
            {row.periodo ? ` · Período: ${periodLabel(row.periodo)}` : ""}
          </p>
          <p className="report-scope">
            Este reporte usa exactamente la selección abierta en la ficha
            {cultivoParam ? ` (${cultivoParam})` : " (vista general)"}.
          </p>
        </div>
        <div className="report-ira">
          <RiskBadge nivel={row.ira_nivel} />
          <div className="report-ira-score">IRA {row.ira_score != null ? row.ira_score.toFixed(3) : "—"}</div>
          <p className="report-ira-plain">{riskPlain(row.ira_nivel)}</p>
        </div>
      </header>

      <section className="report-ai" aria-live="polite">
        <div className="report-ai-head">
          <h2>Análisis con IA</h2>
          <span className="report-ai-badge">{aiLoading ? "Generando…" : ai ? "Listo" : "No disponible"}</span>
        </div>

        {aiLoading && (
          <p className="report-ai-wait">
            La IA está redactando un resumen claro con los mismos datos de esta página…
          </p>
        )}

        {!aiLoading && aiError && (
          <div className="report-ai-error">
            <p>{aiError}</p>
            <p className="report-help">
              Aun así puede imprimir los indicadores de abajo. Para el texto con IA, configure
              OPENROUTER_API_KEY en el servidor.
            </p>
          </div>
        )}

        {!aiLoading && ai?.secciones && (
          <div className="report-ai-grid">
            <article className="report-ai-block">
              <h3>Resumen</h3>
              <p>{ai.secciones.resumen || "—"}</p>
            </article>
            <article className="report-ai-block">
              <h3>Qué significan los números</h3>
              <p>{ai.secciones.numeros || "—"}</p>
            </article>
            <article className="report-ai-block report-ai-block--actions">
              <h3>Qué hacer</h3>
              {actions.length ? (
                <ul>
                  {actions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
              ) : (
                <p>{ai.secciones.acciones || "—"}</p>
              )}
            </article>
            {ai.secciones.frase && (
              <article className="report-ai-block report-ai-block--quote">
                <h3>En una frase</h3>
                <p>{ai.secciones.frase}</p>
              </article>
            )}
          </div>
        )}
      </section>

      <section>
        <h2 className="report-section-title">Indicadores de esta selección</h2>
        <p className="section-help">
          El IRA combina clima (50%), importancia del cultivo (30%) y vulnerabilidad económica (20%).
          {topComponent
            ? ` Hoy el componente más alto es ${topComponent.label}: ${componentPlain(topComponent.key)}`
            : ""}
        </p>
        <div className="report-grid">
          <div className="report-card">
            <h3>Peligro climático (SPC)</h3>
            <div className="value">{row.spc?.toFixed(3) ?? "—"}</div>
            <div className="sub">{pct(row.spc)} · peso 50%</div>
          </div>
          <div className="report-card">
            <h3>Exposición productiva (SEP)</h3>
            <div className="value">{row.sep?.toFixed(3) ?? "—"}</div>
            <div className="sub">{pct(row.sep)} · peso 30%</div>
          </div>
          <div className="report-card">
            <h3>Vulnerabilidad económica (SVE)</h3>
            <div className="value">{row.sve?.toFixed(3) ?? "—"}</div>
            <div className="sub">{pct(row.sve)} · peso 20%</div>
          </div>
          <div className="report-card">
            <h3>Rendimiento esperado</h3>
            <div className="value">{fmtTon(row.rendimiento_predicho)}</div>
            <div className="sub">
              {row.rendimiento_ic_inf != null
                ? `Rango 95%: ${row.rendimiento_ic_inf.toFixed(1)} – ${row.rendimiento_ic_sup.toFixed(1)} t/ha`
                : "Sin predicción para este período"}
            </div>
          </div>
        </div>
      </section>

      <section>
        <h2 className="report-section-title">Lectura rápida</h2>
        <table className="report-table">
          <thead>
            <tr>
              <th>Indicador</th>
              <th>Valor</th>
              <th>En palabras simples</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Nivel IRA</td>
              <td><RiskBadge nivel={row.ira_nivel} /></td>
              <td>{riskPlain(row.ira_nivel)}</td>
            </tr>
            <tr>
              <td>Anomalía</td>
              <td>{row.anomaly_score != null ? row.anomaly_score.toFixed(2) : "—"}</td>
              <td>{row.is_anomaly ? "Este caso se ve atípico frente a otros similares." : "Dentro de un rango esperado."}</td>
            </tr>
            <tr>
              <td>Período</td>
              <td>{periodLabel(row.periodo)}</td>
              <td>Ventana de tiempo que alimenta estas cifras.</td>
            </tr>
            {row.rendimiento_nnet != null && (
              <tr>
                <td>Rendimiento (modelo avanzado)</td>
                <td>{fmtTon(row.rendimiento_nnet)}</td>
                <td>Otra estimación con inteligencia artificial.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      {defor && (
        <section>
          <h2 className="report-section-title">Bosque y territorio</h2>
          <p className="section-help">Pérdida de cobertura arbórea del municipio (GFW/Hansen), no solo del cultivo.</p>
          <div className="report-grid">
            <div className="report-card">
              <h3>Último año</h3>
              <div className="value">{fmtHa(lastDefor?.value)}</div>
            </div>
            <div className="report-card">
              <h3>Últimos 5 años</h3>
              <div className="value">{fmtHa(defor.deforestacion_total_5y)}</div>
            </div>
            <div className="report-card">
              <h3>Últimos 10 años</h3>
              <div className="value">{fmtHa(defor.deforestacion_total_10y)}</div>
            </div>
            <div className="report-card">
              <h3>Tendencia</h3>
              <div className="value">{defor.deforestacion_tendencia_label || "—"}</div>
            </div>
          </div>
        </section>
      )}

      {ndvi?.data?.length > 0 && (
        <section className="report-card report-card--wide">
          <h3>Salud de la vegetación (NDVI satelital)</h3>
          <p style={{ marginTop: 6 }}>
            Último NDVI: <strong>{ndvi.data[0].ndvi?.toFixed(3)}</strong>
            {ndvi.data[0].periodo ? ` (${periodLabel(ndvi.data[0].periodo)})` : ""}
          </p>
          {ndvi.data[0].anomalia != null && (
            <p>
              Diferencia vs. histórico:{" "}
              <strong style={{ color: ndvi.data[0].anomalia < 0 ? "var(--alto)" : "var(--bajo)" }}>
                {ndvi.data[0].anomalia > 0 ? "+" : ""}
                {ndvi.data[0].anomalia.toFixed(1)}%
              </strong>
            </p>
          )}
          <p className="sub" style={{ marginTop: 8 }}>
            Valores más altos suelen indicar vegetación más verde. Fuente: MODIS.
          </p>
        </section>
      )}

      {multiAgent?.agentes?.length > 0 && (
        <section>
          <h2 className="report-section-title">Señales del análisis multi-agente</h2>
          <div className="report-grid">
            {multiAgent.agentes.map((a, i) => (
              <div key={`${a.agente}-${i}`} className="report-card" style={{ fontSize: "0.8125rem" }}>
                <strong>{a.agente}</strong>
                <div style={{ marginTop: 6 }}><RiskBadge nivel={a.nivel} /></div>
                {a.hallazgos?.length > 0 && (
                  <ul style={{ margin: "8px 0 0", paddingLeft: 16, color: "var(--text-secondary)" }}>
                    {a.hallazgos.slice(0, 3).map((h) => <li key={h}>{h}</li>)}
                  </ul>
                )}
              </div>
            ))}
          </div>
          {multiAgent.coordinador && (
            <div className="agent-coordinator">
              <strong>Conclusión ({multiAgent.coordinador.prioridad}):</strong> {multiAgent.coordinador.resumen}
            </div>
          )}
        </section>
      )}

      <footer className="report-footer">
        <p>Alerta — alerta temprana de riesgo climático agrícola en Colombia</p>
        <p>
          Generado el {new Date().toLocaleString("es-CO")}
          {ai?.generado_en ? " · Texto IA vía OpenRouter" : ""}
          {" · "}Datos: IDEAM, DANE, UPRA, IGAC, GFW
        </p>
      </footer>
    </div>
  );
}
