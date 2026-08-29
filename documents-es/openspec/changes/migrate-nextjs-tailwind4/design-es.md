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

`status: complete` · `next_recommended: "sdd-verify — volver a
correr el test enfocado de layout y las comprobaciones de la
reparación de referencias colgantes antes de que PR 2a quede
habilitado para commit + push a develop"`
