import "./globals.css";

export const metadata = {
  title: "Alerta — Riesgo Climático Agrícola",
  description: "Plataforma de alerta temprana para riesgo climático agrícola en Colombia",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body>
        <nav className="nav">
          <a href="/" style={{ color: "inherit", textDecoration: "none" }}><span className="nav-title">Alerta</span></a>
          <span className="nav-subtitle">Riesgo Climático Agrícola</span>
          <div style={{ marginLeft: "auto", display: "flex", gap: 16 }}>
            <a href="/acerca" style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", textDecoration: "none" }}>Acerca</a>
          </div>
        </nav>
        {children}
      </body>
    </html>
  );
}
