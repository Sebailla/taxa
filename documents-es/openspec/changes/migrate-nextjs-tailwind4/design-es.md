# Diseño: migrate-nextjs-tailwind4

## Frontera de alcance de PR 2a

Este diseño es la rebanada PR 2a migrada del cambio
`migrate-nextjs-tailwind4`. Entrega únicamente el **layout** del
monolito modular:

- las cinco carpetas de módulos de capability bajo `src/modules/`
- las cuatro carpetas de capa por módulo (`presentation`,
  `application`, `domain`, `infrastructure`)
- un barrel público por módulo
  (`src/modules/<capability>/index.ts`)
- los alias de ruta de `tsconfig.json` que fijan el acceso entre
  módulos solo por barrel
- el test enfocado de layout
  (`tests/test_module_layers.py`)

Deliberadamente **no** entrega:

- ningún código de runtime dentro de las carpetas de capa (los
  `.gitkeep` de capa son simples placeholders; los componentes
  React, los tokens de Tailwind 4, los fetchers y los stores reales
  aterrizan en rebanadas posteriores según `tasks.md`
  §Fase 2b – §Fase 5)
- ninguna regla de ESLint (la guarda `no-restricted-imports` que
  aplica los alias de ruta llega con PR 2b; la triangulación de
  runtime con PR 2c)
- la decisión finalizada de **frontera de responsabilidad del
  servidor Next.js ↔ FastAPI** (propuesta §Frontera de
  responsabilidad del servidor, §1) — esa decisión es **Abierta /
  Basada-en-evidencia** en esta rebanada y se registra en §1 abajo
  según `specs/modular-architecture/spec.md` regla 7

Este archivo es el destino canónico de toda referencia de la forma
`scope-decisions.md` que aparecía previamente en la propuesta, las
tareas y el spec. Esas referencias se redirigen a este archivo
mediante la pasada de reparación complementaria.

---

## Decisiones de arquitectura por capas

| Decisión | Elección | Por qué |
|---|---|---|
| Lista de capabilities | `taxonomy`, `research`, `design-system`, `browser-state`, `app-shell` | Fijada por `tests/test_module_layers.py::CAPABILITIES` (literal); coincide con propuesta §Capabilities y `tasks.md` §Fase 5 (puertos por capability) |
| Lista de capas | `presentation`, `application`, `domain`, `infrastructure` | Fijada por `specs/modular-architecture/spec.md` regla 3 y la tupla `LAYERS` del test |
| Nombre del barrel | `index.ts` (no `.js`, no `barrel.ts`) | `specs/modular-architecture/spec.md` regla 5; el test de layout fija el sufijo como `.ts` para que un PR futuro no degrade el archivo a JavaScript sin avisar |
| Cuerpo del barrel (PR 2a) | `export {};` (re-export vacío) | Mantiene el archivo como módulo válido de TypeScript para que `tsc --noEmit` lo acepte; las exportaciones reales se añaden rebanada a rebanada según los comentarios dentro de cada barrel |
| Ubicación de módulos | `src/modules/<capability>/` (sin `src/components/`, sin `src/utils/`, sin `src/shared/`) | `specs/modular-architecture/spec.md` regla 2 prohíbe nombres técnicos como partición de primer nivel; `test_no_top_level_technical_dump_folders` del test de layout aplica el conjunto negativo |
| Alias de ruta | `@taxa/<capability>` y `@taxa/<capability>/*` en `tsconfig.json` | Aplicación en tiempo de build del acceso solo por barrel (spec regla 5); la guarda ESLint llega con PR 2b, la triangulación de runtime con PR 2c |
| Marcador de presencia de carpeta | placeholders `.gitkeep` en cada carpeta de capa | Permite que `is_dir()` resuelva antes de que llegue cualquier archivo real; lo elimina la rebanada que deposita el primer archivo real en esa capa |
| Higiene de nombres de capa | Sin renombrados silenciosos de capas a mitad de migración | `test_no_forbidden_layer_name_per_module` del test de layout rechaza cualquier hijo directo inesperado de un módulo |
| Tope de número de módulos | Exactamente cinco módulos (hoy) | `test_total_module_count_matches_pinned_5` del test de layout falla alto si aparece una carpeta extraviada o se elimina una capability sin revisión del spec |

---

## Layout de módulos (PR 2a en disco)

```
src/modules/
├── taxonomy/
│   ├── index.ts                  (barrel — PR 2a: `export {};`)
│   ├── presentation/.gitkeep
│   ├── application/.gitkeep
│   ├── domain/.gitkeep
│   └── infrastructure/.gitkeep
├── research/
│   ├── index.ts                  (barrel — PR 2a: `export {};`)
│   ├── presentation/.gitkeep
│   ├── application/.gitkeep
│   ├── domain/.gitkeep
│   └── infrastructure/.gitkeep
├── design-system/
│   ├── index.ts                  (barrel — PR 2a: `export {};`)
│   ├── presentation/.gitkeep
│   ├── application/.gitkeep
│   ├── domain/.gitkeep
│   └── infrastructure/.gitkeep
├── browser-state/
│   ├── index.ts                  (barrel — PR 2a: `export {};`)
│   ├── presentation/.gitkeep
│   ├── application/.gitkeep
│   ├── domain/.gitkeep
│   └── infrastructure/.gitkeep
└── app-shell/
    ├── index.ts                  (barrel — PR 2a: `export {};`)
    ├── presentation/.gitkeep
    ├── application/.gitkeep
    ├── domain/.gitkeep
    └── infrastructure/.gitkeep
```

Total: **5 módulos × 4 capas = 20 carpetas de capa**, **5 barrels**,
**0 archivos de runtime** en esta rebanada. La forma
`barrel vacío + .gitkeep` es toda la superficie de código de PR 2a.

---

## Alias de ruta de `tsconfig.json` (PR 2a)

| Alias | Resuelve a | Lo usa |
|---|---|---|
| `@taxa/taxonomy` | `src/modules/taxonomy/index.ts` | Puertos de capability de PR 5 (tareas 5.1–5.3) |
| `@taxa/taxonomy/*` | `src/modules/taxonomy/*` | Fixtures de la guarda ESLint de PR 2b/c |
| `@taxa/research` | `src/modules/research/index.ts` | Puertos de PR 5 (tareas 5.4–5.6) |
| `@taxa/research/*` | `src/modules/research/*` | Fixtures de la guarda ESLint de PR 2b/c |
| `@taxa/design-system` | `src/modules/design-system/index.ts` | Bootstrap de frontend de PR 3 (tareas 3.1–3.8) |
| `@taxa/design-system/*` | `src/modules/design-system/*` | Fixtures de la guarda ESLint de PR 2b/c |
| `@taxa/browser-state` | `src/modules/browser-state/index.ts` | browser-state de PR 4 (tareas 4.1–4.4) |
| `@taxa/browser-state/*` | `src/modules/browser-state/*` | Fixtures de la guarda ESLint de PR 2b/c |
| `@taxa/app-shell` | `src/modules/app-shell/index.ts` | Bootstrap de frontend de PR 3 (host de `src/app/page.tsx`) |
| `@taxa/app-shell/*` | `src/modules/app-shell/*` | Fixtures de la guarda ESLint de PR 2b/c |

El modo estricto está activado por completo (`strict`,
`noImplicitAny`, `strictNullChecks`, `noUnusedLocals`,
`noUnusedParameters`, `noImplicitReturns`,
`noFallthroughCasesInSwitch`), de modo que las rebanadas futuras
que rellenen la capa de dominio deben compilar bajo esas flags
**sin** React, Next, FastAPI ni ningún subsistema de I/O — esa es
la invariante de `specs/modular-architecture/spec.md` regla 4 para
la capa de dominio.

`include` se acota a `src/**/*.ts` y `src/**/*.tsx`; `web`, `etl`,
`tests`, `api` se excluyen (cada uno tiene su propio toolchain;
mezclar el modo estricto TS con el tooling de Python aquí sería
prematuro).

---

## Cambios de archivos (solo PR 2a)

| Ruta | Acción | Descripción |
|---|---|---|
| `tsconfig.json` | Crear | Modo estricto + 5 alias de ruta por capability. La configuración completa de Next.js / JSX / plugins llega con PR 3 (tarea 3.1). |
| `src/modules/taxonomy/index.ts` | Crear | Barrel público de `taxonomy`. Re-export vacío en PR 2a; las exportaciones reales llegan con PR 5 (tareas 5.1–5.3). |
| `src/modules/taxonomy/{presentation,application,domain,infrastructure}/.gitkeep` | Crear × 4 | Placeholders de capa vacíos para `taxonomy`. |
| `src/modules/research/index.ts` | Crear | Barrel público de `research`. Re-export vacío en PR 2a; las exportaciones reales llegan con PR 5 (tareas 5.4–5.6). |
| `src/modules/research/{presentation,application,domain,infrastructure}/.gitkeep` | Crear × 4 | Placeholders de capa vacíos para `research`. |
| `src/modules/design-system/index.ts` | Crear | Barrel público de `design-system`. Re-export vacío en PR 2a; las exportaciones reales llegan con PR 3 (tareas 3.1–3.8). |
| `src/modules/design-system/{presentation,application,domain,infrastructure}/.gitkeep` | Crear × 4 | Placeholders de capa vacíos para `design-system`. |
| `src/modules/browser-state/index.ts` | Crear | Barrel público de `browser-state`. Re-export vacío en PR 2a; las exportaciones reales llegan con PR 4 (tareas 4.1–4.4). |
| `src/modules/browser-state/{presentation,application,domain,infrastructure}/.gitkeep` | Crear × 4 | Placeholders de capa vacíos para `browser-state`. |
| `src/modules/app-shell/index.ts` | Crear | Barrel público de `app-shell`. Re-export vacío en PR 2a; las exportaciones reales llegan con PR 3 (el módulo host de la única ruta de Next.js en `src/app/page.tsx`). |
| `src/modules/app-shell/{presentation,application,domain,infrastructure}/.gitkeep` | Crear × 4 | Placeholders de capa vacíos para `app-shell`. |
| `tests/test_module_layers.py` | Crear | 40 aserciones enfocadas de layout (10 funciones pytest, parametrizadas sobre las 5 capabilities y 4 capas — RED → GREEN → TRIANGULATE capturado). Los nombres de test con prefijo AC de propuesta §Criterios de éxito llegan con PR 5. |
| `openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks}.md` + `specs/modular-architecture/spec.md` | Migrar | Ya en `origin/develop` (pre-PR-2a). PR 2a solo los toca mediante la reparación de referencias colgantes en §Preguntas abiertas abajo. |
| `documents-es/openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks}-es.md` + `specs/modular-architecture/spec-es.md` | Migrar | Espejos en español de los mismos tres archivos, según `openspec/AGENTS.md`. |
| `openspec/changes/migrate-nextjs-tailwind4/design.md` (este archivo) | Crear | Artefacto compañero de reparación; acotado a PR 2a. |
| `documents-es/openspec/changes/migrate-nextjs-tailwind4/design-es.md` | Crear | Espejo fiel en español de este archivo. |
| `web/**`, `api/server.py`, `Makefile`, `package.json`, `extension/manifest.json`, `etl/**` | **Sin cambios** | Fuera del alcance de PR 2a según `tasks.md` §Fuera de alcance. |

Líneas totales de código+test de PR 2a: **409** (`tsconfig.json` 45
+ 5 barrels 115 + 20 placeholders `.gitkeep` de capa 0 +
`tests/test_module_layers.py` 249). PR 2a lleva una `size:exception`
aceptada (+9 líneas, +2,3 % sobre el presupuesto de revisión de
400 líneas); ver `apply-progress-es.md` §Registro de cambios (entrada
del 2026-08-29).

---

## Interfaces / Contratos (PR 2a)

```ts
// Cada barrel es un módulo válido de TypeScript que no re-exporta
// nada en PR 2a. Las exportaciones reales aterrizan rebanada a
// rebanada según los comentarios dentro de cada archivo
// (preservados literalmente del código migrado).
//
// src/modules/taxonomy/index.ts
export {};

// src/modules/research/index.ts
export {};

// src/modules/design-system/index.ts
export {};

// src/modules/browser-state/index.ts
export {};

// src/modules/app-shell/index.ts
export {};
```

```jsonc
// tsconfig.json (extracto relevante)
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "allowSyntheticDefaultImports": true,
    "verbatimModuleSyntax": false,
    "baseUrl": ".",
    "paths": {
      "@taxa/taxonomy":       ["src/modules/taxonomy/index.ts"],
      "@taxa/taxonomy/*":      ["src/modules/taxonomy/*"],
      "@taxa/research":        ["src/modules/research/index.ts"],
      "@taxa/research/*":      ["src/modules/research/*"],
      "@taxa/design-system":   ["src/modules/design-system/index.ts"],
      "@taxa/design-system/*": ["src/modules/design-system/*"],
      "@taxa/browser-state":   ["src/modules/browser-state/index.ts"],
      "@taxa/browser-state/*": ["src/modules/browser-state/*"],
      "@taxa/app-shell":       ["src/modules/app-shell/index.ts"],
      "@taxa/app-shell/*":     ["src/modules/app-shell/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.tsx"],
  "exclude": ["node_modules", "web", "etl", "tests", "api"]
}
```

PR 2a **no** añade superficie pública nueva a FastAPI. El contrato
`/api/*` permanece byte-idéntico al de `origin/develop` según
propuesta §Fuera de Alcance (fila "Reescritura del backend") y la
línea base existente de `tests/test_smoke.py` (63 passed, 8 skipped).

---

## Estrategia de testing (PR 2a)

| Capa | Qué | Cómo |
|---|---|---|
| Layout (enfocado) | `tests/test_module_layers.py` | 40 aserciones sobre 10 funciones pytest, parametrizadas sobre las 5 capabilities y 4 capas (RED → GREEN → TRIANGULATE capturado). Verifica: existe la raíz de módulos; existe cada carpeta de capability; existe cada carpeta de capa por módulo; existe cada barrel `index.ts`; cada barrel es `.ts` no `.js`; no hay carpetas técnicas de primer nivel; cada raíz de módulo está alineada con capability; el conteo total de módulos es exactamente cinco; ningún nombre prohibido de capa por módulo. |
| Backend | (sin cambios) | `tests/test_smoke.py`, `etl/tests/`, el resto de la suite. PR 2a no debe regresionar ninguna de las 63 passed / 8 skipped existentes. |
| Frontend | (sin cambios) | Sin nuevo runner de test de frontend. El fixture de Playwright permanece intacto; PR 5 actualiza los selectores cuando aterriza React. |

El test enfocado de layout fija las **constantes** sobre las que
descansa el resto del diseño (`CAPABILITIES`, `LAYERS`,
`BARREL_NAME`), de modo que el test fallará alto si alguno de
esos nombres deriva sin una revisión correspondiente del spec o
del diseño.

---

## Fuera de alcance de PR 2a

Estas piezas aterrizan en rebanadas posteriores según `tasks.md`;
PR 2a NO debe tocar ninguna:

- **PR 2b**: patrones barrel-only de `.eslintrc.cjs` (5 caps × 4
  capas = 20 patrones); fixture de test runtime `barrel_import.js`.
- **PR 2c**: 20 fixtures
  `scripts/eslint-fixtures/deep_import_<capability>_<layer>.js` y
  el bloque de triangulación runtime de
  `tests/test_no_restricted_imports.py`.
- **PR 2d**: tipos planos TS + invariantes de
  `src/modules/taxonomy/domain/taxon.ts`;
  `tests/test_taxonomy_domain.py`.
- **PR 2e**: guarda de framework-tokens por grep
  (`tests/test_domain_purity.py`) sobre la capa de dominio (aquí
  la regla 4 del spec se vuelve test ejecutable).
- **PR 3**: Bootstrap de frontend — entry de Next.js
  (`src/app/layout.tsx`, `src/app/page.tsx`), bloque `@theme` de
  Tailwind 4 (`src/modules/design-system/infrastructure/globals.css`),
  reescritura de `Makefile::api`, reorientación de
  `api/server.py:1847` a la salida de Next.js elegida (`out/`,
  según §1 abajo), reubicación de `web/search_urls.js` a
  `src/modules/research/infrastructure/search-engines.js`.
- **PR 4**: `src/modules/browser-state/{store,keys,defaults}.ts`
  — cuatro claves de `localStorage`, cada una con exactamente un
  sitio de lectura y uno de escritura dentro de `useEffect`
  detrás de un flag `mounted`.
- **PR 5**: puertos por capability —
  `src/modules/taxonomy/{domain,application,infrastructure,presentation}`,
  `src/modules/research/{domain,application,infrastructure,presentation}`,
  composición de host por `AppShell`; el borrado de los legacy
  `web/*.{html,js,css}` + `tailwind.config.js`.
- **§1 Decisión** (este archivo, §1 abajo): la frontera Next.js ↔
  FastAPI permanece **Abierta / Basada-en-evidencia** durante PR
  2a. PR 3 es la rebanada que la cierra (porque PR 3 es donde
  `next build` corre de verdad y `web/dist/build-profile.json` se
  vuelve real).

---

## Límite de rollback (PR 2a)

Revertir el commit de PR 2a elimina **solo** estas rutas:

```
tsconfig.json
src/modules/taxonomy/index.ts
src/modules/taxonomy/{presentation,application,domain,infrastructure}/.gitkeep
src/modules/research/index.ts
src/modules/research/{presentation,application,domain,infrastructure}/.gitkeep
src/modules/design-system/index.ts
src/modules/design-system/{presentation,application,domain,infrastructure}/.gitkeep
src/modules/browser-state/index.ts
src/modules/browser-state/{presentation,application,domain,infrastructure}/.gitkeep
src/modules/app-shell/index.ts
src/modules/app-shell/{presentation,application,domain,infrastructure}/.gitkeep
tests/test_module_layers.py
```

junto a las migraciones de artefactos OpenSpec:

```
openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks,apply-progress,design}.md
openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md
documents-es/openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks,apply-progress,design}-es.md
documents-es/openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec-es.md
```

La reversión de PR 2a **no** elimina nada de `web/`, `api/`,
`Makefile`, `package.json`, `extension/manifest.json`, `etl/`, ni
de los artefactos de los sub-PRs de PR 1 (esos viven en sus propios
PRs y commits). Ningún otro PR o sub-PR está acoplado a la
superficie de PR 2a en esta rebanada.

---

## §1 Decisión de frontera de responsabilidad del servidor (Next.js ↔ FastAPI)

**Estado: Decisión de frontera G1 registrada; la selección de
Enfoque (A / B / C) sigue bloqueada por evidencia G2–G6 (§3.3).**

Esta entrada registra la **decisión de frontera G1** seleccionada
por el mantenedor: **FastAPI se mantiene como único origen
desplegado en `127.0.0.1:8765`**, con las rutas, métodos, formas,
status y headers de `/api/*` sin cambios, y
`extension/manifest.json::host_permissions` quedando en
`["http://localhost:8765/*"]`. G1 es una decisión de frontera, no
una selección de Enfoque; la elección de Enfoque (A / B / C) sigue
bloqueada por G2–G6 (§3.3). Según
`specs/modular-architecture/spec.md` regla 7:

> el enfoque elegido se registra en `design.md::§1 Decision`
> ENTONCES la entrada cita este spec por ruta como autoridad
> arquitectónica
> Y si el diseño ve un conflicto con alguna regla aquí, se eleva de
> vuelta a la propuesta antes de implementar

Esta entrada **cita
`openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
como autoridad arquitectónica** para las restricciones del monolito
modular (reglas 1–5) y confirma que **no se ha identificado ningún
conflicto** entre la frontera G1 y cualquier regla del spec. Las
reglas 1, 2, 3, 5 son neutras respecto al framework y restringen
todo Enfoque por igual; la regla 4 (el dominio permanece libre de
framework / I/O) restringe todo Enfoque por igual; la regla 6
exige explícitamente que todo Enfoque respete las reglas 1–5; la
regla 7 es esta misma entrada.

### Decisión G1: invariantes de FastAPI como único origen (registradas)

| Invariante | Regla vinculante | Anclaje |
|---|---|---|
| Único proceso desplegado / único origen HTTP en `127.0.0.1:8765`. Un proceso FastAPI; sin segundo contenedor, grupo de procesos, servicio o puerto de servidor de desarrollo. | spec.md regla 1 | `api/server.py:1818–1820` (`uvicorn.run(app, host="127.0.0.1", port=8765, ...)`) |
| Continuidad de `/api/*`: rutas, métodos, formas de request, formas de response, status codes y headers sin cambios. AC-21 (`tests/test_smoke.py:77 test_search_engine_contract`) puede leer desde una ruta nueva; la forma del contrato se mantiene idéntica. | propuesta §Fuera de Alcance | handlers `/api/*` existentes en `api/server.py` |
| Continuidad de la extensión: `extension/manifest.json::host_permissions` queda en `["http://localhost:8765/*"]`; `content_scripts.matches` queda en `["http://localhost:8765/*"]`. Sin segundo origen, sin puerto nuevo. | spec.md regla 1 | `extension/manifest.json:13–15, :21` |
| Cumplimiento del monolito modular: las reglas 1–7 de `specs/modular-architecture/spec.md` son vinculantes para el Enfoque elegido. | spec.md regla 6 | spec.md mismo |

G1 registra estas invariantes. **No** selecciona un Enfoque, **no**
afirma que una puerta de evidencia haya pasado y **no** afirma que
exista evidencia de paridad o comparabilidad de rendimiento del
legado en disco.

### Ownership de HTML y de activos estáticos (registrado para G1)

- **Owner del HTML**: el `app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")` existente de FastAPI (en `api/server.py:1815`) sirve `/`, `index.html` y el fallback para navegación directa a rutas desconocidas.
- **Owner de los activos estáticos**: el mismo montaje `StaticFiles` sirve cada `/_next/static/*`, `/assets/*`, archivo de fuente, bundle CSS e imagen. G1 **no** permite un segundo origen estático.
- **Constante `WEB_DIR`**: `WEB_DIR = Path(__file__).parent.parent / "web"` en `api/server.py:54`. Reorientar `WEB_DIR` a una salida de build de Next.js (p. ej. `out/`, `web/dist/next-static/` o equivalente) es el único cambio permitido del montaje estático en este cambio.
- **Un montaje, una reescritura**: `app.mount("/", StaticFiles(...))` sigue siendo el único montaje; el middleware estrictamente necesario para el Enfoque elegido (p. ej. SPA-fallback para deep links) se añade en `api/server.py` sin reescribir la signature del montaje.
- **Bind de `uvicorn`**: `uvicorn.run(app, host="127.0.0.1", port=8765, ...)` es el único listener introducido por `make api`. G1 no abre un segundo puerto.

### Fallback de navegación directa (registrado para G1)

- El `StaticFiles(directory=str(WEB_DIR), html=True)` de FastAPI ya provee fallback de `index.html` para rutas desconocidas. La navegación directa a `/`, `/index.html` o cualquier ruta que el montaje no reconozca devuelve el shell SPA mediante ese fallback.
- Los deep links (p. ej. `/taxon/{id}`, `/help`, `/settings`) resuelven a `index.html` mediante el fallback `html=True`; el router del lado cliente dentro de la SPA decide la ruta final. **No se requiere tabla de rutas del lado servidor** bajo G1.
- El fallback forma parte del contrato `StaticFiles` de FastAPI; PR3 no introduce un mecanismo de fallback paralelo bajo G1. Si un Enfoque futuro (p. ej. Enfoque B) requiere fallback adicional, queda bloqueado por G3 (preparación de consumidores, §3.3.3).

### Comportamiento ante arranque y fallo de build (registrado para G1)

- **Un fallo de build NO debe caer silenciosamente al legado**. Si `next build` sale distinto de cero, `make api` DEBE salir distinto de cero y NO debe arrancar uvicorn. Los archivos vanilla del legado solo se alcanzan mediante un `git revert` explícito de la unidad de cutover (§"Unidad atómica de cutover y rollback" abajo), nunca mediante un modo degradado silencioso.
- **Comprobación de runtime**: `scripts/check-runtime.mjs` (tarea 3.4 de PR 3) verifica `node --version >= 20.9.0` antes de que arranque uvicorn. Un fallo sale distinto de cero y aborta el target `make api`.
- **Artefacto de build ausente**: `Makefile::api` invoca el paso de build antes de que uvicorn vincule el puerto. Si el artefacto de build de Next.js está ausente (clon limpio, sin `next build` ejecutado), el target del Makefile falla antes de que uvicorn vincule. Bajo G1 no existe una ruta de código implícita de "servir los archivos legacy".
- **Supervisión de proceso**: uvicorn corre como el único proceso FastAPI. No hay un segundo watcher / supervisor de procesos que pueda cambiar al legado ante un fallo.
- **Puerta de smoke**: `make smoke` (que llama a `tests/test_smoke.py`) devuelve la línea base previa a la migración (63 passed, 8 skipped) **antes** de que exista cualquier artefacto de build de Next.js; la puerta de smoke es independiente del cutover G1.

### Manifiesto de consumidores activos afectados (registrado para G1)

- El cutover atómico DEBE mover cada consumidor activo enumerado en `design.md::§3.1` (consumidores del mount web de FastAPI + consumidores de `web/search_urls.js`) en la misma unidad de release. **Ningún consumidor puede permanecer "activo" contra una ruta que el cutover pretende eliminar.**
- `§3.1` es el inventario autorizado de consumidores activos; el futuro manifiesto coordinado de cutover (§3.4, entregable de PR3d) nombra una ruta de reemplazo y una ruta de verificación para cada consumidor.
- **G1 no edita §3.1.** §3.1 ya enumera más de 20 consumidores activos repartidos entre `web/index.html`, `web/*.js`, los smoke tests, los tests de línea base de evidencia, los tests de build-profile, los tests de cronometraje de hidratación, el manifest de la extensión y `web/search_urls.js` + AC-21. G1 cita §3.1 como la lista vinculante y difiere la actualización del lado consumidor a la rebanada de planificación PR3d.

### Unidad atómica de cutover y rollback (registrada para G1)

- **Unidad de cutover (activación)**: PR3e cambia exactamente lo siguiente de forma atómica, en un único release:
  1. La constante `WEB_DIR` en `api/server.py:54` (reorientada a la salida de build del Enfoque elegido).
  2. Cada actualización de consumidor activo enumerada en `design.md::§3.1` (imports, ruta lectora AC-21, cada consumidor de test).
  3. Los targets `make api` / `make web` del Makefile.
  4. El propio artefacto de build (el directorio de salida de build del Enfoque elegido).
- **Unidad de rollback (desactivación)**: `git revert` del commit de PR3e restaura los cuatro conjuntos juntos. G1 **no admite un revert parcial** — los reverts parciales dejan consumidores que referencian rutas eliminadas y rompen el shell SPA o AC-21.
- **Límite de verificación**: tras el revert, `make smoke` vuelve a la línea base previa a la migración (63 passed, 8 skipped) y `curl http://127.0.0.1:8765/index.html` devuelve el shell vanilla. Sin regresión de AC-21; sin cambio en el manifest de la extensión; sin deriva del contrato `/api/*`.

### Prerrequisitos antes de PR3b / G2 (registrados para G1)

El trabajo de PR3b / G2 NO DEBE comenzar hasta que se satisfaga cada
prerrequisito de abajo. La evidencia ausente, fallida, obsoleta
(>7 días) o incomparable queda **bloqueada**, nunca aprobada.

| Puerta | Productor / artefacto | Estado |
|---|---|---|
| G2 | `scripts/verify_build.py` + `BUILD-INVENTORY.json` | pendiente PR3b |
| G3 | `scripts/verify_consumers.py` + `CONSUMER-READINESS.json` (cada consumidor de §3.1 nominado) | pendiente PR3d |
| G4 | Harness de paridad Playwright + Lighthouse (línea base existente de `tests/test_smoke.py` 63 passed / 8 skipped preservada) | pendiente PR3d |
| G5 | `scripts/measure_hydration.py` (PR 1b.3a, reconstrucción pendiente) + comparabilidad Lighthouse; línea base del legado **no** en disco | bloqueada hasta reconstrucción |
| G6 | `scripts/rehearse_cutover.py` referenciando `design.md::§3.4` | pendiente PR3d |

La sonda de exportación estática desechable (PRs #93–#97) sigue
siendo solo de evidencia; sus artefactos son entradas para la
evidencia G4 / G5, no un sustituto de una selección de Enfoque.
**No se registra ninguna afirmación de paridad o comparabilidad de
rendimiento del legado** en esta rebanada.

### Evidencia requerida para cerrar la selección de Enfoque §1

La selección de Enfoque (A, B o C) se registra aquí **solo** una vez
que **toda** la siguiente evidencia esté en disco:

1. `BUILD-INVENTORY.json` de PR3b (`scripts/verify_build.py`).
2. `CONSUMER-READINESS.json` de PR3d (`scripts/verify_consumers.py`).
3. Delta de Playwright + Lighthouse de PR3d contra la línea base del legado sobre el fixture chromium.
4. Cronometraje de hidratación de `scripts/measure_hydration.py` (PR 1b.3a, reconstrucción pendiente) más comparabilidad con Lighthouse.
5. `cutover-rehearsal.json` del dry-run de PR3d (`scripts/rehearse_cutover.py`).

Hasta que las cinco estén en disco y pasen sus umbrales
(§3.3.2–§3.3.6), la entrada §1 se mantiene en **G1 registrada;
selección de Enfoque bloqueada por evidencia**, y `## §1 Enfoque:
<A | B | C>` **no** se escribe. Si esas mediciones muestran que la
exportación estática de `next build` (Enfoque A) logra una
regresión ≤ 0 % sobre el presupuesto de perf (G5), preserva cada
contrato de consumidor (G3), preserva paridad de comportamiento
(G4), y el ensayo de cutover tiene éxito (G6), entonces **el
Enfoque A es la selección de Enfoque §1 por defecto** porque
preserva el contrato de puerto único (G1) y tiene el radio de
impacto más pequeño. Cualquier otro resultado exige escalar de
vuelta a la propuesta antes de que aterrice código alguno.
**Este fail-safe por defecto es condicional a evidencia real; NO
es una selección hecha en esta rebanada.**

### Lo que esta entrada NO afirma

- **No** afirma que el Enfoque A (exportación estática bajo FastAPI) esté seleccionado. El Enfoque A es uno de tres candidatos; la selección queda bloqueada por G2–G6.
- **No** afirma que G1 "haya pasado". G1 es una decisión de frontera registrada por el diseño; las puertas de evidencia G2–G6 siguen bloqueadas.
- **No** afirma que exista evidencia comparable de rendimiento o paridad del producto legacy, ni que el manifiesto de consumidores activos `§3.1` esté finalizado. El artefacto de línea base del legado `web/dist/evidence-baseline.json` estaba pendiente de reconstrucción en PR 1b.2 / 1b.3a / 1b.3b; la línea base de hidratación G5, el harness de paridad G4 y el manifiesto de cutover `§3.4` son entregables separados de PR3d.

---

## Contrato del motor de runtime

El requisito duro de Next.js 16 se registra en
`package.json::engines.node` cuando `package.json` se reescribe
(tarea 3.4 de PR 3). Hasta entonces, el contrato vive en este
diseño:

- **Node.js `>= 20.9.0`** es el único runtime aceptado.
- Aplicación: `scripts/check-runtime.mjs` (aterriza con la tarea
  3.4 de PR 3) sale distinto de cero cuando `node -v` reporta un
  major/minor/patch inferior.
- La comprobación se invoca desde `Makefile::api` antes de que
  arranque uvicorn.
- Este es el registro canónico que reemplaza la referencia previa
  a `scope-decisions.md::§8`; PR 3 es la rebanada que cablea la
  guarda real.

---

## Línea base de evidencia de migración

Los números baseline del build legacy (tamaño total del código,
roster de módulos, pin de chromium, cronometraje de hidratación) los
producen los sub-PRs de PR 1b.x y se almacenan en
`web/dist/evidence-baseline.json` (emisión en build; el emisor
aterriza con PR 1a.1; el esquema con PR 1a.2; el bloque chromium con
PR 1b.1; el resto con PR 1b.2; el subset de hidratación con PR
1b.3a; el resto con PR 1b.3b). La tarea 1b.3b.3 de PR 1b.3b
referencia esta línea base como el lugar donde ya viven los números
legacy (reemplaza la referencia previa a
`scope-decisions.md::§0`).

PR 2a **no** consume la línea base en sí; PR 5 es la primera
rebanada que compara las rebanadas migradas contra ella.

---

## Superficie de dependencias

La justificación de dependencias (adiciones por capability,
eliminaciones, `@tailwindcss/cli` transitorio, `next/font` para las
fuentes existentes Material Symbols Outlined + Raleway + JetBrains
Mono) vive en este diseño en lugar de un archivo separado
`scope-decisions.md`. Las adiciones son:

- `next@^16` (App Router)
- `react@^19`, `react-dom@^19`
- `tailwindcss` ^4.x
- `@tailwindcss/cli` (solo transitorio; se elimina cuando se retire
  el build vanilla)
- `typescript >= 5.1.0`, `@types/react@^19`,
  `@types/react-dom@^19`, `@types/node`

Eliminaciones: `autoprefixer`, `postcss`, `@tailwindcss/forms`.
Cada eliminación está justificada por la lista de propuesta
§Dependencias; la tarea 3.4 de PR 3 aterriza la reescritura real
de `package.json`.

---

## Preguntas abiertas

- [x] **§1 decisión de frontera G1**: registrada en §1 arriba (esta
      rebanada). FastAPI se mantiene como único origen desplegado en
      `127.0.0.1:8765`; `/api/*` y
      `extension/manifest.json::host_permissions` quedan sin cambios;
      el ownership de HTML / activos estáticos, el fallback de
      navegación directa, el comportamiento ante arranque / fallo de
      build, el manifiesto de consumidores activos afectados, la
      unidad atómica de cutover / rollback y los prerrequisitos de
      PR3b / G2 quedan definidos. **G1 es una decisión de frontera,
      NO una selección de Enfoque** (ver §1 arriba, "Lo que esta
      entrada NO afirma").
- [ ] **§1 selección de Enfoque (G2–G6)**: sigue abierta. Se cierra
      cuando las cinco mediciones (`BUILD-INVENTORY.json`,
      `CONSUMER-READINESS.json`, delta de paridad Playwright +
      Lighthouse, comparabilidad de hidratación,
      `cutover-rehearsal.json`) las produzcan PR3b / PR3d y el
      Enfoque elegido se registre aquí como `## §1 Enfoque: <A | B | C>`
      con cita de vuelta a
      `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
      según la regla 7.
- [ ] **Coste de hidratación en `taxonomy/tree`**: test RED en
      `tests/test_hydration_timing.py` (sin warnings `hydration`
      en consola bajo Playwright). Se cierra cuando la tarea 5.8
      de PR 5 aterrice y el delta sea `≤ 0 %`. La línea base de
      rendimiento del producto legacy que alimenta esta puerta
      **no** está en disco; la puerta queda bloqueada hasta que
      los entregables de PR 1b.3a / 1b.3b se reconstruyan.
- [ ] **Presupuesto de revisión (cerrado)**: el
      `apply-progress-es.md` §Contexto histórico de la propuesta
      estimaba ~1369 LoC para la unidad PR 2 original. La
      repartición PR 2a–2e redujo el conteo autoral por sub-PR a
      ≤ 339 LoC excepto PR 2a con 409 líneas de código+test, que
      lleva una `size:exception` aceptada (+9 líneas, +2,3 %)
      según `apply-progress-es.md` §Registro de cambios (entrada
      del 2026-08-29).

---

## Conjunto de referencias de PR 2a

Cada referencia que este diseño hace de vuelta a los artefactos
migrados de propuesta, tareas y spec:

| § de este diseño | Cita |
|---|---|
| Frontera de alcance de PR 2a | `tasks-es.md` §Fase 2a, §Fase 2b, §Fase 2c, §Fase 2d, §Fase 2e, §Fase 3, §Fase 4, §Fase 5 |
| Decisiones de arquitectura por capas | `specs/modular-architecture/spec-es.md` regla 2, regla 3, regla 5 |
| Layout de módulos (PR 2a en disco) | `tests/test_module_layers.py::CAPABILITIES`, `::LAYERS`, `::BARREL_NAME` |
| Alias de ruta de `tsconfig.json` | `specs/modular-architecture/spec-es.md` regla 5 |
| Cambios de archivos (solo PR 2a) | `proposal-es.md` §Áreas Afectadas, `tasks-es.md` §Fase 2a |
| Interfaces / Contratos | `tests/test_module_layers.py` |
| Estrategia de testing (PR 2a) | `proposal-es.md` §Fuera de Alcance ("Reescritura del backend") |
| Fuera de alcance de PR 2a | `tasks-es.md` §Fase 2b – §Fase 5 |
| Límite de rollback (PR 2a) | `apply-progress-es.md` §Límite de reversión por sub-PR |
| §1 Decisión de frontera | `proposal-es.md` §Frontera de Responsabilidad del Servidor, `specs/modular-architecture/spec-es.md` regla 7 |
| Contrato del motor de runtime | `proposal-es.md` §Dependencias ("Motor de runtime"), `tasks-es.md` tarea 3.4 |
| Línea base de evidencia de migración | `tasks-es.md` §Fase 1a.1 – §Fase 1b.3b |
| Superficie de dependencias | `proposal-es.md` §Dependencias |
| Preguntas abiertas | `apply-progress-es.md` §Contexto histórico, §Registro de cambios |

---

## Planificación del alcance de frontera PR3a

Esta sección reemplaza la asunción previa de que PR3 podía bootstrappear
una exportación estática servida por FastAPI y luego reubicar
`web/search_urls.js`. Añade **solo los artefactos de planificación de
PR3a** — el inventario de consumidores activos (§3.1) y el alcance de
la decisión de frontera G1 (§3.2). La matriz de evidencia G2–G6 y el
manifest coordinado de cutover aterrizan en rebanadas de planificación
posteriores según `tasks-es.md` §Fase 3d/3e y **no** están en este
artefacto. **La decisión de frontera misma no queda seleccionada por
este artefacto, no se registra evidencia como aprobada, y PR3e no
puede activarse hasta que G1–G6 cierren.** La exportación estática
bajo FastAPI permanece bloqueada por la propuesta y esta pasada de
planificación no la reabre.

### §3.1 Inventario de consumidores activos

Este es el inventario concreto de cada consumidor de runtime activo de
los dos bordes de ownership protegidos. Hasta que PR3e active el corte
atómico, **ninguna ruta de este mapa puede eliminarse o reubicarse**
sin romper el frontend vanilla activo o AC-21. El inventario es la
referencia autorizada para el futuro manifest coordinado de cutover
y la evidencia de readiness de consumidores G3.

#### §3.1.1 Consumidores activos del mount web de FastAPI

El proceso FastAPI actual sirve el frontend vanilla mediante:

```python
# api/server.py:1815
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
```

(`WEB_DIR = Path(__file__).parent.parent / "web"` en `api/server.py:54`;
uvicorn vinculado en `api/server.py:1820` a `127.0.0.1:8765`.)

Cada ruta de abajo es una lectura activa de runtime de ese mount:

| Ruta del consumidor | Qué lee | Cuándo |
| --- | --- | --- |
| Browser / Chrome extension / `curl GET /` | `web/index.html` (vía fallback `html=True`) | Cada carga de página |
| Browser / Chrome extension `GET /index.html` | `web/index.html` directamente | Carga directa por URL |
| Tag `<link>` en `web/index.html:13` | `web/dist/tailwind.css` (compilado por `make css`) | En cada carga de página |
| Tag `<script type="module">` en `web/index.html:2163` | `web/app.js` (el **único** tag `<script>` directo en `index.html`) | En cada carga de página |
| Líneas `import` ES en `web/app.js:39–54` | `state.js`, `api.js`, `tree.js`, `breadcrumb.js`, `detail.js`, `nav.js`, `dom.js`, `banner.js`, `help.js`, `keymap.js` (10 módulos) | Primera carga tras parsear `app.js` |
| `import()` dinámico en `web/app.js:88` | `settings.js` (perezoso — panel de settings) | Cuando el usuario abre el panel de settings |
| Líneas `import` ES en `web/nav.js:14–17` | `detail.js`, `search.js`, `tree.js`, `state.js`, `api.js`, `dom.js` | Al parsear nav.js por primera vez |
| Llamadas `import()` dinámicas en `web/nav.js:252, 295, 308, 331, 685` | `settings.js`, `file_explorer.js` (perezosos) | Perezoso al abrir settings / file-explorer |
| `import` en `web/breadcrumb.js:8` | `format.js` (junto a `dom.js` + `state.js`) | En cada render del breadcrumb |
| `import` en `web/search.js:7` | `format.js` (junto a `state.js` + `api.js` + `dom.js`) | Al parsear search.js por primera vez |
| `import()` dinámico en `web/detail.js:482` | `file_explorer.js` (perezoso — visor de archivos) | Cuando el usuario abre el file explorer |
| `import` en `web/file_explorer.js:24` | `file_viewer.js` (y `format.js`) | Al parsear file_explorer.js por primera vez |
| `web/file_viewer.js::loadScriptOnce` (URLs en líneas 25–27, helper en 40+) | libs CDN `mammoth@1.8.0`, `xlsx@0.18.5`, `epubjs@0.3.93` — URLs fijadas en `web/index.html:2180, 2188, 2194` | Perezoso al abrir .docx / .xlsx / .epub |
| `tests/test_smoke.py:150` (`test_static_index_html_served`) | `GET /index.html` (afirma 200 + HTML) | Smoke test |
| `tests/test_smoke.py:157` (`test_static_app_js_served`) | `GET /app.js` (afirma 200 + ≥1000 bytes) | Smoke test |
| `tests/test_evidence_baseline.py:276` (`test_legacy_html_present_and_nontrivial`) | lee `WEB_DIR/index.html` | Evidencia baseline PR 1a.1 |
| `tests/test_evidence_baseline.py:294` (`test_legacy_module_count_matches_exploration`) | lee `WEB_DIR.glob("*.js")` | Evidencia baseline PR 1a.1 |
| `tests/test_evidence_baseline.py:316` (`test_legacy_total_source_size_below_threshold`) | recorre bytes de `WEB_DIR` | Evidencia baseline PR 1a.1 |
| `tests/test_build_profile.py` (p. ej. `test_emit_writes_profile_with_required_keys` en línea 110) | lee `web/dist/build-profile.json` (compilado por `scripts/emit_build_profile.mjs`) | Perfil de build PR 1a.1 |
| `tests/test_hydration_timing.py` (p. ej. `test_measure_hydration_exits_zero_on_valid_artifact` en línea 140) | mide el server-shell first-paint de `web/index.html` | Evidencia de hidratación PR 1b.3a/b |
| `extension/manifest.json:13–15` (`host_permissions`) + `:21` (`content_scripts.matches`) | objetivo de inyección `http://localhost:8765/*` | Cada inyección de content-script de Chrome sobre el origen local |

**Autoridad de mover/borrar el mount**: PR3e, atómica con cada
consumidor activo listado arriba. Ninguna otra rebanada puede cambiar
este mount, la constante `WEB_DIR`, ni el directorio servido.

#### §3.1.2 Consumidores activos de `web/search_urls.js`

El actual `web/search_urls.js` exporta `SEARCH_ENGINES` (14 entradas)
y `CATEGORIES` y es consumido por código vanilla activo, por el test
contractual AC-21, y por el test de agrupación de la pestaña de
búsqueda:

| Ruta del consumidor | Qué lee | Cuándo |
| --- | --- | --- |
| `web/detail.js:24` | `import { SEARCH_ENGINES, CATEGORIES } from "./search_urls.js"` | En cada render del panel de detalle |
| `web/detail.js:325` | `new Map(SEARCH_ENGINES.map((e) => [e.key, e]))` construye `engineByKey` | En cada render del panel de detalle |
| `web/detail.js:332` | `for (const e of SEARCH_ENGINES)` puebla la UI de la pestaña Search | En cada render del panel de detalle |
| `tests/test_smoke.py:77–100` (AC-21 `test_search_engine_contract`) | `open("web/search_urls.js").read()` + parse regex sobre `{ key, label, with_authorship }` | Test contractual en cada `make test` |
| `tests/test_search_categories.py:141` | referencia `CATEGORIES in web/search_urls.js` (agrupación esperada: `general`, `taxonomic`, `academic`, `multimedia`, `documents`) | Tests de la pestaña de búsqueda |

**Espejo del lado servidor**: `api/server.py:697 _SEARCH_ENGINES = [...]`
es la fuente autorizada del servidor para `/api/taxon/{id}/searches`.
El frontend lee el archivo JS solo para fallback de `icon` y `label`
cuando la respuesta del servidor no está disponible; las URLs vienen
siempre del servidor (`urllib.parse.quote_plus`). El test contractual
AC-21 (`tests/test_smoke.py:77–100`) exige que los dos literales
coincidan en `key`, `label`, y `with_authorship` en el mismo orden.

**Autoridad de mover/borrar `web/search_urls.js`**: PR3e, atómica con
los cinco consumidores de arriba. PR3a solo puede **autorar una
ubicación futura** (p. ej. `src/data/search-engines.js`) y
documentarla; PR3e debe actualizar los imports, la ruta lectora del
test, y el archivo legacy en la misma unidad de release.

### §3.2 Alcance de la decisión de frontera single-FastAPI-origin (entrada G1)

La frontera por decidir es **cómo un único desplegable FastAPI es
dueño del origen local `127.0.0.1:8765` mientras una UI de reemplazo
se envía junto a él**. El alcance de abajo enumera cada entrada que
PR3a registra. **Ninguna entrada queda seleccionada, evidenciada, ni
implícita como aprobada por este artefacto.** La decisión real
permanece bloqueada pendiente de una futura revisión de propuesta que
aporte la evidencia que la propuesta actual rechaza explícitamente.

#### §3.2.1 Fijos (reglados, no sujetos a elección de PR3a)

- **Ownership de proceso / origen** — FastAPI es el único proceso
  desplegable y el único origen HTTP sobre `127.0.0.1:8765`
  (`api/server.py:1818–1820`:
  `if __name__ == "__main__": uvicorn.run(app, host="127.0.0.1", port=8765, ...)`).
- **Continuidad de la API** — las rutas, métodos, formas de request,
  formas de response, status codes y headers de `/api/*` permanecen
  sin cambios. AC-21 (`tests/test_smoke.py:77 test_search_engine_contract`)
  permanece sin cambios excepto por la ruta que lee.
- **Continuidad de la extensión** — `extension/manifest.json::host_permissions`
  se queda en `["http://localhost:8765/*"]` (líneas 13–15);
  `content_scripts.matches` se queda en `["http://localhost:8765/*"]`
  (línea 21). Ni un segundo origen, ni un puerto nuevo.
- **Cumplimiento del monolito modular** — las reglas 1–7 de
  `specs/modular-architecture/spec-es.md` son vinculantes para el
  enfoque elegido.

#### §3.2.2 En alcance (requieren decisión)

- **Owner del HTML** — qué proceso sirve `/`, `index.html`, y el
  fallback para navegación directa a rutas desconocidas (deep links
  a `/taxon/{id}` y similares).
- **Owner de los assets estáticos** — qué proceso sirve los bundles
  JS, CSS, fonts, y cualquier otro `/assets/*`.
- **Contrato de build/start** — comandos exactos, comprobación del
  runtime de Node (`node --version ≥ 20.9.0`), ubicación del
  artefacto, y comportamiento ante fallo. **Un fallo de build NO
  debe caer silenciosamente al runtime legacy.**
- **Fallback de navegación directa** — mecanismo exacto para
  `/taxon/{id}` y otras rutas solo-cliente cuando se llegan sin un
  roundtrip al servidor.
- **Unidad de cutover/rollback** — rutas exactas cambiadas juntas en
  la activación y límite exacto de reversión.

#### §3.2.3 Fuera de alcance (ya rechazados por la propuesta)

- **Exportación estática bajo FastAPI** — bloqueada por las puertas
  de evidencia; no es default, fallback, ni objetivo de
  implementación en PR3b–PR3e. Reabrirla exige una revisión de
  propuesta con evidencia nueva.
- **Dos runtimes activos independientes** — rechazado; coordinated
  legacy cut, no capa de compatibilidad.
- **Migración solo del mount o solo del archivo de búsqueda** —
  rechazado; ambos bordes deben moverse atómicamente con todos los
  consumidores (§3.1).
- **Cualquier cosa que requiera cambiar `/api/*`, el manifest de la
  extensión, o el comportamiento de SQLite/DB** — fuera del alcance
  de este cambio.

#### §3.2.4 Autoridad de la decisión

Cuando la frontera G1 se registre (futura revisión de propuesta +
evidencia G1), DEBE:

1. Cumplir las reglas 1–7 de `specs/modular-architecture/spec-es.md`.
2. Citar `specs/modular-architecture/spec-es.md` como autoridad
   arquitectónica.
3. Listar cada ruta de consumidor activo que impacta; cada una debe
   aparecer en el futuro manifest coordinado de cutover.
4. Pasar G1 (este artefacto, actas de revisión de diseño) antes de
   que arranque cualquier trabajo de PR3b/3c/3d/3e.

### §3.3 Productores y umbrales de evidencia

Cada puerta tiene un productor nombrado, un comando de invocación, una ruta de artefacto y un umbral de aceptación. **Ninguna puerta queda marcada como aprobada por este artefacto.** Evidencia ausente, fallida, obsoleta (>7 días) o incomparable queda **bloqueada**, nunca aprobada. PR3a registra la matriz productor + comando + artefacto + umbral abajo; PR3b–PR3e adjuntan los resultados reales.

#### §3.3.2 G2 — construcción de base

| Campo | Valor |
| --- | --- |
| Productor | `scripts/verify_build.py` (AÚN NO AUTORIADO — se enviará en PR3b junto a la base) |
| Comando | `python scripts/verify_build.py --out <build-root> --node-min 20.9.0` |
| Artefacto | `<build-root>/BUILD-INVENTORY.json` + log de build + snapshot `node --version` |
| Umbral | (a) comando de build sale 0; (b) inventario lista cada artefacto esperado (entrada HTML, bundles JS, CSS, fuentes); (c) versión Node cumple `≥20.9.0`; (d) fallo de build produce salida no-cero y **no** recurre silenciosamente al legado |

##### §3.3.2.1 Definición del contrato G2 (entrada canónica para el verificador strict-TDD G2)

Esta subsección es la entrada canónica para el verificador strict-TDD G2 posterior (`scripts/verify_build.py` + `<build-root>/BUILD-INVENTORY.json`). **G2 queda `bloqueado — contrato definido; verificador no implementado`**, no `aprobado`, hasta que cada aserción de abajo quede escrita y en verde.

| Perilla | Valor |
| --- | --- |
| Raíz del workspace candidato (autorizado, sin activación) | `tools/g2-candidate/` — según la tarea del padre. El workspace candidato **no** cablea FastAPI, `web/`, CI, `package.json` raíz, `Makefile`, ni `extension/manifest.json`. **No** selecciona el Enfoque A / B / C. **No** selecciona exportación estática. Existe solo como raíz de build autocontenida para verificación G2; montar su salida bajo FastAPI es una decisión separada G3+G6. |
| Comando de build esperado | `<candidate-root>/node_modules/.bin/next build` invocado con `cwd = <candidate-root>`; salida no-cero se propaga; **sin** fallback silencioso a ficheros del legado; captura de stdout/stderr en `<candidate-root>/build.log`. |
| Raíz de salida de build esperada | `<candidate-root>/out/` (exportación estática de Next.js; `next.config.mjs` lleva `output: "export"` más `images: { unoptimized: true }` y `trailingSlash: false`). |
| Clases de activos requeridas (ruta-de-aplicación) | (i) única entrada HTML de ruta-de-aplicación normal `<candidate-root>/out/index.html`; (ii) **clase JS** = uno-o-más ficheros `*.js` no vacíos en cualquier punto bajo `<candidate-root>/out/_next/static/chunks/**` (Next.js 16 / Turbopack emite chunks JS planos **sin requisito del subdirectorio `chunks/app/`**); (iii) **clase CSS** = uno-o-más ficheros `*.css` no vacíos en cualquier punto bajo `<candidate-root>/out/_next/static/chunks/**` (los bundles CSS están co-ubicados con los chunks JS bajo `chunks/**`, **no** bajo un directorio separado `static/css/`); (iv) fuentes estáticas bajo `<candidate-root>/out/_next/static/media/` si se usa `next/font`. El verificador clasifica `index.html` como la **única** entrada HTML de ruta-de-aplicación normal; `404.html` y `500.html`, si Next.js los emite, se registran bajo la clase de activo **separada** `error_pages` (ver siguiente fila) y nunca bajo la clase de ruta-de-aplicación. |
| Exenciones de página de error (clasificadas aparte) | `404.html` y `500.html` son exenciones de página de error explícitamente permitidas. Si están presentes, el verificador las registra bajo la clase de activo **separada** `error_pages` — **no** se promueven a entradas de ruta-de-aplicación, **no** se listan bajo `assets[]` para la clase `application_route_html`, y su ausencia **nunca** es un fallo de clases faltantes para el contrato de ruta-de-aplicación. Su presencia se reporta, no se requiere. |
| Staging post-build de manifiestos (atómico) | Antes de validar el inventario, el verificador G2 DEBE hacer staging atómicamente de los manifiestos de Next desde `<candidate-root>/.next/` a `<candidate-root>/out/.next/` contra el **contrato verificado de Next.js 16 / Turbopack**: `<candidate-root>/.next/build-manifest.json` → `<candidate-root>/out/.next/build-manifest.json` es **requerido** (el fallo de clase faltante es su ausencia de la salida del build); `<candidate-root>/.next/app-build-manifest.json` → `<candidate-root>/out/.next/app-build-manifest.json` es **opcional y nunca un fallo de clase faltante** — el verificador intenta la copia solo cuando el manifiesto fuente existe, registra `staged` / `not_emitted` en `assets[]`, y nunca falla por su ausencia (el build limpio real de Next 16.3.3 / Turbopack emite solo `build-manifest.json`). El staging de `build-manifest.json` es todo-o-nada: cualquier fallo individual de copia del manifiesto requerido aborta el paso de staging, retira cualquier staging parcial, **no** deja ningún `BUILD-INVENTORY.json` válido en disco, y propaga una salida no-cero. El verificador valida los manifiestos en staging solo después de que la copia requerida de `build-manifest.json` tenga éxito; la ausencia de `<candidate-root>/.next/build-manifest.json` es un fallo de staging. |
| Excepción de tamaño (fichero generado, condicional) | Una `size:exception` se aplica **solo** a `tools/g2-candidate/package-lock.json`, y **solo después** de que `npm ci` salga 0 contra el `tools/g2-candidate/package.json` local del candidato. La excepción es condicional y nula si `npm ci` falla (no se commitea ningún `package-lock.json`). **Ningún otro fichero generado bajo `tools/g2-candidate/` queda exceptuado** del presupuesto de revisión por PR — todo otro artefacto generado (salida de build, manifiestos, logs, artefactos de captura, otros lockfiles) cuenta bajo el tope de líneas autoradas. |
| Esquema y ubicación del inventario | `<candidate-root>/out/BUILD-INVENTORY.json` — objeto JSON con claves `node_version` (string, ≥ `"20.9.0"`), `candidate_root` (string), `build_command` (string), `build_started_at` / `build_finished_at` (strings ISO-8601), `exit_code` (int), `assets[]` (cada entrada: `{class, path, sha256, bytes}`), `missing_classes[]` (clases de activo ausentes de `out/`); emitido atómicamente por el verificador G2 **solo cuando** toda precondición se cumple: `npm ci` sale 0 (si no, no aplica la excepción de `package-lock.json`); versión Node `≥ 20.9.0`; el build sale 0; el staging post-build de manifiestos (fila arriba) hace staging atómicamente de `build-manifest.json` (requerido) y hace staging best-effort de `app-build-manifest.json` (opcional, `not_emitted` **no** es una entrada de clase faltante); cada clase de activo de ruta-de-aplicación requerida está presente con bytes no-cero (CSS + JS ambos bajo `_next/static/chunks/**`, sin requisito de `static/css/`, sin requisito de `chunks/app/`); `404.html` / `500.html` si presentes se reportan bajo la clase separada `error_pages` (su ausencia no falla el contrato de ruta-de-aplicación). Ante cualquier fallo (build, staging del manifiesto requerido, clase de ruta-de-aplicación requerida faltante, versión Node) el verificador sale no-cero y **no** emite ningún `BUILD-INVENTORY.json` válido. |
| Versión de Node requerida | `>= 20.9.0` (requisito duro de Next.js 16); capturada desde `node --version` al inicio del verificador G2; desajuste falla rápido con salida no-cero **antes** de invocar el build. |
| Semántica de fallo | (a) build sale no-cero → verificador sale no-cero, no se emite `BUILD-INVENTORY.json`; (b) la copia de staging de `build-manifest.json` **requerido** falla o la fuente está ausente → verificador sale no-cero, no se emite `BUILD-INVENTORY.json`, staging parcial limpiado; (b′) `app-build-manifest.json` opcional ausente (`not_emitted`) → **no** es un fallo, se registra como `not_emitted` en `assets[]` solo cuando el verificador elige registrarlo (presencia/ausencia nunca acota el contrato); (c) build sale 0 pero falta clase de activo de ruta-de-aplicación requerida (único `index.html`, `*.css` no vacíos bajo `_next/static/chunks/**`, `*.js` no vacíos bajo `_next/static/chunks/**`) → verificador sale no-cero, no se emite `BUILD-INVENTORY.json` (entradas `error_pages` ausentes NO son un fallo); (d) versión Node por debajo de `20.9.0` → verificador sale no-cero antes de invocar el build; (e) `<candidate-root>/out/index.html` ausente pese a build exitoso → verificador clasifica como fallo de clases faltantes. **No se permite el fallback silencioso a ficheros del legado en ninguna rama.** |
| Frontera de verificación (precondiciones del verificador strict-TDD G2) | El verificador strict-TDD G2 posterior DEBE implementarse contra este contrato: asertar cada clase de activo de **ruta-de-aplicación** requerida presente con bytes no-cero y `sha256` estable (clase CSS = `*.css` bajo `_next/static/chunks/**`, clase JS = `*.js` bajo `_next/static/chunks/**`; asertar **sin** requisito de un directorio separado `_next/static/css/` ni de un subdirectorio `_next/static/chunks/app/`); asertar que `<candidate-root>/out/index.html` es la **única** entrada HTML de ruta-de-aplicación (asertar que cualquier `404.html` / `500.html` si presente queda clasificado bajo `error_pages`, **no** promovido a `application_route_html`); asertar que el paso de staging post-build de manifiestos tuvo éxito antes de cualquier otra aserción de clase de activo — `build-manifest.json` es **requerido** (fuente ausente o copia fallida es un fallo) y `app-build-manifest.json` es **opcional** (el verificador intenta la copia solo cuando el manifiesto fuente existe, registra `staged` / `not_emitted`, y nunca falla por su ausencia); asertar versión de Node `≥ 20.9.0` desde `node --version`; asertar que el código de salida del verificador se propaga a `make g2-candidate-build` para que ningún fallback silencioso al legado sea posible. Montar bajo el `StaticFiles` de FastAPI (sigue en `127.0.0.1:8765`) **no** es parte de G2; es incumbencia G3+G6. **Hasta que esas aserciones queden escritas y en verde, G2 queda `bloqueado — contrato definido; verificador no implementado`, no `aprobado`.** |

#### §3.3.3 G3 — preparación de consumidores

| Campo | Valor |
| --- | --- |
| Productor | `scripts/verify_consumers.py` (AUTORIADO en disco — verificador fusionado vía PR #109 `test(g3): verify consumer readiness`; augmento de runtime controlado `--serve` / `--venv` / `--repo-root` / `--fixture-web-root` fusionado vía PR #111 `fix(g3): control readiness verification runtime`; aplicación fail-closed de forma HTTP vía `tools/g3-legacy-fixture/scripts/check_http_status.py` fusionada vía PR #115 `fix(g3): enforce HTTP consumer expectations`; preservación de symlinks de virtualenv fusionada vía PR #116 `fix(g3): preserve virtualenv Python paths`) |
| Comando | `python scripts/verify_consumers.py --manifest openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json --out <build-root> [--serve --venv <repo>/.venv/bin/python --fixture-web-root <repo>/tools/g3-legacy-fixture/web --repo-root <repo>]` |
| Artefacto | `<build-root>/CONSUMER-READINESS.json` |
| Umbral | para cada consumidor listado en §3.1, el `cutover-manifest.json` canónico (§3.3.3.1) nombra `current_path`, `ownership_edge`, `replacement`, `verification`, `activation_status`, `rollback`; **fail-closed**: cualquier `activation_status: unselected` => el verificador sale no-cero y no emite ningún `CONSUMER-READINESS.json` válido; ningún consumidor de §3.1 permanece "activo" contra una ruta que PR3e pretende eliminar. **La selección es de dos niveles**: (Nivel-1) **selección legacy pre-cut** queda autorada el 2026-08-30 para cada consumidor contra la `current_path` del legado en disco y **verificada el 2026-08-30 por PR #116** para los **26 / 26** consumidores vía `--serve --venv --fixture-web-root --repo-root` (enrutamiento fail-closed de forma HTTP a través de `tools/g3-legacy-fixture/scripts/check_http_status.py`); (Nivel-2) **selección atomic-cut** (reemplazo post-corte con el artefacto de build del Enfoque A / B / C elegido) requiere PASS de G2 + G4 + G5 + G6 y queda para PR3d/PR3e. Las filas contractuales de Nivel-1 / Nivel-2 en §3.3.3.1 (abajo) hacen el modelo dual vinculante para el futuro verificador strict-TDD. |
| **Disposición (evidencia canónica 2026-08-30 — merge PR #116)** | **PASS — preparación de consumidores Nivel-1 (legacy pre-cut) verificada end-to-end sobre un merge limpio de PR #109 + PR #111 + PR #115 + PR #116 en `origin/develop`.** Los **26 / 26** consumidores de `design.md::§3.1` ejecutan su `verification.command` contra el fixture controlado (`tools/g3-legacy-fixture/web/` servido por `python -m http.server` en un puerto libre aislado vía `--fixture-web-root`) con aplicación fail-closed de forma HTTP enrutada a través de `tools/g3-legacy-fixture/scripts/check_http_status.py`; cada comando sale `0`; un `<build-root>/CONSUMER-READINESS.json` válido se emite atómicamente (el esquema valida: `manifest_path`, `manifest_sha256`, `node_version ≥ 20.9.0`, `verified_at`, `exit_code = 0`, cada `consumers[].status = "ready"`, `unselected_count = 0`, `failed_verifications[]` vacío, `activation_complete = true`). **El PASS de Nivel-1 NO implica PASS de Nivel-2** — Nivel-2 (selección atomic-cut contra el artefacto de build del Enfoque A / B / C elegido) sigue acoado por PASS de G4 + G5 + G6; los Enfoques A / B / C quedan sin seleccionar; no ocurre ninguna activación de FastAPI. |
| **Línea de comando canónica (captura de evidencia PR #116)** | `python scripts/verify_consumers.py --manifest openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json --out <build-root> --serve --venv <repo-root>/.venv/bin/python --fixture-web-root <repo-root>/tools/g3-legacy-fixture/web --repo-root <repo-root>` — `--serve` arranca el servidor local controlado (elegido por `--serve --fixture-web-root` como `python -m http.server` contra el árbol `web/` del fixture en un puerto TCP libre elegido por el SO, nunca el `8765` del legado); `--venv` reescribe cualquier token `pytest` inicial del `verification.command` al python del venv resuelto (PR #116 preserva la ruta del symlink para que Python mantenga su venv); `--fixture-web-root` reescribe la URL `127.0.0.1:<legacy>` de cada consumidor al puerto aislado elegido; las expectativas con forma HTTP (`"200"`, `"200 for each"`) se enrutan a través de `tools/g3-legacy-fixture/scripts/check_http_status.py` (descubierto en `<repo-root>/tools/g3-legacy-fixture/scripts/check_http_status.py`; fail-closed si está ausente — PR #115). Las expectativas sin forma HTTP (`"ok"`, `"1 passed"`, `"all passed"`, texto arbitrario) mantienen la semántica de sólo-exit-del-shell. |
| **Cobertura (evidencia 2026-08-30)** | Los **26** consumidores de `design.md::§3.1` pasan — **21** en §3.1.1 (mount web de FastAPI: 2 lecturas HTML `mount-runtime-html-root-001` + `mount-runtime-html-direct-002`, 1 link CSS `mount-runtime-link-tag-css-003`, 1 entrada JS módulo `mount-runtime-script-tag-app-js-004`, 4 ES-import `mount-runtime-import-app-js-modules-005` + `mount-runtime-import-nav-js-modules-007` + `mount-runtime-import-breadcrumb-js-008` + `mount-runtime-import-search-js-009`, 3 import dinámico `mount-runtime-dynamic-import-app-js-settings-006` + `mount-runtime-dynamic-import-nav-js-file-explorer-settings-010` + `mount-runtime-dynamic-import-detail-js-file-explorer-011`, 1 pin CDN `mount-runtime-cdn-pin-file-viewer-012`, 3 smoke/evidence-baseline tests `test-contract-smoke-static-index-013` + `test-contract-smoke-static-app-js-014` + `test-evidence-baseline-legacy-html-015` / `test-evidence-baseline-module-count-016` / `test-evidence-baseline-source-size-017` (plegados por resumen de cobertura), 2 tests build-profile/hidratación `test-build-profile-emit-keys-018` + `test-hydration-timing-valid-artifact-019`, 1 pin de manifest de extensión `extension-manifest-origin-pin-020`) + **5** en §3.1.2 (`web/search_urls.js`: 3 usos de runtime en detail.js `search-urls-runtime-detail-import-001` + `search-urls-runtime-detail-engineByKey-002` + `search-urls-runtime-detail-populate-003`, 2 tests contractuales `search-urls-test-contract-ac21-004` + `search-urls-test-search-categories-005`). Ningún consumidor queda `unselected` contra Nivel-1. |
| **Lo que este PASS NO afirma** | (i) NO afirma PASS de G3 para **Nivel-2** (atomic-cut): Nivel-2 sigue requiriendo G4 (paridad Playwright + Lighthouse) + G5 (línea base de hidratación reproducible — actualmente `irreproducible` según auditoría §3.3.5) + G6 (éxito del dry-run de `cutover-rehearsal.json`). (ii) NO afirma que **A / B / C** esté seleccionado; la exportación estática (Enfoque A) y B / C quedan sin seleccionar hasta que la evidencia de Nivel-2 cierre. (iii) NO afirma **activación de FastAPI**: ningún repoint de `WEB_DIR`, ningún cutover atómico, ninguna mutación de `api/server.py`, ningún cambio en Makefile / extensión / fuente de producto queda implicado. El frontend vanilla del legado continúa sirviéndose exactamente como en `develop`. (iv) NO altera el `cutover-manifest.json` canónico ni ningún `<build-root>/CONSUMER-READINESS.json` emitido previamente — el manifiesto se queda en 26 consumidores de §3.1 (Nivel-1 `selected`, Nivel-2 unselected) y el artefacto de readiness es una **emisión nueva** bajo la captura de evidencia de PR #116. |
| **Camino de cierre hacia adelante** | (1) Reconstruir la línea base del legado bajo el CLI G5 actual según el camino de cierre de §3.3.5 para que exista un delta reproducible candidato-vs-línea-base; (2) autorar `scripts/rehearse_cutover.py` y producir `cutover-rehearsal.json` según §3.3.6; (3) aterrizar el harness de paridad Playwright + Lighthouse y producir informes de paridad según §3.3.4 (G4); (4) solo después de que G4 + G5 + G6 cierren, llevar cada consumidor a Nivel-2 `selected` contra el artefacto de build del Enfoque elegido y re-ejecutar el verificador G3 para evaluación de Nivel-2; (5) la emisión de Nivel-2 reemplaza (o aumenta) la emisión de Nivel-1 con reemplazos de ruta nueva y preparación atomic-cut. Hasta que (1)–(3) cierren, **G3 queda `aprobado para Nivel-1; no aprobado para Nivel-2`**. |

##### §3.3.3.1 Definición del contrato G3 (entrada canónica para el verificador strict-TDD G3)

Esta subsección es la entrada canónica para el verificador strict-TDD G3 (`scripts/verify_consumers.py` + `<build-root>/CONSUMER-READINESS.json`; autordado vía PR #109 + PR #111; aplicación fail-closed de forma HTTP + preservación de symlinks de virtualenv autordadas vía PR #115 + PR #116). Define el inventario machine-readable canónico en `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`, el esquema de `CONSUMER-READINESS.json`, la semántica atómica / de fallo, y los requisitos de fixtures de test. **G3 APRUEBA para Nivel-1 (preparación legacy pre-cut) — el verificador (`scripts/verify_consumers.py`, AUTORIADO en disco vía PR #109 + PR #111 + PR #115 + PR #116) ejecuta el `verification.command` de cada consumidor de §3.1 contra el fixture controlado (`tools/g3-legacy-fixture/web/`) con `--serve --venv --fixture-web-root --repo-root`; los 26 / 26 consumidores salen `0`; `<build-root>/CONSUMER-READINESS.json` se emite atómicamente con `activation_complete: true`, `unselected_count: 0`, `failed_verifications[]` vacío, y `exit_code: 0`.** **G3 NO APRUEBA para Nivel-2 (selección atomic-cut) — Nivel-2 sigue requiriendo PASS de G4 + G5 + G6; la pasada de Nivel-2 aterriza en PR3d/PR3e y NO queda en esta pasada de planificación.** La selección es **de dos niveles**: Nivel-1 (legacy pre-cut, APROBADO 2026-08-30 vía PR #116) NO requiere PASS de G2/G4/G5/G6; Nivel-2 (atomic-cut, acoado por PASS de G4/G5/G6) aterriza en PR3d/PR3e y NO queda en esta pasada de planificación.

| Perilla | Valor |
| --- | --- |
| Ruta del manifiesto canónico | `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` — fuente única de verdad para cada consumidor activo en `design.md::§3.1`. Autorado el 2026-08-30 con los 26 consumidores enumerados (21 en §3.1.1 mount web de FastAPI + 5 en §3.1.2 `web/search_urls.js`); **selección legacy pre-cut (Nivel-1) autorada el 2026-08-30 para cada consumidor** — cada consumidor lleva `activation_status: selected` y `replacement.status: selected` contra su `current_path` del legado en disco (el campo `replacement.path` nombra el fichero del legado o el conjunto de ficheros del legado que el consumidor lee actualmente; la `replacement.note` documenta la semántica de Nivel-1). Ningún consumidor queda sin seleccionar contra la línea base del legado pre-cut; **la selección de Nivel-1 APROBÓ el 2026-08-30 vía merge de PR #109 + PR #111 + PR #115 + PR #116** (los 26 / 26 consumidores verifican limpio contra el fixture controlado; comando canónico + detalles del artefacto en la fila `Disposición` de §3.3.3 arriba). La futura pasada atomic-cut (Nivel-2) reemplaza (o aumenta) las entradas de Nivel-1 con reemplazos de ruta nueva bajo PASS de G4 + G5 + G6. |
| Forma de nivel superior del manifiesto | Objeto JSON con claves `$schema_version`, `change`, `planning_artifact`, `generated_by`, `scope_intent`, `anchor`, `fail_closed_summary`, `edges[]` (cada uno `{id, label, anchor, single_origin_contract}`), `consumers[]`, `selection_invariants`, `verifier_contract_summary`. El manifiesto DEBE listar **cada** consumidor activo de §3.1 (sin omisión, sin colapsar); añadir un consumidor exige enmendar tanto `cutover-manifest.json` como `design.md::§3.1` en la misma pasada de planificación. |
| Esquema del registro de consumidor | Cada entrada en `consumers[]` DEBE llevar los siete campos `id` (string estable), `ownership_edge` (debe igualar uno de `edges[].id`), `current_path` (la ruta de runtime / ruta lectora de test actualmente activa contra el borde de ownership elegido), `replacement` (`{status: "unselected" | "selected", path?, note?}`), `verification` (`{command, expect}`), `activation_status` (`"unselected" | "selected"`), `rollback` (la sentencia exacta de revert que restaura `current_path`). El verificador rechaza cualquier registro al que le falte uno de estos campos. |
| Convención de ID estable | `id` DEBE seguir `<edge-prefix>-<kind>-NNN` donde `<edge-prefix>` es `mount-` (mount web FastAPI) o `search-urls-` (`web/search_urls.js`), `<kind>` es un slug corto (p. ej. `runtime-html-root`, `runtime-es-import-static`, `runtime-cdn-pin`, `test-contract-smoke`, `test-contract-ac21`, `extension-manifest-origin-pin`), y `NNN` es un contador de 3 dígitos con cero a la izquierda por cubo `(edge, kind)`. Los IDs son inmutables una vez emitidos; renombrar un ID exige una nueva pasada de planificación y una nota de migración en `apply-progress.md`. |
| Unidad atómica de cutover | PR3e DEBE actualizar (1) la constante `WEB_DIR` en `api/server.py:54`, (2) **cada** consumidor en `cutover-manifest.json` (imports, ruta lectora AC-21, cada consumidor de test, cada línea de pin CDN), (3) los targets `make api` / `make web` del Makefile, y (4) el artefacto de build del Enfoque elegido, **en un único release**. La activación parcial la rechaza el verificador; el `atomic_cutover_invariant` del manifiesto lo codifica. |
| Unidad de rollback | `git revert <pr3e-sha>` restaura cada `current_path` del manifiesto simultáneamente. El revert parcial se rechaza bajo G1 (según registro de decisión §1). El `rollback_invariant` del manifiesto lo codifica. |
| Semántica de fallo (fail-closed, dos niveles) | (a) cualquier consumidor con `activation_status: unselected` => el verificador sale no-cero, no emite `CONSUMER-READINESS.json`; (b) cualquier consumidor con `replacement.status: unselected` => igual; (c) cualquier consumidor al que le falte un campo requerido => igual; (d) cualquier consumidor con `verification.command` que sale no-cero contra el runtime legacy pre-cut (evaluación de Nivel-1) O contra `<build-root>` (evaluación de Nivel-2) => igual; (e) la evaluación de Nivel-2 no puede comenzar a menos que la evaluación de Nivel-1 pase Y PASS de G2/G4/G5/G6, y un fallo de Nivel-2 cierra el artefacto igual que un fallo de Nivel-1; (f) versión Node por debajo de `20.9.0` => igual (paridad con G2); (g) `CONSUMER-READINESS.json` se escribe **solo** atómicamente (temp file + rename) y **solo** cuando toda precondición arriba se cumple. **No se permite el fallback silencioso a ficheros del legado bajo ninguna rama.** |
| Esquema de `CONSUMER-READINESS.json` | Objeto JSON emitido por `scripts/verify_consumers.py` en `<build-root>/CONSUMER-READINESS.json`. Claves requeridas: `manifest_path` (string), `manifest_sha256` (string, hash estable del manifiesto canónico), `node_version` (string, ≥ `"20.9.0"`), `verified_at` (string ISO-8601), `exit_code` (int, DEBE ser `0` para un artefacto válido), `consumers[]` (una entrada por consumidor del manifiesto con `{id, current_path, replacement_path?, verification_exit_code, activation_status, status: "ready" | "not_ready"}`), `unselected_count` (int), `failed_verifications[]` (lista de `{id, command, exit_code, stderr_tail}`), `activation_complete` (bool, DEBE ser `true` para un artefacto válido). El artefacto es **inválido** cuando `activation_complete` es `false` O `exit_code != 0` O `unselected_count > 0` O existe cualquier entrada en `failed_verifications[]`. El verificador lo escribe vía temp-file + rename y retira cualquier fichero parcial ante fallo. |
| Requisitos de fixtures de test | (i) el `cutover-manifest.json` canónico mismo (commiteado en este cambio; sirve como fixture red/green del parser de esquema del verificador); (ii) un `tmp_path/<fixture-manifest>.json` transitorio por test, parametrizado sobre (a) un consumidor con `activation_status: unselected` (espera salida no-cero, sin artefacto), (b) un consumidor con `replacement.status: unselected` (espera salida no-cero, sin artefacto), (c) un consumidor al que le falta un campo requerido (espera salida no-cero, sin artefacto), (d) un consumidor cuyo `verification.command` devuelve no-cero (espera salida no-cero, sin artefacto), (e) cada consumidor con `activation_status: selected` y `verification.command` que devuelve `0` (espera salida cero, artefacto válido con `activation_complete: true`); (iii) una fixture de estabilidad SHA256 que aserta que el `manifest_sha256` del manifiesto coincide entre dos ejecuciones consecutivas del verificador contra el mismo manifiesto en disco; (iv) una fixture de invariante fail-closed que aserta que el verificador NUNCA escribe `CONSUMER-READINESS.json` cuando sale no-cero. |
| Regla de selección — Nivel-1 (legacy pre-cut) | Para llevar un consumidor a `selected` bajo Nivel-1 (legacy pre-cut, registrado el 2026-08-30 para cada consumidor), el manifiesto DEBE nombrar `replacement.path` igual a (o consistente con) la `current_path` del legado en disco Y `replacement.note` DEBE documentar la semántica de Nivel-1 Y `verification.command` DEBE apuntar al runtime del legado alcanzable en el mount de FastAPI sobre 127.0.0.1:8765 (o la ruta lectora de fichero equivalente). **Nivel-1 NO requiere PASS de G2/G4/G5/G6** — Nivel-1 es un artefacto de documentación que nombra el destino legacy pre-cut por consumidor; el frontend vanilla del legado continúa sirviéndose exactamente como en `develop` (sin repoint de `WEB_DIR`, sin cutover atómico, sin activación de FastAPI). **Nivel-1 ES un PASS de G3** — cada consumidor de Nivel-1 quedó verificado el 2026-08-30 vía merge de PR #109 + PR #111 + PR #115 + PR #116 contra el fixture controlado con `--serve --venv --fixture-web-root --repo-root`; los 26 / 26 consumidores salen `0`; `<build-root>/CONSUMER-READINESS.json` se emite atómicamente (ver la fila `Disposición` de §3.3.3 arriba para la evidencia canónica del PASS). |
| Regla de selección — Nivel-2 (atomic-cut, acoado) | Para llevar un consumidor a `selected` bajo Nivel-2 (atomic-cut, reemplazo post-corte con el artefacto de build del Enfoque A / B / C elegido), el manifiesto DEBE nombrar `replacement.path` + `verification.command` + `verification.expect` para la **ruta nueva** Y DEBE existir evidencia de test fallido para la ruta nueva Y G2 (`BUILD-INVENTORY.json` reproducible — ya `aprobado` el 2026-08-30 desde `taxa-worktrees/migrate-nextjs-g2-evidence-capture`) + G4 (paridad Playwright + Lighthouse) + G5 (línea base de hidratación reproducible — actualmente `irreproducible` según auditoría §3.3.5) + G6 (éxito del dry-run de `cutover-rehearsal.json`) DEBEN estar todas `aprobadas`. La exportación estática (Enfoque A) y cualquier otro Enfoque (B / C) siguen sin seleccionar hasta que esas puertas cierren; **ningún consumidor se lleva a Nivel-2 en esta pasada de planificación**. La entrada de Nivel-2 queda registrada junto a (NO reemplazando) las entradas de Nivel-1 cuando PR3d/PR3e corra. |
| Estado combinado de selección | El estado del manifiesto del 2026-08-30 es **Nivel-1 seleccionado para cada consumidor, Nivel-2 sin seleccionar para cada consumidor**. El verificador (autordado en disco vía PR #109 + PR #111 + PR #115 + PR #116; en `scripts/verify_consumers.py` + tests en `tests/test_verify_consumers.py`) evalúa primero Nivel-1 (preparación legacy pre-cut — cada `verification.command` sale 0 contra el runtime del legado a través del fixture controlado + `--serve --venv --fixture-web-root --repo-root`) y luego Nivel-2 (preparación atomic-cut — cada `verification.command` sale 0 contra `<build-root>` Y PASS de G2/G4/G5/G6). **La evaluación de Nivel-1 pasó el 2026-08-30 (PASS — los 26 / 26 consumidores salen 0; `CONSUMER-READINESS.json` se emite con `activation_complete: true`, `unselected_count: 0`, `failed_verifications[]` vacío, `exit_code: 0`).** La evaluación de Nivel-2 aún no se ejecuta; un fail-closed de Nivel-2 (cuando se ejecute Nivel-2) se dispara solo después de que Nivel-1 pase, y Nivel-2 requiere PASS de G4 + G5 + G6 para tener éxito. |
| Procedencia (esta pasada de planificación) | Manifiesto autorado el 2026-08-30 desde `design.md::§3.1` (inventario de consumidores activos) verbatim; cada ID de consumidor se emitió desde un namespace `mount-` o `search-urls-` nuevo; ningún consumidor se colapsó ni se fusionó. **Pasada de selección legacy pre-cut del 2026-08-30 (esta sección, segunda actualización):** cada `replacement.path`, `replacement.status` y `activation_status` de consumidor se lleva a `selected` contra la `current_path` del legado en disco; el bloque `selection_invariants` lleva un modelo de selección de dos niveles (Nivel-1 legacy pre-cut, Nivel-2 atomic-cut acoado por G2/G4/G5/G6); `all_replacements_unselected` se lleva a `false`; `fail_closed_summary` y `verifier_contract_summary` se actualizan con el lenguaje de umbrales de Nivel-1 / Nivel-2. **Pasada de registro del PASS de Nivel-1 del 2026-08-30 (esta sección, tercera actualización — merge PR #116):** la evidencia canónica del PASS G3 se captura vía `python scripts/verify_consumers.py --manifest openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json --out <build-root> --serve --venv <repo-root>/.venv/bin/python --fixture-web-root <repo-root>/tools/g3-legacy-fixture/web --repo-root <repo-root>` (las cuatro características PR #109 / #111 / #115 / #116 activas: el verificador existe, el runtime controlado existe, la aplicación fail-closed de forma HTTP existe, la preservación de symlinks de venv existe); el `verification.command` de cada consumidor de §3.1 corre contra el fixture controlado con enrutamiento fail-closed de forma HTTP a través de `tools/g3-legacy-fixture/scripts/check_http_status.py`; los 26 / 26 salen `0`; `<build-root>/CONSUMER-READINESS.json` se emite atómicamente con `activation_complete: true`, `unselected_count: 0`, `failed_verifications[]` vacío, `exit_code: 0`. **El PASS de Nivel-1 queda registrado; la selección atomic-cut de Nivel-2 sigue acoada por PASS de G4 + G5 + G6; no se implica ninguna activación de FastAPI; los Enfoques A / B / C quedan sin seleccionar.** El espejo en español `documents-es/openspec/changes/migrate-nextjs-tailwind4/design-es.md::§3.3.3.1` lleva la traducción fiel al español de esta fila. |

#### §3.3.4 G4 — paridad de comportamiento

| Campo | Valor |
| --- | --- |
| Productor | Suite Playwright + Lighthouse (AÚN NO AUTORIADO — se enviará en PR3d); `tests/test_smoke.py` existente (sin cambios) |
| Comando | `make test && make parity` (propuesto) |
| Artefacto | `parity-reports/<date>/{navigation,api,search,a11y,browser-state}.json` |
| Umbral | rutas de navegación coinciden con el legado; `/api/*` coincide con el legado (pruebas existentes verdes); AC-21 sigue pasando contra la ubicación lectora post-corte; accesibilidad ≥ puntuación del legado; claves de estado del navegador (`last-taxon-id`, `tree-source`, `selected-realm`, `version-banner-dismissed`) hidratan la UI de reemplazo idénticamente |

#### §3.3.5 G5 — comparabilidad de rendimiento

| Campo | Valor |
| --- | --- |
| Productor | `scripts/measure_hydration.py` (entregable PR 1b.3a — **reconstrucción pendiente**, no entregado a `develop`) + Lighthouse |
| Comando | `python scripts/measure_hydration.py --baseline docs/baselines/legacy-web-2026-08-26.json --candidate <build-root> --iterations 10` |
| Artefacto | `parity-reports/<date>/hydration.json` |
| Umbral | primer render server-shell dentro de ±10 % de la línea base del legado; latencia de interacción (pestañas clave / dropdown búsqueda) dentro de ±10 % de la línea base del legado; tamaño de bundle dentro del umbral declarado (TBD; registrado en PR3b) |
| **Disposición (auditoría 2026-08-30)** | **Irreproducible — no aceptado para G5.** El artefacto de línea base del legado `web/dist/evidence-baseline.json` y los ficheros de evidencia del legado observados capturan solo 2026-08-28 y carecen de: (a) línea de comando de captura; (b) log stdout/stderr de captura; (c) entorno de captura (versión Node, coincidencia de SHA256 de chromium pin, versión FastAPI, hash de ruta); (d) número de iteraciones; (e) JSON Playwright crudo; (f) JSON Lighthouse crudo (perf/a11y/best-practices); (g) fila de delta candidato vs línea base; (h) coincidencia con los flags CLI actuales de G5 (`--baseline`, `--candidate`, `--iterations`) y con el esquema actual (`parity-reports/<date>/hydration.json` con sus nombres de campo). Hasta que una línea base del legado reproducible Y una ejecución candidata reproducible estén ambas en disco y las dos se unan a través del comando + esquema G5, G5 queda **`bloqueada — línea base no reproducible; comparación no intentada`**, nunca `aprobada`. |
| **Ficheros de evidencia revisados (solo nombres; contenido no aceptado)** | (1) `web/dist/evidence-baseline.json` — captura del legado 2026-08-28; esquema pineado pero faltan metadatos de captura; (2) `tests/test_evidence_baseline.py` — tests de contrato de esquema + pin chromium; no es una captura del legado; (3) `tools/static-export-probe/scripts/capture.mjs` — captura de la sonda desechable; no es una línea base del legado; (4) `tools/static-export-probe/evidence/*.json` si están presentes — artefactos de la sonda; no son una línea base del legado. Ninguno de estos satisface el inventario de pruebas faltantes de abajo. |
| **Inventario de pruebas faltantes** | (i) línea de comando de captura; (ii) log stdout/stderr de captura; (iii) entorno de captura (versión Node, coincidencia de SHA256 de chromium pin, versión FastAPI, hash de ruta FastAPI); (iv) número de iteraciones; (v) JSON Playwright crudo; (vi) JSON Lighthouse crudo (perf/a11y/best-practices); (vii) fila de delta candidato vs línea base; (viii) coincidencia con los flags CLI actuales de G5 + nombres de campo del esquema. |
| **Camino de cierre** | (1) re-ejecutar la captura del legado bajo el CLI G5 actual (`scripts/measure_hydration.py --baseline <new-baseline.json> --candidate <legacy-server-root> --iterations 10`) para que el fichero de línea base del legado lleve los ítems de prueba faltantes; (2) re-ejecutar la captura candidata una vez que el verificador G2 (por §3.3.2 arriba) emita un `<candidate-root>/out/BUILD-INVENTORY.json` reproducible; (3) unir los dos a través del comando G5; (4) solo entonces asertar los umbrales ±10 %. **Hasta que aterrice el paso (1) del camino de cierre, G5 es irreproducible; hasta que aterrice el paso (2), el lado candidato es irreproducible; hasta que aterrice el paso (3), no existe ninguna comparación.** |

#### §3.3.6 G6 — ensayo de corte

| Campo | Valor |
| --- | --- |
| Productor | `scripts/rehearse_cutover.py` (AÚN NO AUTORIADO — se enviará en PR3d) |
| Comando | `python scripts/rehearse_cutover.py --manifest openspec/changes/migrate-nextjs-tailwind4/design.md::§3.4 --dry-run` |
| Artefacto | `parity-reports/<date>/cutover-rehearsal.json` |
| Umbral | cada ruta listada en §3.4 queda verificada por el ensayo: ruta de montaje, raíz de artefacto servido, comportamiento fallback, cada actualización de consumidor, ruta lectora AC-21; el dry-run coincide exactamente con el manifiesto; el ensayo de reversión restaura el montaje previo + el grafo canónico de consumidores |

---

`status: complete (rebanada PR 2a; alcance de frontera PR3a con plan productor/umbral de evidencia G2–G6 añadido — ninguna frontera seleccionada para el Enfoque A / B / C; contrato G2 definido en §3.3.2.1 con **cuatro** correcciones explícitas del mantenedor aplicadas contra el contrato de salida verificado de Next.js 16.3.3 / Turbopack: (1) `size:exception` SOLO para `tools/g2-candidate/package-lock.json`, solo después de que `npm ci` salga 0 contra el `package.json` local del candidato, ningún otro fichero generado exceptuado; (2) staging post-build de manifiestos atómico desde `<candidate-root>/.next/` → `<candidate-root>/out/.next/` — `build-manifest.json` requerido (su ausencia es un fallo de clase faltante), `app-build-manifest.json` opcional y nunca un fallo de clase faltante (copia best-effort registrada como `staged` / `not_emitted`); (3) `index.html` única entrada HTML de ruta-de-aplicación normal, `404.html`/`500.html` exenciones de página de error explícitamente permitidas clasificadas bajo una clase de activo `error_pages` separada; (4) **corrección del contrato de salida de Next 16 / Turbopack** — clase **CSS** requerida = uno-o-más `*.css` no vacíos bajo `out/_next/static/chunks/**` (no bajo `out/_next/static/css/`); clase **JS** requerida = uno-o-más `*.js` no vacíos bajo `out/_next/static/chunks/**` (sin requisito del subdirectorio `chunks/app/`); PASS de G2 registrado el 2026-08-30 desde el árbol limpio `taxa-worktrees/migrate-nextjs-g2-evidence-capture` sobre `develop@a74289b` (build finalizado `2026-08-30T18:11:02Z`, Node `v26.8.1`, inventario en `taxa-worktrees/migrate-nextjs-g2-evidence-capture/tools/g2-candidate/out/BUILD-INVENTORY.json` con `missing_classes[]` vacío, todas las clases requeridas de ruta-de-aplicación presentes, `build-manifest.json` en staging a 607 bytes / sha256 `f52f7edd901e373a2a24a4ecf8ba61c96ad227093c6440dc4a3a6ca58a92f2a3`, `app-build-manifest.json` opcional `not_emitted`, 14 tests enfocados del verificador + 34 del candidato pasan, log de build capturado — la advertencia de múltiples lockfiles no es bloqueante); línea base del legado de G5 dispuesta como irreproducible según auditoría §3.3.5 del 2026-08-30; contrato G3 definido en §3.3.3.1 con manifiesto machine-readable canónico en `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` autorado el 2026-08-30 que enumera los 26 consumidores de §3.1 (21 §3.1.1 mount web FastAPI + 5 §3.1.2 web/search_urls.js) con IDs estables, `current_path`, `ownership_edge`, `replacement`, `verification`, `activation_status`, `rollback`; **selección legacy pre-cut (Nivel-1) autorada el 2026-08-30 para cada consumidor** — cada consumidor lleva `activation_status: selected` y `replacement.status: selected` contra su `current_path` del legado en disco; `all_replacements_unselected` llevado a `false`; **PASS de Nivel-1 de G3 registrado el 2026-08-30 vía merge PR #109 + PR #111 + PR #115 + PR #116** — comando canónico `python scripts/verify_consumers.py --manifest openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json --out <build-root> --serve --venv <repo-root>/.venv/bin/python --fixture-web-root <repo-root>/tools/g3-legacy-fixture/web --repo-root <repo-root>`; los **26 / 26** consumidores de §3.1 ejecutan `verification.command` contra el fixture controlado (`tools/g3-legacy-fixture/web/` servido por `python -m http.server` en un puerto libre aislado) con aplicación fail-closed de forma HTTP vía `tools/g3-legacy-fixture/scripts/check_http_status.py`; cada uno sale `0`; `<build-root>/CONSUMER-READINESS.json` se emite atómicamente con `manifest_path`, `manifest_sha256`, `node_version ≥ 20.9.0`, `verified_at`, `exit_code = 0`, cada `consumers[].status = "ready"`, `unselected_count = 0`, `failed_verifications[]` vacío, `activation_complete = true`; **G3 APRUEBA para Nivel-1 (preparación legacy pre-cut)**; **G3 NO aprueba para Nivel-2** — Nivel-2 (selección atomic-cut contra el artefacto de build del Enfoque A / B / C elegido) sigue acoado por PASS de G4 + G5 + G6; los Enfoques A / B / C quedan sin seleccionar; la pasada atomic-cut de Nivel-2 aterriza en PR3d/PR3e después de que G4 / G5 / G6 cierren; el contrato §3.3.3.1 define un **modelo de selección de dos niveles** — Nivel-1 (APROBADO 2026-08-30, legacy pre-cut, sin PASS de G2/G4/G5/G6 requerido) Y Nivel-2 (atomic-cut, acoado por PASS de G4/G5/G6, NO en esta pasada); `fail_closed_summary` y `verifier_contract_summary` actualizados con umbrales de Nivel-1 / Nivel-2; **fail-closed (Nivel-1 + Nivel-2)**: el verificador G3 (`scripts/verify_consumers.py`, AUTORIADO en disco vía PR #109 + PR #111 + PR #115 + PR #116; en `scripts/verify_consumers.py` + tests en `tests/test_verify_consumers.py`) no emite ningún `CONSUMER-READINESS.json` válido mientras CUALQUIER `verification.command` salga no-cero O mientras CUALQUIER puerta de G4/G5/G6 falle (Nivel-2) O mientras falte CUALQUIER campo requerido O mientras la versión Node esté por debajo de `20.9.0` O mientras las expectativas con forma HTTP carezcan del helper `check_http_status.py` (fail-closed PR #115); G4 / G6 siguen bloqueadas (verificadores no autordos); G5 sigue `irreproducible` según auditoría §3.3.5; exportación estática sin seleccionar (los Enfoques A / B / C quedan sin seleccionar); sin activación de FastAPI (sin repoint de `WEB_DIR`, sin cutover atómico, sin cambio en `api/server.py` / Makefile / extensión / API / fuente de producto); **disposición de G3: `APROBADO para Nivel-1; NO APROBADO para Nivel-2`**; la pasada atomic-cut de Nivel-2 aterriza en PR3d/PR3e después de que G4 / G5 / G6 cierren; ninguna frontera seleccionada más allá del PASS de G2; ningún fichero fuente / tests / scripts / config / Makefile / extensión / API / fuente de producto tocado, comiteado, o pusheado en esta pasada; espejo en inglés actualizado en paralelo)`
