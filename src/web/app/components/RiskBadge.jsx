const LEVELS = { Bajo: "bajo", Medio: "medio", Alto: "alto", Crítico: "critico" };

export default function RiskBadge({ nivel }) {
  const cls = `badge badge--${LEVELS[nivel] || ""}`;
  return <span className={cls}>{nivel || "—"}</span>;
}
