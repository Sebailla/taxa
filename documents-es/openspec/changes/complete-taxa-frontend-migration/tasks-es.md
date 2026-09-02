# Tareas: complete-taxa-frontend-migration

> TDD estricto: ROJO → VERDE → TRIANGULAR → REFACTORIZAR. Las reglas
> del monolito modular de
> `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
> aplican a cada unidad de UI/archivo. **El Enfoque A es FINAL**
> (bloqueado el 2026-09-02; registrado en `design.md::§1`); no hay
> ruta de anulación abierta. **El predecesor
> `migrate-nextjs-tailwind4/` está congelado** — sus archivos
> DEBEN permanecer byte-idénticos durante toda la fase de apply
> de este cambio.

## Frontera de alcance para este archivo de tareas

- **En alcance**: cada sub-PR bajo el Enfoque A listado en
  `design.md` §"Sub-PR slice under Approach A" (3a, 3b, 3c, 3d,
  4a, 4b, 5a, 5b, 5c) más un **bloque de validación de Fase 6**
  (reconstrucción G5 / autoría de ensayo G6 / medición G4) que
  corre **después de que el camino candidato completo esté
  acumulado en la rama tracker
  `docs/complete-taxa-frontend-migration-plan`** pero **antes** de
  que PR 3e pueda aterrizar. PR 3e (cutover atómico) se publica solo
  cuando las seis puertas están verdes.
- **El cierre de G4 / G5 / G6 es trabajo de validación**, no un
  objetivo de migración independiente: sus artefactos se registran
  en `apply-progress.md` §Registro de cambios como flips de
  puertas, y NO DEBEN generar código nuevo en `web/**`, handlers
  de ruta nuevos en `api/server.py`, ni archivos nuevos en
  `extension/**`. Los verificadores / medidores de cierre corren
  contra la build candidata ya aterrizada (3a–5c) bajo el fixture
  de chromium que el predecesor capturó.
- **Predecesor congelado**: `openspec/changes/migrate-nextjs-tailwind4/**`
  es historia de solo lectura. La protección de rama rechaza
  cualquier PR que lo edite. La Fase 6 referencia el
  `apply-progress.md` y el `cutover-manifest.json` del predecesor
  solo como entradas de planificación.
- **Invariantes del backend FastAPI preservadas**: los handlers
  de ruta, la lógica SQLite/WAL, el flujo de materialize, la
  defensa SSRF de `save-url` y las formas byte a byte de
  `/api/*` quedan sin cambios. La constante `WEB_DIR` en
  `api/server.py:54` es la única línea que puede cambiar en
  `api/server.py` bajo el Enfoque A, más el middleware de
  fallback SPA de `next/font` `<link rel="preload">` /
  `StaticFiles` estrictamente necesario para servir
  `out/index.html` desde el montaje `StaticFiles(html=True)`
  existente.
- **TDD estricto aplicado**: cada tarea de implementación
  escribe su test que falla PRIMERO. Las tareas siguen los
  marcadores `R` (ROJO), `G` (VERDE), `T` (TRIANGULAR — escenarios
  extra más allá del mínimo que falla el primer VERDE), `Refactor`
  (limpieza sin deriva de comportamiento).

## Pronóstico de carga de revisión

| Campo | Valor |
|-------|-------|
| Líneas modificadas estimadas | ~2.225 authored a través de 13 sub-PRs (9 bootstrap + browser-state + puertos de capability + 3 validación Fase 6 + 1 cutover atómico) |
| Riesgo de presupuesto de 400 líneas | Bajo (el sub-PR más grande es 5b a ~360 líneas authored; 10 / 13 sub-PRs ≤ 230 líneas) |
| PRs encadenados recomendados | **Sí** — 13 PRs hijos encadenados (~2.225 líneas authored en total ≫ 400, y el cutover atómico exige que la feature se integre antes de llegar a `develop`) |
| División sugerida | PR 3a → 3b → 3c → 3d → 4a → 4b → 5a → 5b → 5c → Fase 6a (G5) → Fase 6b (G6) → Fase 6c (medición G4) → PR 3e (cutover atómico, con compuerta) |
| Estrategia de entrega | ask-on-risk (según preflight; el Enfoque A ya está bloqueado, sin anulación abierta) |
| Estrategia de cadena | **feature-branch-chain** (elegida por el usuario). El tracker `docs/complete-taxa-frontend-migration-plan` es draft/no-merge y es el **único** PR que apunta a `develop`; el PR hijo 3a apunta al tracker; cada hijo posterior apunta a su rama predecesora inmediata. Sustituye, para este cambio, el default de `AGENTS.md` §4 de apuntar directo a `develop`. |

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Low
```

### Topología de la cadena (Feature Branch Chain)

La rama tracker ya existe: **`docs/complete-taxa-frontend-migration-plan`**.
Permanece en **draft / no-merge** hasta que los 13 PRs hijos estén
revisados e integrados. **Nada llega a `develop` hasta que el
tracker se fusiona.**

| Posición | Sub-PR | Rama | Base (destino del PR) |
|---|---|---|---|
| Tracker | — | `docs/complete-taxa-frontend-migration-plan` | `develop` — **draft / no-merge** |
| 1 / 13 | 3a | `feat/complete-taxa-frontend-migration-01-3a` | `docs/complete-taxa-frontend-migration-plan` (tracker) |
| 2 / 13 | 3b | `feat/complete-taxa-frontend-migration-02-3b` | `feat/complete-taxa-frontend-migration-01-3a` |
| 3 / 13 | 3c | `feat/complete-taxa-frontend-migration-03-3c` | `feat/complete-taxa-frontend-migration-02-3b` |
| 4 / 13 | 3d | `feat/complete-taxa-frontend-migration-04-3d` | `feat/complete-taxa-frontend-migration-03-3c` |
| 5 / 13 | 4a | `feat/complete-taxa-frontend-migration-05-4a` | `feat/complete-taxa-frontend-migration-04-3d` |
| 6 / 13 | 4b | `feat/complete-taxa-frontend-migration-06-4b` | `feat/complete-taxa-frontend-migration-05-4a` |
| 7 / 13 | 5a | `feat/complete-taxa-frontend-migration-07-5a` | `feat/complete-taxa-frontend-migration-06-4b` |
| 8 / 13 | 5b | `feat/complete-taxa-frontend-migration-08-5b` | `feat/complete-taxa-frontend-migration-07-5a` |
| 9 / 13 | 5c | `feat/complete-taxa-frontend-migration-09-5c` | `feat/complete-taxa-frontend-migration-08-5b` |
| 10 / 13 | 6a | `feat/complete-taxa-frontend-migration-10-6a` | `feat/complete-taxa-frontend-migration-09-5c` |
| 11 / 13 | 6b | `feat/complete-taxa-frontend-migration-11-6b` | `feat/complete-taxa-frontend-migration-10-6a` |
| 12 / 13 | 6c | `feat/complete-taxa-frontend-migration-12-6c` | `feat/complete-taxa-frontend-migration-11-6b` |
| 13 / 13 | 3e | `feat/complete-taxa-frontend-migration-13-3e` | `feat/complete-taxa-frontend-migration-12-6c` |

```text
develop
 └── docs/complete-taxa-frontend-migration-plan   ← PR tracker (draft / no-merge)
      ↑ base del PR 3a: docs/complete-taxa-frontend-migration-plan
      └── feat/complete-taxa-frontend-migration-01-3a
           ↑ base del PR 3b: …-01-3a
           └── feat/complete-taxa-frontend-migration-02-3b
                ↑ base del PR 3c: …-02-3b
                └── feat/complete-taxa-frontend-migration-03-3c
                     ↑ … 3d → 4a → 4b → 5a → 5b → 5c → 6a → 6b → 6c …
                     └── feat/complete-taxa-frontend-migration-13-3e
                          ← cutover atómico, último hijo de la cadena
```

**Flujo de integración**: los hijos se fusionan **en orden** dentro
del tracker. A medida que cada hijo se fusiona, el siguiente se
reapunta al tracker (GitHub reapunta automáticamente cuando la rama
base se fusiona y se borra); el tracker acumula la feature completa.
Una vez que PR 3e (el último hijo) se fusiona, el tracker sale de
draft y se fusiona a `develop` como único punto de integración.

**El cuerpo de cada PR hijo DEBE llevar** la sección
`## Chain Context` (Chain / Tracker PR / Position / Base / Depends
on / Follow-up / Review budget / Starts at / Ends with) más un
diagrama de dependencias que marque el PR actual con `📍`. La
sección Chain Context se **añade** a la plantilla de PR del repo —
no reemplaza las secciones requeridas `## Resumen` / `## Cambios` /
`## Validación` / `## Lo que NO cambió`.

**Higiene de diff**: un PR hijo cuyo diff muestre archivos fuera de
su propia rebanada es un **bug de base**, no un hallazgo de
revisión. Reapuntar o rebasear sobre el predecesor correcto hasta
que solo aparezca la unidad de trabajo actual.

> Orden: **3a → 3b → 3c → 3d → 4a → 4b → 5a → 5b → 5c → 6a (G5)
> → 6b (G6) → 6c (medición G4) → 3e**. Cada PR hijo apunta a su
> **rama predecesora inmediata**; solo el tracker apunta a
> `develop`. La Fase 6 corre **después** de que el camino
> candidato completo (3a–5c) esté verde y acumulado en el tracker,
> y **antes** de que PR 3e pueda aterrizar. PR 3e tiene compuerta
> en G1 + G2 + G3 Tier-1 (todos registrados del predecesor) más el
> cierre de G4 + G5 + G6 (los tres entregados por la Fase 6).
> Reversión = `git revert <pr3e-sha>` (ver §"Reversión bajo la
> cadena").

## Marcadores de TDD estricto

Cada tarea usa uno de cuatro marcadores, en línea con el
vocabulario de tareas del predecesor y el precedente strict-TDD
de `tests/test_module_layers.py` /
`tests/test_no_restricted_imports.py`:

- `R` — ROJO. Autora el test que falla (o aserción expandida)
  PRIMERO. El repo DEBE permanecer verde antes de añadir el test;
  el test nuevo DEBE fallar por la razón correcta antes de
  escribir cualquier código de producción.
- `G` — VERDE. Implementa el código de producción mínimo que
  invierte ROJO a VERDE. Sin expansión de alcance más allá del
  test que falla.
- `T` — TRIANGULAR. Añade los escenarios adicionales que atrapan
  el siguiente modo de fallo (matriz parametrizada, casos de
  borde, cláusulas "y / y / y" estilo RFC-2119). Cada escenario
  de triangulación aterriza con su propio ciclo de
  test-falla-luego-pasa.
- `Refactor` — Limpia el código VERDE (renombrar, extraer,
  deduplicar). Los tests DEBEN seguir verdes; el refactor NO
  DEBE cambiar el comportamiento observable ni empujar el diff
  por encima del presupuesto de revisión de 400 líneas.

## Fase 3a: Entrada del App Router + toolchain TS (PR 3a → rama tracker)

Rebana la tarea 3.1 del predecesor (`src/app/{layout,page}.tsx` +
`next.config.mjs` + config TS / plugin de Next en `tsconfig.json`).
TDD estricto según `design.md` §"Module boundaries" (los barrels
de taxonomía / research / design-system / browser-state /
app-shell ya fueron entregados por el predecesor PR 2a; PR 3a
solo añade la página host del App Router que los consume).

- [ ] 3a.1 R — `tests/test_app_shell_render.py` (nuevo): la
  build de Next.js emite `out/index.html` con `<html lang="en">`,
  `<head>` lleva un `<meta name="viewport" content="width=device-width,
  initial-scale=1">`, y un `<link rel="preload" …>` para la
  fuente Raleway que produce `next/font`. El test lee
  `out/index.html` después de `next build` y verifica el
  contrato de marcado. <!-- sdd-owner: implementation -->
- [ ] 3a.2 G — `src/app/layout.tsx` (nuevo, ~50 LoC): shell
  host de `<html>` / `<body>`, importa `next/font/google` para
  `Raleway`, `JetBrains Mono`, `Material Symbols Outlined`,
  monta el `<AppShell>` desde `@taxa/app-shell`. Importa
  `./globals.css` para que las utilidades de Tailwind 4 estén
  disponibles en toda la app. <!-- sdd-owner: implementation -->
- [ ] 3a.3 G — `src/app/page.tsx` (nuevo, ~70 LoC): la entrada
  cliente de pantalla única — envuelve `<AppShell>` detrás de
  una frontera `"use client"`, inicializa el flag `mounted`
  para seguridad de hidratación (uso diferido a Fase 4b, pero
  el slot se reserva aquí). <!-- sdd-owner: implementation -->
- [ ] 3a.4 G — `next.config.mjs` (nuevo, ~30 LoC): declara
  `output: "export"`, `images: { unoptimized: true }`,
  `trailingSlash: false`, `reactStrictMode: true`; coincide con
  el contrato G2 en `design.md` §"Static build / start
  lifecycle". <!-- sdd-owner: implementation -->
- [ ] 3a.5 T — triangulación de `tests/test_app_shell_render.py`:
  el test también verifica que `<body>` NO lleva `data-theme`
  en el primer paint (sin lectura de localStorage antes de la
  hidratación) y lleva `data-theme` después de que el typed
  store rehidrata (verificado via stub de Playwright en Fase 6c,
  assertado aquí via presencia de marcado estático). <!-- sdd-owner: implementation -->
- [ ] 3a.6 Refactor — colapsar el par page/layout en un único
  import de `<AppShell>`; asegurar que los alias de ruta de
  `tsconfig.json` (`@taxa/<capability>`) resuelven bajo Next 16
  + Turbopack. <!-- sdd-owner: implementation -->

**Evidencia por tarea (test enfocado + harness de runtime + reversión)**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3a.1–3a.3 | `.venv/bin/python3 -m pytest tests/test_app_shell_render.py -v` | `npx next build` exit 0; `out/index.html` no vacío | `git revert <3a-sha>` elimina `src/app/{layout,page}.tsx`, `next.config.mjs`; nada más tocado |
| 3a.4 | mismo | mismo | mismo (`next.config.mjs` incluido en la reversión) |
| 3a.5 | mismo | mismo | mismo |
| 3a.6 | mismo | `npx tsc --noEmit` exit 0 contra `src/` | mismo |

## Fase 3b: Tokens de diseño + `@theme` de Tailwind 4 (PR 3b → rama del PR 3a)

Rebana la tarea 3.2 del predecesor
(`src/modules/design-system/infrastructure/globals.css` con
`@import "tailwindcss"` + `@theme` + `@layer base`) más el test de
enumeración `tests/test_tailwind_4_parity.py` que el diseño
especifica.

- [ ] 3b.1 R — `tests/test_tailwind_4_parity.py` (nuevo): lee
  `web/index.html` (fuente legacy) y verifica que cada token
  `:root { --x }` está declarado con el mismo nombre y un valor
  no vacío en `src/app/globals.css`; verifica que cada
  referencia `var(--x)` en el bloque `<style>` legacy resuelve
  a una declaración no vacía. <!-- sdd-owner: implementation -->
- [ ] 3b.2 R — `tests/test_tailwind_4_parity.py` (enumeración de
  clases de utilidad): para cada clase de utilidad que emite
  la build legacy (`bg-primary`, `text-on-surface`,
  `border-outline-variant`, `bg-surface-container-lowest`,
  `shadow-sm`, `rounded-r-md`, `bg-primary-fixed`,
  `text-on-primary-fixed`, …), el test grepea el
  `out/_next/static/chunks/*.css` generado y verifica que
  resuelve a una declaración CSS no vacía. <!-- sdd-owner: implementation -->
- [ ] 3b.3 G — `src/app/globals.css` (nuevo, ~150 LoC):
  `@import "tailwindcss";` + bloque `@theme { … }` que refleja
  cada token `:root` legacy (paleta clara, paleta oscura
  `[data-theme="dark"]`, familia `--realm-*`); bloque
  `@layer base { … }` que contiene cada regla a medida del
  bloque `<style>` legacy en orden de origen (cumple el
  requisito de orden de cascada en `design.md` §"Design
  tokens"). <!-- sdd-owner: implementation -->
- [ ] 3b.4 T — extiende el test de paridad para verificar que
  los alias del namespace `--color-primary` de Tailwind 4
  resuelven al valor legacy `--primary` (atrapa deriva
  silenciosa del namespace); verifica que `@keyframes`,
  `.animate-spin`, selectores `color-mix()`, la regla
  `body { overscroll-behavior: none; … }` y el reset
  `main > :first-child { margin-top: 0 !important; }` están
  presentes bajo `@layer base` en orden de origen. <!-- sdd-owner: implementation -->
- [ ] 3b.5 G — `src/modules/design-system/infrastructure/index.ts`
  (nuevo, ~20 LoC): el barrel exporta el `<Icon>` (envoltorio
  de glyphs Material Symbols Outlined, nombres congelados:
  `search`, `folder_open`, `folder`, `chevron_right`,
  `expand_more`, `close`, `settings`, `help`, `science`,
  `science_off`, `download`) más la primitiva de layout
  `<Button>`. <!-- sdd-owner: implementation -->
- [ ] 3b.6 Refactor — elimina cualquier literal hexadecimal de
  `src/` fuera del módulo design-system; la guardia de grep va
  en `tests/test_design_system_purity.py` (parametrizado). <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3b.1–3b.4 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` lleva las declaraciones esperadas | `git revert <3b-sha>` elimina `src/app/globals.css` y `src/modules/design-system/**`; Fase 3a intacta |
| 3b.5 | mismo | `npx tsc --noEmit` contra `src/modules/design-system/` | mismo |
| 3b.6 | `.venv/bin/python3 -m pytest tests/test_design_system_purity.py -v` | mismo | mismo |

## Fase 3c: Pipeline de build + verificación de runtime (PR 3c → rama del PR 3b)

Rebana la tarea 3.4 del predecesor (reescritura de `Makefile::api`
+ `scripts/check-runtime.mjs` + reescritura de `package.json`).

- [ ] 3c.1 R — `tests/test_make_api_build.py` (nuevo): invoca
  `make api` en un clon `tmp_path` (o vía shim de subproceso) y
  verifica que el target de Makefile invoca `next build`
  **antes** de que uvicorn vincule el puerto; verifica que
  uvicorn no vincula cuando `next build` sale distinto de
  cero. <!-- sdd-owner: implementation -->
- [ ] 3c.2 R — `tests/test_make_api_build.py` (bloque de
  verificación de runtime de Node): mockea `node --version` a
  un valor por debajo de `20.9.0` y verifica que `make api`
  sale distinto de cero **antes** de que uvicorn vincule. <!-- sdd-owner: implementation -->
- [ ] 3c.3 G — `scripts/check-runtime.mjs` (nuevo, ~25 LoC):
  compara `process.versions.node` contra `20.9.0`; sale
  distinto de cero con un mensaje de error claro nombrando la
  versión observada vs requerida cuando está por debajo. <!-- sdd-owner: implementation -->
- [ ] 3c.4 G — `Makefile` (modificado, ~50 LoC de delta en
  bloques `api:` y `css:`): el target `api:` ejecuta
  `scripts/check-runtime.mjs` → `npm ci` → `npm run build:web`
  → `uvicorn … --port 8765` en ese orden; el paso `css:` de
  Tailwind-3.4 legacy se elimina (la build de Tailwind 4 vive
  dentro de `next build`); `make css` se vuelve un shim
  no-op que sale 0 (se conserva por compatibilidad con scripts
  externos; documentado en el encabezado de `Makefile`). <!-- sdd-owner: implementation -->
- [ ] 3c.5 G — `package.json` (modificado, ~40 LoC de delta):
  bumpea a `next@^16`, `react@^19`, `react-dom@^19`,
  `tailwindcss@^4`; añade el toolchain de TS (`typescript@>=5.1.0`,
  `@types/react@^19`, `@types/react-dom@^19`, `@types/node`);
  añade `engines.node: ">=20.9.0"`; elimina `autoprefixer`,
  `postcss`, `@tailwindcss/forms`; añade
  `scripts.build:web` (`next build`) y conserva
  `scripts.check-runtime` (`node scripts/check-runtime.mjs`). <!-- sdd-owner: implementation -->
- [ ] 3c.6 T — triangulación de `tests/test_make_api_build.py`:
  verifica el modo de fallo donde `out/index.html` falta
  incluso después de una `next build` exitosa (p. ej. `out/`
  corrupto) causa que `make api` salga distinto de cero antes
  de que uvicorn vincule; verifica que uvicorn vincula
  **solo** a `127.0.0.1:8765` (sin segundo listener en
  `0.0.0.0` ni en cualquier otro puerto). <!-- sdd-owner: implementation -->
- [ ] 3c.7 Refactor — orden de dependencias de `package.json`
  alfabético; tabs de recetas de `Makefile` preservados (sin
  espacios). <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c.1–3c.2, 3c.6 | `.venv/bin/python3 -m pytest tests/test_make_api_build.py -v` | `make api` exit 0 en Node ≥ 20.9.0; `lsof -i :8765` muestra solo uvicorn | `git revert <3c-sha>` restaura `Makefile::api` (cadena `make css` legacy), `package.json` (deps legacy de Tailwind 3.4), elimina `scripts/check-runtime.mjs` |
| 3c.3 | `node scripts/check-runtime.mjs` exit 0 en Node ≥ 20.9.0, exit 1 por debajo | mismo | mismo |
| 3c.4 | mismo | `make api` arranca uvicorn en 8765 | mismo |
| 3c.5 | `node -e "const p=require('./package.json'); assert(p.engines.node === '>=20.9.0')"` | `npm ci` exit 0 | mismo |

## Fase 3d: Repoint de `WEB_DIR` + actualización del lector AC-21 (PR 3d → rama del PR 3c)

Rebana las tareas 3.6 + 3.7 del predecesor (repoint de
`api/server.py:54` `WEB_DIR` + `web/search_urls.js` →
`src/data/search-engines.js` + actualización de `open()` del
test AC-21). Nota: este es **solo el repoint de `WEB_DIR`** — el
cutover sigue siendo atómico con PR 3e (este sub-PR no borra
`web/index.html`; eso vive en PR 5c junto a las actualizaciones
e2e).

- [ ] 3d.1 R — `tests/test_static_mount.py` (nuevo): verifica
  que `api/server.py:54` declara
  `WEB_DIR = Path(__file__).parent.parent / "out"` (repointed).
  Verifica que la signature del mount en `api/server.py:1815`
  permanece byte-idéntica
  (`app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True),
  name="web")`). <!-- sdd-owner: implementation -->
- [ ] 3d.2 R — `tests/test_static_mount.py` (bloque de origen
  único): verifica que `uvicorn.run(…)` vincula solo a
  `127.0.0.1:8765`; verifica que
  `extension/manifest.json::host_permissions` queda
  `["http://localhost:8765/*"]`; verifica que
  `content_scripts.matches` queda
  `["http://localhost:8765/*"]`. <!-- sdd-owner: implementation -->
- [ ] 3d.3 G — `api/server.py` (modificado, delta de 1 línea en
  línea 54 + middleware mínimo para cablear el preload de
  `next/font` en la respuesta `out/index.html` si Next no
  inlinea el `<link>` — solo se añade si la triangulación de
  Fase 3a lo marca): `WEB_DIR = Path(__file__).parent.parent /
  "out"`. Ninguna otra línea de `api/server.py` cambia. <!-- sdd-owner: implementation -->
- [ ] 3d.4 G — `src/data/search-engines.js` (nuevo, ~100 LoC):
  copia byte a byte de `web/search_urls.js` con el nombre de
  export cambiado a `SEARCH_ENGINES` (coincide con el literal
  canónico que refleja `api/server.py::_SEARCH_ENGINES`). La
  forma byte — `key`, `label`, `with_authorship`, ordering —
  queda idéntica; `template` e `icon` quedan intactos según
  el contrato AC-21 de `tests/test_smoke.py`. <!-- sdd-owner: implementation -->
- [ ] 3d.5 G — `tests/test_smoke.py` (modificado, ~5 LoC de
  delta): el `open("web/search_urls.js").read()` del test
  `test_search_engine_contract` se actualiza a
  `open("src/data/search-engines.js").read()`. El
  `open("api/server.py").read()` del lado Python queda sin
  cambios. Contrato AC-21 preservado. <!-- sdd-owner: implementation -->
- [ ] 3d.6 T — triangulación de `tests/test_static_mount.py`:
  verifica que el movimiento del archivo no rompe el test
  contractual ejecutándolo en un clon `tmp_path` limpio;
  verifica que los campos coincidentes del literal en
  `api/server.py::_SEARCH_ENGINES` son byte-idénticos a
  `src/data/search-engines.js` en cada entrada. <!-- sdd-owner: implementation -->
- [ ] 3d.7 Refactor — elimina el antiguo archivo
  `web/search_urls.js` del repo (diferido a PR 5c junto al
  resto de `web/*`; Fase 3d solo pone en escena el archivo
  nuevo). <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3d.1–3d.2, 3d.6 | `.venv/bin/python3 -m pytest tests/test_static_mount.py -v` | `make api` arranca uvicorn; `curl http://127.0.0.1:8765/index.html` devuelve 200 con el contenido de `out/index.html` (cuando `out/` existe) | `git revert <3d-sha>` restaura `api/server.py:54` al valor legacy; elimina `src/data/search-engines.js`; revierte el parche `open()` de `tests/test_smoke.py` |
| 3d.3 | mismo | mismo | mismo |
| 3d.4–3d.5 | `.venv/bin/python3 -m pytest tests/test_smoke.py::test_search_engine_contract -v` | mismo | mismo |

## Fase 4a: Typed store + 4 sitios de lectura + 4 sitios de escritura (PR 4a → rama del PR 3d)

Rebana las tareas 4.1 + 4.2 del predecesor
(`src/modules/browser-state/{store,keys,defaults}.ts` + 4 sitios
de lectura + 4 sitios de escritura dentro de `useEffect`).

- [ ] 4a.1 R — `tests/test_browser_state_keys.py` (nuevo):
  grepea `src/modules/browser-state/**` y verifica que hay
  exactamente cuatro sitios de llamada
  `localStorage.getItem(…)` + exactamente cuatro
  `localStorage.setItem(…)` + cero
  `localStorage.removeItem(…)` fuera de la affordance tipada
  `reset()`. Verifica que ningún otro módulo
  (`src/modules/taxonomy/**`, `src/modules/research/**`,
  `src/modules/app-shell/**`, `src/modules/design-system/**`)
  lee o escribe `localStorage` directamente. <!-- sdd-owner: implementation -->
- [ ] 4a.2 G — `src/modules/browser-state/domain/keys.ts`
  (nuevo, ~30 LoC): constantes tipadas de `LocalStorageKey`
  (`"taxa.settings.theme"`, `"taxa.tree.source"`,
  `"taxa.tree.lastTaxonId"`, `"taxa.tree.kebabOpenId"`) más
  valores por defecto tipados según la tabla del spec
  `browser-state-hydration`
  (`theme: "light" \| "dark"` por defecto `light`,
  `tree-source: "col" \| "worms" \| "freshwater"` por defecto
  `col`, `last-taxon-id: number \| null` por defecto `null`,
  `kebab-open-id: number \| null` por defecto `null`). <!-- sdd-owner: implementation -->
- [ ] 4a.3 G — `src/modules/browser-state/infrastructure/store.ts`
  (nuevo, ~80 LoC): cuatro funciones `read(key)` y cuatro
  funciones `write(key, value)`, una por clave, cada una
  envolviendo `try/catch` para tragarse excepciones de
  `localStorage` (modo privado / cuota excedida). Exporta un
  `subscribe(key, cb)` tipado que devuelve un handle de
  desuscripción; exporta un `reset()` tipado que llama a
  `localStorage.removeItem` para cada clave. TS plano en
  `domain/`; las llamadas a `localStorage` viven en
  `infrastructure/` según la regla 4 del modular-architecture. <!-- sdd-owner: implementation -->
- [ ] 4a.4 G — `src/modules/browser-state/index.ts` (nuevo
  barrel, ~10 LoC): reexporta los cuatro `read`, cuatro
  `write`, `subscribe`, `reset`, los defaults tipados y el
  tipo de listener tipado. **No** se exporta ningún getter /
  setter crudo de `localStorage`. <!-- sdd-owner: implementation -->
- [ ] 4a.5 T — triangulación de
  `tests/test_browser_state_keys.py`: parametriza la matriz de
  4 claves; verifica que no existe `localStorage.getItem` /
  `setItem` en `src/modules/research/infrastructure/` (la
  clave `taxa.fex.treeWidth` del splitter sigue siendo
  propiedad del módulo file explorer según las Notas del
  spec). <!-- sdd-owner: implementation -->
- [ ] 4a.6 Refactor — extrae las excepciones de lectura /
  escritura en un helper `safeStorage` que envuelve `getItem`
  / `setItem` / `removeItem` con el try/catch; reúsalo a
  través de los cuatro sitios de lectura y cuatro de
  escritura. <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 4a.1, 4a.5 | `.venv/bin/python3 -m pytest tests/test_browser_state_keys.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.js` lleva el bundle del typed store | `git revert <4a-sha>` elimina `src/modules/browser-state/**`; nada más tocado |
| 4a.2–4a.4, 4a.6 | `.venv/bin/python3 -m pytest tests/test_browser_state_keys.py -v` | `npx tsc --noEmit` contra `src/modules/browser-state/` | mismo |

## Fase 4b: Guardia de hidratación + test de cero warnings de Playwright (PR 4b → rama del PR 4a)

Rebana las tareas 4.3 + 4.4 del predecesor (`useSyncExternalStore`
detrás de un flag `mounted` + aserción de Playwright de cero
warnings de hidratación).

- [ ] 4b.1 R — `tests/test_hydration_console.py` (nuevo,
  Playwright): carga el fixture de chromium contra `make api`,
  verifica que la consola del navegador emite cero
  `Warning: Text content did not match`, cero
  `Warning: Expected server HTML to contain` y cero
  `Warning: Hydration failed` después del primer paint + ciclo
  de rehidratación. <!-- sdd-owner: implementation -->
- [ ] 4b.2 G — `src/modules/app-shell/presentation/AppShell.tsx`
  (nuevo, ~50 LoC): importa `useSyncExternalStore` desde el
  módulo `browser-state`; lee el typed store detrás de un
  flag `mounted` configurado dentro de `useEffect`; en el
  primer paint, devuelve el estado vacío
  (`selected: null`, `tree: null`, `last-taxon-id: null`); en
  la rehidratación, aplica los defaults tipados desde
  `localStorage` y actualiza la URL al `last-taxon-id` si hay
  uno almacenado. <!-- sdd-owner: implementation -->
- [ ] 4b.3 G — `src/modules/app-shell/infrastructure/page-chrome.tsx`
  (nuevo, ~30 LoC): tabs de header (Browser / Classification /
  Settings) con atributos `data-action="nav-tab"` y
  `data-path="<tab>"`; el toggle de tema sella / quita el
  sello `data-theme` en `<html>` vía el typed store; help
  shell, vista de settings, banner host. <!-- sdd-owner: implementation -->
- [ ] 4b.4 T — triangulación de `tests/test_hydration_console.py`:
  verifica que la consola del fixture de chromium después de
  una recarga forzada (donde `localStorage` tiene un
  `theme: "dark"` almacenado) muestra `data-theme="dark"` en
  `<html>` después del ciclo de rehidratación; verifica que
  no se dispara ningún warning cuando el usuario togglea el
  tema entre paints. <!-- sdd-owner: implementation -->
- [ ] 4b.5 Refactor — extrae el flag `mounted` en un hook
  pequeño `useMounted()` en `src/modules/browser-state/` para
  que el patrón sea reutilizable; reúsalo en `AppShell.tsx` y
  cualquier componente descendiente que lea estado tipado. <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 4b.1, 4b.4 | `.venv/bin/python3 -m pytest tests/test_hydration_console.py -v` | `make api` arranca uvicorn; Playwright corre el fixture de chromium de extremo a extremo | `git revert <4b-sha>` elimina `src/modules/app-shell/presentation/AppShell.tsx` y `infrastructure/page-chrome.tsx`; el store de Fase 4a se queda |
| 4b.2–4b.3 | mismo | `npx next build` exit 0; `npx tsc --noEmit` contra `src/modules/app-shell/` | mismo |
| 4b.5 | mismo | mismo | mismo |

## Fase 5a: Port del módulo taxonomy (PR 5a → rama del PR 4b)

Rebana las tareas 5.1 + 5.2 + 5.3 del predecesor
(`src/modules/taxonomy/{domain,application,infrastructure,presentation}`
+ port de `web/{tree,detail,breadcrumb}.js`).

- [ ] 5a.1 R — `tests/test_taxonomy_infra.py` (nuevo): mockea
  `fetchTaxon`, `fetchChildren`, `fetchDomains`; verifica que
  la capa de aplicación expone solo view-models (sin JSON
  crudo en la capa de presentación); verifica que la forma
  de los tipos `Taxon`, `TaxonTree`, `Breadcrumb` coincide
  con la capa de dominio `taxonomy`. <!-- sdd-owner: implementation -->
- [ ] 5a.2 G — `src/modules/taxonomy/domain/taxon.ts` (~60
  LoC): tipos TS planos para `Taxon`, `TaxonTree`,
  `Breadcrumb`, `DomainId`; invariantes (caminador de cadena
  parental, ordenamiento de rango, inclusión de conjunto
  materializado). El predecesor PR 2d ya envió la superficie
  de tipos; PR 5a extiende con el caminador de cadena parental
  que el diseño especifica. <!-- sdd-owner: implementation -->
- [ ] 5a.3 G — `src/modules/taxonomy/infrastructure/api.ts`
  (~50 LoC): `fetchTaxon(id)` → `GET /api/taxon/{id}`;
  `fetchChildren(id, source)` →
  `GET /api/taxon/{id}/children?source=<col|worms|freshwater>`;
  `fetchDomains()` → `GET /api/domains`. Todas devuelven
  promesas tipadas; los errores de red emergen como
  `NetworkError` tipado. <!-- sdd-owner: implementation -->
- [ ] 5a.4 G — `src/modules/taxonomy/application/useTaxonTree.ts`
  (~80 LoC): el hook `useTaxonTree()`; consume las funciones
  tipadas `fetch*` de `infrastructure`; emite view-models que
  la capa de presentación consume; sin imports de React en
  las capas `domain` o `infrastructure`. <!-- sdd-owner: implementation -->
- [ ] 5a.5 G — `src/modules/taxonomy/presentation/{Tree,
  DetailPanel, Breadcrumb}.tsx` (~200 LoC combinados): porta
  el layout de filas legacy de `web/{tree,detail,breadcrumb}.js`
  (kebab por fila, ícono de búsqueda por fila, indicador de
  materialize por fila, familia monoespaciada del breadcrumb
  para los segmentos de nombre científico). Cada atributo
  legacy `data-action="nav-tab"`, `data-path="<tab>"`,
  `data-theme` se preserva. <!-- sdd-owner: implementation -->
- [ ] 5a.6 T — triangulación de
  `tests/test_taxonomy_infra.py`: parametriza sobre las tres
  fuentes (`col`, `worms`, `freshwater`); verifica que el
  toggle de tree-source re-renderiza el árbol con la fuente
  coincidente; verifica que el caminador del breadcrumb
  maneja taxones raíz (sin padre) y taxones huérfanos (padre
  faltante en la fuente) sin lanzar excepciones. <!-- sdd-owner: implementation -->
- [ ] 5a.7 Refactor — extrae el menú kebab por fila en
  `<Kebab>`; reúsalo a través de `Tree` y `DetailPanel`. <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 5a.1, 5a.6 | `.venv/bin/python3 -m pytest tests/test_taxonomy_infra.py -v` | `make api` arranca uvicorn; `curl /api/domains` devuelve la forma JSON | `git revert <5a-sha>` elimina `src/modules/taxonomy/**` (excepto `domain/taxon.ts` enviado por el predecesor PR 2d — ese se queda); nada más tocado |
| 5a.2–5a.5 | mismo | `npx next build` exit 0; `npx tsc --noEmit` contra `src/modules/taxonomy/` | mismo |

## Fase 5b: Port del módulo research + pin CDN (PR 5b → rama del PR 5a)

Rebana las tareas 5.4 + 5.5 + 5.6 del predecesor
(`src/modules/research/{domain,application,infrastructure,presentation}`
+ port de `web/{file_explorer,file_viewer,format,keymap}.js` + pin
CDN). Este es el sub-PR más grande a ~360 LoC; queda bajo el
presupuesto de 400 líneas según `design.md` §"Sub-PR slice under
Approach A".

- [ ] 5b.1 R — `tests/test_research_infra.py` (nuevo): mockea
  `fetchFiles`, `fetchServe` contra
  `/api/taxon/{id}/files{,/serve}`; verifica que el despachador
  de formatos (PDF / HTML / TXT / MD / DOCX / XLS / XLSX /
  EPUB) enruta al lazy loader correcto; verifica que las URLs
  CDN están fijadas a `mammoth@1.8.0`, `xlsx@0.18.5`,
  `epubjs@0.3.93`. <!-- sdd-owner: implementation -->
- [ ] 5b.2 G — `src/modules/research/domain/{research-file,
  engine, file-node}.ts` (~90 LoC combinados): tipos tipados
  para `ResearchFile`, `Engine`, `FileNode`; el tipo `Engine`
  refleja la forma del literal `SEARCH_ENGINES` (key, label,
  with_authorship, ordering); la unión discriminada
  `ResearchFile` cubre los nueve formatos soportados más los
  fallbacks `Unsupported` y `LegacyDoc`. <!-- sdd-owner: implementation -->
- [ ] 5b.3 G — `src/modules/research/infrastructure/api.ts`
  (~80 LoC): `fetchFiles(id)` → `GET /api/taxon/{id}/files`;
  `fetchServe(id, rel)` →
  `GET /api/taxon/{id}/files/serve?path=<rel>`;
  `loadScriptOnce(name, src)` lazy-loader para bibliotecas
  CDN (URLs fijadas; idempotente). <!-- sdd-owner: implementation -->
- [ ] 5b.4 G — `src/modules/research/infrastructure/search-engines.js`
  (ya enviado por Fase 3d como `src/data/search-engines.js` —
  reexportar desde aquí para el barrel del módulo research,
  con el export nombrado `SEARCH_ENGINES` sin cambios). <!-- sdd-owner: implementation -->
- [ ] 5b.5 G — `src/modules/research/application/{useFileExplorer,
  useFileViewer}.ts` (~120 LoC combinados): los dos hooks;
  consumen las funciones tipadas `fetch*`; emiten
  view-models que consume la capa de presentación. <!-- sdd-owner: implementation -->
- [ ] 5b.6 G — `src/modules/research/presentation/{FileExplorer,
  FileViewer, RawTableTreeTabs, MetaStrip, BreadcrumbPanel,
  Banners}.tsx` (~250 LoC combinados): porta el layout de dos
  paneles legacy de `web/{file_explorer,file_viewer,format,
  keymap}.js`; el strip Raw / Table / Tree; el meta strip
  `FORMAT | SIZE | ENCODING`; el despachador de nueve formatos
  con lazy loading fijado a CDN; los fallbacks legacy DOC y
  no soportado; el banner de fallo de CDN
  `"Viewer offline — raw download unavailable"`; la búsqueda
  del árbol (200 ms de debounce, modos filter / highlight,
  `state.explorer.search.{query, mode, hideEmpty}` persistido);
  el reset de estado del explorador al cambiar taxón. <!-- sdd-owner: implementation -->
- [ ] 5b.7 T — triangulación de `tests/test_research_infra.py`:
  parametriza sobre los nueve formatos (PDF, HTML, TXT, MD,
  DOCX, XLS, XLSX, EPUB, más fallback DOC, más una extensión
  no soportada como `.zip`); verifica que cada formato
  despacha al renderer legacy coincidente; verifica que
  `Content-Type` coincide con la extensión del archivo;
  verifica que el meta strip renderiza el
  `FORMAT=<EXT> | SIZE=<bytes> | ENCODING=UTF-8` coincidente. <!-- sdd-owner: implementation -->
- [ ] 5b.8 Refactor — extrae el meta strip en un único
  componente `<MetaStrip format={…} size={…} encoding="UTF-8" />`;
  extrae el banner de fallo de CDN en `<BannerHost>` para que
  pueda reutilizarse en `app-shell`. <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 5b.1, 5b.7 | `.venv/bin/python3 -m pytest tests/test_research_infra.py -v` | `make api` arranca uvicorn; `curl /api/taxon/<id>/files` devuelve la forma JSON; las URLs CDN devuelven 200 | `git revert <5b-sha>` elimina `src/modules/research/**`; `src/data/search-engines.js` (Fase 3d) se queda |
| 5b.2–5b.6, 5b.8 | mismo | `npx next build` exit 0; `npx tsc --noEmit` contra `src/modules/research/` | mismo |

## Fase 5c: Selectores E2E + contrato `data-*` + borrar legacy (PR 5c → rama del PR 5b)

Rebana las tareas 5.7 + 5.8 + 5.9 del predecesor (Playwright +
actualizaciones de selectores e2e + preservación del contrato
`data-*` + borrar `web/*.{html,js,css}` + `tailwind.config.js`).

- [ ] 5c.1 R — `tests/test_e2e_file_explorer.py` (modificado,
  el test existe pero los selectores preceden al árbol de
  componentes React): verifica que cada selector legacy
  (`data-action="nav-tab"`, `data-path="<tab>"`, `data-theme`,
  atributo de kebab por fila, atributo de ícono de búsqueda
  por fila, atributo de indicador de materialize por fila,
  atributos de datos del meta strip) sigue resolviendo en el
  nuevo árbol de componentes. <!-- sdd-owner: implementation -->
- [ ] 5c.2 R — `tests/test_web_toggle.py` (modificado):
  verifica que el toggle de tema persiste vía
  `localStorage.taxa.settings.theme` y sella `data-theme` en
  `<html>`; verifica que la media query OS
  `prefers-color-scheme` se honra como default cuando no
  existe preferencia almacenada. <!-- sdd-owner: implementation -->
- [ ] 5c.3 G — `tests/test_e2e_file_explorer.py` (actualización
  de selectores, ~120 LoC de delta): actualiza cada selector
  DOM al nuevo árbol de componentes (el contrato de atributo
  `data-*` se preserva; las clases CSS subyacentes cambian a
  clases de utilidad de Tailwind 4). Vuelve a correr el
  fixture de chromium contra `make api`; captura el artefacto
  trace de Playwright. <!-- sdd-owner: implementation -->
- [ ] 5c.4 G — `tests/test_web_toggle.py` (actualización de
  selectores, ~80 LoC de delta): mismo patrón que 5c.3 para
  el toggle de tema. <!-- sdd-owner: implementation -->
- [ ] 5c.5 T — integración del harness de Playwright +
  Lighthouse: parametriza sobre las rutas URL del fixture de
  chromium legacy (`/`, `/index.html`,
  `/_next/static/<h>.js`) y verifica que los traces del
  fixture de chromium coinciden con el nuevo árbol de
  componentes. <!-- sdd-owner: implementation -->
- [ ] 5c.6 G — borrado de `web/index.html` (archivo eliminado
  del repo); borrado de
  `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,
  help,keymap,settings,search,file_explorer,file_viewer,
  format,search_urls}.js` (18 archivos eliminados); borrado
  de `web/index.css`; `web/dist/tailwind.css` ya no se rastrea
  (regenerado por el `make css` revertido tras reversión,
  nunca por la nueva build); borrado de `tailwind.config.js`. <!-- sdd-owner: implementation -->
- [ ] 5c.7 Refactor — el test
  `test_legacy_module_count_matches_exploration` de
  `tests/test_evidence_baseline.py` se actualiza para
  verificar que el roster legacy `web/*.js` está **ausente**
  (el test queda en el suite como guardia de regresión contra
  módulos vanilla legacy que se cuelen de vuelta en el
  árbol). <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 5c.1, 5c.3 | `.venv/bin/python3 -m pytest tests/test_e2e_file_explorer.py -v` | Playwright corre el fixture de chromium de extremo a extremo contra `make api` | `git revert <5c-sha>` restaura `web/*.{html,js,css}` + `tailwind.config.js`; las actualizaciones de selectores de test se revierten; ningún cambio en `src/` |
| 5c.2, 5c.4 | `.venv/bin/python3 -m pytest tests/test_web_toggle.py -v` | mismo | mismo |
| 5c.5 | mismo | mismo; trace de Playwright + JSON de Lighthouse emitidos | mismo |
| 5c.6 | mismo | `make api` arranca uvicorn; `ls web/` vacío | mismo |
| 5c.7 | `.venv/bin/python3 -m pytest tests/test_evidence_baseline.py::test_legacy_module_count_matches_exploration -v` | mismo | mismo |

## Fase 6: Trabajo de validación (después del camino candidato completo, antes de PR 3e)

El camino candidato es el conjunto completo de sub-PRs 3a–5c
acumulado en la rama tracker
`docs/complete-taxa-frontend-migration-plan` (nada ha llegado a
`develop` todavía — el tracker permanece draft/no-merge hasta que
la cadena se completa). La Fase 6 corre **después** de eso,
**antes** de PR 3e. Es **trabajo de validación**, no un objetivo
de migración — no genera código nuevo en `web/**`, handlers de
ruta nuevos en `api/server.py`, ni archivos nuevos en
`extension/**`. Sus artefactos se registran en
`apply-progress.md` §Registro de cambios como flips de puertas
(G5 reproducible, G6 PASS, G4 PASS).

La Fase 6 tiene tres sub-pasos (6a, 6b, 6c) — uno por cierre de
puerta — y PUEDEN entregarse como tres eslabones de la cadena (el
default: posiciones 10 / 11 / 12) o colapsar en un único PR hijo en
la posición 10, dependiendo de si `apply-progress.md` los registra
juntos o separados. Colapsarlos acorta la cadena pero no cambia la
topología: el batch sigue apuntando a la rama del PR 5c y PR 3e
sigue apuntando al último eslabón de la Fase 6. La política
`ask-on-risk` del mantenedor aplica si el batch excede el
presupuesto de 400 líneas (estimado ~220 LoC repartidos a través
de los tres sub-pasos; cómodamente debajo).

### Fase 6a: Cierre de baseline de hidratación G5 (PR 6a → rama del PR 5c)

- [ ] 6a.1 R — `tests/test_hydration_timing.py` (ya enviado
  por el predecesor PR 1b.3b): el test verifica que
  `scripts/measure_hydration.py` sale distinto de cero cuando
  el JSON de baseline legacy falta o es inválido de esquema.
  El test se queda; sin cambio de código de producción. Nuevo
  script helper `scripts/reconstruct_hydration_baseline.py`
  lee los números documentados de
  `delta_server_to_tree_first_paint_ms` del predecesor desde
  `openspec/changes/migrate-nextjs-tailwind4/design.md`
  §"Migration Evidence Baseline" y emite
  `web/dist/evidence-baseline.json` con el mismo esquema que
  fija el test de hidratación. <!-- sdd-owner: implementation -->
- [ ] 6a.2 G — `scripts/reconstruct_hydration_baseline.py`
  (~50 LoC): lee los números baseline legacy literalmente
  desde el design.md del predecesor (la entrada es el código
  fuente markdown parseado para la tabla; la salida es un
  archivo JSON que coincide con el esquema que fija
  `tests/test_hydration_timing.py`). <!-- sdd-owner: implementation -->
- [ ] 6a.3 G — corre `python scripts/measure_hydration.py
  --baseline web/dist/evidence-baseline.json --candidate out/`
  contra la build candidata aterrizada en Fase 5c; emite el
  nuevo JSON de hidratación junto al baseline; registra el
  delta en `apply-progress.md` §Registro de cambios. <!-- sdd-owner: implementation -->
- [ ] 6a.4 T — verifica que el delta ≤ 0 % en initial paint y
  latencia de interacción; si excede, falla cerrado y escribe
  la solicitud de exención en `design.md` §"Risk register"
  antes de que G4 pueda voltearse. <!-- sdd-owner: implementation -->
- [ ] 6a.5 Refactor — colapsa el script + corrida + aserción
  en un único shim `scripts/g5_close.sh` que el worker de
  apply invoca una vez y registra el resultado en
  `apply-progress.md`. <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 6a.1–6a.5 | `.venv/bin/python3 -m pytest tests/test_hydration_timing.py -v` | `scripts/g5_close.sh` exit 0; `apply-progress.md` §Registro de cambios registra el flip de puerta | `git revert <6a-sha>` elimina `scripts/reconstruct_hydration_baseline.py` y el delta de `apply-progress.md`; el JSON baseline legacy se queda (regenerado en la próxima corrida 6a) |

### Fase 6b: Ensayo de cutover G6 (PR 6b → rama del PR 6a)

- [ ] 6b.1 R — `tests/test_rehearse_cutover.py` (nuevo):
  verifica que `scripts/rehearse_cutover.py` sale 0 contra el
  manifesto activado; parametriza sobre los cuatro
  subconjuntos de la unidad de cutover (`web_dir_only`,
  `consumers_only`, `makefile_only`, `artifact_only`) y
  verifica el invariante fail-closed (un ensayo de solo
  subconjunto **falla**). <!-- sdd-owner: implementation -->
- [ ] 6b.2 G — `scripts/rehearse_cutover.py` (~120 LoC):
  dry-runea la unidad atómica de cutover (repoint de WEB_DIR
  + 26 actualizaciones de consumidores + reescritura de
  Makefile + artefacto de build `out/`) contra un clon
  `tmp_path` del candidato. Corre el verificador G3 Tier-2
  (`scripts/verify_consumers.py`) contra el manifesto
  activado; emite `cutover-rehearsal.json` con
  `activation_complete: true`, `unselected_count: 0`, y
  `silent_fallback_paths: []`. Sale distinto de cero en
  cualquier dry-run de solo subconjunto. <!-- sdd-owner: implementation -->
- [ ] 6b.3 G — voltea cada `activation_status` y
  `replacement.status` en
  `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
  de `selected` (legacy pre-cut, Tier-1) al **registro de
  activación post-cut** (Tier-2) para cada uno de los 26
  consumidores §3.1. El flip es un artefacto de planificación
  autordado por el worker de apply en el mismo release que el
  script de ensayo. **El `cutover-manifest.json` del predecesor
  vive bajo `migrate-nextjs-tailwind4/` (directorio congelado)
  — el flip se escribe en una copia de trabajo en
  `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
  según la guía del spec §"Cutover-manifest activation".** La
  copia de trabajo es lo que PR 3e lee al momento del cutover;
  la copia del predecesor permanece byte-idéntica
  (congelada). <!-- sdd-owner: implementation -->
- [ ] 6b.4 T — verifica que el script de ensayo reporta cero
  rutas de fallback silenciosas (no existe ruta de código
  "caer al `web/` legacy ante fallo de build" en
  `Makefile::api` o `api/server.py`). <!-- sdd-owner: implementation -->
- [ ] 6b.5 Refactor — extrae la invocación G3 Tier-2 en un
  helper pequeño `run_g3_tier2(manifest, out)` para que el
  script de ensayo y la verificación PR 3e del worker de
  apply compartan el mismo camino de código. <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 6b.1, 6b.4 | `.venv/bin/python3 -m pytest tests/test_rehearse_cutover.py -v` | `scripts/rehearse_cutover.py` exit 0 contra el manifesto activado; `cutover-rehearsal.json` lleva `activation_complete: true` | `git revert <6b-sha>` elimina `scripts/rehearse_cutover.py`, `tests/test_rehearse_cutover.py`, y la copia de trabajo `cutover-manifest.json`; ningún cambio en `src/` o `api/` |
| 6b.2 | mismo | mismo | mismo |
| 6b.3 | `python scripts/verify_consumers.py --manifest openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json --out out/ --serve --fixture-web-root <candidate>` | el verificador G3 Tier-2 sale 0; `CONSUMER-READINESS.json` reporta los 26 consumidores §3.1 como `selected` | mismo |

### Fase 6c: Medición de paridad G4 Playwright + Lighthouse (PR 6c → rama del PR 6b)

- [ ] 6c.1 R — `tests/test_e2e_file_explorer.py` (ya
  actualizado por Fase 5c) y `tests/test_web_toggle.py` (ya
  actualizado por Fase 5c): los tests se quedan; sin cambio
  de código de producción. La medición G4 es el delta entre
  el trace de Playwright + Lighthouse en la nueva build
  candidata de Fase 5c y el fixture de chromium legacy que
  capturó el predecesor. <!-- sdd-owner: implementation -->
- [ ] 6c.2 G — corre Playwright + Lighthouse contra la build
  candidata aterrizada en Fase 5c; captura
  `out/g4-parity-report.json` con los números de initial
  paint y latencia de interacción. Registra el delta en
  `apply-progress.md` §Registro de cambios. <!-- sdd-owner: implementation -->
- [ ] 6c.3 T — verifica que el delta ≤ 0 % en initial paint y
  latencia de interacción; si excede, falla cerrado y escribe
  la solicitud de exención en `design.md` §"Risk register"
  antes de que G4 pueda voltearse. <!-- sdd-owner: implementation -->
- [ ] 6c.4 Refactor — extrae la medición en `scripts/g4_measure.sh`
  para que el worker de apply la invoque una vez y registre
  el resultado en `apply-progress.md`. <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 6c.1–6c.4 | `.venv/bin/python3 -m pytest tests/test_e2e_file_explorer.py tests/test_web_toggle.py -v` | `scripts/g4_measure.sh` exit 0; `out/g4-parity-report.json` lleva initial paint + latencia de interacción; `apply-progress.md` §Registro de cambios registra el flip de puerta | `git revert <6c-sha>` elimina el delta de `apply-progress.md`; ningún cambio en `tests/` o `scripts/` (el script de medición se queda como futura guardia de regresión) |

## Fase 3e: Cutover atómico (PR 3e → rama del PR 6c, con compuerta en las seis puertas verdes)

La unidad atómica de cutover (según `design.md` §"Atomic
cutover unit") cambia **exactamente lo siguiente** en un único
release. **No se admite reversión de subconjunto.** PR 3e se
publica solo cuando:

- [ ] **G1 PASS** (registrado del predecesor). <!-- sdd-owner: parent -->
- [ ] **G2 PASS** (registrado contra la build limpia verificada
  de Next 16.3.3 / Turbopack; entrada del predecesor
  `apply-progress.md` del 2026-08-30). <!-- sdd-owner: parent -->
- [ ] **G3 Tier-1 PASS** (registrado: los 26 consumidores §3.1
  verdes contra el runtime legacy pre-cut vía el fixture
  controlado y `scripts/verify_consumers.py`; PR #109 + #111 +
  #115 + #116). <!-- sdd-owner: parent -->
- [ ] **G4 PASS** (Fase 6c medido; registrado en
  `apply-progress.md` §Registro de cambios). <!-- sdd-owner: parent -->
- [ ] **G5 reproducible** (Fase 6a reconstruido; registrado en
  `apply-progress.md` §Registro de cambios). <!-- sdd-owner: parent -->
- [ ] **G6 PASS** (Fase 6b ensayado; registrado en
  `apply-progress.md` §Registro de cambios). <!-- sdd-owner: parent -->

Si alguna puerta está ausente, fallida, obsoleta (> 7 días) o
incomparable, PR 3e está **bloqueado**, nunca en éxito. El
cutover de cuatro conjuntos:

1. **Constante `WEB_DIR`** en `api/server.py:54` (ya
   reorientada en Fase 3d; PR 3e voltea el artefacto de build
   bajo `out/` desde la build candidata a la build de producción
   con la verificación de runtime `engines.node >= 20.9.0`
   activa).
2. **Cada actualización de consumidor activo** en
   `design.md::§3.1` del predecesor (ya autordada por Fase 3d
   para la ruta del lector AC-21; PR 3e voltea los 25
   consumidores §3.1 restantes para que lean desde el árbol de
   componentes React en lugar de las rutas `web/*` legacy). El
   flip es el registro de activación post-cut en
   `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
   (copia de trabajo; la copia del predecesor queda congelada).
3. **Los targets `Makefile::api` y `Makefile::web`** (ya
   reescritos por Fase 3c; PR 3e voltea el paso `make css` de
   Tailwind-3.4 legacy de "regenerar `web/dist/tailwind.css`"
   a "exit 0 no-op" — la build de Tailwind 4 vive dentro de
   `next build`).
4. **El artefacto de build** — el directorio `out/` mismo
   (`out/index.html`, `out/_next/static/chunks/**`,
   `out/.next/build-manifest.json`, la clasificación de página
   de error si se emite `404.html` / `500.html`). El artefacto
   se regenera por la build de producción al momento del
   cutover.

La lista de tareas PR 3e (solo después de que las seis puertas
estén verdes):

- [ ] 3e.1 R — `tests/test_verify_consumers.py` (ya enviado
  por el predecesor PR #109 + #111 + #115 + #116): el test
  se queda; PR 3e lo vuelve a correr contra el manifesto
  activado en
  `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`. <!-- sdd-owner: implementation -->
- [ ] 3e.2 G — corre `python scripts/verify_consumers.py
  --manifest openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json
  --out out/` contra la build candidata; verifica que
  `CONSUMER-READINESS.json` sale 0 con
  `activation_complete: true`, `unselected_count: 0`. <!-- sdd-owner: implementation -->
- [ ] 3e.3 G — vuelve a correr `make api` contra la build de
  cutover; verifica que uvicorn vincula solo a
  `127.0.0.1:8765`; verifica que
  `curl http://127.0.0.1:8765/index.html` devuelve
  `out/index.html`; verifica que
  `extension/manifest.json::host_permissions` queda
  `["http://localhost:8765/*"]`. <!-- sdd-owner: implementation -->
- [ ] 3e.4 G — vuelve a correr `make smoke` contra la build de
  cutover; verifica que se preserva el baseline de 63 passed,
  8 skipped. <!-- sdd-owner: implementation -->
- [ ] 3e.5 G — voltea el footer de estado de puertas en
  `apply-progress.md` §Status de "blocked / unreproducible /
  blocked" a "PASS recorded (G4 / G5 / G6 cerrados por Fase
  6a / 6b / 6c)". <!-- sdd-owner: implementation -->
- [ ] 3e.6 T — `tests/test_verify_build.py` (ya enviado por la
  evidencia G2 del predecesor): el test se queda; se vuelve a
  correr contra `out/BUILD-INVENTORY.json` de la build de
  cutover; verifica que ninguna clase de activo falta. <!-- sdd-owner: implementation -->
- [ ] 3e.7 Refactor — `apply-progress.md` §Registro de cambios
  registra el hash del commit de cutover, las fechas de flip
  de puertas y la salida del verificador G3 Tier-2. <!-- sdd-owner: implementation -->

### Reversión bajo la cadena

PR 3e es el **último hijo**, no un PR contra `develop`. Existen dos
ventanas de reversión:

| Ventana | Estado | Reversión |
|---|---|---|
| Antes de que el tracker se fusione | Nada está en `develop`; el cutover vive solo en la rama tracker | Retener o cerrar el PR tracker — `develop` queda intacto por construcción |
| Después de que el tracker se fusione | La cadena completa aterriza en `develop` en una única integración | `git revert <pr3e-sha>` restaura la build vanilla legacy atómicamente (según `design.md` §"Rollback unit") |

Para que `<pr3e-sha>` siga siendo direccionable en `develop`, el
tracker DEBE fusionarse con un **merge commit** (sin squash), de
modo que los commits individuales de la cadena sobrevivan a la
integración. Si el tracker se fusiona con squash, la unidad de
reversión atómica pasa a ser el propio merge del tracker:
`git revert -m 1 <tracker-merge-sha>`. En cualquier caso la
reversión es **una sola** que cubre el cutover completo de cuatro
conjuntos — **no se admite reversión de subconjunto**.

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3e.1–3e.2 | `.venv/bin/python3 -m pytest tests/test_verify_consumers.py -v` | el verificador G3 Tier-2 sale 0; `CONSUMER-READINESS.json` lleva `activation_complete: true` | `git revert <pr3e-sha>` restaura la build vanilla legacy atómicamente (según `design.md` §"Rollback unit"): `web/index.html`, `web/app.js`, los 18 módulos `web/*.js`, `web/dist/tailwind.css`, `tailwind.config.js`, el `package.json` + `package-lock.json` legacy, el `Makefile::api` legacy, el `api/server.py:54` legacy |
| 3e.3 | `curl http://127.0.0.1:8765/index.html` devuelve `out/index.html` | `make api` arranca uvicorn en 8765; `lsof -i :8765` muestra solo uvicorn | mismo |
| 3e.4 | `make smoke` exit 0 | mismo | mismo |
| 3e.5 | n/a (artefacto de planificación) | n/a | mismo |
| 3e.6 | `.venv/bin/python3 -m pytest tests/test_verify_build.py -v` | `out/BUILD-INVENTORY.json` no lleva ninguna clase faltante | mismo |
| 3e.7 | n/a | n/a | mismo |

## Fuera de alcance (según `AGENTS.md` y la propuesta)

- **Sin `git push`, `git commit`, `gh pr create`, `git stash`**
  en esta fase de tareas. La fase de apply es dueña de esas
  acciones.
- **Sin nuevos worktrees** — el worker de apply crea worktrees
  según `AGENTS.md` §4.
- **Sin ediciones a `openspec/changes/migrate-nextjs-tailwind4/**`**
  (predecesor congelado).
- **Sin reescritura del backend** (handlers de ruta de
  `api/server.py`, lógica SQLite/WAL, flujo de materialize,
  defensa SSRF en `save-url`).
- **Sin ediciones al pipeline ETL** (`etl/parse_textree`,
  `etl/load_coldp`, `etl/load_worms`,
  `etl/load_freshwater`, migraciones).
- **Sin trabajo de paridad de la extensión Chrome** — un cambio
  separado rastrea cualquier adaptación de la extensión aware
  de React.
- **Sin trabajo de SEO / metadatos / sitemap / robots**.
- **Sin rutas nuevas** (Settings, About, Help) más allá de lo
  que la UI legacy expone hoy.
- **Sin tooling de cobertura** (`coverage.available: false`).
- **Sin rediseño visual** (impeccable / seguimiento de Stitch).

## Contrato de congelación del predecesor (vinculante)

Cada sub-PR en las Fases 3a–6c y PR 3e DEBE satisfacer:

- [ ] `git diff --stat origin/develop -- openspec/changes/migrate-nextjs-tailwind4/`
  muestra cero cambios. <!-- sdd-owner: parent -->
- [ ] `git diff --stat <rama-base-inmediata>` muestra **solo** los
  archivos de esta rebanada (higiene de diff de la cadena; un diff
  contaminado es un bug de base — reapuntar o rebasear, no revisar
  alrededor de él). <!-- sdd-owner: parent -->
- [ ] La verificación de protección de rama del PR rechaza
  cualquier PR que modifique
  `openspec/changes/migrate-nextjs-tailwind4/**`. <!-- sdd-owner: parent -->
- [ ] El hook de CI / lint del PR rechaza lo mismo. <!-- sdd-owner: parent -->

Si un sub-PR edita accidentalmente el directorio del predecesor,
el sub-PR está **bloqueado** y el worker de apply debe revertir
la edición accidental antes de que el PR pueda fusionarse. No
hay ruta `size:exception` para ediciones del predecesor.

## Reconciliación del pronóstico

- **3a** ~175 LoC authored; **3b** ~230; **3c** ~180; **3d** ~190;
  **4a** ~180; **4b** ~90; **5a** ~280; **5b** ~360; **5c** ~200;
  **6a** ~50; **6b** ~120; **6c** ~20 (mayormente artefacto de
  medición); **3e** ~120 (mayormente delta de
  `apply-progress.md` + el commit de cutover). Total: ~2.225 LoC
  authored a través de 13 sub-PRs.
- El sub-PR más grande es **5b** a ~360 LoC authored, cómodamente
  bajo el **presupuesto de revisión de 400 líneas por PR** con
  -40 LoC (-10 %) de holgura. **No se requiere `size:exception`.**
- El sub-PR **6c** es el más pequeño a ~20 LoC; el artefacto de
  medición G4 se registra en `apply-progress.md` en lugar de en
  un diff de código.
- La Fase 6 colectivamente (6a + 6b + 6c) totaliza ~190 LoC
  authored y ~120 LoC de artefacto de medición. Si el mantenedor
  prefiere un único batch encadenado para la Fase 6, los LoC
  combinados siguen bien debajo de 400; si prefiere tres sub-PRs
  separados para foco de revisión, cada uno también está debajo.
- **PRs encadenados recomendados: Sí** — cada sub-PR cabe por sí
  solo en el presupuesto por PR, pero el total de ~2.225 líneas y
  el cutover atómico (la feature DEBE integrarse antes de llegar a
  `develop`) sitúan este cambio en la compuerta de Feature Branch
  Chain.
- **Estrategia de cadena: `feature-branch-chain`** (elegida por el
  usuario). El tracker `docs/complete-taxa-frontend-migration-plan`
  es draft/no-merge y es el **único** PR que apunta a `develop`; el
  PR hijo 3a apunta al tracker; cada hijo posterior apunta a su
  rama predecesora inmediata. Esto sustituye, para este cambio, el
  default de `AGENTS.md` §4 de apuntar directo a `develop` y el
  precedente de apply-progress del predecesor.
- **Longitud de la cadena: 13 PRs hijos + 1 tracker.** El
  presupuesto de revisión por hijo son los LoC authored listados
  arriba; el tracker no lleva presupuesto de revisión propio (es el
  punto de acumulación).
- **Estrategia de entrega: `ask-on-risk`** (según preflight; sin
  flag de riesgo abierto — el Enfoque A es FINAL, el predecesor
  está congelado, cada sub-PR cabe bajo 400 líneas).