# NotePlus — Contexto del proyecto

> Contexto rápido para futuros prompts. Fuente de verdad de negocio: `PROJECT_CONTEXT.md`.
> Este archivo es solo orientación de código. Máx. 500 líneas.

## 1. Qué es
App web para instructores SENA: gestionan fichas (grupos), calificaciones por actividades y porcentajes, asistencia por clase con calendario, y archivo de fichas ya vistas. Solo rol instructor; cada uno ve sus datos.

## 2. Monorepo
- `backend/` — Python, Clean Architecture (`app/domain`, `app/application`, `app/infrastructure`, `app/presentation`, `app/main`). API `/api/v1`, JWT + refresh en cookie httpOnly.
- `frontend/` — React 19 + Vite + TypeScript, Router 7, TanStack Query 5, Tailwind 4.
- `docker-compose.yml` — API + DB + front dev. `PROJECT_CONTEXT.md` — reglas RN-01..RN-23.

## 3. Dominio (resumen, ver `PROJECT_CONTEXT.md` §5-6)
- `Instructor 1─* Ficha 1─* HorarioFicha / Clase / Estudiante / Actividad`.
- `Clase 1─* Asistencia *─1 Estudiante`. `Actividad` 2 niveles máx, hermanas suman 100 (RN-12).
- Notas 0.0–5.0, `notaFinal = Σ(nota × % / 100)`, faltantes = 0 (RN-15, RN-17). Finalizar bloquea notas/actividades, no asistencia (RN-11, RN-19).
- Recurso ajeno → `404` (RN-01). Fechas `YYYY-MM-DD`, zona `America/Bogota`.

## 4. Frontend
- Rutas fichas: `/fichas`, `/fichas/archivadas`, `/fichas/nueva`, `/fichas/:id`, `/fichas/:id/editar`.
- `features/fichas/pages/FichasListPage.tsx` — vista inicio "Mis fichas": toggle activas/archivadas, buscador por nombre/código, lista `space-y-4` de `FichaCard`, `Recordatorios` al final.
- `features/fichas/components/FichaCard.tsx` — wrapper `Card variant="ghost" className="card-fade hover:bg-white"`, header (punto `bg-brand-green`, nombre, código, badges), `MetaTab` horario/trimestre, acciones con `stopPropagation()` + `confirm()`.
- `shared/ui/Card.tsx` — variantes `default | outlined | elevated | ghost` (`ghost = rounded-3xl bg-transparent`).
- Cliente: `shared/api/client.ts`. Hooks: `features/fichas/hooks/useFichas.ts`.

## 5. Estilo clave
`frontend/src/index.css`:
```css
.card-fade {
  background-image: radial-gradient(circle at center, rgb(255 255 255 / 0) 0%, #ffffff 75%);
}
```
Centro transparente, bordes blancos. Tema: `navy-900 #05233a`, `brand-green #2f8f1e`, Inter, fondo `gray-50`.

## 6. Comandos
- Front: `npm run dev | build (tsc -b && vite build) | lint` en `frontend/`.
- Regla IA: un caso de uso por archivo, lógica solo en dominio/aplicación, nada derivado persistido, tests por RN-xx, Conventional Commits.
