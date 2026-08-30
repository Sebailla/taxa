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

**Estado: Abierta / Basada-en-evidencia.**

La decisión entre el Enfoque A (exportación estática de `next build`
bajo FastAPI), el Enfoque B (servidor de dev Next.js completo en un
segundo puerto) y el Enfoque C (híbrido por fases) **no** queda
finalizada en esta rebanada de PR 2a. Según
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
conflicto** entre los candidatos de §1 y cualquier regla del spec
en este punto. Las reglas 1, 2, 3, 5 son neutras respecto al
framework y restringen los tres enfoques por igual; la regla 4 (el
dominio permanece libre de framework / I/O) restringe los tres
enfoques por igual; la regla 6 exige explícitamente que todo
enfoque respete las reglas 1–5; la regla 7 es esta misma entrada.

### Evidencia requerida para cerrar §1

La Decisión §1 se actualizará una vez que **toda** la siguiente
evidencia esté en disco:

1. `web/dist/build-profile.json` de PR 1a.1 + PR 1a.2
   (`scripts/emit_build_profile.mjs` + el test de esquema). Los
   números `total_bytes` y `per_route_bytes` son la entrada de §1.
2. Delta de Playwright + Lighthouse frente a la línea base legacy
   sobre el fixture chromium de PR 1b.1
   (`scripts/verify_chromium.py`) + PR 1b.2
   (`tests/test_evidence_baseline.py`).
3. Medición de coste de hidratación de PR 1b.3a +
   `tests/test_hydration_timing.py` (PR 1b.3b): los números
   `delta_server_to_tree_first_paint_ms` y `console_warnings` son
   la entrada de §1.

### Fail-safe por defecto (si la evidencia lo soporta)

Si las tres mediciones anteriores muestran que la exportación
estática de `next build` (Enfoque A) logra una regresión ≤ 0 %
sobre el presupuesto de perf y satisface todas las reglas de
`specs/modular-architecture/spec.md`, entonces **el Enfoque A es la
decisión §1 por defecto** porque preserva el contrato de puerto
único (propuesta §Incluido) y tiene el radio de impacto más
pequeño. Cualquier otro resultado exige escalar de vuelta a la
propuesta antes de que aterrice código alguno.

### Por qué §1 queda abierta en PR 2a

PR 2a solo añade el **layout** del monolito modular; no corre
`next build`, no emite `web/dist/build-profile.json`, no mide
cronometraje de hidratación y no cambia el sitio de llamada
`app.mount("/", StaticFiles(...))` de FastAPI. La decisión se
difiere deliberadamente a PR 3, que es la primera rebanada donde el
tooling de Next.js está en disco y `next build` puede correr. PR 2a
deja §1 en el estado **Abierta / Basada-en-evidencia** registrado
aquí para que el destino de la referencia de la regla 7 del spec
exista desde el día en que aterriza PR 2a, aunque el contenido de
la decisión llegue después.

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

- [ ] **§1 evidencia**: ver §1 arriba. Se cierra cuando las tres
      mediciones (perfil de build, delta Playwright + Lighthouse,
      cronometraje de hidratación) las produzcan los sub-PRs de
      PR 1 y el Enfoque elegido se registre aquí como
      `## §1 Decisión: <A | B | C>` con cita de vuelta a
      `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
      según la regla 7.
- [ ] **Coste de hidratación en `taxonomy/tree`**: test RED en
      `tests/test_hydration_timing.py` (sin warnings `hydration`
      en consola bajo Playwright). Se cierra cuando la tarea 5.8
      de PR 5 aterrice y el delta sea `≤ 0 %`.
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

#### §3.3.3 G3 — preparación de consumidores

| Campo | Valor |
| --- | --- |
| Productor | `scripts/verify_consumers.py` (AÚN NO AUTORIADO — se enviará en PR3d) |
| Comando | `python scripts/verify_consumers.py --map openspec/changes/migrate-nextjs-tailwind4/design.md::§3.1 --cut-manifest design.md::§3.4` |
| Artefacto | `<build-root>/CONSUMER-READINESS.json` |
| Umbral | para cada consumidor listado en §3.1, el manifiesto §3.4 nombra la ruta de reemplazo y una ruta de verificación; ningún consumidor de §3.1 permanece "activo" contra una ruta que PR3e pretende eliminar |

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

#### §3.3.6 G6 — ensayo de corte

| Campo | Valor |
| --- | --- |
| Productor | `scripts/rehearse_cutover.py` (AÚN NO AUTORIADO — se enviará en PR3d) |
| Comando | `python scripts/rehearse_cutover.py --manifest openspec/changes/migrate-nextjs-tailwind4/design.md::§3.4 --dry-run` |
| Artefacto | `parity-reports/<date>/cutover-rehearsal.json` |
| Umbral | cada ruta listada en §3.4 queda verificada por el ensayo: ruta de montaje, raíz de artefacto servido, comportamiento fallback, cada actualización de consumidor, ruta lectora AC-21; el dry-run coincide exactamente con el manifiesto; el ensayo de reversión restaura el montaje previo + el grafo canónico de consumidores |

---

`status: complete (rebanada PR 2a; alcance de frontera PR3a con plan productor/umbral de evidencia G2–G6 añadido — ninguna frontera seleccionada, ninguna puerta aprobada, sin manifest de cutover todavía)`
