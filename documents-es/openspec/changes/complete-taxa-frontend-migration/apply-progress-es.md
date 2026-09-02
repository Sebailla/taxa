# Progreso de apply: complete-taxa-frontend-migration

> Artefacto de persistencia en modo híbrido. Refleja el
> apply-progress estructurado en Engram (`topic_key` =
> `sdd/complete-taxa-frontend-migration/apply-progress`).
>
> **Estado inicial (2026-09-02)**: cada sub-PR bajo el Enfoque A
> (`tasks.md` Fases 3a–6c + PR 3e) está **pendiente de
> reconstrucción**. Ningún PR hijo se ha abierto todavía. La rama
> tracker `docs/complete-taxa-frontend-migration-plan` ya existe y
> contiene los artefactos de planificación; es la **única** rama que
> apuntará a `develop`, y permanece en **draft / no-merge** hasta
> que toda la cadena esté revisada e integrada. Nada se ha entregado
> a `develop` todavía. La tabla de pre-flight de puertas
> (§Pre-flight de puerta para PR 3e) registra el estado
> trasladado de G1, G2, G3 Tier-1 (todos PASS registrados del
> predecesor) y el estado de cierre de G4, G5, G6 (los tres
> diferidos al trabajo de validación de Fase 6).
>
> **El Enfoque A es FINAL** (bloqueado el 2026-09-02, registrado
> en `design.md::§1`); no hay ruta de anulación abierta. **El
> predecesor `migrate-nextjs-tailwind4/` está congelado** — cada
> sub-PR en este cambio DEBE dejar
> `openspec/changes/migrate-nextjs-tailwind4/**` byte-idéntico (la
> protección de rama rechaza cualquier PR que lo edite).

---

## Estado de reconstrucción

| Sub-PR | Alcance | Presupuesto LoC (authored) | Archivos fuente | Estado |
|--------|---------|----------------------------|-----------------|--------|
| PR 3a | Entrada App Router + toolchain TS | ~175 | `src/app/{layout,page}.tsx` + `next.config.mjs` + `tests/test_app_shell_render.py` (nuevo) | pendiente de reconstrucción |
| PR 3b | Tokens de diseño + `@theme` Tailwind 4 | ~230 | `src/app/globals.css` (nuevo, `@import "tailwindcss"` + `@theme` + `@layer base`) + `src/modules/design-system/{infrastructure/index.ts,presentation/Icon.tsx,presentation/Button.tsx}` (nuevos) + `tests/test_tailwind_4_parity.py` (nuevo) + `tests/test_design_system_purity.py` (nuevo) | pendiente de reconstrucción |
| PR 3c | Pipeline de build + verificación de runtime | ~180 | `Makefile` (modificado, targets `api:` + `css:` reescritos; paso `make css` de Tailwind-3.4 legacy retirado) + `scripts/check-runtime.mjs` (nuevo, Node ≥ 20.9.0) + `package.json` (modificado, `next@^16` / `react@^19` / `tailwindcss@^4` / toolchain TS / `engines.node`) + `tests/test_make_api_build.py` (nuevo) | pendiente de reconstrucción |
| PR 3d | Repoint de `WEB_DIR` + lector AC-21 | ~190 | `api/server.py` (modificado, delta de 1 línea en línea 54 + middleware mínimo de preload `next/font`) + `src/data/search-engines.js` (nuevo, copia byte a byte de `web/search_urls.js` con export nombrado `SEARCH_ENGINES`) + `tests/test_smoke.py` (modificado, actualización de ruta `open()`) + `tests/test_static_mount.py` (nuevo) | pendiente de reconstrucción |
| PR 4a | Typed store + 4 lecturas + 4 escrituras | ~180 | `src/modules/browser-state/{domain/keys.ts,infrastructure/store.ts,index.ts}` (nuevos) + `tests/test_browser_state_keys.py` (nuevo) | pendiente de reconstrucción |
| PR 4b | Guardia de hidratación + cero warnings Playwright | ~90 | `src/modules/app-shell/{presentation/AppShell.tsx,infrastructure/page-chrome.tsx}` (nuevos) + `tests/test_hydration_console.py` (nuevo, Playwright) | pendiente de reconstrucción |
| PR 5a | Port del módulo taxonomy | ~280 | `src/modules/taxonomy/{domain/taxon.ts,infrastructure/api.ts,application/useTaxonTree.ts,presentation/{Tree,DetailPanel,Breadcrumb}.tsx}` (nuevo + extensión) + `tests/test_taxonomy_infra.py` (nuevo) | pendiente de reconstrucción |
| PR 5b | Port del módulo research + pin CDN | ~360 | `src/modules/research/{domain/{research-file,engine,file-node}.ts,infrastructure/{api,search-engines}.{ts,js},application/{useFileExplorer,useFileViewer}.ts,presentation/{FileExplorer,FileViewer,RawTableTreeTabs,MetaStrip,BreadcrumbPanel,Banners}.tsx}` (nuevos) + `tests/test_research_infra.py` (nuevo) | pendiente de reconstrucción |
| PR 5c | Selectores E2E + contrato `data-*` + borrar legacy | ~200 | `tests/test_e2e_file_explorer.py` (modificado, actualización de selectores DOM) + `tests/test_web_toggle.py` (modificado, actualización de toggle de tema) + `tests/test_evidence_baseline.py` (modificado, aserción de roster legacy voltea a "ausente") + borrado de `web/{index.html,index.css}` + borrado de `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,help,keymap,settings,search,file_explorer,file_viewer,format,search_urls}.js` (18 archivos) + borrado de `tailwind.config.js` + `web/dist/tailwind.css` ya no se rastrea | pendiente de reconstrucción |
| Fase 6a | Cierre de baseline de hidratación G5 | ~50 (mayormente medición) | `scripts/reconstruct_hydration_baseline.py` (nuevo) + `scripts/g5_close.sh` (nuevo) + `web/dist/evidence-baseline.json` (regenerado, esquema fijado por `tests/test_hydration_timing.py`) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| Fase 6b | Ensayo de cutover G6 | ~120 | `scripts/rehearse_cutover.py` (nuevo) + `tests/test_rehearse_cutover.py` (nuevo) + `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json` (copia de trabajo; la copia del predecesor queda byte-idéntica congelada) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| Fase 6c | Paridad G4 Playwright + Lighthouse | ~20 (mayormente medición) | `scripts/g4_measure.sh` (nuevo) + `out/g4-parity-report.json` (artefacto Playwright + Lighthouse) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| PR 3e | Cutover atómico | ~120 (mayormente delta de `apply-progress.md`) | `apply-progress.md` (flip de footer de estado de puertas + entrada de registro de cambios) + re-corridas de `tests/test_verify_consumers.py`, `tests/test_verify_build.py`, `make api`, `make smoke` | pendiente de reconstrucción (con compuerta en las seis puertas verdes) |

**Conteo de sub-PRs**: 13 (4 bootstrap + 2 browser-state + 3
puertos de capability + 3 validación Fase 6 + 1 cutover
atómico).

**Total authored**: ~2.225 LoC a través de los 13 sub-PRs. El
sub-PR más grande es **5b** a ~360 LoC (bajo el presupuesto de
400 líneas con -40 LoC de holgura; **no se requiere
`size:exception`**).

### Orden de reconstrucción (determinístico, secuencial a lo largo de la cadena)

```
3a → 3b → 3c → 3d → 4a → 4b → 5a → 5b → 5c → 6a (G5) → 6b (G6) → 6c (medición G4) → 3e (cutover atómico, con compuerta)
```

**Estrategia de cadena: `feature-branch-chain`** (elegida por el
usuario). La rama existente
`docs/complete-taxa-frontend-migration-plan` es el **tracker**:
draft / no-merge, y el **único** PR que apunta a `develop`. El PR
hijo 3a apunta al tracker; cada hijo posterior apunta a su **rama
predecesora inmediata**. Esto sustituye, para este cambio, el
default de `AGENTS.md` §4 de apuntar directo a `develop`.

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

Los hijos se fusionan **en orden** dentro del tracker; a medida que
cada hijo se fusiona, el siguiente se reapunta al tracker (GitHub
reapunta automáticamente cuando la rama base se fusiona y se borra).
El tracker acumula la feature completa y se fusiona a `develop` solo
después de que PR 3e — el último hijo — aterrice.

**La Fase 6 (6a, 6b, 6c) es trabajo de validación**, no un
objetivo de migración. Corre **después** de que el camino
candidato completo (3a–5c) esté verde y acumulado en el tracker, y
**antes** de que PR 3e pueda aterrizar. La Fase 6 puede entregarse
como tres eslabones de la cadena (el default: posiciones
10 / 11 / 12) o colapsar en un único PR hijo en la posición 10,
según la decisión `ask-on-risk` del mantenedor; colapsarla acorta
la cadena sin cambiar la topología (el batch sigue apuntando a la
rama del PR 5c, y PR 3e sigue apuntando al último eslabón de la
Fase 6). Los LoC combinados son ~190 authored + ~120 artefacto de
medición, cómodamente bajo el presupuesto de 400 líneas.

### Política de worktree

- **Colocación CodeGraph-aware**: cada worktree generado para un
  sub-PR se ubica bajo
  `<repo-parent>/<repo-name>-worktrees/<worktree-name>` (el
  home del usuario, hermano del worktree activo, nunca bajo
  `/tmp` / `/var/tmp`). Cada worktree obtiene su propio índice
  `.codegraph/`; el watcher de CodeGraph sincroniza
  automáticamente tras las ediciones.
- **El worktree del predecesor es de solo lectura**:
  `taxa-worktrees/migrate-nextjs-tailwind4-pr1` (si existe) es
  solo historia de planificación. No editar, rebasear ni
  fusionar desde él.
- **Worktrees de reconstrucción** generados por el worker de
  apply para cada sub-PR: creados frescos desde la **rama base**
  de ese sub-PR en la tabla de cadena de arriba — el tracker
  (`docs/complete-taxa-frontend-migration-plan`) para PR 3a, la
  rama predecesora inmediata para cada hijo posterior. Nunca desde
  `origin/develop` directamente: un worktree cortado desde
  `develop` produce un diff contaminado. Patrón de nombre:
  `taxa-worktrees/complete-taxa-frontend-migration-<sub-pr-id>`.

### Manifiesto de reconstrucción (por sub-PR)

Para cada sub-PR, el worker de apply DEBE:

1. Crear un nuevo worktree desde la **rama base** de ese sub-PR
   (ver la tabla de cadena en §Orden de reconstrucción — el tracker
   para PR 3a, la rama predecesora inmediata para cada hijo
   posterior), llamado
   `taxa-worktrees/complete-taxa-frontend-migration-<sub-pr-id>`.
2. Copiar solo los archivos listados para ese sub-PR en
   `tasks.md` §Per-task evidence (columna `Source files` arriba)
   en el nuevo worktree usando `cp -p`. Sin ediciones al copiar.
3. Correr el comando de test enfocado (ver las filas de tareas
   por sub-PR en `tasks.md` §"Per-task evidence"). DEBE pasar
   antes de cualquier commit.
4. Correr el harness de runtime (ver misma tabla). DEBE salir
   0 / devolver la salida esperada.
5. Conventional Commit con subject en inglés (sin trailer de
   IA). Cuerpo del PR en español según `AGENTS.md` §Hard Rules:
   `## Resumen`, `## Cambios`, `## Validación`,
   `## Lo que NO cambió`.
6. Abrir el PR contra la **rama base** de ese sub-PR (nunca
   `develop`) vía la skill `branch-pr`. Añadir una sección
   `## Chain Context` (Chain / Tracker PR / Position / Base /
   Depends on / Follow-up / Review budget / Starts at / Ends with)
   más un diagrama de dependencias que marque el PR actual con
   `📍`. La sección Chain Context se **añade** a la plantilla de PR
   del repo — no reemplaza `## Resumen` / `## Cambios` /
   `## Validación` / `## Lo que NO cambió`.
7. Verificar la higiene de diff de la cadena:
   `git diff --stat <rama-base>` muestra **solo** los archivos de
   esta rebanada. Un diff contaminado es un **bug de base** —
   reapuntar o rebasear sobre el predecesor correcto antes de la
   revisión.
8. En CI verde: marcar las tareas de ese sub-PR como `[x]` en
   `tasks.md` y `tasks-es.md`; anteponer un registro de batch
   por sub-PR aquí y en `apply-progress-es.md` (ver
   §Registro de cambios abajo).
9. Fusionar el hijo dentro del tracker y continuar al siguiente
   sub-PR repitiendo desde el paso 1 con un worktree fresco sobre
   el predecesor ya fusionado. Mantener el PR tracker en **draft /
   no-merge** hasta que los 13 hijos estén revisados e integrados.

### Frontera de reversión por sub-PR

Cada reversión de sub-PR elimina **solo** sus propios archivos
(ver la columna `Source files` arriba y la celda
`Rollback boundary` por tarea en `tasks.md`). Ningún sub-PR
toca los handlers de ruta de `api/server.py`, la lógica
SQLite/WAL, el pipeline ETL ni `extension/manifest.json`. El
repoint de `WEB_DIR` en `api/server.py:54` vive en PR 3d
(atómico con el resto del release de 4 conjuntos del cutover
según `design.md` §"Atomic cutover unit"); su frontera de
reversión es **PR 3e**, no PR 3d solo — PR 3d envía el repoint,
PR 3e es el commit de cutover que voltea el artefacto de build
bajo `out/`. `git revert <pr3e-sha>` es la única reversión de
cutover completo soportada.

**Reversión bajo la cadena** — dos ventanas:

| Ventana | Estado | Reversión |
|---|---|---|
| Antes de que el tracker se fusione | Nada está en `develop`; la cadena vive solo en la rama tracker | Retener o cerrar el PR tracker — `develop` queda intacto por construcción |
| Después de que el tracker se fusione | La cadena completa aterriza en `develop` en una única integración | `git revert <pr3e-sha>` restaura la build vanilla legacy atómicamente (según `design.md` §"Rollback unit") |

Para que `<pr3e-sha>` siga siendo direccionable en `develop`, el
tracker DEBE fusionarse con un **merge commit** (sin squash), de
modo que los commits individuales de la cadena sobrevivan a la
integración. Si el tracker se fusiona con squash, la unidad de
reversión atómica pasa a ser el propio merge del tracker:
`git revert -m 1 <tracker-merge-sha>`. En cualquier caso la
reversión es **una sola** que cubre el cutover completo de cuatro
conjuntos — **no se admite reversión de subconjunto**.

---

## Registro de cambios

La fase de apply puebla esta sección por sub-PR. Cada entrada
registra el id del sub-PR, el hash del commit, los flips de
puerta (si los hay) y cualquier justificación de
`size:exception` (no se espera ninguna; el sub-PR más grande es
5b a ~360 LoC, bajo el presupuesto de 400 líneas).

### 2026-09-02 — Estado de planificación inicial

- `tasks.md` y `tasks-es.md` autordos (este cambio);
  `proposal.md` / `spec.md` / `design.md` trasladados
  literalmente del predecesor.
- `apply-progress.md` y `apply-progress-es.md` inicializados
  con la tabla de estado de reconstrucción de arriba; todos los
  sub-PRs marcados como **pendientes de reconstrucción**.
- G1 PASS registrado (predecesor `design.md::§1`).
- G2 PASS registrado (entrada del predecesor
  `apply-progress.md` del 2026-08-30 contra la build limpia
  verificada de Next 16.3.3 / Turbopack).
- G3 Tier-1 PASS registrado (predecesor `apply-progress.md`,
  PR #109 + #111 + #115 + #116, los 26 consumidores §3.1 en
  verde vía `scripts/verify_consumers.py`).
- Cierre de G4 / G5 / G6 diferido a Fase 6 (trabajo de
  validación tras el camino candidato).

> (Entradas posteriores por sub-PR anexadas abajo por el worker
> de apply, un bloque por fusión de sub-PR.)

---

## Pre-flight de puerta para PR 3e (cutover atómico)

La unidad atómica de cutover (según `design.md` §"Atomic
cutover unit") cambia exactamente lo siguiente en un único
release:

1. **Constante `WEB_DIR`** en `api/server.py:54` (ya reorientada
   en Fase 3d; PR 3e voltea el artefacto de build bajo `out/`
   desde la build candidata a la build de producción con la
   verificación de runtime `engines.node >= 20.9.0` activa).
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

**No se admite reversión de subconjunto.** PR 3e se publica
solo cuando cada puerta de abajo está PASS:

| Puerta | Estado (trasladado / cierre planificado) | Fuente |
| --- | --- | --- |
| G1 (origen único) | **PASS registrado** | Predecesor `design.md::§1` |
| G2 (build fundacional) | **PASS registrado** contra la build limpia verificada de Next 16.3.3 / Turbopack | Entrada del predecesor `apply-progress.md` del 2026-08-30 |
| G3 Tier-1 (preparación de consumidores, legacy pre-cut) | **PASS registrado** — los 26 consumidores §3.1 en verde vía el fixture controlado, `scripts/verify_consumers.py` | Predecesor `apply-progress.md` (PR #109 + #111 + #115 + #116) |
| G4 (paridad Playwright + Lighthouse) | **bloqueado — verificador no autordado**; debe cerrar en la fase de apply | Fase 6c — `scripts/g4_measure.sh` contra la build candidata aterrizada en Fase 5c |
| G5 (baseline de hidratación) | **no reproducible — baseline legacy no en disco**; debe reconstruirse o reemplazarse durante la fase de apply | Fase 6a — `scripts/reconstruct_hydration_baseline.py` lee los números documentados del predecesor desde `design.md` §"Migration Evidence Baseline" |
| G6 (ensayo de cutover) | **bloqueado — verificador no autordado**; debe cerrar en la fase de apply | Fase 6b — `scripts/rehearse_cutover.py` dry-runea la unidad atómica de cutover contra el manifesto activado de la copia de trabajo |

**Secuencia de activación de cutover** (cuando las seis puertas
estén verdes):

1. Autorar el **registro de activación post-cut** en
   `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
   (la copia de trabajo; el predecesor
   `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
   queda byte-idéntico congelado) — voltea `activation_status`
   y `replacement.status` a Tier-2 para cada uno de los 26
   consumidores §3.1.
2. Aplicar la **unidad atómica de cutover** — el cambio de
   cuatro conjuntos en un único release (según
   `design.md` §"Atomic cutover unit").
3. Correr el verificador G3 Tier-2 contra la selección
   activada; `CONSUMER-READINESS.json` sale 0 con
   `activation_complete: true`, `unselected_count: 0`.
4. Correr `make smoke` + Playwright + Lighthouse; verificar la
   lista de paridad (según `design.md` §"Parity / evidence
   plan").
5. Marcar el PR de cutover (hijo 13 / 13, apuntando a la rama del
   PR 6c) listo para revisión y voltear el footer de estado de
   puertas en §Status abajo de "blocked / unreproducible /
   blocked" a "PASS recorded".
6. Fusionar PR 3e dentro del tracker — la cadena queda completa.
   Sacar `docs/complete-taxa-frontend-migration-plan` **de draft**
   y fusionarlo a `develop` con un **merge commit** (sin squash,
   para que `<pr3e-sha>` siga siendo direccionable para la
   reversión atómica). Este es el único punto en el que la
   migración llega a `develop`.

---

## Reconciliación del pronóstico (trasladada de `tasks.md` §"Forecast reconciliation")

- **3a** ~175 LoC authored; **3b** ~230; **3c** ~180; **3d**
  ~190; **4a** ~180; **4b** ~90; **5a** ~280; **5b** ~360;
  **5c** ~200; **6a** ~50; **6b** ~120; **6c** ~20; **3e** ~120
  (mayormente delta de `apply-progress.md`). **Total**: ~2.225
  LoC authored a través de 13 sub-PRs.
- El sub-PR más grande es **5b** a ~360 LoC, cómodamente bajo
  el **presupuesto de revisión de 400 líneas por PR** con
  -40 LoC (-10 %) de holgura. **No se requiere
  `size:exception`.**
- **PRs encadenados recomendados**: **Sí** — cada sub-PR cabe
  por sí solo en el presupuesto por PR, pero el total de ~2.225
  líneas y el cutover atómico (la feature DEBE integrarse antes
  de llegar a `develop`) sitúan este cambio en la compuerta de
  Feature Branch Chain.
- **Estrategia de cadena**: **`feature-branch-chain`** (elegida
  por el usuario). El tracker
  `docs/complete-taxa-frontend-migration-plan` es draft/no-merge
  y es el **único** PR que apunta a `develop`; el PR hijo 3a
  apunta al tracker; cada hijo posterior apunta a su rama
  predecesora inmediata. Sustituye, para este cambio, el default
  de `AGENTS.md` §4 de apuntar directo a `develop` y el
  precedente de apply-progress del predecesor.
- **Estrategia de entrega**: **`ask-on-risk`** (según
  preflight; sin flag de riesgo abierto — el Enfoque A es
  FINAL, el predecesor está congelado, cada sub-PR cabe bajo
  400 líneas).
- **Decision needed before apply**: **No** (Enfoque A
  bloqueado, estrategia de cadena conocida, cada sub-PR dentro
  del presupuesto).

---

## Carga / Frontera de PR

- **Modo**: **Feature Branch Chain** — 1 tracker draft/no-merge
  (`docs/complete-taxa-frontend-migration-plan` → `develop`) más
  13 PRs hijos secuenciales (Fase 3 + Fase 4 + Fase 5, seguidos
  de los eslabones de validación de la Fase 6, seguidos del
  cutover atómico PR 3e como último hijo).
- **Total sub-PRs**: **13** (3a, 3b, 3c, 3d, 4a, 4b, 5a, 5b,
  5c, 6a, 6b, 6c, 3e — notar que 6a, 6b, 6c son trabajo de
  validación tras el camino candidato; 3e tiene compuerta en
  las seis puertas verdes).
- **Cada sub-PR ≤ 360 LoC authored**; **ningún** sub-PR excede
  el presupuesto de revisión de 400 líneas por PR. **No se
  espera ni planifica ninguna `size:exception`.**
- **La base de cada PR hijo** = su **rama predecesora inmediata**
  (el tracker para PR 3a). **Solo el tracker apunta a `develop`,
  y permanece en draft / no-merge hasta que la cadena se
  completa.**

---

## Riesgos

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Secuencia de reconstrucción interrumpida; fusión parcial de sub-PRs de Fase 3 deja el proyecto en estado inconsistente. | Media | El test enfocado de cada sub-PR pasa independientemente de sub-PRs subsiguientes. Bajo el Feature Branch Chain ningún estado parcial puede llegar a `develop`: los hijos se acumulan solo en el tracker draft/no-merge. Un hijo atascado bloquea a sus sucesores dentro de la cadena, nunca a `develop`. |
| Directorio del predecesor `migrate-nextjs-tailwind4/` editado accidentalmente durante la reconstrucción; los archivos fuente se desvían de la historia de planificación congelada. | Alta | El directorio del predecesor está marcado como solo lectura a nivel de sistema de archivos; CI / protección de rama rechaza cualquier PR que lo modifique. El cuerpo del PR de cada sub-PR debe incluir una sección `## Lo que NO cambió` confirmando que el predecesor quedó byte-idéntico. |
| Trabajo de validación de Fase 6 genera accidentalmente código nuevo en `web/**`, handlers de ruta nuevos en `api/server.py`, o archivos nuevos en `extension/**` (viola el contrato "solo validación, no migración"). | Media | Las tareas de Fase 6 están limitadas a shims `scripts/*`, artefactos de medición en `out/`, y deltas de `apply-progress.md`. No se permiten ediciones en `web/**`, handlers de ruta de `api/server.py` o `extension/**` en Fase 6. El borrado 5c.6 vive en PR 5c, NO en Fase 6. |
| Reconstrucción de G5 produce un baseline que se deriva de los números documentados del predecesor (la auditoría §3.3.5 del predecesor lista el baseline legacy como **no reproducible**). | Media | `scripts/reconstruct_hydration_baseline.py` lee los números documentados literalmente desde `openspec/changes/migrate-nextjs-tailwind4/design.md` §"Migration Evidence Baseline"; cualquier deriva se registra como actualización del registro de riesgos en `design.md` antes de que G5 pueda voltearse. |
| Ensayo de G6 falla cerrado (dry-run de solo subconjunto sale distinto de cero) y bloquea el cutover. | Baja | El invariante fail-closed es el spec — las reversiones de subconjunto rompen el shell SPA. PR 3e se publica solo cuando el ensayo atómico completo sale 0. |
| Medición de G4 excede el presupuesto de delta ≤ 0 % en initial paint o latencia de interacción. | Media | `scripts/g4_measure.sh` registra el delta; si excede 0 %, el worker de apply escribe una solicitud de exención en `design.md` §"Risk register" y la puerta queda bloqueada hasta que un mantenedor la apruebe. |
| Seis sub-PRs nuevos (3a–3d, 4a–4b) más cuatro (5a–5c) más tres de validación (6a–6c) más uno de cutover (3e) inflan el conteo total de PRs que los mantenedores revisan. | Baja | Cada sub-PR ≤ 360 LoC; el foco de revisión se mantiene estrecho; la estrategia de cadena es `feature-branch-chain` según la elección explícita del usuario, así que cada hijo se revisa contra su predecesor inmediato y el revisor nunca vuelve a leer una rebanada ya aterrizada. |
| Un PR hijo se corta desde `origin/develop` en lugar de su base de cadena, por lo que su diff muestra rebanadas ajenas ya fusionadas en el tracker. | Media | Tratar un diff contaminado como **bug de base**, no como hallazgo de revisión: reapuntar o rebasear sobre el predecesor inmediato hasta que solo aparezca la unidad de trabajo actual. El paso 7 de §Manifiesto de reconstrucción convierte `git diff --stat <rama-base>` en una compuerta por PR. |
| Flip del `cutover-manifest.json` de la copia de trabajo (Fase 6b.3) edita accidentalmente la copia congelada del predecesor en vez de la copia de trabajo. | Alta | El flip se escribe en `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json` (copia de trabajo); el predecesor `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` queda byte-idéntico. El worker de apply DEBE hacer diff de ambas copias antes de PR 3e. |

---

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

---

## Estado

**El Enfoque A es FINAL** (bloqueado el 2026-09-02; registrado
en §1 de `design.md`). G1 PASS registrado; G2 PASS registrado
contra la build limpia verificada de Next 16.3.3 / Turbopack;
G3 Tier-1 PASS registrado (los 26 consumidores §3.1 en verde
contra el runtime legacy pre-cut vía el fixture controlado,
`scripts/verify_consumers.py`, PR #109 + #111 + #115 + #116).
G3 Tier-2 (selección atomic-cut) **NO PASADO** — con compuerta
en el cierre de G4 + G5 + G6. G4 (paridad Playwright +
Lighthouse) **bloqueado — verificador no autordado**; debe
cerrar en la fase de apply vía Fase 6c. G5 (baseline de
hidratación) **no reproducible — baseline legacy no en
disco**; debe reconstruirse o reemplazarse durante la fase de
apply vía Fase 6a. G6 (ensayo de cutover) **bloqueado —
verificador no autordado**; debe cerrar en la fase de apply vía
Fase 6b. El predecesor
`openspec/changes/migrate-nextjs-tailwind4/**` está
**congelado**. Sin activación de FastAPI en esta pasada de
diseño; el cutover atómico PR 3e se publica solo cuando las
seis puertas estén verdes.

> **Footer (flips de la fase de apply)**: G1: PASS registrado ·
> G2: PASS registrado · G3 Tier-1: PASS registrado · G3 Tier-2:
> NO PASADO (con compuerta) · G4: bloqueado — verificador no
> autordado · G5: no reproducible — baseline legacy no en disco
> · G6: bloqueado — verificador no autordado. El footer voltea
> a PASS registrado para G4 / G5 / G6 solo después de que Fase
> 6 cierre y PR 3e se publique.

---

## Siguiente paso

La **fase de apply** (`sdd-apply`) lee `tasks.md` y este
`apply-progress.md`, luego ejecuta el manifiesto de
reconstrucción (§Manifiesto de reconstrucción) sub-PR por
sub-PR. El trabajo de validación de Fase 6 (6a, 6b, 6c) corre
después de que el camino candidato (3a–5c) esté verde y antes
de PR 3e. El cutover atómico PR 3e se publica solo cuando las
seis puertas estén verdes. La **fase de verify** (`sdd-verify`)
confirma la lista de paridad (según `design.md` §"Parity /
evidence plan") y la unidad de reversión (`git revert <pr3e-sha>`
restaura la build vanilla legacy atómicamente). La **fase de
archive** (`sdd-archive`) copia cada spec per-dominio
literalmente en
`openspec/specs/{frontend-runtime,design-tokens,browser-state-hydration,frontend-bootstrap,research}/spec.md`
y promueve el spec modular-architecture al árbol de specs
canónicos.