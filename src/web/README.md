# src/web/ — Frontend (Next.js)

Aplicación React con Next.js App Router para visualizar resultados de riesgo climático agrícola.

## Archivos

| Archivo | Propósito |
|---------|-----------|
| `package.json` | Dependencias: next, react, react-dom |
| `next.config.mjs` | Proxy `/api/*` al backend, output standalone |
| `jsconfig.json` | Alias `@/` para imports absolutos |
| `Dockerfile` | Imagen para docker-compose (dev) |
| `app/layout.jsx` | Root layout con metadata global |
| `app/page.jsx` | Página principal: FilterBar + Map + Ranking |
| `app/globals.css` | Estilos base |
| `app/components/FilterBar.jsx` | Filtros (cultivo, mes, departamento) |
| `app/components/Map.jsx` | Mapa de riesgo municipal |
| `app/components/Ranking.jsx` | Tabla de ranking municipio–cultivo |
| `app/components/MunicipioCard.jsx` | Ficha detallada por municipio |
| `app/components/RiskBadge.jsx` | Insignia visual de nivel de riesgo |
| `app/hooks/useAPI.js` | Hook genérico para llamadas a la API |

## Desarrollo

```bash
cd src/web
npm install
npm run dev
```

El frontend corre en `http://localhost:3000`. Las llamadas a `/api/*` se redirigen al backend configurado en `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).
