# Notas y Asistencias para Instructores SENA — Contexto del Proyecto

> Este documento es la **fuente de verdad** del proyecto. Está escrito para que una persona o una IA pueda entender el dominio, las reglas de negocio y la arquitectura, y aplicarlos sin ambigüedad.
> Si una instrucción del usuario contradice este documento, **pregunta antes de actuar** y, si se confirma el cambio, actualiza este archivo.
> Las secciones marcadas con ⚠️ son decisiones tomadas por defecto que el dueño del proyecto aún puede cambiar.

---

## 1. Resumen

Aplicación web para que **instructores del SENA** gestionen, por **ficha** (grupo de estudiantes):

- Calificaciones con una calculadora de notas basada en actividades y porcentajes.
- Asistencia por clase, con un calendario de clases.
- Administración de fichas, estudiantes y actividades, con archivo de fichas ya vistas.

Alcance: aplicación sencilla, sin cálculos complejos. Prioridad: **claridad, mantenibilidad y escalabilidad** razonable, no sobreingeniería.

Usuarios: solo **instructores**. Cada instructor ve únicamente sus propios datos. No hay rol de estudiante ni de administrador (por ahora).

---

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Node.js 20+, **Express**, **TypeScript** ⚠️ |
| Base de datos | **PostgreSQL** |
| Acceso a datos | **Prisma** ⚠️ (aislado en infraestructura; se puede cambiar sin tocar dominio ni aplicación) |
| Validación | **Zod** (en la capa de presentación) |
| Seguridad | **bcrypt** (hash de contraseñas), **jsonwebtoken** (JWT), helmet, cors, express-rate-limit |
| Frontend | **React + Vite + TypeScript**, React Router, TanStack Query, React Hook Form + Zod |
| Calendario | FullCalendar |
| Tests | Vitest (backend y frontend), Supertest para integración HTTP |
| Contenedores | Docker + Docker Compose (API, DB, front en desarrollo) |
| Logs | pino |

---

## 3. Arquitectura: Clean Architecture

### 3.1 Regla de dependencia (inviolable)

```
presentation ──► application ──► domain
infrastructure ──► application ──► domain
```

- `domain` **no importa nada** de otras capas ni de librerías externas (ni Express, ni Prisma, ni bcrypt).
- `application` solo importa de `domain`. Define **puertos** (interfaces) que `infrastructure` implementa.
- `infrastructure` implementa los puertos (repositorios, hasher, token service, reloj).
- `presentation` (HTTP) traduce request → caso de uso → response. **Sin lógica de negocio.**
- La composición de dependencias ocurre **solo** en `main/` (composition root).

### 3.2 Estructura del backend

```
backend/
├── prisma/                      # schema.prisma y migraciones
├── src/
│   ├── domain/
│   │   ├── entities/            # Instructor, Ficha, HorarioFicha, Clase, Estudiante,
│   │   │                        # Asistencia, Actividad, Calificacion
│   │   ├── value-objects/       # Nota, Porcentaje, Email, CodigoFicha
│   │   ├── services/            # GradeCalculator, ClassScheduleGenerator (lógica pura)
│   │   └── errors/              # DomainError y subclases (ver sección 8)
│   ├── application/
│   │   ├── ports/               # Interfaces: *Repository, PasswordHasher, TokenService, Clock
│   │   ├── use-cases/
│   │   │   ├── auth/            # RegisterInstructor, LoginInstructor, RefreshSession
│   │   │   ├── fichas/          # CreateFicha, UpdateFicha, ArchiveFicha, ListFichas, ...
│   │   │   ├── estudiantes/
│   │   │   ├── clases/          # ListCalendar, UpdateClase
│   │   │   ├── asistencias/     # SaveAsistencias
│   │   │   ├── actividades/
│   │   │   └── calificaciones/  # SetCalificacion, GetFichaGrades, FinalizeFicha, ReopenFicha
│   │   └── dtos/
│   ├── infrastructure/
│   │   ├── persistence/prisma/  # Implementaciones de repositorios + mappers
│   │   ├── security/            # BcryptPasswordHasher, JwtTokenService
│   │   ├── time/                # SystemClock
│   │   └── config/              # env validado con Zod
│   ├── presentation/http/
│   │   ├── routes/
│   │   ├── controllers/
│   │   ├── middlewares/         # auth, error handler, rate limit, validate
│   │   └── schemas/             # Zod schemas de request
│   └── main/                    # composition root, app.ts, server.ts
└── tests/
    ├── unit/                    # domain + use cases (repositorios en memoria)
    └── integration/             # HTTP + BD de prueba
```

### 3.3 Estructura del frontend (por features)

```
frontend/src/
├── app/                # router, providers, layout
├── shared/             # ui, hooks, api client, utils
└── features/
    ├── auth/
    ├── fichas/         # listado, detalle, archivadas, formulario
    ├── estudiantes/
    ├── asistencias/    # calendario + marcado rápido
    └── calificaciones/ # calculadora, actividades, resumen
```

Cada feature contiene `api/`, `components/`, `hooks/`, `pages/`, `types/`.

---

## 4. Lenguaje ubicuo

Los **términos del dominio se mantienen en español** porque no tienen traducción fiel; los sufijos técnicos van en inglés.
Ejemplos: `Ficha`, `FichaRepository`, `CreateFichaUseCase`, `fichaId`, `notaMinimaAprobacion`.

| Término | Significado |
|---|---|
| Instructor | Usuario de la app. Dueño de sus fichas. |
| Ficha | Grupo de estudiantes de un programa en un trimestre, con código y horario. |
| Clase | Una sesión concreta (fecha + hora) de una ficha. |
| Actividad | Ítem evaluable de una ficha, con porcentaje sobre la nota final. |
| Subactividad | Actividad hija de otra; su porcentaje es relativo a la actividad padre. |
| Nota mínima de aprobación | Umbral por ficha para marcar Aprobado / No aprobado. |
| Ficha finalizada | Ficha con notas bloqueadas. |
| Ficha archivada ("ya vista") | Ficha de trimestres pasados, oculta de la vista activa. |

---

## 5. Modelo de dominio

### 5.1 Entidades

**Instructor**
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK |
| nombre | string | requerido |
| email | string | único, normalizado a minúsculas |
| passwordHash | string | bcrypt, nunca se expone |

**Ficha**
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK |
| instructorId | uuid | FK, dueño |
| codigo | string | código SENA de la ficha |
| nombre | string | |
| fechaInicio | date | fecha de inicio de clases |
| trimestre | string | trimestre calendario (ej. `T2 2026`), editable; por defecto se deriva de `fechaInicio` |
| totalClases | int | ⚠️ número total de clases de la ficha |
| notaMinimaAprobacion | decimal | por ficha |
| archivada | boolean | "ya vista" |
| finalizada | boolean | notas bloqueadas |

Unicidad: `(instructorId, codigo, fechaInicio)`. Una misma ficha puede repetirse en otro trimestre con otra fecha de inicio.

**HorarioFicha** (uno o varios por ficha)
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK |
| fichaId | uuid | FK |
| diaSemana | int | 0–6 (0 = domingo) |
| hora | time | hora de inicio |
| duracionMinutos | int | ⚠️ opcional, por defecto 60 |

**Clase**
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK |
| fichaId | uuid | FK |
| fecha | date | sin zona horaria |
| hora | time | |
| modalidad | enum | `PRESENCIAL` \| `VIRTUAL` (por defecto `PRESENCIAL`) |
| realizada | boolean | por defecto `true` ⚠️ |
| observacion | text? | justificación/notas del día |

Unicidad: `(fichaId, fecha, hora)`.

**Estudiante**
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK |
| fichaId | uuid | FK |
| nombre | string | |
| tipoIdentificacion | enum | `CC` \| `TI` \| `CE` \| `PA` \| `PEP` \| `PPT` \| `RC` (tipos de documento colombianos; por defecto `CC`) |
| identificacion | string | única por ficha |
| email | string? | |
| contacto | string? | teléfono u otro dato de contacto |

**Asistencia**
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK |
| claseId | uuid | FK |
| estudianteId | uuid | FK |
| estado | enum | `ASISTIO` \| `NO_ASISTIO` |
| justificacion | text? | notas sobre la inasistencia |

Unicidad: `(claseId, estudianteId)`.

**Actividad**
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK |
| fichaId | uuid | FK |
| parentId | uuid? | null = actividad de primer nivel |
| nombre | string | |
| fechaLimite | date? | |
| porcentaje | decimal | 0–100, relativo al padre (o a la nota final si no hay padre) |
| orden | int | para ordenar en la UI |

**Calificacion**
| Campo | Tipo | Notas |
|---|---|---|
| id | uuid | PK |
| actividadId | uuid | FK |
| estudianteId | uuid | FK |
| nota | decimal | dentro de la escala |

Unicidad: `(actividadId, estudianteId)`.

### 5.2 Relaciones

```
Instructor 1─* Ficha 1─* HorarioFicha
                 Ficha 1─* Clase 1─* Asistencia *─1 Estudiante
                 Ficha 1─* Estudiante 1─* Calificacion *─1 Actividad
                 Ficha 1─* Actividad 1─* Actividad (subactividades)
```

Todas las relaciones hijas usan borrado en cascada desde la ficha, excepto por la regla RN-04 (las fichas no se borran si ya tienen calificaciones; se archivan).

---

## 6. Reglas de negocio

Cada regla tiene un ID estable. **Los tests y los commits deben referenciarlo** (ej. `feat: RN-12 bloqueo de notas`).

### Propiedad y acceso
- **RN-01** Todo recurso pertenece a un instructor a través de su ficha. **Toda consulta y mutación se filtra por el `instructorId` del token.** Un recurso ajeno responde `404`, no `403`, para no revelar su existencia.

### Fichas
- **RN-02** `(instructorId, codigo, fechaInicio)` es único.
- **RN-03** Al crear una ficha se **generan automáticamente** sus `Clase`s: a partir de `fechaInicio`, se recorren las semanas y, por cada `HorarioFicha`, se crea una clase en su día/hora, ordenadas por fecha, hasta completar `totalClases`. Ejemplo: martes 6 pm, 10 clases → 10 clases, un martes por semana.
- **RN-04** Una ficha con calificaciones **no se elimina**; se archiva. Una ficha sin datos sí puede eliminarse. ⚠️
- **RN-05** Archivar ("ya vista") oculta la ficha de la vista activa y la lista en la sección **Fichas archivadas**. Es reversible (desarchivar). Una ficha archivada es de **solo lectura** hasta que se desarchive. ⚠️
- **RN-06** Si cambia el horario o `totalClases` de una ficha, solo se regeneran las clases **futuras sin asistencia ni cambios manuales**; nunca se pierden asistencias ya registradas.

### Estudiantes
- **RN-07** La `identificacion` es única dentro de una ficha. El mismo estudiante puede estar en varias fichas (son registros independientes).

### Asistencia y clases
- **RN-08** La asistencia se marca por `(clase, estudiante)` con estado `ASISTIO` o `NO_ASISTIO`; la justificación es opcional.
- **RN-09** Una clase tiene `modalidad` (presencial/virtual) y `realizada` (sí/no), editables por el instructor. Si una clase se marca como **no realizada**, no se pueden registrar asistencias para ella.
- **RN-10** El calendario muestra las clases de todas las fichas **activas** del instructor y resalta el día actual. "Hoy" se calcula en la zona horaria `America/Bogota` mediante el puerto `Clock`.
- **RN-11** Las asistencias se pueden editar mientras la ficha no esté archivada, aunque esté finalizada (finalizar bloquea **notas**, no asistencia). ⚠️

### Actividades y notas
- **RN-12** Los porcentajes de las actividades **hermanas** deben sumar exactamente 100. Esto aplica al primer nivel (sobre la nota final) y a las subactividades de cada padre (sobre el padre). Se valida en el backend.
- **RN-13** Profundidad máxima del árbol: actividad → subactividad (2 niveles). ⚠️
- **RN-14** Una actividad **con subactividades** no recibe nota directa: su nota es el promedio ponderado de sus hijas. Solo las actividades hoja reciben `Calificacion`.
- **RN-15** Escala de notas: **0.0 a 5.0** con un decimal ⚠️. Una nota fuera de rango se rechaza.
- **RN-16** `notaMinimaAprobacion` se define por ficha. El estudiante está **Aprobado** si `notaFinal >= notaMinimaAprobacion`, y **No aprobado** en caso contrario. El estado **se calcula, no se guarda**.
- **RN-17** `notaFinal = Σ (nota_actividad × porcentaje / 100)`, con las actividades sin calificar contadas como 0. Además se expone `notaAcumulada`, calculada solo sobre lo ya calificado y normalizada a su porcentaje, como información parcial. ⚠️
- **RN-18** El redondeo se aplica **solo al mostrar o al devolver el resultado final** (1 decimal, mitad hacia arriba), nunca en cálculos intermedios.
- **RN-19** **Finalizar ficha**: bloquea toda modificación de `Actividad` (nombre, porcentaje, estructura) y de `Calificacion`. **Reabrir** es una acción explícita del instructor, que vuelve a permitir cambios.
- **RN-20** Cambiar porcentajes o la nota mínima recalcula todos los resultados en la siguiente lectura, porque nada derivado se persiste.

### Autenticación
- **RN-21** Email único. La contraseña se guarda solo con bcrypt (cost 12). Mínimo 8 caracteres.
- **RN-22** Login devuelve un **access token JWT** de vida corta (15 min) y un **refresh token** en cookie `httpOnly`, `Secure`, `SameSite=Lax` (7 días) ⚠️. Los errores de login usan un mensaje genérico ("Credenciales inválidas").
- **RN-23** El login tiene rate limit por IP + email.

---

## 7. Casos de uso por módulo

### Módulo Adición (fichas, estudiantes, actividades)
- Listar fichas activas / archivadas.
- Crear, editar y archivar/desarchivar ficha (genera clases, RN-03).
- Dentro de una ficha: CRUD de estudiantes, ver actividades, entrar a la calculadora.
- Importar estudiantes con normalización en frontend (CSV/Excel/TXT/copiar-pegar, alias de columnas, tipo+valor juntos, caso SofiaPlus "NOMBRE CC #####") + modal de confirmación de mapeo → `POST /fichas/:fichaId/estudiantes/import-batch` (RN-07). El `POST .../import` CSV rígido queda deprecado.
- Exportar estudiantes, notas y asistencias a CSV/Excel generado en frontend.

### Módulo Asistencias
- Calendario con clases de todas las fichas activas (hora y ficha), resaltando hoy.
- Acceso rápido a "mi clase de hoy".
- Al seleccionar una clase: lista de estudiantes con estado, justificación por estudiante, observación del día, modalidad, realizada/no realizada.
- Guardado en lote (`PUT` de todas las asistencias de la clase).

### Módulo Calculadora
- CRUD de actividades y subactividades con porcentajes (validación RN-12).
- Tabla de notas: estudiantes × actividades, con nota final y estado Aprobado/No aprobado.
- Configurar nota mínima de la ficha.
- Finalizar / reabrir ficha (RN-19).

### Módulo 4
⚠️ Pendiente de definir por el dueño del proyecto (se mencionaron cuatro módulos, pero solo se describieron tres). No implementar nada hasta que se especifique.

---

## 8. Convenciones de la API

- Prefijo: `/api/v1`. JSON siempre. Fechas `YYYY-MM-DD`, horas `HH:mm`.
- Todas las rutas excepto `/auth/register`, `/auth/login` y `/auth/refresh` requieren `Authorization: Bearer <accessToken>`.

| Recurso | Endpoints principales |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me` |
| Fichas | `GET /fichas?archivada=false`, `POST /fichas`, `GET/PATCH/DELETE /fichas/:id`, `POST /fichas/:id/archive`, `POST /fichas/:id/unarchive`, `POST /fichas/:id/finalize`, `POST /fichas/:id/reopen` |
| Estudiantes | `GET/POST /fichas/:fichaId/estudiantes`, `PATCH/DELETE /fichas/:fichaId/estudiantes/:id`, `POST /fichas/:fichaId/estudiantes/import-batch` |
| Clases | `GET /clases?from=&to=` (calendario), `GET /clases/today`, `PATCH /clases/:id` |
| Asistencias | `GET /clases/:claseId/asistencias`, `PUT /clases/:claseId/asistencias` |
| Actividades | `GET/POST /fichas/:fichaId/actividades`, `PATCH/DELETE /fichas/:fichaId/actividades/:id` |
| Notas | `GET /fichas/:fichaId/notas` (matriz + cálculo), `PUT /actividades/:id/calificaciones` |

### Errores

Formato uniforme:

```json
{ "error": { "code": "WEIGHTS_NOT_100", "message": "Los porcentajes deben sumar 100", "details": {} } }
```

| Error de dominio | HTTP |
|---|---|
| ValidationError | 400 |
| UnauthorizedError | 401 |
| NotFoundError (incluye recurso ajeno) | 404 |
| ConflictError (duplicados, ficha finalizada/archivada) | 409 |
| Error inesperado | 500 (sin filtrar detalles internos) |

Los errores se lanzan como `DomainError` en dominio/aplicación y se traducen a HTTP **solo** en el middleware de errores.

---

## 9. Seguridad

- Nunca devolver `passwordHash`. Nunca loguear contraseñas ni tokens.
- Validar toda entrada con Zod antes de llegar al caso de uso.
- Variables de entorno (`DATABASE_URL`, `JWT_SECRET`, `JWT_REFRESH_SECRET`, etc.) validadas al arrancar; el proceso falla si faltan. Nunca commitear `.env`.
- helmet, CORS restringido al origen del frontend, rate limit en login.
- Consultas parametrizadas (Prisma). Nada de SQL concatenado.

---

## 10. Tiempo y fechas

- Las fechas de clase (`fecha`, `fechaInicio`, `fechaLimite`) se guardan como `DATE` **sin hora ni zona**, y las horas como `TIME`. Esto evita desplazamientos por UTC.
- Zona horaria de negocio: `America/Bogota`.
- El dominio no llama a `new Date()` directamente: usa el puerto `Clock`, lo que hace los tests deterministas.

---

## 11. Reglas para IA y colaboradores

1. **Lee este archivo completo antes de escribir código.** Cita el ID de la regla (RN-xx) cuando implementes lógica de negocio.
2. **Respeta la regla de dependencia** (3.1). Prohibido importar `express`, `@prisma/client`, `bcrypt` o `jsonwebtoken` en `domain/` o `application/`.
3. **Un caso de uso por archivo**, con una sola responsabilidad y un método `execute`. Recibe sus dependencias por constructor.
4. **Lógica de negocio solo en dominio/aplicación.** Controladores y repositorios no calculan notas ni validan reglas.
5. **Nunca persistas datos derivados** (nota final, estado aprobado, conteos). Se calculan.
6. **Usa `Decimal`** (o enteros escalados) para notas y porcentajes; nunca comparaciones de `float` sin tolerancia.
7. **No inventes reglas.** Si algo no está definido aquí (o está marcado ⚠️ y no se ha confirmado), pregunta.
8. **Cada regla RN-xx tiene al menos un test unitario.** Escribe el test junto con la implementación.
9. **Cambios de esquema = migración Prisma.** Nunca editar la BD a mano.
10. **No añadas dependencias** sin justificarlas; prefiere lo que ya está en el stack.
11. **Nombres:** dominio en español, términos técnicos en inglés, código en TypeScript estricto (`strict: true`), sin `any`.
12. **Commits** pequeños con Conventional Commits (`feat`, `fix`, `refactor`, `test`, `docs`).
13. **Si cambias una regla o el modelo, actualiza este documento en el mismo cambio.**

---

## 12. Estrategia de pruebas

- **Unitarias (prioridad alta):** `GradeCalculator`, `ClassScheduleGenerator`, validación de porcentajes, bloqueo por ficha finalizada. Casos de uso con repositorios en memoria.
- **Integración:** endpoints con Supertest contra una base de datos PostgreSQL de prueba (Docker). Cubrir autenticación y el aislamiento entre instructores (RN-01).
- **Frontend:** componentes clave (tabla de notas, formulario de asistencia) con Testing Library.

Casos mínimos de la calculadora: porcentajes que no suman 100, subactividades, notas faltantes, nota exactamente igual a la mínima, ficha finalizada, cambio de porcentajes tras calificar.

---

## 13. Hoja de ruta

### Fase 0 — Cimientos
- [ ] Monorepo (`backend/`, `frontend/`), TypeScript estricto, ESLint + Prettier
- [ ] Docker Compose (PostgreSQL + API)
- [ ] Esquema Prisma inicial y primera migración
- [ ] Composition root, middleware de errores, validación de entorno

### Fase 1 — Autenticación
- [ ] Registro y login (bcrypt + JWT + refresh) — RN-21 a RN-23
- [ ] Middleware de autenticación y `GET /auth/me`
- [ ] Login/registro en el frontend, rutas protegidas

### Fase 2 — Módulo Adición
- [ ] CRUD de fichas con horarios y generación de clases (RN-02, RN-03)
- [ ] Archivar/desarchivar y vista de archivadas (RN-04, RN-05)
- [ ] CRUD de estudiantes (RN-07)

### Fase 3 — Asistencias
- [ ] Endpoint de calendario y "clase de hoy" (RN-10)
- [ ] Marcado de asistencia en lote, modalidad, realizada (RN-08, RN-09)
- [ ] Calendario en el frontend con FullCalendar

### Fase 4 — Calculadora
- [ ] Árbol de actividades y validación de porcentajes (RN-12 a RN-14)
- [ ] Calificaciones y cálculo de nota final / estado (RN-15 a RN-18, RN-20)
- [ ] Finalizar / reabrir (RN-19)
- [ ] Tabla de notas en el frontend

### Fase 5 — Pulido
- [ ] Exportar notas y asistencias a Excel/CSV
- [ ] Importar estudiantes desde CSV
- [ ] Despliegue (Docker) y respaldos de la BD
- [ ] Módulo 4 (cuando se defina)

---

## 14. Decisiones abiertas (⚠️)

| # | Pregunta | Valor por defecto |
|---|---|---|
| 1 | ¿Qué es el cuarto módulo? | Sin definir |
| 2 | `totalClases`: ¿es total de la ficha o por cada día del horario? | Total de la ficha |
| 3 | Escala de notas | 0.0–5.0 |
| 4 | Nota final con actividades sin calificar | Cuentan como 0 (+ `notaAcumulada` informativa) |
| 5 | Profundidad de subactividades | 2 niveles |
| 6 | Ficha archivada | Solo lectura, reversible |
| 7 | Asistencia en ficha finalizada | Editable |
| 8 | Refresh token + cookie httpOnly | Sí |
| 9 | ORM | Prisma |
| 10 | Clase nueva | `realizada = true` por defecto |
