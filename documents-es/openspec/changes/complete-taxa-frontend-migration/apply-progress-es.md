# Progreso de apply: complete-taxa-frontend-migration

> Artefacto de persistencia en modo híbrido. Refleja el
> apply-progress estructurado en Engram (`topic_key` =
> `sdd/complete-taxa-frontend-migration/apply-progress`).
>
> **Estado inicial (2026-09-02)**: cada sub-PR bajo el
> Enfoque A (`tasks.md` Fases 3a–6c + PR 3e) está
> **pendiente de reconstrucción**. Ningún PR hijo se ha
> abierto todavía. La rama tracker
> `docs/complete-taxa-frontend-migration-plan` ya existe y
> contiene los artefactos de planificación; es la **única**
> rama que apuntará a `develop`, y permanece en **draft /
> no-merge** hasta que toda la cadena esté revisada e
> integrada. Nada se ha entregado a `develop` todavía. La
> tabla de pre-flight de puertas (§Pre-flight de puerta
> para PR 3e) registra el estado trasladado de G1, G2, G3
> Tier-1 (todos PASS registrados del predecesor) y el
> estado de cierre de G4, G5, G6 (los tres diferidos al
> trabajo de validación de Fase 6).
>
> **El Enfoque A es FINAL** (bloqueado el 2026-09-02,
> registrado en `design.md::§1`); no hay ruta de anulación
> abierta. **El predecesor `migrate-nextjs-tailwind4/` está
> congelado** — cada sub-PR en este cambio DEBE dejar
> `openspec/changes/migrate-nextjs-tailwind4/**`
> byte-idéntico (la protección de rama rechaza cualquier PR
> que lo edite).
>
> **2026-09-02 — revisión correctiva del plan**: la tabla
> de reconstrucción de abajo, la tabla de topología de la
> cadena y el ámbito por sub-PR fueron reordenados y
> re-ambidos después de que el portón de apply identificara
> un defecto de orden de dependencia (PR 3a requería
> `next build`/`out/index.html` antes de que existieran el
> toolchain de Next/React/Tailwind/TypeScript y el contrato
> de runtime de Node; esos aterrizaban en el PR 3c
> original, DESPUÉS del PR 3a original). La topología
> corregida introduce un **PR de bootstrap de toolchain en
> la posición 1**, degrada la **exportación estática del
> App Router** a la posición 2 (ahora satisfacible porque
> el toolchain ya existe), mantiene Tailwind/tokens en la
> posición 3, fusiona la reescritura del Makefile con el
> repoint de `WEB_DIR` + AC-21 en la posición 4, y sigue
> con state, ports, e2e, validación y cutover atómico. El
> conteo de 13 hijos se preserva.

---

## Estado de reconstrucción

> **Justificación del reordenamiento (revisión correctiva
> del plan)**. La Fase 3a original era insatisfacible
> porque su testigo de `next build` requería el toolchain
> que la Fase 3c original envió DESPUÉS de ella. La
> topología corregida invierte la dependencia: el
> **bootstrap de toolchain** aterriza primero (posición 1),
> la **exportación estática del App Router** segundo
> (posición 2, testigo ahora satisfacible). El trabajo de
> Tailwind/tokens de la Fase 3b original se mueve a la
> posición 3 (depende de Tailwind instalado en la
> posición 1). La reescritura de `Makefile::api` de la
> Fase 3c original se fusiona con el repoint de `WEB_DIR`
> + lector AC-21 de la Fase 3d original en un único
> sub-PR en la **posición 4** (depende de que `next build`
> produzca `out/` vía la receta `Makefile::api`; el
> contrato de runtime de Node de la posición 1 se invoca
> desde el Makefile). Las posiciones 5–13 (4a hasta 3e)
> conservan su numeración de tarea del predecesor y su
> ámbito. **El conteo de 13 hijos se preserva.**

| Sub-PR | Alcance | Presupuesto LoC (authored) | Archivos fuente | Estado |
|--------|---------|----------------------------|-----------------|--------|
| PR 3a | **Bootstrap de toolchain** (NUEVA posición 1) | ~210 authored; excepción de lockfile generado aprobada por el usuario | `package.json` + `package-lock.json` regenerado (la excepción queda restringida a cambios de resolución requeridos por este manifiesto, y ambos se revisan juntos; `next@^16` / `react@^19` / `react-dom@^19` / `tailwindcss@^4` / toolchain TS / `engines.node ">=20.9.0"` / `scripts.check-runtime` / `scripts.build:web`; deps legacy de Tailwind 3.4 eliminadas) + `scripts/check-runtime.mjs` (nuevo, Node ≥ 20.9.0) + `tsconfig.json` (modificado en su lugar; el predecesor ya está en la raíz del repo; config base + aliases de ruta `@taxa/<capability>`) + `.nvmrc` (nuevo, pin `20`) + `tests/test_toolchain_bootstrap.py` (nuevo) + `tests/test_check_runtime.py` (nuevo) | pendiente de reconstrucción |
| PR 3b | **Exportación estática del App Router** (NUEVA posición 2; era el 3a original) | ~175 | `src/app/{layout,page}.tsx` (nuevos) + `next.config.mjs` (nuevo, `output: "export"` + `images.unoptimized: true` + `trailingSlash: false` + `reactStrictMode: true`) + `tests/test_app_shell_render.py` (nuevo, lee `out/index.html` después de `npx next build`) | pendiente de reconstrucción |
| PR 3c | **Tokens de diseño + `@theme` de Tailwind 4** (era el 3b original; ahora posición 3; depende de `tailwindcss@^4` de 3a) | ~230 | `src/app/globals.css` (nuevo, `@import "tailwindcss"` + `@theme` + `@layer base`) + `src/modules/design-system/{infrastructure/index.ts,presentation/Icon.tsx,presentation/Button.tsx}` (nuevos) + `tests/test_tailwind_4_parity.py` (nuevo) + `tests/test_design_system_purity.py` (nuevo) | pendiente de reconstrucción |
| PR 3d | **Makefile/mount** (NUEVA posición 4; fusiona 3c + 3d originales; depende de `next build` de 3b + Tailwind de 3c) | ~240 | `Makefile` (modificado, target `api:` ejecuta `check-runtime.mjs` → `npm ci` → `npm run build:web` → `uvicorn … --port 8765`; `make css` se vuelve shim no-op) + `api/server.py` (modificado, delta de 1 línea en línea 54, `WEB_DIR = Path(__file__).parent.parent / "out"`) + `src/data/search-engines.js` (nuevo, copia byte a byte de `web/search_urls.js` con export nombrado `SEARCH_ENGINES`) + `tests/test_smoke.py` (modificado, actualización de ruta `open()`) + `tests/test_static_mount.py` (nuevo) + `tests/test_make_api_build.py` (nuevo) | pendiente de reconstrucción |
| PR 4a | Typed store + 4 lecturas + 4 escrituras (sin cambios) | ~180 | `src/modules/browser-state/{domain/keys.ts,infrastructure/store.ts,index.ts}` (nuevos) + `tests/test_browser_state_keys.py` (nuevo) | pendiente de reconstrucción |
| PR 4b | Guardia de hidratación + cero warnings Playwright (sin cambios) | ~90 | `src/modules/app-shell/{presentation/AppShell.tsx,infrastructure/page-chrome.tsx}` (nuevos) + `tests/test_hydration_console.py` (nuevo, Playwright) | pendiente de reconstrucción |
| PR 5a | Port del módulo taxonomy (extendido; absorbe el strip de pestañas de DetailPanel + OverviewTab + Kebab Search-online fuerza) | ~310 | `src/modules/taxonomy/{domain/taxon.ts,infrastructure/api.ts,application/useTaxonTree.ts,presentation/{Tree,DetailPanel,OverviewTab,Kebab,Breadcrumb}.tsx}` (nuevo + extensión; `DetailPanel` envía el strip de tres pestañas `Overview` / `Search` / `Folder` según la superficie UI verificada, con `Overview` siempre disponible/visible) + `tests/test_taxonomy_infra.py` (nuevo; incluye el testigo de regresión Playwright `Search online` → pestaña `Search`) | pendiente de reconstrucción |
| PR 5b | Port del módulo research + pin CDN (extendido; absorbe SearchTab + FolderTab + SearchLinkList + re-anclaje de la pestaña `Browser` del header como Research global) | ~395 | `src/modules/research/{domain/{research-file,engine,file-node}.ts,infrastructure/{api,search-engines}.{ts,js},application/{useFileExplorer,useFileViewer}.ts,presentation/{FileExplorer,FileViewer,RawTableTreeTabs,MetaStrip,BreadcrumbPanel,Banners,SearchLinkList,SearchTab,FolderTab}.tsx}` (nuevo; `SearchTab` renderiza las cinco secciones de categoría `General` / `Taxonomic` / `Academic` / `Multimedia` / `Documents` en orden fijo; `FolderTab` es un cuerpo separado; `SearchLinkList` mapea cada `Engine` a un anchor con `target="_blank"` + `rel="noopener noreferrer"`) + `src/modules/app-shell/infrastructure/page-chrome.tsx` (modificado; pestaña `Browser` del header re-anclada como Research global / file explorer, NO scoped por taxón) + `tests/test_research_infra.py` (nuevo; incluye la triangulación de la lista categorizada de enlaces salientes y el testigo de Browser-global) | pendiente de reconstrucción |
| PR 5c | Selectores E2E + contrato `data-*` + borrar legacy (sin cambios) | ~200 | `tests/test_e2e_file_explorer.py` (modificado, actualización de selectores DOM) + `tests/test_web_toggle.py` (modificado, actualización de toggle de tema) + `tests/test_evidence_baseline.py` (modificado, aserción de roster legacy voltea a "ausente") + borrado de `web/{index.html,index.css}` + borrado de `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,help,keymap,settings,search,file_explorer,file_viewer,format,search_urls}.js` (18 archivos) + borrado de `tailwind.config.js` + `web/dist/tailwind.css` ya no se rastrea | pendiente de reconstrucción |
| Fase 6a | Cierre de baseline de hidratación G5 (sin cambios) | ~50 (mayormente medición) | `scripts/reconstruct_hydration_baseline.py` (nuevo) + `scripts/g5_close.sh` (nuevo) + `web/dist/evidence-baseline.json` (regenerado, esquema fijado por `tests/test_hydration_timing.py`) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| Fase 6b | Ensayo de cutover G6 (sin cambios) | ~120 | `scripts/rehearse_cutover.py` (nuevo) + `tests/test_rehearse_cutover.py` (nuevo) + `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json` (copia de trabajo; la copia del predecesor queda byte-idéntica congelada) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| Fase 6c | Paridad G4 Playwright + Lighthouse (sin cambios) | ~20 (mayormente medición) | `scripts/g4_measure.sh` (nuevo) + `out/g4-parity-report.json` (artefacto Playwright + Lighthouse) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| PR 3e | Cutover atómico (sin cambios) | ~120 (mayormente delta de `apply-progress.md`) | `apply-progress.md` (flip de footer de estado de puertas + entrada de registro de cambios) + re-corridas de `tests/test_verify_consumers.py`, `tests/test_verify_build.py`, `make api`, `make smoke` | pendiente de reconstrucción (con compuerta en las seis puertas verdes) |

**Conteo de sub-PRs**: **13** (1 bootstrap de toolchain +
1 exportación estática del App Router + 1 Tailwind/tokens
+ 1 Makefile/mount + 2 browser-state + 2 puertos de
capability + 1 e2e + borrar legacy + 3 validación de Fase
6 + 1 cutover atómico).

**Total authored**: ~2.265 LoC a través de los 13
sub-PRs (Δ ≤ 20 LoC del pronóstico previo de ~2.245; el
nuevo split de componentes absorbe el strip de pestañas
de `DetailPanel` + `OverviewTab` + `Kebab` en PR 5a y
`SearchTab` + `FolderTab` + `SearchLinkList` + el re-
anclaje de la pestaña `Browser` del header en PR 5b sin
duplicar código de producción). El sub-PR más grande es
**5b** a ~395 LoC (bajo el presupuesto de 400 líneas con
**-5 LoC de holgura ajustada** — mantenibilidad
rastreada; PR 5b queda dentro del presupuesto de revisión
de 400 líneas pero es el más cargado de presión de la
cadena). La única `size:exception` está aprobada por el
usuario para el `package-lock.json` regenerado de PR 3a;
su trabajo authored permanece ≤400 y se rechaza churn de
lockfile no relacionado. El más pesado de los sub-PRs re-
ambidos es **3d** a ~240 LoC (bajo el presupuesto de 400
líneas con -160 LoC de holgura).

### Orden de reconstrucción (determinístico, secuencial a lo largo de la cadena)

```
3a (bootstrap de toolchain) →
3b (exportación estática del App Router) →
3c (Tailwind/tokens) →
3d (Makefile/mount) →
4a → 4b → 5a → 5b → 5c →
6a (G5) → 6b (G6) → 6c (medición G4) →
3e (cutover atómico, con compuerta)
```

**Estrategia de cadena: `feature-branch-chain`** (elegida
por el usuario). La rama existente
`docs/complete-taxa-frontend-migration-plan` es el
**tracker**: draft / no-merge, y el **único** PR que
apunta a `develop`. El PR hijo 3a apunta al tracker; cada
hijo posterior apunta a su **rama predecesora inmediata**.
Esto sustituye, para este cambio, el default de
`AGENTS.md` §4 de apuntar directo a `develop`.

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

Los hijos se fusionan **en orden** dentro del tracker; a
medida que cada hijo se fusiona, el siguiente se
reapunta al tracker (GitHub reapunta automáticamente
cuando la rama base se fusiona y se borra). El tracker
acumula la feature completa y se fusiona a `develop`
solo después de que PR 3e — el último hijo — aterrice.

**Dependencia por sub-PR (contrato de la revisión
correctiva del plan)**:

| Posición | Depende de | Satisface (testigo) |
|---|---|---|
| 1 / 3a (bootstrap de toolchain) | — | `npm ci` exit 0; `node scripts/check-runtime.mjs` exit 0 en Node ≥ 20.9.0; `npx tsc --noEmit` resuelve todos los aliases `@taxa/*` |
| 2 / 3b (exportación estática del App Router) | 1 | `npx next build` exit 0; `out/index.html` no vacío con meta de viewport + preload de Raleway |
| 3 / 3c (Tailwind/tokens) | 1 | `npx next build` exit 0 con utilidades de Tailwind 4 en `out/_next/static/chunks/*.css`; test de paridad enumera cada token legacy `:root` |
| 4 / 3d (Makefile/mount) | 2 + 3 | `make api` exit 0; uvicorn vincula solo `127.0.0.1:8765`; `curl /index.html` devuelve `out/index.html`; contrato AC-21 preservado |
| 5 / 4a (typed store) | 3 | 4 sitios de lectura + 4 de escritura en `src/modules/browser-state/`; ningún otro módulo toca `localStorage` |
| 6 / 4b (guardia de hidratación) | 5 + 2 | Playwright cero warnings de hidratación; `AppShell` usa flag `mounted` reservado en `src/app/page.tsx` |
| 7 / 5a (port de taxonomy) | 6 | View-models de taxonomía renderizan; toggle de tree-source rehidrata vía `localStorage` |
| 8 / 5b (port de research + pin CDN) | 7 + 4 | Archivos de research renderizan vía despachador de 9 formatos; URLs CDN pineadas |
| 9 / 5c (e2e + borrar legacy) | 8 | Selectores e2e actualizados; contrato `data-*` preservado; `web/*` legacy borrado |
| 10–12 / 6a, 6b, 6c (validación) | 9 | G5 reproducible; G6 PASS; G4 PASS; `apply-progress.md` §Registro de cambios flipa para cada uno |
| 13 / 3e (cutover atómico) | 10, 11, 12 + G1/G2/G3 Tier-1 trasladado | Las seis puertas verdes; flip de cutover-manifest Tier-2; uvicorn sirve `out/index.html` desde la build de producción |

**La Fase 6 (6a, 6b, 6c) es trabajo de validación**, no
un objetivo de migración. Corre **después** de que el
camino candidato completo (posiciones 1–9) esté verde y
acumulado en el tracker, y **antes** de que PR 3e pueda
aterrizar. La Fase 6 puede entregarse como tres eslabones
de la cadena (el default: posiciones 10 / 11 / 12) o
colapsar en un único PR hijo en la posición 10, según la
decisión `ask-on-risk` del mantenedor; colapsarla acorta
la cadena sin cambiar la topología (el batch sigue
apuntando a la rama del PR 5c, y PR 3e sigue apuntando
al último eslabón de la Fase 6). Los LoC combinados son
~190 authored + ~120 artefacto de medición, cómodamente
bajo el presupuesto de 400 líneas.

### Política de worktree

- **Colocación CodeGraph-aware**: cada worktree generado
  para un sub-PR se ubica bajo
  `<repo-parent>/<repo-name>-worktrees/<worktree-name>`
  (el home del usuario, hermano del worktree activo,
  nunca bajo `/tmp` / `/var/tmp`). Cada worktree obtiene
  su propio índice `.codegraph/`; el watcher de CodeGraph
  sincroniza automáticamente tras las ediciones.
- **El worktree del predecesor es de solo lectura**:
  `taxa-worktrees/migrate-nextjs-tailwind4-pr1` (si
  existe) es solo historia de planificación. No editar,
  rebasear ni fusionar desde él.
- **Worktrees de reconstrucción** generados por el worker
  de apply para cada sub-PR: creados frescos desde la
  **rama base** de ese sub-PR en la tabla de cadena de
  arriba — el tracker
  (`docs/complete-taxa-frontend-migration-plan`) para PR
  3a, la rama predecesora inmediata para cada hijo
  posterior. Nunca desde `origin/develop` directamente:
  un worktree cortado desde `develop` produce un diff
  contaminado. Patrón de nombre:
  `taxa-worktrees/complete-taxa-frontend-migration-<sub-pr-id>`.

### Manifiesto de reconstrucción (por sub-PR)

Para cada sub-PR, el worker de apply DEBE:

1. Crear un nuevo worktree desde la **rama base** de ese
   sub-PR (ver la tabla de cadena en §Orden de
   reconstrucción — el tracker para PR 3a, la rama
   predecesora inmediata para cada hijo posterior),
   llamado
   `taxa-worktrees/complete-taxa-frontend-migration-<sub-pr-id>`.
2. Copiar solo los archivos listados para ese sub-PR en
   `tasks.md` §Per-task evidence (columna `Archivos
   fuente` arriba) en el nuevo worktree usando `cp -p`.
   Sin ediciones al copiar.
3. Correr el comando de test enfocado (ver las filas de
   tareas por sub-PR en `tasks.md` §"Per-task evidence").
   DEBE pasar antes de cualquier commit.
4. Correr el harness de runtime (ver misma tabla). DEBE
   salir 0 / devolver la salida esperada.
5. Conventional Commit con subject en inglés (sin trailer
   de IA). Cuerpo del PR en español según `AGENTS.md`
   §Hard Rules: `## Resumen`, `## Cambios`,
   `## Validación`, `## Lo que NO cambió`.
6. Abrir el PR contra la **rama base** de ese sub-PR
   (nunca `develop`) vía la skill `branch-pr`. Añadir una
   sección `## Chain Context` (Chain / Tracker PR /
   Position / Base / Depends on / Follow-up / Review
   budget / Starts at / Ends with) más un diagrama de
   dependencias que marque el PR actual con `📍`. La
   sección Chain Context se **añade** a la plantilla de
   PR del repo — no reemplaza `## Resumen` / `## Cambios`
   / `## Validación` / `## Lo que NO cambió`.
7. Verificar la higiene de diff de la cadena:
   `git diff --stat <rama-base>` muestra **solo** los
   archivos de esta rebanada. Un diff contaminado es un
   **bug de base** — reapuntar o rebasear sobre el
   predecesor correcto antes de la revisión.
8. En CI verde: marcar las tareas de ese sub-PR como
   `[x]` en `tasks.md` y `tasks-es.md`; anteponer un
   registro de batch por sub-PR aquí y en
   `apply-progress-es.md` (ver §Registro de cambios
   abajo).
9. Fusionar el hijo dentro del tracker y continuar al
   siguiente sub-PR repitiendo desde el paso 1 con un
   worktree fresco sobre el predecesor ya fusionado.
   Mantener el PR tracker en **draft / no-merge** hasta
   que los 13 hijos estén revisados e integrados.

### Frontera de reversión por sub-PR

Cada reversión de sub-PR elimina **solo** sus propios
archivos (ver la columna `Archivos fuente` arriba y la
celda `Frontera de reversión` por tarea en `tasks.md`).
Ningún sub-PR toca los handlers de ruta de
`api/server.py`, la lógica SQLite/WAL, el pipeline ETL
ni `extension/manifest.json`. El repoint de `WEB_DIR` en
`api/server.py:54` vive en PR 3d (atómico con el resto
del release de 4 conjuntos del cutover según `design.md`
§"Atomic cutover unit"); su frontera de reversión es
**PR 3e**, no PR 3d solo — PR 3d envía el repoint, PR
3e es el commit de cutover que voltea el artefacto de
build bajo `out/`. `git revert <pr3e-sha>` es la única
reversión de cutover completo soportada.

**Reversión bajo la cadena** — dos ventanas:

| Ventana | Estado | Reversión |
|---|---|---|
| Antes de que el tracker se fusione | Nada está en `develop`; la cadena vive solo en la rama tracker | Retener o cerrar el PR tracker — `develop` queda intacto por construcción |
| Después de que el tracker se fusione | La cadena completa aterriza en `develop` en una única integración | `git revert <pr3e-sha>` restaura la build vanilla legacy atómicamente (según `design.md` §"Rollback unit") |

Para que `<pr3e-sha>` siga siendo direccionable en
`develop`, el tracker DEBE fusionarse con un **merge
commit** (sin squash), de modo que los commits
individuales de la cadena sobrevivan a la integración.
Si el tracker se fusiona con squash, la unidad de
reversión atómica pasa a ser el propio merge del
tracker: `git revert -m 1 <tracker-merge-sha>`. En
cualquier caso la reversión es **una sola** que cubre
el cutover completo de cuatro conjuntos — **no se
admite reversión de subconjunto**.

---

## Registro de cambios

La fase de apply puebla esta sección por sub-PR. Cada
entrada registra el id del sub-PR, el hash del commit,
los flips de puerta (si los hay) y cualquier justificación
de `size:exception` (no se espera ninguna; el sub-PR más
grande es 5b a ~360 LoC, bajo el presupuesto de 400
líneas).

### 2026-09-02 — Estado de planificación inicial

- `tasks.md` y `tasks-es.md` autordos (este cambio);
  `proposal.md` / `spec.md` / `design.md` trasladados
  literalmente del predecesor.
- `apply-progress.md` y `apply-progress-es.md`
  inicializados con la tabla de estado de reconstrucción
  de arriba; todos los sub-PRs marcados como
  **pendientes de reconstrucción**.
- G1 PASS registrado (predecesor `design.md::§1`).
- G2 PASS registrado (entrada del predecesor
  `apply-progress.md` del 2026-08-30 contra la build
  limpia verificada de Next 16.3.3 / Turbopack).
- G3 Tier-1 PASS registrado (predecesor
  `apply-progress.md`, PR #109 + #111 + #115 + #116, los
  26 consumidores §3.1 en verde vía
  `scripts/verify_consumers.py`).
- Cierre de G4 / G5 / G6 diferido a Fase 6 (trabajo de
  validación tras el camino candidato).

### 2026-09-02 — Revisión correctiva del plan (esta entrada)

- **Defecto identificado por el portón de apply**: el
  PR 3a original requería `next build`/`out/index.html`
  antes de que existieran el toolchain de
  Next/React/Tailwind/TypeScript y el contrato de
  runtime de Node ≥ 20.9.0 (esos aterrizaban en el PR 3c
  original).
- **Reordenamiento + re-ambido correctivo aplicado**: la
  posición 1 es ahora un **bootstrap de toolchain**
  (absorbe los pins de deps de `package.json` y
  `scripts/check-runtime.mjs` del PR 3c original); la
  posición 2 es ahora la **exportación estática del App
  Router** (testigo satisfacible porque el toolchain
  está en vivo); la posición 3 sigue siendo
  **Tailwind/tokens** (depende de Tailwind instalado en
  la posición 1); la posición 4 fusiona la
  reescritura de `Makefile::api` del PR 3c original con
  el repoint de `WEB_DIR` + lector AC-21 del PR 3d
  original en un único sub-PR de **Makefile/mount** a
  ~240 LoC authored (muy por debajo de 400). Las
  posiciones 5–13 (4a hasta 3e) conservan su numeración
  de tarea del predecesor y su ámbito.
- **Conteo de 13 hijos preservado**: la nueva topología
  de cadena tiene 13 PRs hijos + 1 tracker, idéntico a
  la original.
- **Total authored**: ~2.245 LoC (arriba desde ~2.225 —
  delta ≤ 50 LoC del nuevo split de cableado de tests).
  El sub-PR más grande es 5b a ~360 LoC (bajo 400, sin
  `size:exception`).
- **El Enfoque A, FastAPI/SQLite, el predecesor
  congelado quedan sin cambios**.
- **`tasks.md`, `apply-progress.md` y los espejos en
  español reautordos con la cadena reordenada**; tabla
  de diseño actualizada.
- Sin código comiteado, pusheado ni aplicado. El worker
  de apply lee este plan corregido cuando se abra la
  siguiente ventana de PR.

### 2026-09-02 — Revisión correctiva de superficie UI y estructura de pestañas (esta entrada)

- **Fuente**: inspección en vivo del navegador de
  `http://127.0.0.1:8765/`. El comportamiento actual
  verificado diverge de la narrativa del spec por
  dominio de dos maneras que esta entrada corrige a
  nivel del SDD (los specs por dominio están fuera del
  alcance de esta revisión; el diseño/spec/tareas/
  apply-progress de alto nivel y los espejos fieles en
  español se actualizan).
- **Superficie UI verificada (vinculante)**:
  - Superficie principal: árbol taxonómico (las
    filas renderizan `rank / name / source /
    species-count` más kebab por fila).
  - Seleccionar cualquier nodo — incluidos los
    dominios de nivel superior como `Archaea` —
    abre un **panel de detalle contextual inline**
    con un encabezado inline y un strip de pestañas.
  - **Tres pestañas en orden fijo: `Overview`,
    `Search`, `Folder`.** Las tres alcanzables desde
    cada selección; **`Overview` siempre está
    disponible y siempre es visible** según la
    política seleccionada por el usuario.
  - `Overview` renderiza el nombre científico, el
    estado de aceptación, la autoría, el conteo de
    especies.
  - `Search` renderiza una lista categorizada de
    enlaces salientes (`General`, `Taxonomic`,
    `Academic`, `Multimedia`, `Documents`) en orden
    fijo. **`Search` es una pestaña primaria**, no
    una lista de tarjetas secundaria.
  - `Folder` es un cuerpo separado (indicador de
    materialize por taxón).
  - La pestaña `Browser` del header es el **Research
    global / file explorer** (NO scoped por taxón).
- **Inconsistencia observada (regresión a cerrar)**:
  la acción kebab `Search online` por fila
  actualmente aterriza en `Overview` para taxones de
  nivel superior (y se permite silenciosamente que
  aterrice en `Overview` para cualquier selección
  cuyo `state.activeTab[taxonId]` no haya sido
  establecido explícitamente). Su interacción
  intencionada DEBE forzar la pestaña `Search` activa
  para **cada** selección — de nivel superior o no.
  La fase de apply cierra la regresión en PR 5a /
  PR 5b.
- **Cambios de alcance (vinculantes)**:
  - PR 5a extendido: absorbe el andamiaje del strip
    de pestañas de `DetailPanel` (strip de 3 pestañas
    `Overview` / `Search` / `Folder`), el cuerpo de
    `OverviewTab`, y el menú `Kebab` con la acción
    `Search online` que fuerza `Search`. Pronóstico:
    ~310 LoC (Δ ~+30 del pronóstico previo de ~280).
  - PR 5b extendido: absorbe `SearchTab` (lista
    categorizada de enlaces salientes en orden
    fijo), `FolderTab` (cuerpo separado),
    presentador `SearchLinkList`, y el re-anclaje de
    la pestaña `Browser` del header como Research
    global / file explorer (NO scoped por taxón).
    Pronóstico: ~395 LoC (Δ ~+35 del pronóstico
    previo de ~360). Permanece bajo el presupuesto
    de revisión de 400 líneas por PR con **-5 LoC de
    holgura ajustada**; mantenibilidad rastreada.
  - **Total authored**: ~2.265 LoC a través de los
    13 sub-PRs (Δ ≤ 20 LoC del pronóstico previo de
    ~2.245; el nuevo split de componentes absorbe
    las piezas adicionales sin duplicar código de
    producción).
  - **Topología de cadena de 13 hijos preservada**;
    sin cambios de posición, dependencia, o base de
    rama de PR.
- **Restricciones de código / commit / push / PR /
  topología de cadena honradas**:
  - Sin código, commit, push, PR, o `git revert`
    realizado en esta revisión.
  - Sin cambios de base de PR; sin reordenamiento
    de cadena.
  - El predecesor `migrate-nextjs-tailwind4/`
    permanece byte-idéntico congelado.
- **Artefactos actualizados** (solo a nivel alto; los
  specs por dominio están fuera de alcance):
  - `openspec/changes/complete-taxa-frontend-migration/design.md`
    — tabla de propiedad de módulos actualizada para
    añadir `OverviewTab`, `SearchTab`, `FolderTab`,
    `Kebab`, `SearchLinkList`; nueva sección
    "Superficie de UI y estructura de pestañas
    (comportamiento actual verificado)" ancla el
    contrato vinculante; tabla de rebanada de
    sub-PRs actualizada para reflejar PR 5a (~310
    LoC) y PR 5b (~395 LoC); tabla de archivos
    afectados actualizada; tabla de riesgos
    actualizada con dos nuevas entradas.
  - `openspec/changes/complete-taxa-frontend-migration/spec.md`
    — sección de paridad funcional extendida con
    siete nuevos criterios de aceptación (strip de
    pestañas del panel de detalle, pestaña
    `Overview`, pestaña `Search`, pestaña `Folder`,
    acción kebab `Search online` fuerza pestaña
    `Search`, pestaña `Browser` del header es
    global).
  - `openspec/changes/complete-taxa-frontend-migration/tasks.md`
    — PR 5a extendido con `OverviewTab`, strip de
    pestañas de `DetailPanel`, contrato kebab
    `Search online` fuerza `Search`, y un testigo
    Playwright de regresión del strip de pestañas;
    PR 5b extendido con `SearchTab`, `FolderTab`,
    `SearchLinkList`, y re-anclaje de la pestaña
    `Browser` del header; tablas de evidencia por
    tarea actualizadas.
  - `openspec/changes/complete-taxa-frontend-migration/apply-progress.md`
    — tabla de sub-PR actualizada (columnas de
    archivos fuente de PR 5a / PR 5b); pronóstico
    total authored actualizado; orden de
    reconstrucción preservado; esta entrada de
    registro de cambios registrada.
  - Espejos en español
    `documents-es/openspec/changes/complete-taxa-frontend-migration/{design-es,spec-es,tasks-es,apply-progress-es}.md`
    — traducciones fieles de las actualizaciones de
    alto nivel de arriba; sin contenido extra
    introducido; los specs por dominio permanecen
    fuera de alcance.

> (Entradas posteriores por sub-PR anexadas abajo por
> el worker de apply, un bloque por fusión de sub-PR.)

---

## Pre-flight de puerta para PR 3e (cutover atómico)

La unidad atómica de cutover (según `design.md` §"Atomic
cutover unit") cambia exactamente lo siguiente en un
único release:

1. **Constante `WEB_DIR`** en `api/server.py:54` (ya
   reorientada en Fase 3d; PR 3e voltea el artefacto de
   build bajo `out/` desde la build candidata a la
   build de producción con la verificación de runtime
   `engines.node >= 20.9.0` activa).
2. **Cada actualización de consumidor activo** en
   `design.md::§3.1` del predecesor (ya autordada por
   Fase 3d para la ruta del lector AC-21; PR 3e voltea
   los 25 consumidores §3.1 restantes para que lean
   desde el árbol de componentes React en lugar de las
   rutas `web/*` legacy). El flip es el registro de
   activación post-cut en
   `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
   (copia de trabajo; la copia del predecesor queda
   congelada).
3. **Los targets `Makefile::api` y `Makefile::web`**
   (ya reescritos por Fase 3d; PR 3e voltea el paso
   `make css` de Tailwind-3.4 legacy de "regenerar
   `web/dist/tailwind.css`" a "exit 0 no-op" — la
   build de Tailwind 4 vive dentro de `next build`).
4. **El artefacto de build** — el directorio `out/`
   mismo (`out/index.html`,
   `out/_next/static/chunks/**`,
   `out/.next/build-manifest.json`, la clasificación de
   página de error si se emite `404.html` /
   `500.html`). El artefacto se regenera por la build
   de producción al momento del cutover.

**No se admite reversión de subconjunto.** PR 3e se
publica solo cuando cada puerta de abajo está PASS:

| Puerta | Estado (trasladado / cierre planificado) | Fuente |
| --- | --- | --- |
| G1 (origen único) | **PASS registrado** | Predecesor `design.md::§1` |
| G2 (build fundacional) | **PASS registrado** contra la build limpia verificada de Next 16.3.3 / Turbopack | Entrada del predecesor `apply-progress.md` del 2026-08-30 |
| G3 Tier-1 (preparación de consumidores, legacy pre-cut) | **PASS registrado** — los 26 consumidores §3.1 en verde vía el fixture controlado, `scripts/verify_consumers.py` | Predecesor `apply-progress.md` (PR #109 + #111 + #115 + #116) |
| G4 (paridad Playwright + Lighthouse) | **bloqueado — verificador no autordado**; debe cerrar en la fase de apply | Fase 6c — `scripts/g4_measure.sh` contra la build candidata aterrizada en posiciones 1–9 |
| G5 (baseline de hidratación) | **no reproducible — baseline legacy no en disco**; debe reconstruirse o reemplazarse durante la fase de apply | Fase 6a — `scripts/reconstruct_hydration_baseline.py` lee los números documentados del predecesor desde `design.md` §"Migration Evidence Baseline" |
| G6 (ensayo de cutover) | **bloqueado — verificador no autordado**; debe cerrar en la fase de apply | Fase 6b — `scripts/rehearse_cutover.py` dry-runea la unidad atómica de cutover contra el manifesto activado de la copia de trabajo |

**Secuencia de activación de cutover** (cuando las seis
puertas estén verdes):

1. Autorar el **registro de activación post-cut** en
   `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
   (la copia de trabajo; el predecesor
   `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
   queda byte-idéntico congelado) — voltea
   `activation_status` y `replacement.status` a Tier-2
   para cada uno de los 26 consumidores §3.1.
2. Aplicar la **unidad atómica de cutover** — el cambio
   de cuatro conjuntos en un único release (según
   `design.md` §"Atomic cutover unit").
3. Correr el verificador G3 Tier-2 contra la selección
   activada; `CONSUMER-READINESS.json` sale 0 con
   `activation_complete: true`, `unselected_count: 0`.
4. Correr `make smoke` + Playwright + Lighthouse;
   verificar la lista de paridad (según `design.md`
   §"Parity / evidence plan").
5. Marcar el PR de cutover (hijo 13 / 13, apuntando a la
   rama del PR 6c) listo para revisión y voltear el
   footer de estado de puertas en §Status abajo de
   "blocked / unreproducible / blocked" a "PASS
   recorded".
6. Fusionar PR 3e dentro del tracker — la cadena queda
   completa. Sacar
   `docs/complete-taxa-frontend-migration-plan` **de
   draft** y fusionarlo a `develop` con un **merge
   commit** (sin squash, para que `<pr3e-sha>` siga
   siendo direccionable para la reversión atómica).
   Este es el único punto en el que la migración llega a
   `develop`.

---

## Reconciliación del pronóstico (corregida)

- **3a** ~210 LoC authored (bootstrap de toolchain —
  absorbe ~40 LoC de pins de deps de `package.json` +
  ~25 LoC de `scripts/check-runtime.mjs` + ~50 LoC de
  base de `tsconfig.json` + 1 LoC de `.nvmrc` + ~95 LoC
  de dos tests nuevos); **3b** ~175 (exportación
  estática del App Router; testigo ahora satisfacible);
  **3c** ~230; **3d** ~240 (el sub-PR re-ambido más
  pesado en la frontera de la posición 4, fusionando
  Makefile + WEB_DIR + AC-21); **4a** ~180; **4b** ~90;
  **5a** ~280; **5b** ~360; **5c** ~200; **6a** ~50;
  **6b** ~120; **6c** ~20; **3e** ~120 (mayormente
  delta de `apply-progress.md`). **Total**: ~2.245 LoC
  authored a través de 13 sub-PRs (delta ≤ 50 LoC de
  las ~2.225 pre-corrección).
- El sub-PR más grande es **5b** a ~360 LoC,
  cómodamente bajo el **presupuesto de revisión de 400
  líneas por PR** con -40 LoC (-10 %) de holgura. **No
  se requiere `size:exception`.**
- El sub-PR re-ambido más pesado es **3d** a ~240 LoC;
  -160 LoC (-40 %) de holgura. **No se requiere
  `size:exception`.**
- **PRs encadenados recomendados**: **Sí** — cada
  sub-PR cabe por sí solo en el presupuesto por PR, pero
  el total de ~2.245 líneas y el cutover atómico (la
  feature DEBE integrarse antes de llegar a `develop`)
  sitúan este cambio en la compuerta de Feature Branch
  Chain.
- **Estrategia de cadena**:
  **`feature-branch-chain`** (elegida por el usuario).
  El tracker `docs/complete-taxa-frontend-migration-plan`
  es draft/no-merge y es el **único** PR que apunta a
  `develop`; el PR hijo 3a apunta al tracker; cada hijo
  posterior apunta a su rama predecesora inmediata.
  Sustituye, para este cambio, el default de
  `AGENTS.md` §4 de apuntar directo a `develop` y el
  precedente de apply-progress del predecesor.
- **Estrategia de entrega**: **`ask-on-risk`** (según
  preflight; sin flag de riesgo abierto — el Enfoque A
  es FINAL, el predecesor está congelado, cada sub-PR
  cabe bajo 400 líneas, el orden de dependencia
  corregido satisface el defecto del portón de apply).
- **Decision needed before apply**: **No** (Enfoque A
  bloqueado, estrategia de cadena conocida, cada sub-PR
  dentro del presupuesto, orden de dependencia
  corregido).

---

## Carga / Frontera de PR

- **Modo**: **Feature Branch Chain** — 1 tracker
  draft/no-merge
  (`docs/complete-taxa-frontend-migration-plan` →
  `develop`) más 13 PRs hijos secuenciales (bootstrap
  de toolchain → exportación estática del App Router →
  Tailwind/tokens → Makefile/mount → 4a → 4b → 5a → 5b
  → 5c, seguidos de los eslabones de validación de la
  Fase 6, seguidos del cutover atómico PR 3e como último
  hijo).
- **Total sub-PRs**: **13** (3a, 3b, 3c, 3d, 4a, 4b,
  5a, 5b, 5c, 6a, 6b, 6c, 3e — notar que 6a, 6b, 6c son
  trabajo de validación tras el camino candidato; 3e
  tiene compuerta en las seis puertas verdes).
- **Cada sub-PR ≤ 360 LoC authored**; **ningún** sub-PR
  excede el presupuesto de revisión de 400 líneas por
  PR. **No se espera ni planifica ninguna
  `size:exception`.**
- **La base de cada PR hijo** = su **rama predecesora
  inmediata** (el tracker para PR 3a). **Solo el tracker
  apunta a `develop`, y permanece en draft / no-merge
  hasta que la cadena se completa.**

---

## Riesgos

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Secuencia de reconstrucción interrumpida; fusión parcial del bootstrap de toolchain + sub-PRs del App Router deja el proyecto en estado inconsistente. | Media | El test enfocado de cada sub-PR pasa independientemente de sub-PRs subsiguientes. Bajo el Feature Branch Chain ningún estado parcial puede llegar a `develop`: los hijos se acumulan solo en el tracker draft/no-merge. Un hijo atascado bloquea a sus sucesores dentro de la cadena, nunca a `develop`. |
| Directorio del predecesor `migrate-nextjs-tailwind4/` editado accidentalmente durante la reconstrucción; los archivos fuente se desvían de la historia de planificación congelada. | Alta | El directorio del predecesor está marcado como solo lectura a nivel de sistema de archivos; CI / protección de rama rechaza cualquier PR que lo modifique. El cuerpo del PR de cada sub-PR debe incluir una sección `## Lo que NO cambió` confirmando que el predecesor quedó byte-idéntico. |
| Trabajo de validación de Fase 6 genera accidentalmente código nuevo en `web/**`, handlers de ruta nuevos en `api/server.py`, o archivos nuevos en `extension/**` (viola el contrato "solo validación, no migración"). | Media | Las tareas de Fase 6 están limitadas a shims `scripts/*`, artefactos de medición en `out/`, y deltas de `apply-progress.md`. No se permiten ediciones en `web/**`, handlers de ruta de `api/server.py` o `extension/**` en Fase 6. El borrado 5c.6 vive en PR 5c, NO en Fase 6. |
| Reconstrucción de G5 produce un baseline que se deriva de los números documentados del predecesor (la auditoría §3.3.5 del predecesor lista el baseline legacy como **no reproducible**). | Media | `scripts/reconstruct_hydration_baseline.py` lee los números documentados literalmente desde `openspec/changes/migrate-nextjs-tailwind4/design.md` §"Migration Evidence Baseline"; cualquier deriva se registra como actualización del registro de riesgos en `design.md` antes de que G5 pueda voltearse. |
| Ensayo de G6 falla cerrado (dry-run de solo subconjunto sale distinto de cero) y bloquea el cutover. | Baja | El invariante fail-closed es el spec — las reversiones de subconjunto rompen el shell SPA. PR 3e se publica solo cuando el ensayo atómico completo sale 0. |
| Medición de G4 excede el presupuesto de delta ≤ 0 % en initial paint o latencia de interacción. | Media | `scripts/g4_measure.sh` registra el delta; si excede 0 %, el worker de apply escribe una solicitud de exención en `design.md` §"Risk register" y la puerta queda bloqueada hasta que un mantenedor la apruebe. |
| Sub-PR 5b (port del módulo research + pin CDN) infla el sub-PR más grande a ~360 LoC; los revisores siguen viendo una unidad de trabajo enfocada. | Baja | El sub-PR 5b es un port cohesivo de `web/{file_explorer,file_viewer,format,keymap}.js`; la organización 5 × 4 del módulo research coincide con el spec canónico modular-architecture. El presupuesto de 400 líneas se mantiene con -40 LoC de holgura. |
| Un PR hijo se corta desde `origin/develop` en lugar de su base de cadena, por lo que su diff muestra rebanadas ajenas ya fusionadas en el tracker. | Media | Tratar un diff contaminado como **bug de base**, no como hallazgo de revisión: reapuntar o rebasear sobre el predecesor inmediato hasta que solo aparezca la unidad de trabajo actual. El paso 7 de §Manifiesto de reconstrucción convierte `git diff --stat <rama-base>` en una compuerta por PR. |
| Flip del `cutover-manifest.json` de la copia de trabajo (Fase 6b.3) edita accidentalmente la copia congelada del predecesor en vez de la copia de trabajo. | Alta | El flip se escribe en `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json` (copia de trabajo); el predecesor `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` queda byte-idéntico. El worker de apply DEBE hacer diff de ambas copias antes de PR 3e. |
| **Regresión de orden de dependencia** (NUEVO de la revisión correctiva del plan): un mantenedor futuro revisa la cadena y reintroduce el orden original (exportación estática del App Router antes del bootstrap de toolchain). | Media | La revisión correctiva del plan registra permanentemente el contrato de dependencia en `tasks.md` §"Dependencia por sub-PR", este `apply-progress.md` §"Dependencia por sub-PR", y `design.md` §"Sub-PR slice under Approach A". Cualquier solicitud de reordenamiento de la cadena debe reabrir el portón de apply para una auditoría de dependencia fresca antes de fusionar. |
| El bootstrap de toolchain (posición 1) aterriza en un host con un `package-lock.json` preexistente de un intento previo de Next 14 / React 18; `npm ci` resuelve contra el lock equivocado. | Media | El sub-PR 3a.2 elimina explícitamente `autoprefixer`, `postcss`, `@tailwindcss/forms` del `package.json` reescrito; `npm ci` regenera un `package-lock.json` limpio contra las deps pineadas. La triangulación de `tests/test_toolchain_bootstrap.py` verifica que no quedan deps legacy perdidas. |

---

## Contrato de congelación del predecesor (vinculante)

Cada sub-PR en las Fases 3a–6c y PR 3e DEBE satisfacer:

- [ ] `git diff --stat origin/develop --
      openspec/changes/migrate-nextjs-tailwind4/`
      muestra cero cambios. <!-- sdd-owner: parent -->
- [ ] `git diff --stat <rama-base-inmediata>` muestra
      **solo** los archivos de esta rebanada (higiene
      de diff de la cadena; un diff contaminado es un
      bug de base — reapuntar o rebasear, no revisar
      alrededor de él). <!-- sdd-owner: parent -->
- [ ] La verificación de protección de rama del PR
      rechaza cualquier PR que modifique
      `openspec/changes/migrate-nextjs-tailwind4/**`.
      <!-- sdd-owner: parent -->
- [ ] El hook de CI / lint del PR rechaza lo mismo.
      <!-- sdd-owner: parent -->

Si un sub-PR edita accidentalmente el directorio del
predecesor, el sub-PR está **bloqueado** y el worker de
apply debe revertir la edición accidental antes de que
el PR pueda fusionarse. No hay ruta `size:exception`
para ediciones del predecesor.

---

## Estado

**El Enfoque A es FINAL** (bloqueado el 2026-09-02;
registrado en §1 de `design.md`). G1 PASS registrado;
G2 PASS registrado contra la build limpia verificada
de Next 16.3.3 / Turbopack; G3 Tier-1 PASS registrado
(los 26 consumidores §3.1 en verde contra el runtime
legacy pre-cut vía el fixture controlado,
`scripts/verify_consumers.py`, PR #109 + #111 + #115 +
#116). G3 Tier-2 (selección atomic-cut) **NO PASADO** —
con compuerta en el cierre de G4 + G5 + G6. G4 (paridad
Playwright + Lighthouse) **bloqueado — verificador no
autordado**; debe cerrar en la fase de apply vía Fase
6c. G5 (baseline de hidratación) **no reproducible —
baseline legacy no en disco**; debe reconstruirse o
reemplazarse durante la fase de apply vía Fase 6a. G6
(ensayo de cutover) **bloqueado — verificador no
autordado**; debe cerrar en la fase de apply vía Fase
6b. El predecesor
`openspec/changes/migrate-nextjs-tailwind4/**` está
**congelado**. Sin activación de FastAPI en esta pasada
de diseño; el cutover atómico PR 3e se publica solo
cuando las seis puertas estén verdes.

**Revisión correctiva del plan aplicada el
2026-09-02**: la topología de cadena de arriba reemplaza
el orden original del `docs/complete-taxa-frontend-migration-plan`
después de que el portón de apply identificara el defecto
de orden de dependencia (el PR 3a no podía requerir
`next build`/`out/index.html` antes de que existieran el
toolchain de Next/React/Tailwind/TypeScript y el contrato
de runtime de Node). La cadena corregida coloca el
bootstrap de toolchain en la posición 1, la exportación
estática del App Router en la posición 2 (ahora
satisfacible), Tailwind/tokens en la posición 3, el
sub-PR Makefile/mount fusionado en la posición 4, y los
sub-PRs restantes en orden de dependencia correcto en
las posiciones 5–13. El conteo de 13 hijos se preserva.

**Revisión correctiva de superficie UI y estructura de
pestañas aplicada el 2026-09-02**: la inspección en vivo
del navegador de `http://127.0.0.1:8765/` reveló una
superficie UI verificada que diverge de la narrativa del
spec por dominio. El diseño/spec/tareas/apply-progress
de alto nivel y los espejos fieles en español se revisaron
para anclar el contrato vinculante (Overview siempre
disponible/visible; Search es una pestaña primaria; Search
online fuerza Search; Browser es Research global). Los
specs por dominio están fuera del alcance de esta
revisión. La topología de cadena de 13 hijos se preservó;
sin cambios de posición de PR, dependencia, o base de
rama. Los pronósticos de PR 5a y PR 5b se movieron a ~310
LoC y ~395 LoC respectivamente (este último con -5 LoC de
holgura ajustada contra el presupuesto de revisión de 400
líneas por PR); el total authored es ahora ~2.265 LoC
(Δ ≤ 20 del pronóstico previo de ~2.245).

> **Footer (flips de la fase de apply)**: G1: PASS
> registrado · G2: PASS registrado · G3 Tier-1: PASS
> registrado · G3 Tier-2: NO PASADO (con compuerta) ·
> G4: bloqueado — verificador no autordado · G5: no
> reproducible — baseline legacy no en disco · G6:
> bloqueado — verificador no autordado. El footer
> voltea a PASS registrado para G4 / G5 / G6 solo
> después de que Fase 6 cierre y PR 3e se publique.

---

## Siguiente paso

La **fase de apply** (`sdd-apply`) lee `tasks.md` y este
`apply-progress.md`, luego ejecuta el manifiesto de
reconstrucción (§Manifiesto de reconstrucción) sub-PR
por sub-PR. El trabajo de validación de Fase 6 (6a,
6b, 6c) corre después de que el camino candidato
(posiciones 1–9) esté verde y antes de PR 3e. El
cutover atómico PR 3e se publica solo cuando las seis
puertas estén verdes. La **fase de verify**
(`sdd-verify`) confirma la lista de paridad (según
`design.md` §"Parity / evidence plan") y la unidad de
reversión (`git revert <pr3e-sha>` restaura la build
vanilla legacy atómicamente). La **fase de archive**
(`sdd-archive`) copia cada spec per-dominio
literalmente en
`openspec/specs/{frontend-runtime,design-tokens,browser-state-hydration,frontend-bootstrap,research}/spec.md`
y promueve el spec modular-architecture al árbol de
specs canónicos.
