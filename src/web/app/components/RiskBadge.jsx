const COLORS = { Bajo: "#22c55e", Medio: "#eab308", Alto: "#f97316", Crítico: "#ef4444" };

export default function RiskBadge({ nivel }) {
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 600,
        color: "#fff",
        backgroundColor: COLORS[nivel] || "#888",
      }}
    >
      {nivel || "—"}
    </span>
  );
}
