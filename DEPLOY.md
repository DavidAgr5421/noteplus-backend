# Despliegue a productivo — Render (API) + Neon (Postgres) + Vercel (front)

> Orden obligatorio: **1. Neon → 2. Render → 3. Vercel**.
> La URL de cada capa se necesita en la siguiente.

## 1. Base de datos en Neon

1. Crea un proyecto en Neon (región cercana a Render, ej. US East) con base `noteplus`.
2. Copia la **connection string directa** (sin pooler, puerto 5432). Para este proyecto usa la URL directa: el pooler transaccional de Neon rompe los prepared statements de asyncpg.
3. Deriva dos URLs de esa misma cadena:
   - `DATABASE_URL`: cambia el esquema a `postgresql+asyncpg://`
     `postgresql+asyncpg://user:pass@ep-xxx.aws.neon.tech/noteplus`
   - `SYNC_DATABASE_URL` (solo scripts/tests): deja `postgresql://` y agrega `?sslmode=require`.

## 2. API en Render (Blueprint)

1. Dashboard → **New → Blueprint** → conecta este repo. Render lee `render.yaml` y te pedirá:
   - `DATABASE_URL` y `SYNC_DATABASE_URL` (del paso 1).
   - `CORS_ORIGINS`: la URL de Vercel del paso 3. ⚠️ En el primer despliegue pon un temporal y corrígelo después (ver paso 4).
2. Los secretos JWT se autogeneran (`generateValue`). No los cambies después o invalidas todas las sesiones.
3. Render corre `alembic upgrade head` solo antes de cada deploy (`preDeployCommand`).
4. Verifica: `https://TU-API.onrender.com/api/v1/health` → `{"status":"ok",...}`.
   Nota: en plan free Render duerme el servicio; la primera petición tarda ~1 min.

### Variables del backend (referencia)

| Var | Valor en prod | Por qué |
|---|---|---|
| `ENV` | `production` | Apaga `/docs`, activa `Secure` en cookies |
| `DATABASE_URL` | `postgresql+asyncpg://…` (Neon) | Motor async |
| `DB_SSL` | `true` | Neon exige TLS |
| `CORS_ORIGINS` | `https://tu-app.vercel.app` | front permitido (coma si hay más) |
| `COOKIE_SAMESITE` | `none` | front y API están en distinto sitio; sin esto el refresh no viaja y la sesión muere cada 15 min |
| `JWT_SECRET` / `JWT_REFRESH_SECRET` | generados | Firmas; rotarlos cierra sesiones |

## 3. Front en Vercel

1. **Import Project** → selecciona el repo → **Root Directory: `frontend/`** (Vercel detecta Vite solo).
2. Environment Variable (Production): `VITE_API_URL=https://TU-API.onrender.com/api/v1`.
   ⚠️ Vite la incrusta en el **build**: define la variable **antes** de desplegar; si la cambias, redeploy.
3. Deploy. `frontend/vercel.json` ya trae el rewrite SPA (`/* → /index.html`) para recargas y rutas directas.

## 4. Cierre del círculo

1. Vuelve a Render → `CORS_ORIGINS` = URL real de Vercel → **Manual Deploy** (o cambia el valor y redeploy).
2. Prueba de humo en el front:
   - Registro + login (cookie `refresh_token` con `SameSite=None; Secure`).
   - Recarga la página tras 15 min (el refresh silencioso debe renovar sin sacarte).
   - Importar 2 estudiantes de prueba y exportar a Excel.
3. Si el login falla con CORS: revisa que `CORS_ORIGINS` sea exactamente el origen (sin `/` final).

## Desarrollo local (sin cambios)

`docker-compose up` sigue igual: `.env` local con `ENV=development`, `COOKIE_SAMESITE=lax`, `DB_SSL=false`.
