# src/web/ — Frontend (Next.js)

Aplicación React con Next.js App Router para visualizar resultados de riesgo climático agrícola, con asistente IA y reportes PDF.

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `package.json` | Dependencias: next, react, react-dom |
| `Dockerfile` | Imagen para docker-compose |
| `app/layout.jsx` | Root layout con metadata global |
| `app/page.jsx` | Página principal: FilterBar + Map + Ranking |
| `app/globals.css` | Estilos base |
| `app/components/FilterBar.jsx` | Filtros (cultivo, departamento) |
| `app/components/Map.jsx` | Mapa de riesgo municipal (Leaflet) |
| `app/components/Ranking.jsx` | Tabla de ranking municipio–cultivo |
| `app/components/MunicipioCard.jsx` | Ficha detallada por municipio + chat asistente IA |
| `app/components/RiskBadge.jsx` | Insignia visual de nivel de riesgo |
| `app/hooks/useAPI.js` | Hook genérico para llamadas a la API |
| `app/reporte/[codigo]/page.jsx` | Página de reporte ejecutivo imprimible/PDF con análisis generado por IA |

## Desarrollo

```bash
cd src/web
npm install
npm run dev
```

El frontend corre en `http://localhost:3000`. Las llamadas a `/api/*` se redirigen al backend configurado en `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
