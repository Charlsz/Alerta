import "./globals.css";

export const metadata = {
  title: "Alerta — Riesgo Climático Agrícola",
  description: "Plataforma de alerta temprana para riesgo climático agrícola en Colombia",
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
