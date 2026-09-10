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
>
> **2026-09-02 — re-división del CSS**: la re-auditoría
> **2026-09-02 — re-plan de la sub-secuencia PR 3c (esta
> entrada)**. Después de que los PRs #144 (3a, bootstrap
> de toolchain), #145 (3b, exportación estática del App
> Router) y #146 (reconciliación de 3b) aterrizaran en el
> tracker, el PR 3c único original en la posición 3 fue
> diagnosticado como **insatisfacible**: reclamaba ~230
> LoC mientras que el bloque `<style>` inline legacy en
> `web/index.html` (líneas 14–1972 = **1.963 líneas**)
> debía portarse verbatim a Tailwind 4 (`@theme` para
> tokens, `@layer base` para la cascada, más el barrel
> de design-system). El usuario autorizó una
> sub-secuencia encadenada que reemplaza el PR 3c único
> con **cuatro hijos revisables en las posiciones 3–6**
> (`3c-i` tokens / base / modo oscuro, `3c-ii` estilos de
> árbol / detalle de taxonomía, `3c-iii` estilos de
> Search / Folder / Browser global, `3c-iv` animaciones
> / utilidades + paridad CSS final + barrel de
> design-system), cada uno ≤ 400 líneas authored
> incluyendo tests. Los hijos restantes se **renumeran**
> (`3d → 7`, `4a → 8`, `4b → 9`, `5a → 10`, `5b → 11`,
> `5c → 12`, `6a → 13`, `6b → 14`, `6c → 15`, `3e → 16`)
> para mantener el contrato de dependencia lineal.
> **PR 3c-i se basa en el tracker** (la rama
> `docs/complete-taxa-frontend-migration-plan` **tras**
> el merge de la reconciliación PR #146, recogiendo el
> estado 3a + 3b + reconciliación ya fusionado sin un
> paso extra de reconciliación); cada hijo posterior
> apunta a su rama predecesora inmediata. El total
> authored LoC sube de ~2.245 a ~3.485 porque cada regla
> CSS legacy se porta; el sub-PR más grande nuevo es
> **3c-i a ~390 LoC** (-10 LoC de holgura bajo 400).
> **No se abre ninguna `size:exception` nueva**; la
> excepción del lockfile de PR 3a permanece como la
> única. **El Enfoque A, FastAPI/SQLite, el predecesor
> congelado y la estrategia de Feature Branch Chain
> quedan sin cambios**.

> **2026-09-02 — re-plan de la sub-secuencia PR 3c
> (racional — esta entrada)**. Después de que los PRs
> #144 (3a), #145 (3b) y #146 (reconciliación de 3b)
> aterrizaran en el tracker, el PR 3c único original en
> la posición 3 fue diagnosticado como insatisfacible:
> reclamaba ~230 LoC mientras que el bloque `<style>`
> inline legacy en `web/index.html` (líneas 14–1972 =
> **1.963 líneas**) debía portarse verbatim a Tailwind 4
> (`@theme` para tokens, `@layer base` para la cascada,
> más el barrel de design-system). El usuario autorizó
> una sub-secuencia encadenada que reemplaza el PR 3c
> único con **cuatro hijos revisables en las posiciones
> 3–6** (`3c-i` tokens / base / modo oscuro, `3c-ii`
> estilos de árbol / detalle de taxonomía, `3c-iii`
> estilos de Search / Folder / Browser global, `3c-iv`
> animaciones / utilidades + paridad CSS final + barrel
> de design-system), cada uno ≤ 400 líneas authored
> incluyendo tests. Los hijos restantes se renumeran
> (`3d → 7`, `4a → 8`, `4b → 9`, `5a → 10`, `5b → 11`,
> `5c → 12`, `6a → 13`, `6b → 14`, `6c → 15`, `3e → 16`)
> para mantener el contrato de dependencia lineal.
> **PR 3c-i se basa en el tracker** (la rama
> `docs/complete-taxa-frontend-migration-plan` **tras**
> el merge de la reconciliación PR #146, recogiendo el
> estado 3a + 3b + reconciliación ya fusionado sin un
> paso extra de reconciliación); cada hijo posterior
> apunta a su rama predecesora inmediata. El total
> authored LoC sube de ~2.245 a ~3.485 porque cada regla
> CSS legacy se porta; el sub-PR más grande nuevo es
> **3c-i a ~390 LoC** (-10 LoC de holgura bajo 400).
> **No se abre ninguna `size:exception` nueva**; la
> excepción del lockfile de PR 3a permanece como la
> única. **El Enfoque A, FastAPI/SQLite, el predecesor
> congelado y la estrategia de Feature Branch Chain
> quedan sin cambios**.

| Sub-PR | Alcance | Presupuesto LoC (authored) | Archivos fuente | Estado |
|--------|---------|----------------------------|-----------------|--------|
| PR 3a | **Bootstrap de toolchain** (NUEVA posición 1) | ~210 authored; excepción de lockfile generado aprobada por el usuario | `package.json` + `package-lock.json` regenerado (la excepción queda restringida a cambios de resolución requeridos por este manifiesto, y ambos se revisan juntos; `next@^16` / `react@^19` / `react-dom@^19` / `tailwindcss@^4` / toolchain TS / `engines.node ">=20.9.0"` / `scripts.check-runtime` / `scripts.build:web`; deps legacy de Tailwind 3.4 eliminadas) + `scripts/check-runtime.mjs` (nuevo, Node ≥ 20.9.0) + `tsconfig.json` (modificado en su lugar; el predecesor ya está en la raíz del repo; config base + aliases de ruta `@taxa/<capability>`) + `.nvmrc` (nuevo, pin `20`) + `tests/test_toolchain_bootstrap.py` (nuevo) + `tests/test_check_runtime.py` (nuevo) | **fusionado como PR #144 en el tracker** |
| PR 3b | **Bootstrap autocontenido de exportación estática del App Router** (posición 2; la corrección del defecto de dependencia re-ambia la entrada estilo-3a original del App Router a un bootstrap autocontenido que NO importa `@taxa/app-shell` ni `./globals.css`) | ~175 | `src/app/{layout,page}.tsx` (nuevos, **cuerpo marcador semántico mínimo**; **sin montaje de AppShell, sin import de globals.css**) + `next.config.mjs` (nuevo, `output: "export"` + `images.unoptimized: true` + `trailingSlash: false` + `reactStrictMode: true`) + `tests/test_app_shell_render.py` (nuevo, lee `out/index.html` después de `npx next build`; verifica meta de viewport + preload Raleway + archivo Raleway `.woff2` en `out/_next/static/media/`) | **fusionado como PR #145 en el tracker, con PR #146 de reconciliación también fusionado** |
| PR 3c-i | **Tokens / base / modo oscuro** (NUEVA posición 3; se basa en el tracker tras PR #146) | ~390 (≤ 400; -10 LoC de holgura) | `src/app/globals.css` (nuevo, `@import "tailwindcss"` + bloque `@theme` con cada token legacy `:root` + cascada `[data-theme="dark"]` + familia `--realm-*`) + `@layer base` (resets de body / html / `main > :first-child` + selectores focus-visible globales) + `tests/test_tailwind_4_parity.py` (nuevo, rebanada de tokens `:root`) | pendiente de reconstrucción (primer hijo de la sub-secuencia 3c) |
| PR 3c-ii | **Estilos de árbol / detalle de taxonomía** (NUEVA posición 4; depende de 3c-i) | ~380 (≤ 400; -20 LoC de holgura) | `src/app/globals.css` (extendido, selectores de taxonomía: `.tier-header`, `.tree-row`, `.rank-badge`, `.scientific-name`, `.tree-source-toggle`, `#detail-panel`, `.detail-card`, `.detail-section`, `.overview-section`, `.detail-item`, `.search-pulse`, `.detail-tabs`, `.search-icon-btn`, `.materialize-btn`, kebab, modal de materialize, variantes `.tree-row[data-realm="…"]` tintadas por reino) + `tests/test_tailwind_4_parity.py` (rebanada de selectores de taxonomía) | pendiente de reconstrucción |
| PR 3c-iii | **Estilos de Search / Folder / Browser global** (NUEVA posición 5; depende de 3c-ii) | ~390 (≤ 400; -10 LoC de holgura) | `src/app/globals.css` (extendido, selectores de browser / search / folder: `.toast`, `.search-engines-grid`, `.search-category-header`, `.search-engine-btn`, `.fex-meta-strip`, `.fex-tab-strip`, `.fex-snippet-frame`, `.fex-shell`, `.fex-tree-pane`, `.fex-viewer-pane`, `.fex-splitter`, `.fex-row`, `.fex-tree-header`, `.fex-children`, `.fex-banner`, `.fex-empty-state`, `.fex-search-*`, `.fex-csv-*`, `.fex-json-*`, `.fex-tree-truncated`) + `tests/test_tailwind_4_parity.py` (rebanada de selectores de browser) | pendiente de reconstrucción |
| PR 3c-iv | **Animaciones / utilidades + paridad CSS final + barrel de design-system** (NUEVA posición 6; depende de 3c-iii) | ~280 (≤ 400; -120 LoC de holgura) | `src/app/globals.css` (extendido, reglas `@keyframes`, `.animate-spin`, marcos del visor de imagen / vídeo, selectores de la vista Settings) + `src/modules/design-system/{infrastructure/index.ts,presentation/Icon.tsx,presentation/Button.tsx}` (nuevos) + `tests/test_tailwind_4_parity.py` (enumeración de `@keyframes` + clases de utilidad) + `tests/test_design_system_purity.py` (nuevo) | pendiente de reconstrucción |
| PR 3d | **Makefile/mount** (NUEVA posición 7; fusiona 3c + 3d originales; depende de `next build` de 3b + tokens de Tailwind 4 + `@layer base` + `@layer components` de 3c-iv) | ~240 | `Makefile` (modificado, target `api:` ejecuta `check-runtime.mjs` → `npm ci` → `npm run build:web` → `uvicorn … --port 8765`; `make css` se vuelve shim no-op) + `api/server.py` (modificado, delta de 1 línea en línea 54, `WEB_DIR = Path(__file__).parent.parent / "out"`) + `src/data/search-engines.js` (nuevo, copia byte a byte de `web/search_urls.js` con export nombrado `SEARCH_ENGINES`) + `tests/test_smoke.py` (modificado, actualización de ruta `open()`) + `tests/test_static_mount.py` (nuevo) + `tests/test_make_api_build.py` (nuevo) | pendiente de reconstrucción |
| PR 4a | Typed store + 4 lecturas + 4 escrituras (sin cambios) | ~180 | `src/modules/browser-state/{domain/keys.ts,infrastructure/store.ts,index.ts}` (nuevos) + `tests/test_browser_state_keys.py` (nuevo) | pendiente de reconstrucción |
| PR 4b | Guardia de hidratación + integración de AppShell + cero warnings Playwright (la corrección del defecto de dependencia mueve la integración de `<AppShell>` en `src/app/{layout,page}.tsx` a este sub-PR) | ~90 | `src/modules/app-shell/{presentation/AppShell.tsx,infrastructure/page-chrome.tsx}` (nuevos) + `src/app/{layout,page}.tsx` (modificados, integra `<AppShell>` desde `@taxa/app-shell` en el host del App Router; la corrección del defecto de dependencia) + `tests/test_hydration_console.py` (nuevo, Playwright) | pendiente de reconstrucción |
| PR 5a | Port del módulo taxonomy (extendido; absorbe el strip de pestañas de DetailPanel + OverviewTab + Kebab Search-online fuerza) | ~280 | `src/modules/taxonomy/{domain/taxon.ts,infrastructure/api.ts,application/useTaxonTree.ts,presentation/{Tree,DetailPanel,Breadcrumb}.tsx}` (nuevo + extensión; `DetailPanel` envía el strip de tres pestañas `Overview` / `Search` / `Folder` según la superficie UI verificada, con `Overview` siempre disponible/visible; la capa de presentation de taxonomía se monta sobre los selectores de `@layer components` de PR 3c-ii) + `tests/test_taxonomy_infra.py` (nuevo; incluye el testigo de regresión Playwright `Search online` → pestaña `Search`) | pendiente de reconstrucción |
| PR 5b | Port del módulo research + pin CDN (extendido; absorbe SearchTab + FolderTab + SearchLinkList + re-anclaje de la pestaña `Browser` del header como Research global) | ~360 | `src/modules/research/{domain/{research-file,engine,file-node}.ts,infrastructure/{api,search-engines}.{ts,js},application/{useFileExplorer,useFileViewer}.ts,presentation/{FileExplorer,FileViewer,RawTableTreeTabs,MetaStrip,BreadcrumbPanel,Banners}.tsx}` (nuevo; `SearchTab` renderiza las cinco secciones de categoría `General` / `Taxonomic` / `Academic` / `Multimedia` / `Documents` en orden fijo; `FolderTab` es un cuerpo separado; `SearchLinkList` mapea cada `Engine` a un anchor con `target="_blank"` + `rel="noopener noreferrer"`; la capa de presentation de research se monta sobre los selectores de `@layer components` de PR 3c-iii) + `src/modules/app-shell/infrastructure/page-chrome.tsx` (modificado; pestaña `Browser` del header re-anclada como Research global / file explorer, NO scoped por taxón) + `tests/test_research_infra.py` (nuevo; incluye la triangulación de la lista categorizada de enlaces salientes y el testigo de Browser-global) | pendiente de reconstrucción |
| PR 5c | Selectores E2E + contrato `data-*` + borrar legacy (extendido; depende de PR 5b + PR 3c-iv; el borrado del `web/index.html` legacy retira el CSS inline legacy de 1.963 líneas que los cuatro hijos de la sub-secuencia PR 3c migraron a `src/app/globals.css`) | ~200 | `tests/test_e2e_file_explorer.py` (modificado, actualización de selectores DOM) + `tests/test_web_toggle.py` (modificado, actualización de toggle de tema) + `tests/test_evidence_baseline.py` (modificado, aserción de roster legacy voltea a "ausente") + borrado de `web/{index.html,index.css}` + borrado de `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,help,keymap,settings,search,file_explorer,file_viewer,format,search_urls}.js` (18 archivos) + borrado de `tailwind.config.js` + `web/dist/tailwind.css` ya no se rastrea | pendiente de reconstrucción |
| Fase 6a | Cierre de baseline de hidratación G5 (sin cambios) | ~50 (mayormente medición) | `scripts/reconstruct_hydration_baseline.py` (nuevo) + `scripts/g5_close.sh` (nuevo) + `web/dist/evidence-baseline.json` (regenerado, esquema fijado por `tests/test_hydration_timing.py`) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| Fase 6b | Ensayo de cutover G6 (sin cambios) | ~120 | `scripts/rehearse_cutover.py` (nuevo) + `tests/test_rehearse_cutover.py` (nuevo) + `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json` (copia de trabajo; la copia del predecesor queda byte-idéntica congelada) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| Fase 6c | Paridad G4 Playwright + Lighthouse (sin cambios) | ~20 (mayormente medición) | `scripts/g4_measure.sh` (nuevo) + `out/g4-parity-report.json` (artefacto Playwright + Lighthouse) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| Fase 6c slice 6c.0 (aterrizado, no-cierre) | Sub-slice de paridad de navegación G4 | ~400 (productor) + ~200 (tests) + ~15 (Makefile) | `tools/g4-capture/scripts/parity_navigation.mjs` (nuevo; driver Playwright; `playwright@1.49.1` pinned aislado) + `tools/g4-capture/package.json` (delta de 1 línea; `playwright@1.49.1`) + `tools/g4-capture/package-lock.json` (regenerado vía `npm install --package-lock-only`) + `tests/test_capture_parity.py` (25 nuevos tests herméticos) + `Makefile` (target `parity-navigation`) + `tools/g4-capture/README.md` (contrato del slice 3 documentado como no-cierre) + delta de `apply-progress.md` §Registro de cambios | aterrizado (solo navegación; G4 permanece bloqueado; sin flip G3 Tier-2 / cutover status) |
| PR 5c.2-B.1b-i (aterrizado, no-cierre) | CLI de captura + runner Chromium para exportación React | ~250 authored (run.mjs + chromium-driver.mjs + README + package.json +3) + ~30 docs OpenSpec (EN+ES) | `tools/react-e2e-harness/scripts/run.mjs` (nuevo; CLI; `--origin` + `--output-root` obligatorios; validación de origen fail-closed; `evidence.json` atómico con timestamp solo tras éxito; inyección dinámica de `runFn`) + `tools/react-e2e-harness/scripts/chromium-driver.mjs` (nuevo; navegación Chromium sin cabeza; import dinámico de `playwright`; aserciones de contrato de datos React; traza concisa; cierre fiable del navegador) + `tools/react-e2e-harness/package.json` (+3 líneas; `scripts.capture = "node scripts/run.mjs"`) + `tools/react-e2e-harness/README.md` (uso conciso del origen provisto por el caller + lista fail-closed + lista de diferimientos) + 6 archivos de doc OpenSpec (§Registro de cambios / §Addenda entradas; diferimiento estrechándose) | aterrizado (solo CLI + runner de captura; G4 permanece bloqueado; sin flip G3 Tier-2 / cutover status; sin servidor fixture de API, sin servidor HTTP de exportación, sin target de Makefile, sin tests herméticos del driver, sin borrado legacy, sin agregación G4) |
| PR 5c.2-B.1b-ii-c (aterrizado, no-cierre) | Orquestador de composición E2E React + driver CLI + target de Makefile + `capture:composed` package-script + rebanada de tests de composición hermética | ~25 authored delta sobre `composed-capture.mjs` (impl parcial preservado; `LOOPBACK_HOSTS` + `validateTaxonId`/`validateHost` endurecidos + `startFixtureFn`/`startExportFn` inyectados) + ~289 authored sobre `tests/test_5c_2_b_react_harness.py` (bloque de composición, 11 casos herméticos) + ~3 cada uno en `tasks.md` / `tasks-es.md` (flip de entrada) + ~6 archivos de doc OpenSpec (este addenda + espejo) | `tools/react-e2e-harness/scripts/composed-capture.mjs` (impl parcial + endurecimiento de validación + `startFixtureFn`/`startExportFn` inyectados) + `Makefile` (target `capture-react-e2e` existente; requiere `OUTPUT_ROOT`) + `tools/react-e2e-harness/package.json` (`scripts.capture:composed` existente) + `tests/test_5c_2_b_react_harness.py` (bloque de composición) + 6 archivos de doc OpenSpec | aterrizado (solo composición + CLI + target de Makefile + package-script + rebanada de tests hermética; G4 permanece bloqueado; sin flip G3 Tier-2 / cutover status; sin ejecución real de Chromium; sin modernización de selectores e2e; sin borrado legacy `web/*`; sin agregación G4) |
| PR 3e | Cutover atómico (sin cambios) | ~120 (mayormente delta de `apply-progress.md`) | `apply-progress.md` (flip de footer de estado de puertas + entrada de registro de cambios) + re-corridas de `tests/test_verify_consumers.py`, `tests/test_verify_build.py`, `make api`, `make smoke` | pendiente de reconstrucción (con compuerta en las seis puertas verdes) |

**Conteo de sub-PRs**: **16** (1 bootstrap de toolchain +
1 exportación estática del App Router + **4 hijos de la
sub-secuencia PR 3c (3c-i / 3c-ii / 3c-iii / 3c-iv)** +
1 Makefile/mount + 2 browser-state + 2 puertos de
capability + 1 e2e + borrar legacy + 3 validación de
Fase 6 + 1 cutover atómico).

**Total authored**: ~3.485 LoC a través de los 16
sub-PRs (Δ ~+1.240 LoC del pronóstico previo de ~2.245;
el re-plan de la sub-secuencia PR 3c particiona la
migración del CSS inline legacy de 1.963 líneas en 4
hijos totalizando ~1.500 líneas authored
(reemplazando los ~230 LoC del PR 3c único previo) y
añade el test de paridad consolidado;
la corrección del defecto de dependencia
redistribuye ~30 LoC entre PR 3b (-25), PR 3c-i (+2) y
PR 4b (+30) sin cambiar la topología de la cadena). El
sub-PR más grande es **3c-i a ~390 LoC** (-10 LoC de
holgura bajo el presupuesto de revisión de 400 líneas
por PR); el previamente-más-grande 5b queda segundo a
~395 LoC (-5 LoC de holgura). PR 3d queda a ~240 LoC
(-160 LoC / -40 % de holgura contra el presupuesto de
400 líneas). La única `size:exception` está aprobada
por el usuario para el `package-lock.json` regenerado
de PR 3a; su trabajo authored permanece ≤400 y se
rechaza churn de lockfile no relacionado. **No se abre
ninguna `size:exception` nueva** para la sub-secuencia
PR 3c. El borrado
del `web/index.html` en PR 5c retira el CSS inline
legacy de 1.963 líneas que los cuatro hijos de la
sub-secuencia PR 3c migraron a `src/app/globals.css`.

### Orden de reconstrucción (determinístico, secuencial a lo largo de la cadena)

```
3a (bootstrap de toolchain; PR #144) →
3b (exportación estática del App Router; PR #145 + reconciliación PR #146) →
3c-i (tokens / base / modo oscuro; se basa en el tracker) →
3c-ii (estilos de árbol / detalle de taxonomía) →
3c-iii (estilos de Search / Folder / Browser global) →
3c-iv (animaciones / utilidades + paridad CSS final + barrel de design-system) →
3d (Makefile/mount) →
4a → 4b → 5a → 5b → 5c →
6a (G5) → 6b (G6) → 6c (medición G4) →
3e (cutover atómico, con compuerta)
```

**Estrategia de cadena: `feature-branch-chain`** (elegida
por el usuario). La rama existente
`docs/complete-taxa-frontend-migration-plan` (referida
como **PR #146**) es el **tracker**: draft / no-merge,
y el **único** PR que apunta a `develop`. El PR hijo 3a
apunta al tracker; PR 3b apunta a PR 3a; **PR 3c-i
apunta al tracker** (la rama
`docs/complete-taxa-frontend-migration-plan` **tras**
el merge de la reconciliación PR #146, recogiendo el
estado 3a + 3b + reconciliación ya fusionado sin un
paso extra de reconciliación); cada hijo posterior
apunta a su **rama predecesora inmediata**. Esto
sustituye, para este cambio, el
default de `AGENTS.md` §4 de apuntar directo a
`develop`.

| Posición | Sub-PR | Rama | Base (destino del PR) |
|---|---|---|---|
| Tracker | — | `docs/complete-taxa-frontend-migration-plan` (PR #146) | `develop` — **draft / no-merge** |
| 1 / 22 | 3a | `feat/complete-taxa-frontend-migration-01-3a` | `docs/complete-taxa-frontend-migration-plan` (tracker) |
| 2 / 22 | 3b | `feat/complete-taxa-frontend-migration-02-3b` | `feat/complete-taxa-frontend-migration-01-3a` |
| 3 / 22 | 3c-i | `feat/complete-taxa-frontend-migration-03-3c-i` | `docs/complete-taxa-frontend-migration-plan` (tracker, **tras el merge de la reconciliación PR #146**) |
| 4 / 22 | 3c-ii | `feat/complete-taxa-frontend-migration-04-3c-ii` | `feat/complete-taxa-frontend-migration-03-3c-i` |
| 5 / 22 | 3c-iii | `feat/complete-taxa-frontend-migration-05-3c-iii` | `feat/complete-taxa-frontend-migration-04-3c-ii` |
| 5.5 / 22 | 5.5 (aterrizado) | `feat/complete-taxa-frontend-migration-05-5-3c-iv-predecessor` | `feat/complete-taxa-frontend-migration-05-3c-iii` |
| 5.6 / 22 | 5.6 (aterrizado) | `feat/complete-taxa-frontend-migration-05-6-3c-iv-predecessor` | `feat/complete-taxa-frontend-migration-05-5-3c-iv-predecessor` |
| 6 / 22 | 3c-iv-barrel | `feat/complete-taxa-frontend-migration-06-3c-iv-barrel` | `feat/complete-taxa-frontend-migration-05-6-3c-iv-predecessor` (commit base post-PR-5.6; según el replan five-slice de 3c-iv) |
| 7 / 22 | 3c-iv-keyframes | `feat/complete-taxa-frontend-migration-07-3c-iv-keyframes` | `feat/complete-taxa-frontend-migration-06-3c-iv-barrel` |
| 8 / 22 | 3c-iv-viewer | `feat/complete-taxa-frontend-migration-08-3c-iv-viewer` | `feat/complete-taxa-frontend-migration-07-3c-iv-keyframes` |
| 9 / 22 | 3c-iv-settings | `feat/complete-taxa-frontend-migration-09-3c-iv-settings` | `feat/complete-taxa-frontend-migration-08-3c-iv-viewer` |
| 10 / 22 | 3c-iv-colors | `feat/complete-taxa-frontend-migration-10-3c-iv-colors` | `feat/complete-taxa-frontend-migration-09-3c-iv-settings` |
| 11 / 22 | 3d | `feat/complete-taxa-frontend-migration-11-3d` | `feat/complete-taxa-frontend-migration-10-3c-iv-colors` (los consumidores CSS finales dependen de colors, según el replan five-slice de 3c-iv) |
| 12 / 22 | 4a | `feat/complete-taxa-frontend-migration-12-4a` | `feat/complete-taxa-frontend-migration-06-3c-iv-barrel` (los consumidores de design-system dependen de barrel, según el replan five-slice de 3c-iv) |
| 13 / 22 | 4b | `feat/complete-taxa-frontend-migration-13-4b` | `feat/complete-taxa-frontend-migration-12-4a` |
| 14 / 22 | 5a | `feat/complete-taxa-frontend-migration-14-5a` | `feat/complete-taxa-frontend-migration-13-4b` |
| 15 / 22 | 5b | `feat/complete-taxa-frontend-migration-15-5b` | `feat/complete-taxa-frontend-migration-14-5a` |
| 16 / 22 | 5c | `feat/complete-taxa-frontend-migration-16-5c` | `feat/complete-taxa-frontend-migration-10-3c-iv-colors` (los consumidores CSS finales dependen de colors; según el replan five-slice de 3c-iv) |
| 17 / 22 | 6a | `feat/complete-taxa-frontend-migration-17-6a` | `feat/complete-taxa-frontend-migration-16-5c` |
| 18 / 22 | 6b | `feat/complete-taxa-frontend-migration-18-6b` | `feat/complete-taxa-frontend-migration-17-6a` |
| 19 / 22 | 6c | `feat/complete-taxa-frontend-migration-19-6c` | `feat/complete-taxa-frontend-migration-18-6b` |
| 20 / 22 | 3e | `feat/complete-taxa-frontend-migration-20-3e` | `feat/complete-taxa-frontend-migration-19-6c` |

Los hijos se fusionan **en orden** dentro del tracker; a
medida que cada hijo se fusiona, el siguiente se
reapunta al tracker (GitHub reapunta automáticamente
cuando la rama base se fusiona y se borra). El tracker
acumula la feature completa y se fusiona a `develop`
solo después de que PR 3e — el último hijo — aterrice.

**Dependencia por sub-PR (contrato de la revisión
correctiva del plan + replan de la sub-secuencia del PR 3c +
replan five-slice de 3c-iv)**:

| Posición | Depende de | Satisface (testigo) |
|---|---|---|
| 1 / 3a (bootstrap de toolchain) | — | `npm ci` exit 0; `node scripts/check-runtime.mjs` exit 0 en Node ≥ 20.9.0; `npx tsc --noEmit` resuelve todos los aliases `@taxa/*` |
| 2 / 3b (exportación estática del App Router) | 1 | `npx next build` exit 0; `out/index.html` no vacío con meta de viewport + preload de Raleway |
| 3 / 3c-i (tokens / base / modo oscuro) | tracker tras PR #146 (= 1 + 2 + reconciliación) | `src/app/globals.css::@theme` declara cada token legacy `:root`; presente la cascada `[data-theme="dark"]`; presente la familia `--realm-*`; el test de paridad enumera cada token legacy `:root` y referencia `var(--name)`; `out/_next/static/chunks/*.css` carga las declaraciones esperadas. **Se basa en el tracker** (no en `feat/complete-taxa-frontend-migration-02-3b-reconcile`) para que la sub-secuencia 3c recoja el estado 3a + 3b + reconciliación ya fusionado sin un paso extra de reconciliación. |
| 4 / 3c-ii (estilos de árbol / detalle de taxonomía) | 3 | `src/app/globals.css` carga cada selector legacy de taxonomía (`.tier-header`, `.tree-row`, `.rank-badge`, `.scientific-name`, `.tree-source-toggle`, `#detail-panel`, `.detail-card`, `.detail-section`, `.overview-section`, `.detail-item`, `.search-pulse`, `.detail-tabs`, `.search-icon-btn`, `.materialize-btn`, kebab, modal de materialize, variantes `.tree-row[data-realm="…"]` tintadas por reino); el test de paridad enumera cada uno. |
| 5 / 3c-iii (estilos de Search / Folder / Browser global) | 4 | `src/app/globals.css` carga cada selector legacy de browser / search / folder (`.toast`, `.search-engines-grid`, `.search-category-header`, `.search-engine-btn`, `.fex-meta-strip`, `.fex-tab-strip`, `.fex-snippet-frame`, `.fex-shell`, `.fex-tree-pane`, `.fex-viewer-pane`, `.fex-splitter`, `.fex-row`, `.fex-tree-header`, `.fex-children`, `.fex-banner`, `.fex-empty-state`, `.fex-search-*`, `.fex-csv-*`, `.fex-json-*`, `.fex-tree-truncated`); el test de paridad enumera cada uno. |
| 5.5 / 5.5 (reparación de pipeline Tailwind 4 / PostCSS, aterrizada) | 5 | `npx next build` exit 0; el bundle CSS compilado contiene el preflight de Tailwind 4 + la expansión `@layer theme { :root, :host { … } }`; `@tailwindcss/postcss` es el plugin PostCSS registrado; los literales `@theme {` / `@import "tailwindcss"` están ausentes del bundle CSS compilado. **Aterrizada; G2-PASS-pendiente-de-captura-Fase-6.** |
| 5.6 / 5.6 (reparación de paridad estructural DOM↔CSS, aterrizada) | 5.5 + PR 5a + PR 5b | el bundle CSS compilado contiene los 15 ganchos estructurales emitidos por React + los 9 selectores de estado + las 2 reglas colapsadas de descendientes + el puente de selector kebab + las 5 declaraciones de triangulación visible-state / chainable / scrollable. **Aterrizada; G2-PASS-pendiente-de-captura-Fase-6.** |
| 6 / 3c-iv-barrel (barrel de design-system + Icon/Button + purity test, NUEVO primer hijo de la sub-secuencia 3c-iv) | commit base post-PR-5.6 | el barrel `src/modules/design-system/infrastructure/index.ts` exporta los tokens de tema tipados + las primitivas `<Icon>` + `<Button>`; `src/modules/design-system/presentation/{Icon.tsx,Button.tsx}` envían el envoltorio de glyphs Material Symbols Outlined + la primitiva de layout Button; `tests/test_design_system_purity.py` afirma que cada literal hex vive dentro de `src/modules/design-system/` (sin fuga a otros módulos). |
| 7 / 3c-iv-keyframes (cinco `@keyframes` legacy + paridad de `.animate-spin`) | 6 | `src/app/globals.css` carga cada regla `@keyframes` legacy (`detail-card-enter`, `detail-card-leave`, `search-pulse-anim`, `materialize-spin`, `toast-slide-in`) + `.animate-spin`; el test de paridad enumera cada uno. |
| 8 / 3c-iv-viewer (paridad CSS del visor de imagen / vídeo) | 7 | `src/app/globals.css` carga cada selector de marco del visor (`.fex-image-frame`, `.fex-image`, `.fex-image-advisory`, `.fex-video-frame`, `.fex-video-el`); el test de paridad enumera cada uno. |
| 9 / 3c-iv-settings (paridad CSS de la vista Settings) | 8 | `src/app/globals.css` carga cada selector de Settings (`.settings-shell`, `.settings-header`, `.settings-list`, `.settings-row`, `.settings-row-text`, `.settings-row-title`, `.settings-row-description`, `.settings-row-control`, `.settings-theme-toggle`, `.settings-theme-btn`, `.settings-theme-btn-active`, `.settings-action-btn`, `.settings-link-btn`); el test de paridad enumera cada uno. |
| 10 / 3c-iv-colors (aliases del namespace `--color-*` de Tailwind + paridad de utility, hijo terminal de la sub-secuencia 3c-iv) | 9 | el bloque `@theme` de `src/app/globals.css` carga cada alias del namespace `--color-*` de Tailwind; el contrato de paridad de clases de utilidad legacy (`bg-primary`, `text-on-surface`, `border-outline-variant`, `bg-surface-container-lowest`, `bg-primary-fixed`, `text-on-primary-fixed`, etc.) resuelve a declaraciones CSS no vacías en `out/_next/static/chunks/*.css`; el test de paridad enumera cada uno. |
| 11 / 3d (Makefile/mount) | 10 + 2 (los consumidores CSS finales dependen de colors, según el replan five-slice de 3c-iv) | `make api` exit 0; uvicorn vincula solo `127.0.0.1:8765`; `curl /index.html` devuelve `out/index.html`; contrato AC-21 preservado |
| 12 / 4a (typed store) | 6 (los consumidores de design-system dependen de barrel, según el replan five-slice de 3c-iv) | 4 sitios de lectura + 4 de escritura en `src/modules/browser-state/`; ningún otro módulo toca `localStorage` |
| 13 / 4b (guardia de hidratación) | 12 + 2 | Playwright cero warnings de hidratación; `AppShell` usa flag `mounted` reservado en `src/app/page.tsx` |
| 14 / 5a (port de taxonomy) | 13 | View-models de taxonomía renderizan; toggle de tree-source rehidrata vía `localStorage` |
| 15 / 5b (port de research + pin CDN) | 14 + 11 | Archivos de research renderizan vía despachador de 9 formatos; URLs CDN pineadas |
| 16 / 5c (e2e + borrar legacy) | 15 + 10 (los consumidores CSS finales dependen de colors, según el replan five-slice de 3c-iv) | Selectores e2e actualizados; contrato `data-*` preservado; `web/*` legacy borrado |
| 17–19 / 6a, 6b, 6c (validación) | 16 | G5 reproducible; G6 PASS; G4 PASS; `apply-progress.md` §Registro de cambios flipa para cada uno |
| 20 / 3e (cutover atómico) | 17, 18, 19 + G1/G2/G3 Tier-1 trasladado | Las seis puertas verdes; flip de cutover-manifest Tier-2; uvicorn sirve `out/index.html` desde la build de producción |

**La Fase 6 (6a, 6b, 6c) es trabajo de validación**, no
un objetivo de migración. Corre **después** de que el
camino candidato completo (posiciones 1–16) esté verde y
acumulado en el tracker, y **antes** de que PR 3e pueda
aterrizar. La Fase 6 puede entregarse como tres eslabones
de la cadena (el default: posiciones 17 / 18 / 19 de la
topología de 22 hijos) o colapsar en un único PR hijo en
la posición 17, según la decisión `ask-on-risk` del
mantenedor; colapsarla acorta la cadena sin cambiar la
topología (el batch sigue apuntando a la rama del PR 5c,
y PR 3e sigue apuntando al último eslabón de la Fase 6).
Los LoC combinados son ~190 authored + ~120 artefacto de
medición, cómodamente bajo el presupuesto de 400 líneas.

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

    ### 2026-09-08 — PR 5c.2-B.1b-i: CLI de captura + runner Chromium para exportación React aterrizados (workspace aislado `tools/react-e2e-harness/`; servidor fixture + servidor de exportación + tests herméticos + modernización de selectores + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos)

        - **Alcance (esta entrada)**. PR 5c.2-B.1b-i aterriza la **CLI de captura + runner Chromium** en el workspace aislado `tools/react-e2e-harness/` solo (sin superficie de edición en `src/`, sin cambios de API/FastAPI/SQLite/extension, sin cambios en `domain/keys.ts` / `infrastructure/store.ts`, sin cambio en `next.config.mjs` / `package.json` de producción, sin captura G4, sin borrado legacy). Archivos: `tools/react-e2e-harness/scripts/run.mjs` (CLI; requiere `--origin` + `--output-root`; rechaza `file://` / no-http(s) / rutas en el origen / flags faltantes / colisiones de salida; inyecta dinámicamente el `runFn` desde `./chromium-driver.mjs`; escribe `evidence.json` atómico con timestamp solo tras una captura exitosa — fail-closed; sin puerto por defecto hard-coded) + `tools/react-e2e-harness/scripts/chromium-driver.mjs` (navegación Chromium sin cabeza; importa dinámicamente `playwright` desde el `node_modules/` local; valida los contratos de datos de React `data-harness-root` + `data-harness-surface` + `data-harness-taxon-id` no nulo + `[data-explorer="ready"]` + ambos slots `[data-pane]` + `input[data-search-input]` + ≥1 `[data-file-path]`; captura trazas concisas `pageerror` / `console.error` / navegación / aserciones; cierra el navegador de forma fiable vía `finally`) + `tools/react-e2e-harness/package.json` (+3 líneas: `scripts.capture = "node scripts/run.mjs"` junto a `build` / `start` / `lint`; private + ESM sin cambios; `engines.node >=20.9.0` sin cambios) + `tools/react-e2e-harness/README.md` (nuevo; uso conciso del origen provisto por el caller; lista fail-closed; lista de diferimientos).
          - **TDD estricto**: sin superficie de test en esta sub-rebanada. **RED** = verificación de contrato de fuente pre-implementación (`scripts/run.mjs` + `scripts/chromium-driver.mjs` + directorio `scripts/` ausentes) PASÓ sobre la fuente previa a `5c.2-B.1b-i`. **GREEN** = `node --check` sobre ambos módulos exit `0` + rechazo CLI de `missing --origin` / `missing --output-root` / `file://` / ruta en origen cada uno exit `1` con una línea de error clara. Inyección de `runFn` + `now()` ejercita el camino feliz de escritura atómica Y el camino de fallo del runner inyectado (sin evidencia publicada en el fallo). **Sin éxito de runtime de navegador reclamado** (servidor fixture de API + servidor HTTP de exportación diferidos).
          - **Diferimientos (vinculantes)**: servidor fixture de API, orquestación del servidor HTTP de exportación, target de Makefile, tests herméticos del driver, modernización de selectores e2e sobre el nuevo árbol de componentes, borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`. Sin cambio de `src/` de producción; sin cambio en `domain/keys.ts` / `infrastructure/store.ts`; sin agregación G4; sin cambio de FastAPI/SQLite/extension.
          - **Estado de G4 / G3 Tier-2 / cutover (sin cambios)**: G4 paridad Playwright + Lighthouse permanece **bloqueada** (solo uno de cinco sub-slices entregado; sin flip end-to-end de `scripts/verify_parity.py`); G3 Tier-2 permanece con compuerta en G4 + G6; G6 permanece bloqueada; PR 3e se publica solo cuando G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6 estén todos verdes. **El aterrizaje de la CLI de captura NO voltea G4** — solo se envió la CLI + runner Chromium.
        - **Alcance de este intento (vinculante)**: 4 archivos del arnés (`scripts/run.mjs`, `scripts/chromium-driver.mjs`, `package.json`, `README.md`) + 6 archivos de doc OpenSpec (`tasks.md`, `design.md`, `apply-progress.md` + espejos en español). Sin commit/push; sin servidor fixture; sin target de Makefile; sin rebanada de test hermético; sin borrado legacy `web/*`; sin cambio en `tools/g4-capture/**`; sin cambio de FastAPI/SQLite/extension.

    ### 2026-09-09 — PR 5c.2-B.1b-ii-a: API fixture React FileExplorer hermética aterrizada (workspace aislado `tools/react-e2e-harness/`; servidor HTTP de exportación estático + rebanada de composición + tests herméticos del driver + modernización de selectores + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos)

    - `tools/react-e2e-harness/scripts/fixture-server.mjs` (nuevo; ~209 LoC; Node puro built-ins `node:http` + `node:buffer`; cero deps npm; cero delta en `package.json` del arnés; CLI `--port N` / `--host H` OR `--port 0` asignado por el OS; nunca hard-coded 8765; refleja la forma FastAPI de producción `GET /api/taxon/1/files` devolviendo el `FilesEnvelope` tipado + `GET /api/taxon/1/files/serve?path=<encoded>` devolviendo el cuerpo del archivo + `Content-Type` correspondiente + `Content-Disposition: inline; filename="<basename>"`; corpus fixture determinista en memoria `index.html` / `notes.md` / `readme.txt` / `paper.pdf` + `Papers/lynx.pdf` recursivo; `safeResolve()` refleja `api/server.py::_safe_resolve()` paso a paso: rechaza vacío / NUL / percent malformado / absoluto / `..` / `.` + join explícito de segmentos + verificación de padre estricto; solo el id de taxon `1` servido; rutas desconocidas / taxon desconocido / método incorrecto / traversal codificado URL rechazados fail-closed 400 / 404 / 405; importable vía `startServer({port, host}) → {schema, taxonId, host, port, baseUrl, server, close}`).
    - `tests/test_5c_2_b_react_harness.py` (nuevo; ~230 LoC; 27 tests pytest de fixture (incluyendo expansiones parametrizadas); `subprocess` Node + Python `urllib`; sin Playwright / Chromium / FastAPI / SQLite / red; contrato de fuente RED-gate, ciclo de vida start/stop, forma del envelope, tipos de contenido de cuatro formatos + magic `%PDF-`, fail-closed traversal parametrizado sobre `..` / `../../etc/passwd` / `%2Fetc%2Fpasswd` / `%2E%2E%2Fpasswd`, archivo desconocido 404, taxon desconocido 404, ruta desconocida 404, no-GET 405).
    - **TDD estricto**: **RED** = verificación de contrato de fuente pre-implementación (`fixture-server.mjs` ausente) FALLÓ sobre la fuente previa a `5c.2-B.1b-ii-a`. **GREEN** = `node --check` exit `0` + los 27 tests pytest de fixture pasan (incluyendo expansiones parametrizadas); sonda de ciclo de vida confirma puerto elegido por el caller honrado, puertos OS-asignados únicos, `SIGTERM` libera el listener; aserciones de envelope confirman cada campo de `FilesEnvelope`, orden carpetas antes de archivos, las cuatro extensiones del fixture (HTML / Markdown / texto / PDF), subfolder recursivo `Papers/`; aserciones de tipo de contenido confirman `text/html` / `text/markdown` / `text/plain` / `application/pdf` + `Content-Disposition: inline; filename="…"` + magic `%PDF-`; aserciones fail-closed confirman traversal / absoluto / traversal codificado URL / path-faltante todos 400 con detalle claro, taxon desconocido 404, ruta desconocida 404, no-GET 405. Sin cambios de fuente/API de producción; sin cambios en `domain/keys.ts` / `infrastructure/store.ts`; sin borrado legacy `web/*.{html,js,css}`; sin agregación G4.
    - **Diferimientos (vinculantes)**: orquestación del servidor HTTP de exportación estático + rebanada de composición (5c.2-B.1b-ii-b), target `make capture-react-e2e`, tests herméticos del driver de captura (chromium-driver.mjs envuelto por fixtures Python), modernización de selectores e2e sobre el nuevo árbol de componentes, borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`. Sin commit/push; sin target de Makefile; sin borrado legacy `web/*`; sin cambio en `tools/g4-capture/**`; sin cambio de FastAPI/SQLite/extension.
    - **Estado de G4 / G3 Tier-2 / cutover (sin cambios)**: G4 paridad Playwright + Lighthouse permanece **bloqueada** (solo dos de cinco sub-slices enviados; sin flip end-to-end de `scripts/verify_parity.py`); G3 Tier-2 permanece con compuerta en el cierre de G4 + G6; G6 permanece bloqueada; PR 3e se publica solo cuando G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6 estén todos verdes. **El aterrizaje del fixture API NO voltea G4** — solo se envió el fixture API + la rebanada de test hermética; sin agregación G4; sin artefacto de build de producción; sin éxito de runtime de navegador.
    - **Alcance de este intento (vinculante)**: 1 archivo del arnés (`scripts/fixture-server.mjs`) + 1 archivo de test (`tests/test_5c_2_b_react_harness.py`) + 6 archivos de doc OpenSpec (`tasks.md`, `design.md`, `apply-progress.md` + espejos en español). Sin commit/push; sin servidor de exportación estático; sin target de Makefile; sin rebanada de composición; sin tests herméticos del driver de captura; sin borrado legacy `web/*`; sin cambio en `tools/g4-capture/**`; sin cambio de FastAPI/SQLite/extension.

        ### 2026-09-09 — PR 5c.2-B.1b-ii-b: servidor HTTP de exportación estática hermético aterrizado (workspace aislado `tools/react-e2e-harness/`; rebanada de composición + tests herméticos del driver + modernización de selectores + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos)

        - `tools/react-e2e-harness/scripts/export-server.mjs` (nuevo; ~298 LoC; Node puro built-ins `node:http` + `node:fs/promises` + `node:path` + `node:url`; cero deps npm; cero delta en `package.json` del arnés; CLI `--port N` / `--host H` OR `--port 0` asignado por el OS; nunca hard-coded 8765; default loopback `127.0.0.1`; `--root` obligatorio, absoluto, directorio existente; validado ANTES de bindear cualquier listener (fail-closed); `/` mapea a `index.html`; archivos exactos bajo la raíz servidos recursivamente con el Content-Type correspondiente (HTML / HTM / JS / MJS / CSS / JSON / MAP / XML / TXT / SVG / PNG / JPG / JPEG / GIF / WEBP / ICO / WOFF / WOFF2 / TTF / OTF — extensiones desconocidas caen a `application/octet-stream`); HEAD refleja el Content-Type + Content-Length de GET sin cuerpo; `safeJoin()` rechaza `..` / `.` ANTES de cualquier join, divide segmentos explícitamente, aplica verificación de padre estricto después del join (refleja la postura defensiva de `fixture-server.mjs`); traversal / leakage de directorio / rutas desconocidas / métodos no-GET rechazados fail-closed (404 / 405 con `Allow: GET, HEAD`); importable vía `startServer({port, host, root}) → {schema, root, host, port, baseUrl, server, close}` para que la rebanada de composición pueda spawn/teardown en-proceso; la CLI parsea `--root` / `--port` / `--host` / `--help` y sale non-zero en flags desconocidas; apagado SIGINT / SIGTERM manejado vía un único guardia `shuttingDown`).
        - `tests/test_5c_2_b_react_harness.py` (modificado; bloque fixture existente retenido verbatim; bloque export-server añadido dentro del mismo archivo con constante de ruta `EXPORT_SERVER` + `_spawn_export` + `_wait_export_ready` + fixtures `exptree` / `exp`; archivo total ahora 54 pytest cases (27 fixture, 27 export-server, incluyendo expansiones parametrizadas); mismo enfoque `subprocess` Node + Python `urllib`; sin Playwright / Chromium / FastAPI / SQLite / red; contrato de fuente RED-gate, gating CLI (`--root` faltante / relativo / inexistente cada uno exit non-zero), ciclo de vida start/stop, `/` → `index.html`, siete familias de Content-Type (HTML / JS / MJS / CSS / JSON / PNG / WOFF2) + fallback `application/octet-stream` para `.bin`, archivo anidado bajo la raíz, HEAD refleja GET, fail-closed traversal parametrizado sobre `..` / `../../etc/passwd` / `%2Fetc%2Fpasswd` / `%2E%2E%2Fpasswd`, directorio-no-servido 404, ruta-desconocida 404, no-GET 405 con `Allow: GET, HEAD`).
        - **TDD estricto**: **RED** = verificación de contrato de fuente pre-implementación (`export-server.mjs` ausente) FALLÓ sobre la fuente previa a `5c.2-B.1b-ii-b`. **GREEN** = `node --check` exit `0` + los 54 pytest cases pasan (27 fixture, 27 export-server, incluyendo expansiones parametrizadas); sonda de ciclo de vida confirma puerto elegido por el caller honrado, puertos OS-asignados únicos, `SIGTERM` libera el listener; sonda de gating CLI confirma `--root` faltante / relativo / inexistente cada uno exit non-zero; sonda de `/` → `index.html` confirma que el `index.html` de la raíz de exportación se sirve con `text/html`; sonda de tipo de contenido confirma siete familias MIME + fallback `application/octet-stream`; sonda de archivo anidado confirma que `/sub/nested.html` resuelve al archivo dentro del directorio `sub/`; sonda de HEAD-mirror confirma Content-Type + Content-Length iguales a GET y sin cuerpo; sonda de traversal confirma `..` / `../../etc/passwd` / `%2Fetc%2Fpasswd` / `%2E%2E%2Fpasswd` todos 404; sonda de leakage de directorio confirma `/sub/` 404 (sin listado, sin auto-append de `index.html`); sonda de ruta desconocida confirma `/no-such-file.html` 404; sonda de no-GET confirma que POST devuelve exactamente 405 con `Allow: GET, HEAD`. Sin cambios de fuente/API de producción; sin cambios en `domain/keys.ts` / `infrastructure/store.ts`; sin borrado legacy `web/*.{html,js,css}`; sin agregación G4.
        - **Diferimientos (vinculantes)**: wiring de la rebanada de composición (servidores fixture + de exportación iniciados juntos por el driver del arnés), target `make capture-react-e2e`, tests herméticos del driver de captura (chromium-driver.mjs envuelto por fixtures Python), modernización de selectores e2e sobre el nuevo árbol de componentes, borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`. Sin commit/push; sin target de Makefile; sin rebanada de composición; sin borrado legacy `web/*`; sin cambio en `tools/g4-capture/**`; sin cambio de FastAPI/SQLite/extension.
        - **Estado de G4 / G3 Tier-2 / cutover (sin cambios)**: G4 paridad Playwright + Lighthouse permanece **bloqueada** (solo tres de cinco sub-slices enviados; sin flip end-to-end de `scripts/verify_parity.py`); G3 Tier-2 permanece con compuerta en el cierre de G4 + G6; G6 permanece bloqueada; PR 3e se publica solo cuando G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6 estén todos verdes. **El aterrizaje del servidor de exportación estática NO voltea G4** — solo se enviaron el servidor HTTP de exportación + el bloque de tests hermético; sin agregación G4; sin artefacto de build de producción; sin éxito de runtime de navegador.
        - **Alcance de este intento (vinculante)**: 1 archivo del arnés (`scripts/export-server.mjs`) + 1 archivo de test (`tests/test_5c_2_b_react_harness.py` — bloque export-server añadido; el bloque fixture existente preservado verbatim) + 6 archivos de doc OpenSpec (`tasks.md`, `design.md`, `apply-progress.md` + espejos en español). Sin commit/push; sin target de Makefile; sin rebanada de composición; sin tests herméticos del driver de captura; sin borrado legacy `web/*`; sin cambio en `tools/g4-capture/**`; sin cambio de FastAPI/SQLite/extension.

            ### 2026-09-09 — PR 5c.2-B.1b-ii-c: orquestador de composición + CLI + target de Makefile + rebanada de tests de composición hermética aterrizados (workspace aislado `tools/react-e2e-harness/`; tests herméticos del driver de captura + modernización de selectores + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos)

            - `tools/react-e2e-harness/scripts/composed-capture.mjs` (impl parcial preservado; +25 LoC delta: conjunto `LOOPBACK_HOSTS` + `validateTaxonId` endurecido (rechaza cualquier id ≠ 1) + `validateHost` endurecido (solo loopback: 127.0.0.1 / ::1 / localhost) + `startFixtureFn` / `startExportFn` inyectados por defecto que preservan el camino `startServer` en-proceso mientras permiten a la rebanada de tests hermética observar el orden de cierre). Cablea `fixture-server.mjs` (5c.2-B.1b-ii-a) → `buildFn` inyectado (default `npm run build` con `NEXT_PUBLIC_HARNESS_BASE_URL` fijado al fixture) → sonda de acceso `out/index.html` (fail-closed) → `export-server.mjs` (5c.2-B.1b-ii-b) → `captureFn` inyectado (default `run.mjs::capture` de 5c.2-B.1b-i) en un único orquestador `composeCapture({harnessDir, outputRoot, taxonId, host, buildFn, captureFn, startFixtureFn, startExportFn, now})`. La CLI requiere `--output-root`; rechaza host no-loopback; rechaza cualquier `--taxon-id` distinto del `1` sintético; nunca hard-codes un puerto (`--port 0` para ambos servidores); limpieza en orden inverso bajo `finally` anidados (export cerrado antes que fixture).
            - `tests/test_5c_2_b_react_harness.py` (+289 LoC; bloque de composición añadido; bloques fixture + export-server existentes preservados verbatim; total del archivo ahora 65 pytest cases incluyendo expansiones parametrizadas). 11 nuevos casos herméticos: contrato de fuente (archivo existe + `node --check` + cero-dep), gating de CLI (`--output-root` obligatorio + `--host 0.0.0.0` rechazado + `--taxon-id 2` rechazado), primitivas de validación (`validateTaxonId("1") → 1`; cualquier otro entero positivo / cero / negativo / no-numérico lanza; `validateHost` acepta `127.0.0.1` / `::1` / `localhost` y rechaza todo lo demás), orquestación en-proceso con `out/index.html` sintético + `buildFn` inyectado + `captureFn` inyectado (devuelve sobre estructurado `taxa.react-e2e-composed-capture/1` con baseUrls loopback asignados por el OS), bypass de build → fail-closed (`buildFn` reclama éxito pero no hay `out/index.html` → `composeCapture` lanza ANTES de iniciar el servidor de exportación o invocar `captureFn`), y limpieza en orden inverso en fallo de captura (secuencia `close()` rastreada por espías: export `seq=1`, fixture `seq=2`). Mismo enfoque `subprocess` Node + Python `urllib`; sin Playwright / Chromium / FastAPI / SQLite / red.
            - `Makefile::capture-react-e2e` (target existente preservado verbatim; requiere `OUTPUT_ROOT`; reenvía `HARNESS_DIR`; sin puertos de producción horneados).
            - `tools/react-e2e-harness/package.json` (`scripts.capture:composed = "node scripts/composed-capture.mjs"` existente preservado verbatim; +3 líneas netas).
            - **TDD estricto**: **RED** = verificación de contrato de fuente pre-`5c.2-B.1b-ii-c` (módulo de composición ausente) FALLÓ sobre la fuente previa a `5c.2-B.1b-ii-c`; el sub-ciclo de endurecimiento de validación corrió en vivo (desactivar la comprobación `n !== HARNESS_TAXON_ID` envió `test_composed_capture_validate_taxon_id_accepts_one_only` + `test_composed_capture_cli_rejects_other_taxon_id` a RED con fallos claros — la CLI cayó hasta una invocación real de `npm run build` que surfaceó la validación faltante). **GREEN** = `node --check` exit `0` sobre `composed-capture.mjs` + los 65 tests herméticos pasan (21 fixture + 27 export-server + 11 composición + 6 source-contract parametrizados). **Sin éxito de runtime de navegador reclamado** — `chromium-driver.mjs` es alcanzable vía el `captureFn` por defecto, pero la rebanada de tests de composición nunca lo invoca (el fixture en-proceso usa un stub de captura inyectado que devuelve evidencia sintética); sin artefacto de build de producción; sin flip end-to-end de `scripts/verify_parity.py`.
            - **Diferimientos (vinculantes)**: tests herméticos del driver de captura que ejercitan `chromium-driver.mjs` end-to-end contra un fixture real + servidor de exportación (la rebanada de tests de composición usa un stub de captura inyectado; el driver de captura completo aún no se ejercita), modernización de selectores e2e sobre el nuevo árbol de componentes, borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`. Sin commit/push; sin borrado legacy `web/*`; sin cambio en `tools/g4-capture/**`; sin cambio de FastAPI/SQLite/extension.
            - **Estado de G4 / G3 Tier-2 / cutover (sin cambios)**: G4 paridad Playwright + Lighthouse permanece **bloqueada** (solo cuatro de cinco sub-slices enviados; sin flip end-to-end de `scripts/verify_parity.py`); G3 Tier-2 permanece con compuerta en el cierre de G4 + G6; G6 permanece bloqueada; PR 3e se publica solo cuando G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6 estén todos verdes. **El aterrizaje de la composición NO voltea G4** — solo se enviaron orquestador + CLI + target de Makefile + package-script + rebanada de tests de composición hermética; sin ejecución real de Chromium; sin agregación G4; sin artefacto de build de producción; sin éxito de runtime de navegador.
            - **Alcance de este intento (vinculante)**: 1 archivo del arnés (`scripts/composed-capture.mjs` — impl parcial preservado; +25 LoC delta para endurecimiento de validación + seams de inyección) + 1 archivo de test (`tests/test_5c_2_b_react_harness.py` — bloque de composición añadido; bloques fixture + export-server existentes preservados verbatim) + 6 archivos de doc OpenSpec (`tasks.md`, `design.md`, `apply-progress.md` + espejos en español). Sin commit/push; sin ejecución real de Chromium; sin modernización de selectores e2e; sin borrado legacy `web/*`; sin cambio en `tools/g4-capture/**`; sin cambio de FastAPI/SQLite/extension.

    ### 2026-09-08 — Slice 6c.0 productor solo de navegación de Fase 6c (no-cierre)

    - `tools/g4-capture/scripts/parity_navigation.mjs` (nuevo;
      ~400 LoC bajo el presupuesto de 400 líneas; productor
      de paridad de navegación dirigido por Playwright;
      dynamic-imports `playwright` desde el workspace
      `tools/g4-capture/node_modules/` aislado; sin cambios
      en dependencias raíz). Escribe
      `<outputRoot>/<UTC-timestamp>/{legacy,candidate}/
      {navigation.json,manifest.snapshot.json,run.json}`
      atómicamente (la estrategia sibling-backup refleja
      `capture.mjs`).
    - `tools/g4-capture/package.json` (modificado, delta de 1
      línea: `playwright@1.49.1` exact-pinned junto al
      `lighthouse@12.2.1` + `chrome-launcher@1.2.1` existente;
      private + ESM sin cambios).
    - `tools/g4-capture/package-lock.json` (regenerado vía
      `npm install --package-lock-only` para pinear
      `playwright@1.49.1` y sus deps transitivas; la
      actualización del lockfile se circunscribe a
      `tools/g4-capture` y no toca dependencias raíz).
    - `tests/test_capture_parity.py` (modificado, 25 nuevos
      tests herméticos `parity_navigation`; `runFn` inyectado
      + `now()` fijo para que el productor corra sin
      navegador real, sin red en vivo, y sin binario chromium
      instalado).
    - `Makefile` (modificado, target `make parity-navigation`
      añadido; acepta `LEGACY_ORIGIN` / `CANDIDATE_ORIGIN` /
      `PATHS` / `MANIFEST` / `OUTPUT_ROOT` explícitos; sin
      puertos de producción horneados; sin target umbrella
      `make parity` aún).
    - `tools/g4-capture/README.md` (extendido, contrato del
      slice 3 documentado como no-cierre; los otros cuatro
      reportes G4 permanecen pendientes).
    - **No-cierre**: el slice 6c.0 entrega solo el reporte de
      navegación; el agregador (`scripts/verify_parity.py`)
      aún requiere los otros cuatro reportes antes de poder
      correr de extremo a extremo. G4 permanece **bloqueado**;
      G3 Tier-2 permanece NOT PASSED; sin flip de cutover
      status. Los sub-slices restantes 6c.1–6c.4 capturan
      `api` / `search` / `a11y` / `browser-state` y el flip
      de la compuerta. Reversión: `git revert <6c-sha>`
      elimina el productor + tests + delta del Makefile +
      delta del lockfile; los sub-slices 6c restantes quedan
      intactos.

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

    ### 2026-09-02 — Corrección del defecto de dependencia (esta entrada)

    - **Defecto identificado por la re-auditoría de
      pre-flight del portón de apply**: el
      `src/app/layout.tsx` del PR 3b importaba
      `@taxa/app-shell` (un módulo que el PR 4b envía en
      la posición 6/13 — *más tarde* en la cadena) y
      `./globals.css` (un archivo que el PR 3c envía en la
      posición 3/13 — *más tarde* en la cadena). En su
      testigo de `next build`, ninguno de los dos archivos
      objetivo existía todavía, por lo que el testigo era
      insatisfacible. La misma auditoría marcó la aserción
      de triangulación de PR 3b.5 que dice que la salida
      de build referencia la ruta del barrel del typed
      store `@taxa/browser-state` — ese archivo de barrel
      no existe hasta que el PR 4a aterriza.
    - **Re-ambiado correctivo aplicado**: el PR 3b se
      re-ambia a un **bootstrap autocontenido de
      exportación estática del App Router** —
      `src/app/{layout,page}.tsx` se convierten en
      marcadores semánticos mínimos (solo preload Raleway)
      que no importan ni `@taxa/app-shell` ni
      `./globals.css`. La línea `import "./globals.css";`
      se mueve al PR 3c (que ya posee `globals.css`). La
      integración de `<AppShell>` en
      `src/app/{layout,page}.tsx` se mueve al PR 4b (que
      ya posee `src/modules/app-shell/**`). La referencia
      insatisfacible a `@taxa/browser-state` de PR 3b.5 se
      elimina y se reemplaza con la aserción del archivo
      Raleway `.woff2` en `out/_next/static/media/`.
    - **Conteo de 13 hijos preservado**: la topología y el
      orden de la cadena quedan sin cambios; solo cambian
      las listas de archivos por PR y los testigos de test.
    - **Total authored**: ~2.282 LoC (Δ ~+37 LoC de las
      ~2.245 previas; la corrección del defecto de
      dependencia quita ~25 LoC del PR 3b (sin cableado
      de AppShell/globals.css), añade ~30 LoC al PR 4b
      (costura de integración del AppShell) y ~2 LoC al
      PR 3c (línea `import "./globals.css";`); cada sub-PR
      queda muy por debajo de 400).
    - **El sub-PR más grande** sigue siendo **5b** a
      ~360 LoC (-40 LoC / -10 % de holgura). **No se
      requiere nueva `size:exception`** — solo permanece la
      excepción previa de `package-lock.json` regenerado
      de PR 3a.
    - **El Enfoque A, FastAPI/SQLite, el predecesor
      congelado y los specs por dominio quedan sin
      cambios**.
    - **Restricciones de código / commit / push / PR /
      topología de cadena honradas**:
      - Sin código, commit, push, PR o `git revert`
        realizado en esta revisión.
      - Sin cambios de base de PR; sin reordenamiento de
        cadena; sin cambios de posición de sub-PR.
      - El predecesor `migrate-nextjs-tailwind4/`
        permanece byte-idéntico congelado.
      - Ninguna edición de código fuente realizada (esta
        es una revisión de planificación de alto nivel
        solamente).
    - **Artefactos actualizados** (solo a nivel alto; los
      specs por dominio permanecen fuera de alcance):
      - `openspec/changes/complete-taxa-frontend-migration/design.md`
        — tabla de rebanada de sub-PR actualizada para PR
        3b (-25 LoC), PR 3c (+2 LoC), PR 4b (+30 LoC);
        sección `Orden de dependencia` actualizada para
        marcar la corrección del defecto de dependencia
        como el contrato; tabla de `Archivos afectados`
        actualizada para `src/app/{layout,page}.tsx`,
        `src/app/globals.css`, `src/modules/app-shell/**`;
        nueva nota añadida bajo "Sub-PR slice under
        Approach A" sobre la corrección del defecto de
        dependencia.
      - `openspec/changes/complete-taxa-frontend-migration/spec.md`
        — nota aclaratoria añadida antes de "Next step"
        sobre la corrección del defecto de dependencia a
        nivel de PR; los criterios de aceptación por
        dominio, el contrato del backend, las puertas de
        validación y la unidad de rollback quedan sin
        cambios.
      - `openspec/changes/complete-taxa-frontend-migration/tasks.md`
        — Fase 3b re-ambiada (3b.2 G quita el montaje de
        AppShell y el import de globals.css; 3b.3 G quita
        el envoltorio de AppShell y `"use client"`; 3b.5
        T quita la referencia insatisfacible a
        `@taxa/browser-state` y añade la aserción del
        archivo Raleway `.woff2`; descripción de 3b.6
        Refactor actualizada); Fase 3c añade 3c.7 G (la
        integración de `import "./globals.css";` en
        `src/app/layout.tsx`) + fila de evidencia 3c.7;
        Fase 4b añade 4b.6 G (la integración del AppShell
        en `src/app/{layout,page}.tsx`) + fila de
        evidencia 4b.6; sección Per-sub-PR dependency
        actualizada para 3b / 3c / 4b; Forecast
        reconciliation actualizado a ~2.282 LoC; tabla
        Review Workload Forecast actualizada; nueva nota
        "corrección del defecto de dependencia (esta
        revisión)" añadida en el header.
      - `openspec/changes/complete-taxa-frontend-migration/apply-progress.md`
        — tabla de reconstrucción actualizada para los
        archivos fuente y LoC de PR 3b / 3c / 4b;
        Reconciliación del pronóstico (corregida)
        actualizada a ~2.282 LoC; esta nueva entrada de
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
| G5 (baseline de hidratación) | **PASS registrado — captura fresca bajo el protocolo de reemplazo aprobado por el usuario** (`scripts/g5_close.sh` exit 0; tanto el baseline como el candidato servidos por HTTP controlado — `http://127.0.0.1:64809/` y `http://127.0.0.1:64824/`; métrica observable `DOMContentLoaded`; 1 warm-up + 9 muestras medidas retenidas por lado; agregación por mediana por lado con muestras crudas y procedencia preservadas; tolerancia absoluta (candidato − baseline) ≤ 10 ms satisfecha — mediana baseline `3.3 ms`, mediana candidato `3.2 ms`, delta `−0.1 ms`, umbral `10 ms`; `baseline_source: "captured"` en `evidence/g5/status.json` y `source: "captured"` en `out/hydration-candidate.json`; `evidence/g5/status.json` registra `status: "ready"`, `regression: false`, sin `blocker`; `evidence/g5/regression-report.json` registra `pass: true` con el contrato completo de muestras/warmup/origen/mediana por lado y el delta absoluto). La regla previa de porcentaje/mediana 5+2 (baseline 0.0 / 3.0 ms vs candidato 1.0 / 4.0 ms; `initial_paint_delta_pct: Infinity`, `interaction_latency_delta_pct: 33.33%`; exit de comparación 4) está **superada** por este protocolo fresco y se retiene en el registro de cambios como historial de auditoría. **G5 está cerrada** bajo el protocolo de reemplazo aprobado por el usuario. | Fase 6a — `scripts/reconstruct_hydration_baseline.py` (captura HTTP del fixture legacy), `scripts/capture_hydration_candidate.py` (captura HTTP del candidato `out/`) y `scripts/g5_close.sh` (el arnés de runtime) produjeron juntos la evidencia del protocolo fresco registrada en `evidence/g5/{status,regression-report}.json`. El protocolo de reemplazo aprobado por el usuario registrado en `design.md` §"G5 — baseline de hidratación" ata cada reintento futuro: el fallo se mantiene bloqueado, sin PASS automático, sin PASS previo trasladado a través de un fallo. |
| G6 (ensayo de cutover) | **PASS registrado — `cutover-rehearsal.json` capturado en `2026-09-06T15:10:54Z`** (puerto controlado 55637 — nunca el FastAPI 8765 ambiente; `activation_complete: true`; los 26 consumidores §3.1 seleccionados; `unselected_count: 0`; `silent_fallback_paths: []`; `g3_tier2_exit_code: 0`); unidad atómica de cutover + unidad de reversión consistentes | Fase 6b — `scripts/rehearse_cutover.py` dry-runea la unidad atómica de cutover contra el manifesto activado de la copia de trabajo; el manifesto activado de la copia de trabajo (`openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`) carga el flip Tier-2 para los 26 consumidores §3.1; el predecesor `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` queda byte-idéntico congelado |

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
5. Marcar el PR de cutover (hijo 16 / 16, apuntando a la
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
      de dos tests nuevos); **3b** ~175 (App Router static
      export; testigo ahora satisfacible); **3c-i** ~390
      (tokens / base / modo oscuro + selectores focus-visible
      globales + `@theme` + cascada dark); **3c-ii** ~380
      (estilos de árbol / detalle de taxonomía + kebab +
      modal de materialize + variantes de árbol tintadas por
      reino); **3c-iii** ~390 (estilos de Search / Folder /
      Browser global + chrome del file explorer + visores CSV /
      JSON); **3c-iv** ~280 (animaciones + marcos del visor
      de imagen / vídeo + vista Settings + barrel de
      design-system + paridad final de clases de utilidad);
      **3d** ~240 (el sub-PR re-ambido más pesado en la
      frontera de posición 7, fusionando Makefile + WEB_DIR +
      AC-21); **4a** ~180; **4b** ~90; **5a** ~280; **5b**
      ~360; **5c** ~200; **6a** ~50; **6b** ~120; **6c**
      ~20; **3e** ~120 (mayormente delta de
      `apply-progress.md`).
      **Total**: ~3.485 LoC authored a través de **16**
      sub-PRs (Δ ~+1.240 LoC de las ~2.245 previas a través
      de 13 sub-PRs; el delta es el port completo del
      bloque `<style>` inline legacy). La corrección del
      defecto de dependencia quita ~25 LoC del PR 3b (sin
      cableado de AppShell/globals.css) y añade ~30 LoC al
      PR 4b (costura de integración del AppShell) más ~2
      LoC al PR 3c-i (línea `import "./globals.css";`);
      cada sub-PR queda muy por debajo de 400).
    - El sub-PR más grande es **3c-i a ~390 LoC** (-10 LoC
      de holgura contra el presupuesto de revisión de 400
      líneas por PR). El previamente-más-grande 5b queda
      segundo a ~360 LoC (-40 LoC / -10 % de holgura). PR
      3d queda a ~240 LoC (-160 LoC / -40 % de holgura
      contra el presupuesto de 400 líneas). **No se
      requiere nueva `size:exception`** — solo permanece la
      excepción previa de `package-lock.json` regenerado de
      PR 3a.
    - **PRs encadenados recomendados**: **Sí** — cada
      sub-PR cabe por sí solo en el presupuesto por PR, pero
      el total de ~3.485 líneas y el cutover atómico (la
      feature DEBE integrarse antes de llegar a `develop`)
      sitúan este cambio en la compuerta de Feature Branch
      Chain. La propia sub-secuencia 3c son cuatro hijos
      encadenados porque el CSS inline de 1.963 líneas debe
      portarse verbatim a `src/app/globals.css` y ese
      trabajo no cabe bajo 400 LoC como un único PR.
    - **Estrategia de cadena**:
      **`feature-branch-chain`** (elegida por el usuario).
      El tracker `docs/complete-taxa-frontend-migration-plan`
      (referido como PR #146) es draft/no-merge y es el
      **único** PR que apunta a `develop`; el PR hijo 3a
      apunta al tracker (ahora fusionado como PR #144); PR
      3b apunta a PR 3a (ahora fusionado como PR #145, con
      la reconciliación PR #146 también fusionada);
      **PR 3c-i apunta al tracker** (tras el merge de la
      reconciliación PR #146, recogiendo el estado 3a + 3b
      + reconciliación ya fusionado sin un paso extra de
      reconciliación); cada hijo posterior de la
      sub-secuencia 3c apunta a su rama predecesora
      inmediata; cada hijo posterior al 3c apunta a su
      rama predecesora inmediata. Sustituye, para este
      cambio, el default de `AGENTS.md` §4 de apuntar
      directo a `develop` y el precedente de apply-progress
      del predecesor.
    - **Estrategia de entrega**: **`ask-on-risk`** (según
      preflight; sin flag de riesgo abierto — el Enfoque A
      es FINAL, el predecesor está congelado, cada sub-PR
      cabe bajo 400 líneas, la cadena corregida satisface
      el orden de dependencia que el portón de apply
      identificó como defecto, y el re-plan de la
      sub-secuencia PR 3c satisface el presupuesto de LoC
      que el portón de apply identificó como insatisfacible
      para el PR 3c único original).
    - **Decision needed before apply**: **No** (Enfoque A
      bloqueado, estrategia de cadena conocida, cada sub-PR
      dentro del presupuesto, orden de dependencia
      corregido, re-plan de la sub-secuencia PR 3c
      aplicado).

---

## Carga / Frontera de PR

- **Modo**: **Feature Branch Chain** — 1 tracker
  draft/no-merge
  (`docs/complete-taxa-frontend-migration-plan` →
  `develop`) más **16** PRs hijos secuenciales (bootstrap
  de toolchain → exportación estática del App Router →
  **3c-i tokens / base / modo oscuro → 3c-ii estilos de
  árbol / detalle de taxonomía → 3c-iii estilos de
  Search / Folder / Browser global → 3c-iv animaciones
  / utilidades + paridad CSS final + barrel de
  design-system** → Makefile/mount → 4a → 4b → 5a → 5b
  → 5c, seguidos de los eslabones de validación de la
  Fase 6, seguidos del cutover atómico PR 3e como
  último hijo).
- **Total sub-PRs**: **16** (3a, 3b, **3c-i, 3c-ii,
  3c-iii, 3c-iv**, 3d, 4a, 4b, 5a, 5b, 5c, 6a, 6b, 6c,
  3e — la sub-secuencia 3c reemplaza al PR 3c único
  original; 6a, 6b, 6c son trabajo de validación tras
  el camino candidato; 3e tiene compuerta en las seis
  puertas verdes).
- **Cada sub-PR ≤ 390 LoC authored**; **ningún** sub-PR
  excede el presupuesto de revisión de 400 líneas por
  PR. **No se espera ni planifica ninguna nueva
  `size:exception`** (la excepción previa de
  `package-lock.json` regenerado de PR 3a permanece
  como la única).
- **La base de cada PR hijo** = su **rama predecesora
  inmediata**, **excepto PR 3c-i que apunta al
  tracker** (la rama
  `docs/complete-taxa-frontend-migration-plan` tras el
  merge de la reconciliación PR #146). **Solo el
  tracker apunta a `develop`, y permanece en draft /
  no-merge hasta que la cadena se completa.**

---

## Riesgos

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Secuencia de reconstrucción interrumpida; fusión parcial del bootstrap de toolchain + sub-PRs del App Router deja el proyecto en estado inconsistente. | Media | El test enfocado de cada sub-PR pasa independientemente de sub-PRs subsiguientes. Bajo el Feature Branch Chain ningún estado parcial puede llegar a `develop`: los hijos se acumulan solo en el tracker draft/no-merge. Un hijo atascado bloquea a sus sucesores dentro de la cadena, nunca a `develop`. |
| Directorio del predecesor `migrate-nextjs-tailwind4/` editado accidentalmente durante la reconstrucción; los archivos fuente se desvían de la historia de planificación congelada. | Alta | El directorio del predecesor está marcado como solo lectura a nivel de sistema de archivos; CI / protección de rama rechaza cualquier PR que lo modifique. El cuerpo del PR de cada sub-PR debe incluir una sección `## Lo que NO cambió` confirmando que el predecesor quedó byte-idéntico. |
| Trabajo de validación de Fase 6 genera accidentalmente código nuevo en `web/**`, handlers de ruta nuevos en `api/server.py`, o archivos nuevos en `extension/**` (viola el contrato "solo validación, no migración"). | Media | Las tareas de Fase 6 están limitadas a shims `scripts/*`, artefactos de medición en `out/`, y deltas de `apply-progress.md`. No se permiten ediciones en `web/**`, handlers de ruta de `api/server.py` o `extension/**` en Fase 6. El borrado 5c.6 vive en PR 5c, NO en Fase 6. |
| Reconstrucción de G5 produce un baseline que se deriva de los números documentados del predecesor (la auditoría §3.3.5 del predecesor lista el baseline legacy como **no reproducible**). | **Retirada / superada** | La regla previa de porcentaje/mediana 5+2 está **superada** por el protocolo de reemplazo aprobado por el usuario registrado en `design.md` §"G5 — baseline de hidratación" y atada por la captura fresca bajo ese protocolo. La evidencia del protocolo fresco (métrica observable `DOMContentLoaded`; ambos lados servidos por HTTP controlado — `http://127.0.0.1:64809/` y `http://127.0.0.1:64824/`; 1 warm-up + 9 muestras medidas retenidas por lado; agregación por mediana por lado con muestras crudas y procedencia preservadas; tolerancia absoluta (candidato − baseline) ≤ 10 ms satisfecha; mediana baseline `3.3 ms`, mediana candidato `3.2 ms`, delta `−0.1 ms`, umbral `10 ms`) está registrada en `openspec/changes/complete-taxa-frontend-migration/evidence/g5/{status,regression-report}.json` y G5 está **PASS registrada / cerrada** bajo el protocolo de reemplazo aprobado por el usuario. La regla previa 5+2 se retiene en el registro de cambios de abajo como historial de auditoría; la **solicitud** de excepción metodológica está superada por el protocolo registrado y la evidencia del protocolo fresco. |
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
6c. G5 (baseline de hidratación) **PASS registrado /
cerrada — captura fresca bajo el protocolo de reemplazo
aprobado por el usuario** (`scripts/g5_close.sh` exit 0;
tanto el baseline como el candidato servidos por HTTP
controlado — `http://127.0.0.1:64809/` y `http://127.0.0.1:64824/`;
métrica observable `DOMContentLoaded`; 1 warm-up + 9
muestras medidas retenidas por lado; agregación por mediana
por lado con muestras crudas y procedencia preservadas;
tolerancia absoluta (candidato − baseline) ≤ 10 ms satisfecha —
mediana baseline `3.3 ms`, mediana candidato `3.2 ms`, delta
`−0.1 ms`, umbral `10 ms`; `baseline_source: "captured"` en
`evidence/g5/status.json` y `source: "captured"` en
`out/hydration-candidate.json`; `evidence/g5/status.json`
registra `status: "ready"`, `regression: false`, sin `blocker`;
`evidence/g5/regression-report.json` registra `pass: true` con
el contrato completo de muestras/warmup/origen/mediana por
lado y el delta absoluto). La regla previa de
porcentaje/mediana 5+2 (el baseline previo 0.0 / 3.0 ms vs
candidato 1.0 / 4.0 ms; regresión en ambos ejes; exit de
comparación 4) está **superada** por este protocolo fresco y
se retiene en el registro de cambios de abajo como historial
de auditoría únicamente. La **solicitud** de excepción
metodológica registrada en entradas previas del registro de
cambios está superada por el protocolo de reemplazo aprobado
por el usuario y la evidencia del protocolo fresco. G5
permanece sujeta al protocolo de reemplazo aprobado por el
usuario: el fallo se mantiene bloqueado, sin PASS automático,
sin PASS previo trasladado a través de un fallo. G6
(ensayo de cutover) **PASS registrado —
`cutover-rehearsal.json` capturado en
`2026-09-06T15:10:54Z`** (puerto controlado 55637 — nunca
el FastAPI 8765 ambiente; `activation_complete: true`; los
26 consumidores §3.1 seleccionados; `unselected_count: 0`;
`silent_fallback_paths: []`; `g3_tier2_exit_code: 0`); la
unidad atómica de cutover + la unidad de reversión son
consistentes; 0 rutas de fallback silencioso detectadas;
el worker de apply puede proceder a PR 3e. El predecesor
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

**Corrección del defecto de dependencia aplicada el
2026-09-02** (esta nota de estado): la re-auditoría de
pre-flight del portón de apply identificó un segundo defecto
de dependencia dentro de la topología corregida — el
`src/app/layout.tsx` del PR 3b importaba `@taxa/app-shell`
(un módulo que el PR 4b envía en la posición 9/16) y
`./globals.css` (un archivo que el PR 3c-i envía en la
posición 3/16), ninguno de los cuales existía cuando el
testigo de `next build` del PR 3b tenía que correr. La
misma auditoría marcó la aserción de triangulación
insatisfacible a `@taxa/browser-state` de PR 3b.5 (el
archivo de barrel no existe hasta el PR 4a). **El PR 3b se
re-ambia a un bootstrap autocontenido de exportación
estática del App Router** (sin AppShell, sin import de
globals.css); la línea `import "./globals.css";` se mueve
al PR 3c-i; la integración de `<AppShell>` en
`src/app/{layout,page}.tsx` se mueve al PR 4b. **El total
authored tras la corrección del defecto de dependencia es
~2.282 LoC** (Δ ~+37 LoC de las ~2.245 previas; PR 3b se
reduce ~25 LoC, PR 3c-i crece ~2 LoC, PR 4b crece ~30
LoC); cada sub-PR queda muy por debajo de 400; **solo
permanece la excepción previa de `package-lock.json`
regenerado de PR 3a**.

**Re-plan de la sub-secuencia PR 3c aplicado el
2026-09-02** (esta nota de estado): el PR 3c único
original en la posición 3 era **insatisfacible** — se
le había encargado migrar el bloque `<style>` inline de
**1.963 líneas** del `web/index.html` legacy en un
único sub-PR mientras se mantenía bajo el presupuesto
de revisión por PR de 400 líneas; la migración no
cabía. Por tanto la porción de CSS se **re-planea como
cuatro hijos encadenados** (PR 3c-i / PR 3c-ii / PR
3c-iii / PR 3c-iv) en posiciones 3 / 16, 4 / 16,
5 / 16, 6 / 16, cada uno ≤ 400 líneas authored y
particionado por concern: tokens / base / modo oscuro;
estilos de árbol / detalle de taxonomía; estilos de
Search / Folder / Browser global; animaciones /
utilidades + paridad CSS final + barrel de
design-system. El **tracker
`docs/complete-taxa-frontend-migration-plan` (tras el
merge de la reconciliación PR #146)** es el punto de
partida fusionado para el primer nuevo hijo CSS (PR
3c-i); cada hijo posterior apunta a su rama
predecesora inmediata. Los cuatro hijos CSS migran
colectivamente las 1.963 líneas legacy del CSS inline
a `src/app/globals.css` (≤ 1.500 líneas authored más el
reset base de Tailwind 4, bien dentro del presupuesto
del predecesor para `out/_next/static/chunks/*.css`);
el bloque `<style>` legacy se retira en PR 5c. **El
total authored es ahora ~3.485 LoC a través de 16
sub-PRs** (Δ ~+1.240 LoC de las ~2.245 previas; el
re-plan de la sub-secuencia PR 3c particiona la
migración del CSS inline legacy de 1.963 líneas en 4
hijos totalizando ~1.500 LoC (reemplazando los ~230
LoC del PR 3c único previo) y añade un test de
paridad consolidado; cada sub-PR queda muy por debajo
de 400); **solo permanece la excepción previa de
`package-lock.json` regenerado de PR 3a**.

**Nota de supersesión (esta nota de estado)**. La
sección previa de este §Estado titulada **"Nota de
supersesión de la re-división del PR 3c-d del
2026-09-03"** (referenciando el re-plan de tareas del
PR #150 con tres hijos 3c-d / 3c-e / 3c-f y un conteo
de 18 hijos, junto con la narrativa "PRs fusionadas
3c-a/#147, 3c-b/#148, 3c-c/#149 preservadas") está
**superada** por el **re-plan de la sub-secuencia PR 3c
del 2026-09-02** registrado arriba y en el §Cambio de
registro como entrada autoritativa. El conteo
vigente es **16 hijos** (no 18); los hijos CSS son
**3c-i / 3c-ii / 3c-iii / 3c-iv** (no 3c-a..f); las
referencias "PR #147 / #148 / #149" son ficticias y no
corresponden a PRs fusionadas reales del repositorio.
La narrativa previa se retiene en el historial de git
como contexto de planificación rechazado; el estado
actual del tracker y el conteo de hijos derivan del
re-plan de la sub-secuencia PR 3c descrito arriba.

> **Footer (flips de la fase de apply)**: G1: PASS
> registrado · G2: PASS registrado · G3 Tier-1: PASS
> registrado · G3 Tier-2: NO PASADO (con compuerta) ·
> G4: bloqueado — verificador no autordado ·
> G5: PASS registrado — captura fresca bajo el protocolo de reemplazo aprobado por el usuario (DOMContentLoaded; HTTP controlado; 1 warm-up + 9 medidas por lado; mediana; mediana baseline 3.3 ms, mediana candidato 3.2 ms, delta −0.1 ms vs umbral 10 ms; regla previa 5+2 de porcentaje/mediana superada, retenida como historial de auditoría únicamente) ·
> G6: PASS registrado — `cutover-rehearsal.json`
> capturado en `2026-09-06T15:10:54Z` (puerto
> controlado 55637 — nunca el FastAPI 8765 ambiente;
> `activation_complete: true`; `unselected_count: 0`;
> `silent_fallback_paths: []`; `g3_tier2_exit_code: 0`;
> unidad atómica de cutover + unidad de reversión
> consistentes; 0 rutas de fallback silencioso
> detectadas). El footer voltea a PASS registrado para
> G4 solo después de que Fase 6c cierre y PR 3e se
> publique. G3 Tier-2 voltea a PASS registrado solo en
> PR 3e después de que G4 cierre.

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

---

## Addenda — 2026-09-04: re-plan de Fase 5a en cuatro rebanadas (solo anexo)

Esta es una adenda de decisión deliberadamente **solo anexo**; la prosa de
arriba para Fase 5a (port de taxonomy, PR 5a en la posición de cadena
que actualmente ocupa) se conserva verbatim. Registra una supersesión
solo documental que gobierna cómo el **próximo** worktree de código
re-rebanará PR 5a en cuatro sub-PRs revisables. El WIP sobredimensionado
de PR 5a (5a.1–5a.9 + strip de `DetailPanel` + force-Search de `Kebab` +
testigo Playwright del strip en una sola rebanada, muy por encima del
presupuesto de 400 líneas por PR) queda **descartado**.

- **WIP sobredimensionado de 5a descartado.** La enumeración previa
  monolítica (5a.1 R, 5a.2 G, 5a.3 G, 5a.4 G, 5a.5 G, 5a.6 G, 5a.7 T,
  5a.8 T, 5a.9 Refactor en un PR) se reemplaza por el re-plan de cuatro
  rebanadas de abajo. La enumeración descartada se conserva solo como
  contexto histórico; **no** es autoritativa para el próximo worktree.
- **5a.1 — foundation.** `src/modules/taxonomy/{domain,application,
  infrastructure}/**` solo: superficie de tipos, invariantes, funciones
  `fetch*`, hook `useTaxonTree`; la capa de aplicación emite solo
  view-models. Sin `Tree.tsx`, `DetailPanel.tsx`, `Kebab.tsx` ni `TabStrip`.
- **5a.2 — `Tree` + `Breadcrumb` montados.** `src/modules/taxonomy/
  presentation/{Tree,Breadcrumb}.tsx`; portea el layout legacy de
  `web/{tree,breadcrumb}.js` (glifo kebab por fila reservado, cuerpo del
  menú **no** autorizado todavía — el glifo es no-op hasta 5a.4);
  cabalga sobre los selectores `@layer components` de PR 3c-ii. Sin
  `DetailPanel`, `Overview`, `TabStrip` ni activación global.
- **5a.3 — `DetailPanel` + cuerpo de `Overview` + `TabStrip` local.**
  `src/modules/taxonomy/presentation/{DetailPanel,OverviewTab}.tsx` más
  un `TabStrip` **local** (`["Overview", "Search", "Folder"]`, orden
  fijo, tres hermanas siempre alcanzables, `Overview` siempre visible
  según la política de usuario); sin contrato de activación global
  todavía — el callback force-Search del `Kebab` se conecta solo contra
  este componente local.
- **5a.4 — force-Search de `Search online` de `Kebab` + testigo Chromium.**
  `src/modules/taxonomy/presentation/Kebab.tsx` más la extensión de
  `tests/test_taxonomy_infra.py`: el menú kebab gana la acción `Search
  online`; la acción dispara el callback de activación que **fuerza la
  pestaña `Search` activa** sobre el taxón seleccionado (NO debe caer
  en `Overview`, ni siquiera para taxones de nivel superior); el testigo
  Chromium es el guardián de regresión canónico. **Asignación de
  regresión** (por solicitud):
  `Archaea → Search online → Search` (taxón de nivel superior; la
  regresión viva actual cae en `Overview`; 5a.4 la cierra).
- **Por rebanada ≤ 400 líneas (LoC authored, excluyendo `package-lock.json`
  regenerado).** Cada uno de 5a.1, 5a.2, 5a.3, 5a.4 se dimensiona para
  dejar headroom bajo el presupuesto de 400 líneas por PR que
  Aproximación A bloqueó 2026-09-02. El WIP descartado violaba el
  presupuesto; el re-plan lo restaura.
- **Posiciones de cadena para el próximo worktree de código (topología
  de 22 hijos).** El próximo worktree DEBE usar este mapeo y nada más:
  `5a.1 → 13`, `5a.2 → 14`, `5a.3 → 15`, `5a.4 → 16`, `5b → 17`,
  `5c → 18`, `6a → 19`, `6b → 20`, `6c → 21`, `3e → 22` (cutover
  atómico, aún con compuerta G1–G6). Posiciones 13–16 albergan 5a.1–5a.4;
  posiciones 17–22 albergan cada sub-PR posterior; el conteo de 22
  hijos reemplaza a 16. PR 4b en posición 12/22 es la base de merge para
  5a.1. Topología de cadena, estrategia `feature-branch-chain`, contrato
  "tracker-only targets `develop`", predecesor congelado, Aproximación A,
  FastAPI/SQLite y specs por dominio quedan sin cambios.
- **Promoción de `TabStrip` diferida a design-system — en PR 5b.** El
  primitivo `TabStrip` autor en 5a.3 permanece **local** en
  `src/modules/taxonomy/presentation/` durante la rebanada 5a. Su
  promoción a `src/modules/design-system/` (para que `SearchTab` /
  `FolderTab` de 5b lo consuman como primitivo hermano) queda
  **diferida a PR 5b**, junto con el guardián de regresión de que
  ninguna ruta de importación de taxonomy regrese.
- **Contrato de autoría.** Sin edición de código, sin rebase y sin rama
  nueva en esta adenda; el próximo worktree de código lee esta adenda
  como autoritativa y re-rebana 5a.1–5a.4 según las reglas de arriba. El
  espejo en español vive en
  `documents-es/.../{tasks-es.md,apply-progress-es.md,design-es.md}` y
  carga la misma semántica; cualquier deriva se resuelve a favor del
  inglés.

---

## Addenda — 2026-09-04: re-plan de Fase 5b en cuatro rebanadas (solo anexo)

Esta es una adenda de decisión deliberadamente **solo anexo**; la prosa de
arriba para Fase 5b (port del módulo research + pin de CDN, PR 5b en la
posición de cadena que actualmente ocupa) se conserva verbatim. Registra
una supersesión solo documental que gobierna cómo el **próximo** worktree
de código re-rebanará PR 5b en cuatro sub-PRs revisables. La enumeración
prevista in-line de 5b (5b.1 R + 5b.2–5b.7 G + 5b.8 T + 5b.9 Refactor —
nueve pasos dentro de una sola rebanada de ~395 LoC ya en el presupuesto
de 400 líneas por PR) queda **descartada** y se conserva solo como
contexto histórico.

- **Enumeración in-line de 5b descartada.** La enumeración previa
  monolítica de Fase 5b (5b.1 R tests, 5b.2 G domain, 5b.3 G
  `infrastructure/api.ts`, 5b.4 G re-export de `search-engines.js`,
  5b.5 G hooks de application, 5b.6 G presentation ~290 LoC, 5b.7 G
  delta de app-shell `Browser`, 5b.8 T triangulación, 5b.9 Refactor —
  todo en un PR en la posición previa 17/22) se reemplaza por el
  re-plan de cuatro rebanadas de abajo. La enumeración descartada se
  conserva solo como contexto histórico; **no** es autoritativa para
  el próximo worktree de código.
- **5b.1 — foundation (research domain + infrastructure + re-export de
  search-engines).** `src/modules/research/{domain,infrastructure}/**`:
  tipos `ResearchFile` / `Engine` / `FileNode` (domain); `fetchFiles(id)`,
  `fetchServe(id, rel)`, loader idempotente de CDN `loadScriptOnce(name,
  src)` (`infrastructure/api.ts`); más `search-engines.js` re-exportando
  `SEARCH_ENGINES` desde el `src/data/search-engines.js` de PR 3d (export
  nombrado sin cambios). Sin hooks de application, sin `FileExplorer.tsx`,
  sin `FileViewer.tsx`, sin `SearchTab` / `FolderTab` / `SearchLinkList`,
  sin delta de app-shell.
- **5b.2 — hooks de application.** `src/modules/research/application/
  {useFileExplorer,useFileViewer}.ts`: los dos hooks consumen las
  funciones `fetch*` tipadas de 5b.1 y emiten view-models. Las claves
  de estado persistido (`state.explorer.search.{query, mode,
  hideEmpty}`) y el contrato de **debounce de 200 ms** se **declaran
  aquí** como contratos a nivel de hook para que 5b.3 los consuma; el
  cableado real de `FileExplorer.tsx` / `FileViewer.tsx` queda en 5b.3.
  Sin presentation, sin `SearchTab` / `FolderTab`, sin delta de
  app-shell.
- **5b.3 — presentation de `FileExplorer` + `FileViewer` + comportamiento
  CDN / debounce / estado persistido.** `src/modules/research/
  presentation/{FileExplorer,FileViewer,RawTableTreeTabs,MetaStrip,
  BreadcrumbPanel,Banners}.tsx`: portea el layout legacy de dos paneles
  de `web/{file_explorer,file_viewer,format,keymap}.js`; despachador de
  nueve formatos con lazy loading pineado a CDN (`mammoth@1.8.0`,
  `xlsx@0.18.5`, `epubjs@0.3.93`); fallbacks legacy de DOC y formatos no
  soportados; banner de fallo de CDN
  `"Viewer offline — raw download unavailable"`; búsqueda en árbol con
  **debounce de 200 ms**, modos filter / highlight, y
  `state.explorer.search.{query, mode, hideEmpty}` **persistido** entre
  cambios de taxón; meta strip `FORMAT | SIZE | ENCODING`; reset del
  estado del explorer al cambiar de taxón. Cabalga sobre los
  selectores `@layer components` de PR 3c-iii. Sin `SearchTab` /
  `FolderTab` / `SearchLinkList`, sin delta de app-shell, sin
  promoción de `TabStrip` todavía.
- **5b.4 — `SearchTab` + `FolderTab` + `SearchLinkList` + re-anclaje
  global de `Browser` + promoción de `TabStrip` a design-system.**
  `src/modules/research/presentation/{SearchTab,FolderTab,
  SearchLinkList}.tsx`: `SearchTab` renderiza las cinco secciones de
  categoría (`General` / `Taxonomic` / `Academic` / `Multimedia` /
  `Documents`) en orden fijo; `FolderTab` es **separado** (indicador
  de materialización por taxón; NO debe ser subconjunto de
  `SearchTab`); `SearchLinkList` mapea cada `Engine` a un ancla con
  `target="_blank"` y `rel="noopener noreferrer"`, resolviendo la
  plantilla de URL desde `SEARCH_ENGINES`. Más
  `src/modules/app-shell/infrastructure/page-chrome.tsx` (~30 LoC de
  delta): la pestaña `Browser` del header se re-ancla como
  **explorador global de Research / archivos** — abre sin filtro
  `taxonId`; seleccionar un taxón con `Browser` activo NO debe acotar
  el explorer a ese taxón (el contrato de atributos
  `data-path="browser"` / `data-action="nav-tab"` se preserva). Más la
  promoción diferida de `TabStrip` desde 5a.3 que aterriza aquí: el
  primitivo `TabStrip` local se mueve a `src/modules/design-system/`
  (primitivo hermano), **con el guardián de regresión** de que
  ninguna ruta de importación de taxonomy regrese.
- **Por rebanada ≤ 400 líneas (LoC authored, excluyendo
  `package-lock.json` regenerado).** Cada uno de 5b.1, 5b.2, 5b.3,
  5b.4 se dimensiona para dejar headroom bajo el presupuesto de 400
  líneas por PR que Aproximación A bloqueó 2026-09-02. La enumeración
  in-line descartada de 9 pasos violaba el presupuesto; el re-plan de
  cuatro rebanadas lo restaura.
- **Posiciones de cadena para el próximo worktree de código (tracker +
  25 hijos = 26 PRs totales).** El próximo worktree DEBE usar este
  mapeo y nada más: `5b.1 → 17`, `5b.2 → 18`, `5b.3 → 19`,
  `5b.4 → 20`, `5c → 21`, `6a → 22`, `6b → 23`, `6c → 24`,
  `3e → 25` (cutover atómico, aún con compuerta G1–G6). El conteo de
  25 hijos reemplaza al conteo previo de 22 hijos; posiciones 17–20
  albergan el split 5b.1–5b.4, posiciones 21–25 albergan cada sub-PR
  posterior. PR 4b en posición 12/22 se mantiene como base de merge
  para 5a.1; la base de merge de 5b.1 es el PR que aterriza
  inmediatamente antes de la posición 17 en la topología corregida
  (según la auditoría del próximo worktree de código). Topología de
  cadena, estrategia `feature-branch-chain`, contrato
  "tracker-only targets `develop`", predecesor congelado,
  Aproximación A, FastAPI/SQLite y specs por dominio quedan sin
  cambios.
- **Cierre de la promoción de `TabStrip` en 5b.4.** La promoción de
  `TabStrip` que la adenda de 5a.3 difirió a PR 5b ahora cierra en
  PR 5b.4 (no al final de PR 5b como bloque): el primitivo `TabStrip`
  local se mueve a `src/modules/design-system/`, y el guardián de
  regresión de 5b.4 asegura que ninguna ruta de importación de
  taxonomy regrese. Después de que 5b.4 aterrice, no queda más
  trabajo de `TabStrip` pendiente desde las rebanadas 5a / 5b.
- **Contrato de autoría.** Sin edición de código, sin rebase y sin
  rama nueva en esta adenda; el próximo worktree de código lee esta
  adenda como autoritativa y re-rebana 5b.1–5b.4 según las reglas de
  arriba. El espejo en español vive en
  `documents-es/.../{tasks-es.md,apply-progress-es.md,design-es.md}`
  y carga la misma semántica; cualquier deriva se resuelve a favor del
  inglés.


### 2026-09-07 — Fase 6a: cierre de G5 bajo el protocolo de reemplazo aprobado por el usuario (G5 PASS registrado / cerrada)

- **Captura fresca bajo el protocolo de reemplazo aprobado por el usuario** (esta entrada). El protocolo de reemplazo G5 aprobado por el usuario registrado en `design.md` §"G5 — baseline de hidratación" fue atado por una captura fresca ejecutada bajo ese protocolo; el script canónico de captura (`scripts/g5_close.sh`) salió `0`. La evidencia del protocolo fresco es ahora el registro autoritativo verificado para G5:
  - **Transporte**: tanto el baseline como el candidato servidos por HTTP controlado (sin `file://`). `baseline_origin: "http://127.0.0.1:64809/"`; `candidate_origin: "http://127.0.0.1:64824/"`.
  - **Métrica observable**: `DOMContentLoaded` (capturada vía PerformanceNavigationTiming sobre el servicio HTTP controlado; reemplaza al par previo de paint-inicial + latencia-de-interacción).
  - **Muestreo**: 1 warm-up + 9 muestras medidas retenidas por lado; agregación por lado = mediana con muestras crudas + muestras de warmup + procedencia preservadas en el artefacto.
  - **Tolerancia**: absoluta (candidato − baseline) ≤ 10 ms; mediana baseline `3.3 ms` (crudas: 4.10, 3.40, 3.30, 3.00, 3.60, 2.80, 3.30, 3.00, 3.50; warmup: 39.70), mediana candidato `3.2 ms` (crudas: 5.30, 2.90, 3.10, 3.50, 3.10, 3.20, 3.20, 3.70, 3.30; warmup: 8.20), delta `−0.1 ms` (mediana candidato < mediana baseline; delta negativo es mejora), umbral `10 ms` — tolerancia satisfecha.
  - **Atribución de fuente**: `baseline_source: "captured"` en `evidence/g5/status.json` y `source: "captured"` en `out/hydration-candidate.json` (capturas reales, no derivadas de números documentados del predecesor; no son placeholders).
  - **`evidence/g5/status.json`** (re-capturado bajo este intento): `gate: "G5"`, `status: "ready"`, `captured_at: "2026-09-07T15:41:38Z"`, `baseline_path: web/dist/evidence-baseline.json` (`baseline_source: "captured"`), `candidate_path: out/hydration-candidate.json`, `regression: false`, `threshold_ms: 10.0`, `baseline_median_ms: 3.299999952316284`, `candidate_median_ms: 3.200000047683716`, `delta_ms: -0.09999990463256836`, `blocker: null`.
  - **`evidence/g5/regression-report.json`** (re-capturado bajo este intento): esquema completo por lado con `baseline.samples` (9), `baseline.warmup_samples` (1), `candidate.samples` (9), `candidate.warmup_samples` (1), `baseline_origin` / `candidate_origin`, `baseline_build: "legacy"` / `candidate_build: "migrated"`, `pass: true`, el `delta_ms` y `threshold_ms` absolutos registrados arriba. Conforme al esquema del protocolo fresco; no al esquema del contrato previo de porcentaje/mediana 5+2.

- **Supersesión de la evidencia previa de porcentaje/mediana 5+2 (historial de auditoría retenido)**. La regla previa de captura 5+2 (muestras retenidas del baseline `5`; muestras retenidas del candidato `5`; comparación porcentual `initial_paint_delta_pct` / `interaction_latency_delta_pct`; medianas baseline 0.0 / 3.0 ms; medianas candidato 1.0 / 4.0 ms; `initial_paint_delta_pct: Infinity`; `interaction_latency_delta_pct: 33.33333333333333`; `regression: true`; `regressing_axes: ["initial_paint", "interaction_latency"]`; exit de comparación `4`) está **superada** por la evidencia del protocolo fresco de arriba. El contenido previo de `evidence/g5/{status,regression-report}.json` (el snapshot bloqueado del `2026-09-06T01:37:38Z` en `taxa-worktrees/complete-taxa-frontend-migration-22-6a/`) **no se elimina**; se preserva en el historial de git y en las entradas previas del registro de cambios (2026-09-05 / 2026-09-06) como historial de auditoría. La **solicitud** de excepción metodológica registrada en las entradas 2026-09-05 / 2026-09-06 está superada por el protocolo de reemplazo aprobado por el usuario y la evidencia del protocolo fresco; la solicitud no concede ni exime PASS, cierre o activación de cutover.

- **Actualización de la tabla de puertas de pre-flight**: `G5 (baseline de hidratación)`: `PASS registrado — captura fresca bajo el protocolo de reemplazo aprobado por el usuario` (cita 1 warm-up + 9 medidas por lado, DOMContentLoaded, HTTP controlado, mediana baseline 3.3 ms, mediana candidato 3.2 ms, delta −0.1 ms, umbral 10 ms, ambos `captured`; la regla previa 5+2 de porcentaje/mediana está superada y se retiene como historial de auditoría únicamente). Las otras cinco filas de puertas (G1 / G2 / G3 Tier-1 / G3 Tier-2 / G4 / G6) se preservan exactamente como se registraron previamente; G4 y G3 Tier-2 (con compuerta en el cierre de G4 + G6) y la autoridad de cutover atómico de PR 3e permanecen como bloqueadores independientes.

- **Actualización de narrativa §Status + footer**: la redacción de G5 en la narrativa §Status se volteó a `PASS registrado / cerrada — captura fresca bajo el protocolo de reemplazo aprobado por el usuario` y cita el protocolo 1+9 DOMContentLoaded, el umbral, las medianas y el delta. §Status footer: `G5: PASS registrado — captura fresca bajo el protocolo de reemplazo aprobado por el usuario (DOMContentLoaded; HTTP controlado; 1 warm-up + 9 medidas por lado; mediana; mediana baseline 3.3 ms, mediana candidato 3.2 ms, delta −0.1 ms vs umbral 10 ms; regla previa 5+2 de porcentaje/mediana superada, retenida como historial de auditoría únicamente)`. La redacción del footer para G4, G3 Tier-2 y la autoridad de cutover de PR 3e se preserva exactamente como se registró previamente; G4 / G6 / G3 Tier-2 (con compuerta) permanecen bloqueados, y PR 3e se publica solo cuando las seis puertas estén verdes.

- **Actualización de la tabla §Riesgos**: la fila de riesgo de inestabilidad de G5 se actualiza de `Alta` (solicitud de excepción metodológica, sin PASS) a `Retirada / superada` (protocolo de reemplazo aprobado por el usuario + evidencia del protocolo fresco; PASS registrado; regla previa 5+2 retenida como historial de auditoría). La fila de riesgo aún apunta a `design.md` §"G5 — baseline de hidratación" para el contrato de protocolo vinculante.

- **Alcance de este intento (vinculante)**:
  - **Sin ediciones de fuente / test / salida de build.** No se hace ningún cambio de código, test, ni `scripts/` / `tests/` en este intento; el arnés (`scripts/reconstruct_hydration_baseline.py`, `scripts/capture_hydration_candidate.py`, `scripts/measure_hydration.py`, `scripts/g5_close.sh`) y `tests/test_hydration_timing.py` ya estaban atados al protocolo de reemplazo aprobado por el usuario en intentos previos y no se re-editaron aquí.
  - **Sin cutover de producción, sin restauración de web, sin cambios de backend / ETL / extension, sin commit, sin push.** La huella de Fase 6a se limita a las superficies de edición permitidas listadas en la tarea delegada: `apply-progress.md` (§Registro de cambios + tabla de puertas §Pre-flight + §Riesgos + narrativa §Status + footer §Status), `design.md` (§Evidencia trasladada + §Riesgos + §Estado), `tasks.md` (estado de tareas Fase 6a + lista de puertas de PR 3e + footer §Status), los espejos en español `apply-progress-es.md` / `design-es.md` / `tasks-es.md`, y los artefactos de evidencia canónicos `evidence/g5/{status,regression-report}.json`. El fixture legacy bajo `tools/g3-legacy-fixture/web/`, el código de la app React bajo `src/`, `next.config.mjs`, `package.json`, el artefacto de build bajo `out/`, el predecesor `openspec/changes/migrate-nextjs-tailwind4/**`, el FastAPI `api/server.py`, y la extensión Chrome bajo `extension/**` NO se modifican por este intento. La evidencia previa de porcentaje/mediana 5+2 se preserva en el historial de git (el contenido previo de `evidence/g5/{status,regression-report}.json` bajo `taxa-worktrees/complete-taxa-frontend-migration-22-6a/`) y en las entradas previas del registro de cambios como historial de auditoría únicamente.
      - **No se concede autoridad de cutover.** Esta entrada registra el cierre de G5 bajo el protocolo de reemplazo aprobado por el usuario únicamente. El cutover atómico PR 3e se publica solo cuando G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6 estén todos verdes; G4 permanece bloqueado (verificador no autordado), G3 Tier-2 permanece con compuerta en el cierre de G4 + G6, G6 permanece bloqueado (verificador no autordado), y la autoridad de cutover de PR 3e queda sin cambios.

    ### 2026-09-07 — PR 5c.1a: fundación tipada de browser-state aterrizada (contrato 5 + 5 de llamadas de almacenamiento restaurado; 5c.1b + 5c.2 diferidas; G4 sigue bloqueada)

    - **Alcance (esta entrada)**. PR 5c.1a es una rebanada de fundación tipada: aterriza los literales del dominio de cinco llaves + defaults + validadores (`src/modules/browser-state/domain/keys.ts` — añade `versionBannerDismissed: "taxa.settings.versionBannerDismissed"` (booleano, default `false`); extiende `TreeSource` a `col | worms | freshwater`), el contrato de llamadas de almacenamiento **5 + 5** de `getItem(` / `setItem(` correspondiente (`src/modules/browser-state/infrastructure/store.ts` — cinco + cinco sitios de llamada, todos dentro de `store.ts`; `safe-storage.ts` se queda sin sitios `getItem(` / `setItem(`), y el test de contrato de fuente Python enfocado (`tests/test_browser_state_keys.py`, extendido bajo TDD estricto).
      - **Evidencia de TDD estricto (`tests/test_browser_state_keys.py`)**:
        - **RED observado** antes de la implementación: 8 fallas sobre la fuente de 4 llaves — `test_keys_object_declares_exactly_five_pinned_literals`, `test_keys_short_names_match_pinned_mapping`, `test_defaults_cover_every_key`, `test_exactly_five_getitem_callsites_under_src`, `test_exactly_five_setitem_callsites_under_src`, `test_tree_source_validator_accepts_freshwater`, `test_version_banner_dismissed_defaults_to_false`, `test_store_exposes_ten_mutators_and_listener`; cada una falló en el diff esperado-vs-real documentado.
        - **GREEN observado** después de la implementación: **27/27 tests pasan** (25 preexistentes + 2 nuevos). Sondas de triangulación confirman: orden de nombres de llave preservado exactamente; cuerpo del validador acepta `col | worms | freshwater`; default es el literal `false`; campo del value-map tipado como `boolean`; 5 + 5 sitios de llamada todos bajo `store.ts`; capa de dominio lleva cero tokens prohibidos (`react` / `nextjs` / `fastapi` / `fetch(` / `localStorage` / `document.` / `window.` / `process.`); `node_modules/.bin/tsc --noEmit` limpio para `src/modules/browser-state/`.
        - **Sin paso de REFACTOR** — la implementación aterrizó como un solo delta mecánico mínimo (una fila de literal + una fila en value-map + una fila de default + una línea de validador + un bloque `getItem(` + un bloque `setItem(` + una entrada getter + una entrada setter + una fila de reset + un import). Las sondas de triangulación pasan sin mayor compresión.
      - **Diferimientos (vinculantes, esta entrada)**:
        - **PR 5c.1b (diferida)** — integración React: render del banner + UI de fuente de árbol en presentación del consumidor; actualizaciones de selectores en `tests/test_e2e_file_explorer.py` / `tests/test_web_toggle.py`. Reemplaza la enumeración anterior `5c.1 R / 5c.2 R / 5c.3 G / 5c.4 G`. Sin cambios en `domain/keys.ts` / `infrastructure/store.ts`.
        - **PR 5c.2 (diferida)** — cableado de research / search / folder: port del módulo research + despachador por formato + arnés impulsado por Playwright. Reemplaza la enumeración anterior `5c.5 T / 5c.6 G / 5c.7 Refactor`. Sin cambios en `domain/keys.ts` / `infrastructure/store.ts`.
        - **Estado de G4 (sin cambios).** G4 paridad Playwright + Lighthouse permanece **bloqueada** (verificador no autordado); PR 5c.1a es una rebanada de forma de código, no una rebanada de evidencia G4. El cutover atómico PR 3e se publica solo cuando G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6 estén todos verdes; G4 permanece como bloqueador independiente.
      - **Alcance de este intento (vinculante)**: superficies de edición permitidas limitadas a `src/modules/browser-state/{domain/keys,infrastructure/store}.ts`, `tests/test_browser_state_keys.py`, y los seis archivos OpenSpec (3 EN + 3 ES). Sin páginas / componentes / barrels / hooks de React; sin tests E2E; sin selectores de fuente; sin features de research; sin salidas de build; sin commit/push. El fixture legacy bajo `tools/g3-legacy-fixture/web/`, el resto de `src/`, `next.config.mjs`, `package.json`, el artefacto de build bajo `out/`, el árbol predecesor OpenSpec, el FastAPI `api/server.py`, y la extensión Chrome bajo `extension/**` NO se modifican por este intento. **Sin volteo de puerta, sin autoridad de cutover concedida** — las filas de estado G1 / G2 / G3 Tier-1 / G3 Tier-2 / G4 / G6 y las filas de autoridad de cutover de PR 3e se preservan verbatim desde la entrada previa del registro de cambios.


        ### 2026-09-07 — PR 5c.1b-A: UI de fuente de árbol + ids de nav/breadcrumb aterrizada (5c.1b-B + 5c.2 diferidas; G4 / G3 Tier-2 / cutover siguen bloqueadas)

        - **Alcance (esta entrada)**. PR 5c.1b-A es una rebanada de UI React dividida desde la previa `5c.1b` diferida: aterriza (a) el control accesible de fuente de árbol `id="tree-source-toggle"` con tres botones `data-tree-source="col|worms|freshwater"` + `aria-pressed` por botón + handler de click `setTreeSource(next)` en `src/modules/app-shell/infrastructure/page-chrome.tsx`; (b) ids de React `nav-browser` / `nav-classification` / `nav-settings` en los botones de nav existentes en el mismo archivo; (c) `id="breadcrumb"` en el elemento `<nav>` en ambas ramas condicionales de `src/modules/taxonomy/presentation/Breadcrumb.tsx`; (d) el cableado de contexto de store único — `src/modules/app-shell/presentation/browser-state-store-context.ts` exporta `useBrowserStateStore()` desde un React Context; `AppShell.tsx` es el único sitio de llamada a `createBrowserStateStore()` en el codebase y publica esa única instancia vía `BrowserStateStoreContext.Provider`; `src/app/page.tsx` lee `treeSource` vía el hook + `useSyncExternalStore` y lo fluye a `useTaxonTree({ source: treeSource })` (sin más `source: "col"` hard-coded).
          - **Evidencia de TDD estricto (`tests/test_browser_state_keys.py`)**:
            - **RED observado** antes de la implementación: 6 fallas nuevas sobre la fuente previa a 5c.1b-A — `test_tree_source_toggle_renders_with_three_buttons`, `test_tree_source_toggle_persists_via_set_tree_source`, `test_app_shell_exposes_single_store_via_context`, `test_page_consumes_tree_source_via_app_shell_context`, `test_nav_button_ids_match_legacy_contract`, `test_breadcrumb_renders_with_id_breadcrumb`; cada una falló en el diff esperado-vs-real documentado (faltaba `#tree-source-toggle`, faltaba `setTreeSource` en page-chrome, sin Provider de contexto, `source: "col"` hard-coded, ids `nav-*` faltantes, `id="breadcrumb"` faltante).
            - **GREEN observado** después de la implementación: **33/33 tests pasan** (27 preexistentes + 6 nuevos). Sondas de triangulación confirman: orden del toggle `col / worms / freshwater`; `aria-pressed` estampado por botón; `setTreeSource` cableado vía mapa TREE_SOURCES único; exactamente un sitio de llamada a `createBrowserStateStore()` en app-shell (en `AppShell.tsx`); Provider de contexto cablea la MISMA instancia; `page.tsx` consume vía barrel `@taxa/app-shell` + `useSyncExternalStore`; ids de botón de nav estampados en los botones de nav existentes; `id="breadcrumb"` estampado en ambas ramas `<nav>`; ninguna mención de `localStorage` en page-chrome; pureza de safe-storage preservada; el contrato de 5 + 5 llamadas de almacenamiento sin cambios.
            - **Sin paso de REFACTOR** — la implementación aterrizó como un delta mecánico mínimo (un div de toggle + tres botones en page-chrome + un subscribe noop + un wrap de Provider en AppShell + un archivo de contexto + una re-exportación de barrel + un `id="breadcrumb"` por rama de Breadcrumb + un `useBrowserStateStore` + un `useSyncExternalStore` en page.tsx).
          - **Diferimientos (vinculantes, esta entrada)**:
            - **PR 5c.1b-B (diferida)** — render de VersionBanner + trabajo de cierre/sticky de panel + pulido de hidratación de fuente de árbol; reemplaza la fila monolítica previa `5c.1b (diferida)`. Sin cambios en `domain/keys.ts` / `infrastructure/store.ts`.
            - **PR 5c.2 (diferida, sin cambios)** — cableado de research / search / folder. Sin cambios en `domain/keys.ts` / `infrastructure/store.ts`.
            - **Estado de G4 / G3 Tier-2 / cutover (sin cambios).** G4 paridad Playwright + Lighthouse permanece **bloqueada** (verificador no autordado); G3 Tier-2 permanece con compuerta en el cierre de G4 + G6; G6 permanece bloqueada; el cutover atómico PR 3e se publica solo cuando G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6 estén todos verdes.
          - **Alcance de este intento (vinculante)**: superficies de edición permitidas limitadas a `src/modules/app-shell/{infrastructure/page-chrome.tsx, presentation/AppShell.tsx, presentation/browser-state-store-context.ts, index.ts}`, `src/app/page.tsx`, `src/modules/taxonomy/presentation/Breadcrumb.tsx`, `tests/test_browser_state_keys.py`, y los seis archivos OpenSpec (3 EN + 3 ES). **Sin render de VersionBanner**, sin trabajo de cierre/sticky de panel, sin cambio de comportamiento de Folder/Search research, sin tests G4, sin captura de browser, sin commit/push. El fixture legacy bajo `tools/g3-legacy-fixture/web/`, el resto de `src/`, `next.config.mjs`, `package.json`, el artefacto de build bajo `out/`, el árbol predecesor OpenSpec, el FastAPI `api/server.py`, y la extensión Chrome bajo `extension/**` NO se modifican por este intento. **Sin volteo de puerta, sin autoridad de cutover concedida** — las filas de estado G1 / G2 / G3 Tier-1 / G3 Tier-2 / G4 / G6 y las filas de autoridad de cutover de PR 3e se preservan verbatim desde la entrada previa del registro de cambios.


        ### 2026-09-07 — PR 5c.1b-B: render de VersionBanner + contrato de cierre/sticky de panel aterrizados (5c.2 diferida; G4 / G3 Tier-2 / cutover siguen bloqueadas)

        - **Alcance (esta entrada)**. PR 5c.1b-B es la rebanada React + CSS
          de la fila `5c.1b-B` diferida previa: aterriza (a) el `VersionBanner`
          con gate de mount (`src/modules/app-shell/presentation/VersionBanner.tsx`)
          consumiendo la ÚNICA instancia tipada de `BrowserStateStore` vía
          el hook `useBrowserStateStore()` (sin duplicar `createBrowserStateStore()`),
          leyendo `/api/health` solo DESPUÉS de que `useMounted()` se voltea,
          fallando cerrado ante respuestas no-OK / campos de version-de-schema
          faltantes / no numéricos / errores de red, preservando los ids DOM
          legacy `version-banner` / `version-banner-actual` /
          `version-banner-expected`, persistiendo los descartes vía
          `setVersionBannerDismissed(true)`, y montando dentro del slot
          existente `data-slot="banner-host"` vía `src/modules/app-shell/infrastructure/page-chrome.tsx`
          (consumido vía un import de módulo hermano; el barrel público de
          `app-shell` se queda intacto en esta rebanada porque `index.ts` no
          está en las superficies de edición permitidas);
          (b) el contrato de cierre/sticky de `DetailPanel` (`src/modules/taxonomy/presentation/DetailPanel.tsx`)
          — `id="detail-panel"`, botón de cierre `data-action="close-detail"`
          cableado a un nuevo estado `detailOpen`, un efecto de `forceOpenSearch`
          que también resetea `detailOpen` a `true` para que Search-online
          reabra un panel cerrado (cierra la regresión legacy de no-op
          silencioso), y los hooks estructurales `.detail-header` /
          `.detail-tabs` para el CSS sticky; (c) el contrato mínimo de
          sticky-CSS en `src/app/globals.css` — `position: sticky` + `top:`
          + `z-index` tanto en `.detail-header` como en `.detail-tabs`
          dentro del viewport de scroll existente de `.detail-panel`, más
          una regla mínima de `#version-banner` (todos los colores enrutados
          vía tokens `var(--…)`; sin literales hex crudos).
          - **Evidencia de TDD estricto (`tests/test_browser_state_keys.py`)**:
            - **RED observado** antes de la implementación: 8 fallas nuevas
              sobre la fuente previa a 5c.1b-B —
              `test_page_chrome_mounts_version_banner_without_duplicate_store`,
              `test_app_shell_index_reexports_version_banner`,
              `test_detail_panel_renders_with_id_detail_panel`,
              `test_detail_panel_close_uses_data_action_close_detail`,
              `test_detail_panel_close_hides_panel_and_force_search_reopens`,
              `test_detail_panel_renders_detail_header_and_detail_tabs_hooks`,
              `test_globals_css_pins_detail_header_and_detail_tabs_as_sticky`,
              `test_globals_css_minimal_version_banner_style_uses_tokens_only`;
              5 pruebas adicionales se saltan por `VersionBanner.tsx` aún
              no autorado (gate de presencia de archivo) —
              `test_version_banner_preserves_legacy_dom_ids`,
              `test_version_banner_is_mount_gated_and_fetches_health_only_after_mount`,
              `test_version_banner_fails_closed_on_unavailable_or_malformed_health`,
              `test_version_banner_persists_dismiss_via_typed_store`,
              `test_version_banner_does_not_construct_a_second_store`. Cada
              prueba fallada / saltada reportó un diff esperado-vs-real documentado.
            - **GREEN observado** después de la implementación: **46/46
              tests pasan** (33 preexistentes + 13 nuevos). Las sondas de
              triangulación confirman: `VersionBanner.tsx` lee el store
              tipado vía `useBrowserStateStore` (sin callsite de `createBrowserStateStore`);
              el fetch a `/api/health` vive dentro de `useEffect` con guarda
              `if (!mounted) return;`; las guardas `typeof X !== "number"`
              + `Number.isFinite` devuelven `null` ante payload malformado
              (falla cerrado); el handler `.catch()` absorbe errores de red;
              `setVersionBannerDismissed(true)` cablea el click de descarte
              al MISMO store tipado; `getVersionBannerDismissed()` controla
              la visibilidad al re-montar; `page-chrome.tsx` monta
              `<VersionBanner />` sin un segundo store; el barrel público de
              presentación no se toca en esta rebanada (fuera de superficies); `DetailPanel.tsx`
              estampa `id="detail-panel"` + `data-action="close-detail"`
              + `data-detail-open` + el estado `detailOpen`; el efecto de
              `forceOpenSearch` invoca `setDetailOpen(true)`; los hooks
              estructurales `.detail-header` / `.detail-tabs` están presentes;
              `globals.css` declara `position: sticky` + `top: 0|49px`
              + `z-index: 2|1` en ambos selectores; el cuerpo de la regla
              `#version-banner` tiene CERO literales hex crudos.
              `node_modules/.bin/tsc --noEmit` está limpio para `src/`.
            - **Sin paso de REFACTOR** — la implementación aterrizó como
              un delta mecánico mínimo (un archivo de componente nuevo + un
              mount `<VersionBanner />` en page-chrome + la reescritura de
              DetailPanel + una extensión dirigida de globals.css con
              colores solo de tokens; sin reexportación de barrel público
              porque `index.ts` no está en las superficies de edición permitidas).
          - **Diferimientos (vinculantes, esta entrada)**:
            - **PR 5c.2 (diferida, sin cambios)** — cableado de research
              / search / folder. Sin cambios en `domain/keys.ts` /
              `infrastructure/store.ts`.
            - **Estado de G4 / G3 Tier-2 / cutover (sin cambios).** G4
              paridad Playwright + Lighthouse permanece **bloqueada**
              (verificador no autordado); G3 Tier-2 permanece con compuerta
              en el cierre de G4 + G6; G6 permanece bloqueada; el cutover
              atómico PR 3e se publica solo cuando G1 + G2 + G3 Tier-1 +
              G3 Tier-2 + G4 + G5 + G6 estén todos verdes.
              - **Alcance de este intento (vinculante)**: superficies de edición
                permitidas limitadas a `src/modules/app-shell/{infrastructure/page-chrome.tsx,
                presentation/AppShell.tsx — sin cambios, presentation/VersionBanner.tsx — nuevo}`, `src/modules/taxonomy/presentation/DetailPanel.tsx`,
                `src/app/globals.css`, `tests/test_browser_state_keys.py`, y los seis
                archivos OpenSpec (3 EN + 3 ES). **Sin cambio de comportamiento de
                Folder/Search research**, sin tests G4, sin captura de browser,
                sin salidas de build (`out/`), sin commit/push, sin cambios de
                FastAPI / SQLite / extension. El fixture legacy bajo
                `tools/g3-legacy-fixture/web/`, el resto de `src/`, `next.config.mjs`,
                `package.json`, el predecesor OpenSpec tree, el FastAPI
                `api/server.py`, y la extensión Chrome bajo `extension/**` NO se
                modifican por este intento. **Sin volteo de puerta, sin autoridad
                de cutover concedida** — las filas de estado G1 / G2 / G3 Tier-1
                / G3 Tier-2 / G4 / G6 y las filas de autoridad de cutover de PR
                3e se preservan verbatim desde la entrada previa del registro
                de cambios.


            ### 2026-09-07 — PR 5c.1b-B (correctiva): correcciones de reactividad + coherencia sticky aterrizadas (5c.2 diferida; G4 / G3 Tier-2 / cutover siguen bloqueadas)

            - **Disparador (esta entrada)**. Una revisión de excepción
              de tamaño aceptada de 5c.1b-B (5c.1b-B) identificó tres
              defectos de corrección en el aterrizaje previo de
              5c.1b-B arriba que esta entrada correctiva cierra. NO
              cambian el alcance ni los volteos de puerta de la
              entrada previa — cierran los hallazgos de revisión
              sobre los mismos archivos en las mismas superficies de
              edición permitidas.

            - **Defecto 1 — reactividad de descarte de
              `VersionBanner` (no-op silencioso al click de
              Descartar)**. El `VersionBanner` previo consumía el
              snapshot de descarte del store tipado vía una lectura
              plana `const dismissed = store !== null &&
              store.getVersionBannerDismissed();`. Después de que el
              click de Descartar llamaba a
              `setVersionBannerDismissed(true)`, el mismo componente
              nunca re-renderizaba, por lo que el banner permanecía
              visible hasta que un re-render externo no relacionado
              lo volteara. La corrección cablea `useSyncExternalStore`
              sobre `store.subscribe` +
              `store.getVersionBannerDismissed()` + un fallback de
              server-snapshot `false` (el mismo patrón de `subscribe /
              snapshot / server-snapshot` que
              `infrastructure/page-chrome.tsx` usa para
              `treeSource`). El click de Descartar ahora voltea el
              banner apagado en el mismo render.

            - **Defecto 2 — drift de `top` de header / tabs
              sticky**. `.detail-header` se renderizaba a su altura
              natural dirigida por padding (~44px) y `.detail-tabs {
              top: 49px }` era un número mágico ajustado a mano cinco
              pixels arriba de la altura natural del header. Cualquier
              cambio de padding o font-size en `.detail-header`
              silenciosamente reintroducía el riesgo de solapamiento /
              brecha. La corrección declara UNA propiedad CSS
              personalizada `--detail-header-height: 49px;` en
              `:root` dentro de `@layer components` (junto a los
              tokens de clases de utilidad existentes
              `--primary-fixed` / `--on-primary-fixed` /
              `--surface-container-lowest`) y
              fija TANTO `.detail-header { min-height:
              var(--detail-header-height) }` COMO `.detail-tabs {
              top: var(--detail-header-height) }` a ese único token.
              Header y tabs no pueden derivar; los cambios de padding /
              font se propagan atómicamente. Los colores siguen siendo
              solo de tokens — sin literales hex crudos introducidos.

            - **Defecto 3 — veracidad de apply-progress**. La lista
              RED previa arriba referenciaba
              `test_app_shell_index_reexports_version_banner`, un
              test que NO existe en
              `tests/test_browser_state_keys.py` (ninguna
              reexportación de barrel de `presentation/index.ts`
              para VersionBanner se publica en esta rebanada — el
              componente se monta vía un import de módulo hermano
              desde `infrastructure/page-chrome.tsx`). El conteo
              RED previo de `8 fallas` estaba por tanto inflado por
              exactamente un test fantasma; el conteo real de fallas
              pre-implementación era 7. El conteo GREEN previo de
              `46 / 46 tests pasan (33 preexistentes + 13 nuevos)`
              también estaba ligeramente subestimado porque la
              entrada correctiva agrega dos tests nuevos — el pin de
              reactividad y el pin de coherencia sticky (cada uno con
              su propia evidencia RED/GREEN abajo).

            - **Evidencia de TDD estricto (`tests/test_browser_state_keys.py`)**:
              - **RED observado** antes de la implementación
                correctiva: 7 fallas sobre la fuente previa a
                5c.1b-B (el conteo previo de `8` menos la entrada
                fantasma `test_app_shell_index_reexports_version_banner`)
                — `test_page_chrome_mounts_version_banner_without_duplicate_store`,
                `test_detail_panel_renders_with_id_detail_panel`,
                `test_detail_panel_close_uses_data_action_close_detail`,
                `test_detail_panel_close_hides_panel_and_force_search_reopens`,
                `test_detail_panel_renders_detail_header_and_detail_tabs_hooks`,
                `test_globals_css_pins_detail_header_and_detail_tabs_as_sticky`,
                `test_globals_css_minimal_version_banner_style_uses_tokens_only`;
                5 pruebas adicionales se saltan por `VersionBanner.tsx`
                aún no autorado (gate de presencia de archivo) —
                `test_version_banner_preserves_legacy_dom_ids`,
                `test_version_banner_is_mount_gated_and_fetches_health_only_after_mount`,
                `test_version_banner_fails_closed_on_unavailable_or_malformed_health`,
                `test_version_banner_persists_dismiss_via_typed_store`,
                `test_version_banner_does_not_construct_a_second_store`.
                Dos fallas adicionales aparecen SOLO para esta
                entrada correctiva (los nuevos pines de reactividad
                + coherencia):
                `test_version_banner_subscribes_to_dismissal_via_use_sync_external_store`
                (FALLA porque el `VersionBanner` previo lee
                `getVersionBannerDismissed` una vez vía `const
                dismissed = …` en lugar de `useSyncExternalStore`) y
                `test_globals_css_detail_header_height_token_is_single_source_of_truth`
                (FALLA porque el bloque `:root` previo en
                `@layer components` carece de `--detail-header-height`).
                Cada prueba fallada reportó un diff
                esperado-vs-real documentado.
              - **GREEN observado** después de la implementación
                correctiva: **47/47 tests pasan** (33 preexistentes
                + 14 nuevos — los 12 tests originales de 5c.1b-B más
                los 2 pines correctivos: reactividad + coherencia
                sticky). Las sondas de triangulación confirman:
                `VersionBanner.tsx` invoca `useSyncExternalStore`
                con `store ? store.subscribe : () => () =>
                undefined` (subscribe), `() => (store ?
                store.getVersionBannerDismissed() : false)`
                (snapshot), `() => false` (server snapshot); el arg
                de snapshot referencia `getVersionBannerDismissed`;
                el arg de subscribe referencia `store.subscribe`
                (sin `createBrowserStateStore` paralelo); el fetch
                a `/api/health` aún vive dentro de `useEffect` con
                guarda `if (!mounted) return;`; el click de descarte
                se cablea a través de `setVersionBannerDismissed(true)`
                en el MISMO store tipado y el banner se voltea
                apagado en el mismo render vía el re-subscribe de
                `useSyncExternalStore`; `globals.css` declara
                `--detail-header-height: 49px` exactamente una vez
                en `:root` dentro de `@layer components`; TANTO
                `min-height` de `.detail-header` COMO `top` de
                `.detail-tabs` referencian ese único token vía
                `var(--…)` por lo que los dos no pueden derivar
                aparte; todos los colores de `#version-banner` aún
                se enrutan vía tokens (cero literales hex crudos).
                `node_modules/.bin/tsc --noEmit` está limpio para
                `src/`.
              - **Sin paso de REFACTOR** — la correctiva aterrizó
                como un delta mecánico mínimo (un cableado de
                `useSyncExternalStore` en `VersionBanner.tsx`, una
                declaración de token en `:root` + dos referencias
                `var(--…)` en `globals.css`, dos nuevos tests
                herméticos source-contract en
                `tests/test_browser_state_keys.py`, y la corrección
                de lista RED + reconciliación de conteo GREEN en esta
                entrada de apply-progress).
            - **Diferimientos (vinculantes, esta entrada)**:
              - **PR 5c.2 (diferida, sin cambios)** — cableado de research
                / search / folder. Sin cambios en `domain/keys.ts` /
                `infrastructure/store.ts`.
              - **Estado de G4 / G3 Tier-2 / cutover (sin cambios).** G4
                paridad Playwright + Lighthouse permanece **bloqueada**
                (verificador no autordado); G3 Tier-2 permanece con compuerta
                en el cierre de G4 + G6; G6 permanece bloqueada; el cutover
                atómico PR 3e se publica solo cuando G1 + G2 + G3 Tier-1 +
                G3 Tier-2 + G4 + G5 + G6 estén todos verdes.
            - **Alcance de este intento correctivo (vinculante)**: superficies
              de edición permitidas limitadas a
              `src/modules/app-shell/presentation/VersionBanner.tsx`,
                  `src/app/globals.css`, `tests/test_browser_state_keys.py`,
                  y los seis archivos OpenSpec (3 EN + 3 ES). **Sin construcción
                  de store paralelo**, sin cambio de comportamiento de
                  Folder/Search research, sin tests G4, sin captura de browser,
                  sin salidas de build (`out/`), sin commit/push, sin cambios
                  de FastAPI / SQLite / extension. El fixture legacy bajo
                  `tools/g3-legacy-fixture/web/`, el resto de `src/`, `next.config.mjs`,
                  `package.json`, el predecesor OpenSpec tree, el FastAPI
                  `api/server.py`, y la extensión Chrome bajo `extension/**` NO se
                  modifican por este intento. **Sin volteo de puerta, sin autoridad
                  de cutover concedida** — las filas de estado G1 / G2 / G3 Tier-1
                  / G3 Tier-2 / G4 / G6 y las filas de autoridad de cutover de PR
                  3e se preservan verbatim desde la entrada previa del registro
                  de cambios.


            ### 2026-09-07 — PR 5c.2-A: alineación del contrato de motores de búsqueda aterrizada (roster canónico de 14 motores aplicado en ambos espejos; montaje global de FileExplorer + actualizaciones de selectores/arnés + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos)

            - **Alcance (esta entrada)**. PR 5c.2-A es una rebanada de
              contrato de motores de búsqueda dividida desde la fila previa
              `5c.2` diferida: alinea `api/server.py::_SEARCH_ENGINES` y
              `src/data/search-engines.js::SEARCH_ENGINES` al roster
              canónico de 14 motores (google, imagen, documentos, pdf,
              wikipedia, bhl, researchgate, plos, academia, scielo,
              scholar, youtube, zootaxa, scribd) en los mismos campos
              ordenados, eliminando las tres entradas retiradas de
              `general` social/share (`threads_acipenser`,
              `facebook_acipenser_baerii`, `threads_shared_post`) de ambos
              espejos. `tests/test_smoke.py::test_search_engine_contract` se
              extiende (TDD estricto) para fijar el conteo exacto (14) y la
              lista ordenada de llaves además de la verificación de paridad
              key/label/with_authorship existente;
              `tests/test_smoke.py::test_fixed_search_destinations_are_returned_unchanged`
              se retira (sus tres afirmaciones apuntaban a motores que ya no
              están en el roster — el contrato de URL para los 14 motores
preservados ya está cubierto por
              `tests/test_api_freshwater.py::test_searches_urls_are_well_formed` y
              `test_searches_authorship_on_bhl_and_scholar_only`).
              - **Evidencia de TDD estricto (`tests/test_smoke.py::test_search_engine_contract`)**:
                - **RED observado** antes de la implementación: 1 falla
                  sobre la fuente previa a 5c.2-A (espejos de 17 motores) —
                  `test_search_engine_contract` afirmó
                  `len(py_entries) == 14` y reportó
                  `AssertionError: PR 5c.2-A: api/server.py::_SEARCH_ENGINES must
                  hold 14 engines (the canonical 14-engine roster); got 17
                  assert 17 == 14`. La nueva lista pin
                  `_CANONICAL_ENGINE_KEYS` y las afirmaciones de
                  conteo+llaves-ordenadas en ambos espejos fueron
                  simultáneamente la fuente de la falla; la verificación de
                  paridad cross-file debajo de ellas ya pasaba (ambos lados
                  portaban 17 en lock-step), que es exactamente el agujero
                  de deriva en la misma dirección que los nuevos pins están
                  diseñados para cerrar.
                - **GREEN observado** después de la implementación:
                  **7/7 tests de smoke no-DB pasan** (6 preexistentes no-DB
                  + el test de contrato mismo). Las sondas de triangulación
                  confirman: `api/server.py` se parsea limpiamente vía
                  `ast.literal_eval` (la constante extraída por regex es un
                  literal de lista Python válido); `src/data/search-engines.js`
                  se parsea limpiamente vía la misma regex del lado JS
                  usada por AC-21 (`re.findall` devuelve 14 entradas); las
                  14 llaves ordenadas coinciden con `_CANONICAL_ENGINE_KEYS`
                  exactamente en ambos espejos; la verificación de paridad
                  cross-file (key/label/with_authorship en cada par, más la
                  guarda de conteo igual) aún pasa; la re-exportación en
                  `src/modules/research/infrastructure/search-engines.js`
                  aún expone el mismo roster de 14 entradas a los
                  consumidores (sin cambio en consumidores — solo la fuente
                  de verdad se reduce). `tests/test_research_search_tab.py`
                  (16/16 tests de contrato de fuente pasan — SearchTab aún
                  consume `SEARCH_ENGINES` vía el barrel `@taxa/research`;
                  el driver del resolver aún descarta los tokens `{name}` y
                  `{auth}` correctamente sobre los fixtures sobrevivientes
                  `google` / `scholar`).
                - **Sin paso de REFACTOR** — la implementación aterrizó
                  como un delta mecánico mínimo (tres líneas eliminadas de
                  cada espejo + comentarios explicativos al final + la
                  extensión del pin de TDD estricto en
                  `test_search_engine_contract` + retiro de
                  `test_fixed_search_destinations_are_returned_unchanged`).
              - **Diferimientos (vinculantes, esta entrada)**:
                - **Resto de PR 5c.2 (diferida, sin cambios)** — montaje
                  global de FileExplorer, actualizaciones de selectores/
                  arnés e2e en `tests/test_e2e_file_explorer.py` /
                  `tests/test_web_toggle.py`, y borrado legacy
                  `web/*.{html,js,css}` + `tailwind.config.js`. Sin cambios
                  en `domain/keys.ts` / `infrastructure/store.ts`.
                - **Estado de G4 / G3 Tier-2 / cutover (sin cambios).** G4
                  paridad Playwright + Lighthouse permanece **bloqueada**
                  (verificador no autordado); G3 Tier-2 permanece con
                  compuerta en el cierre de G4 + G6; G6 permanece
                  bloqueada; el cutover atómico PR 3e se publica solo
                  cuando G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6
                  estén todos verdes.
- **Alcance de este intento (vinculante)**: superficies de
                edición permitidas limitadas a `api/server.py`,
                `src/data/search-engines.js`, `tests/test_smoke.py`,
                `tests/test_api_freshwater.py`, `tests/test_research_infra.py`,
                y los seis archivos OpenSpec (3 EN + 3 ES).
                `tests/test_api_freshwater.py` y `tests/test_research_infra.py`
                son testigos directos permitidos del roster de 14 y
                fueron actualizados en esta rebanada para mantener el
                conteo, el orden y la cobertura de API. **Sin montaje global de FileExplorer**, sin
                cambio de comportamiento de Folder/Search research, sin
                cambios en `domain/keys.ts` / `infrastructure/store.ts`,
                sin actualizaciones de selectores/arnés e2e, sin
                borrado legacy, sin tests G4, sin captura de browser,
                sin salidas de build (`out/`), sin commit/push, sin
                cambios de dependencias, sin cambios de FastAPI /
                SQLite / extension más allá de las dos constantes de
                espejo mismas. El fixture legacy bajo
                `tools/g3-legacy-fixture/web/`, el resto de `src/`,
                `next.config.mjs`, `package.json`, el predecesor OpenSpec
                tree, y la extensión Chrome bajo `extension/**` NO se
                modifican por este intento. **Sin volteo de puerta, sin
                autoridad de cutover concedida** — las filas de estado
                G1 / G2 / G3 Tier-1 / G3 Tier-2 / G4 / G6 y las filas de
                autoridad de cutover de PR 3e se preservan verbatim desde
                la entrada previa del registro de cambios.

    ### 2026-09-07 — PR 5c.2-B.1a: andamio del arnés React E2E aterrizado (workspace aislado `tools/react-e2e-harness/`; driver de captura + servidores de fixture/export + tests herméticos del arnés + modernización de selectores + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos)

    - **Alcance (esta entrada)**. PR 5c.2-B.1a aterriza un **workspace privado aislado** en `tools/react-e2e-harness/` (sin superficie de edición en `src/`, sin cambios de API/FastAPI/SQLite/extension, sin cambios en `domain/keys.ts` / `infrastructure/store.ts`, sin cambios en `next.config.mjs` / `package.json` de producción, sin captura G4, sin borrado legacy). Pins: Next 16.3.3, React 19.2.8, ReactDOM 19.2.8, `@playwright/test` 1.56.0, Node ≥ 20.9.0. `npm install` genera `tools/react-e2e-harness/package-lock.json` — la **excepción de tamaño de lockfile generado aprobada por el usuario** solo para este workspace aislado (fuente/docs authored ≤ 400 líneas de diff; total authored = 245 LoC entre `package.json` + `next.config.mjs` + `tsconfig.json` + `app/layout.tsx` + `app/page.tsx`). `next.config.mjs` refleja los flags de exportación estática G2 (`output: "export"`, `images.unoptimized: true`, `trailingSlash: false`, `reactStrictMode: true`); `app/layout.tsx` es un título semántico mínimo del arnés (sin réplica de AppShell / chrome, sin `import "./globals.css"`, sin preload de Raleway); `app/page.tsx` monta `FileExplorer` directamente desde `@taxa/research` contra un id de taxon sintético no nulo (`1`) y un `baseUrl` leído desde `NEXT_PUBLIC_HARNESS_BASE_URL` (default `http://127.0.0.1:8765`); `tsconfig.json` declara aliases de path `@taxa/*` seguros que resuelven a `../../src/modules/*/index.ts` (sin reexportación de barrel).
      - **TDD estricto**: sin superficie de test en esta sub-rebanada. **RED** = verificación negativa de contrato de fuente pre-build (`test ! -e tools/react-e2e-harness/app/page.tsx`) PASÓ sobre la fuente previa a `5c.2-B.1a` (arnés ausente). **GREEN** = `npm ci` exit `0` (32 paquetes) + `npm run build` exit `0` (Next 16.3.3 + Turbopack, ~230ms compile, ~670ms TypeScript, 3 páginas estáticas). `out/index.html` (6247 bytes) contiene `<title>Taxa React E2E Harness — FileExplorer mount</title>`, `data-harness-root="react-e2e"`, `data-harness-surface="file-explorer"`, `data-harness-taxon-id="1"`, y el montaje vivo de `FileExplorer` renderizando `data-explorer="loading"` con `aria-busy="true"`. Triangulación: los 4 flags G2 exportados verbatim; `package.json` fija versiones exactas (`next@16.3.3`, `react@19.2.8`, `react-dom@19.2.8`, `@playwright/test@1.56.0`, `engines.node >=20.9.0`); cada alias `@taxa/*` resuelve a `../../src/modules/*/index.ts`; `app/page.tsx` NO importa AppShell / BrowserSurface / `./globals.css` / la página de producción; `app/layout.tsx` carga un título de arnés distinto del `<title>` de producción. **Sin REFACTOR** (andamio mecánico, REFACTOR N/A).
      - **Diferimientos (vinculantes)**: driver de captura + servidores de fixture/export + tests herméticos del arnés + modernización de selectores e2e sobre el nuevo árbol de componentes + borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`. Sin cambios en `src/` de producción; sin cambios en `domain/keys.ts` / `infrastructure/store.ts`; sin captura G4 autordada.
      - **Estado de G4 / G3 Tier-2 / cutover (sin cambios)**: G4 paridad Playwright + Lighthouse permanece **bloqueada** (verificador no autordado); G3 Tier-2 permanece con compuerta en el cierre de G4 + G6; G6 permanece bloqueada; PR 3e se publica solo cuando G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6 estén todos verdes. **El aterrizaje del andamio NO voltea G4** — solo workspace + green-path de exportación estática.
    - **Alcance de este intento (vinculante)**: superficies de edición permitidas limitadas a `tools/react-e2e-harness/{package.json, package-lock.json, next.config.mjs, tsconfig.json, app/layout.tsx, app/page.tsx}` (workspace aislado del arnés) y 6 archivos OpenSpec (3 EN + 3 ES). `package-lock.json` = lockfile generado (excepción de tamaño aprobada por el usuario para este workspace aislado solo, 1142 LoC, sin líneas autordadas a mano); restante authored fuente/docs = 245 LoC. Sin montaje global de FileExplorer en la app de producción, sin cambio de comportamiento de Folder/Search research, sin cambios en `domain/keys.ts` / `infrastructure/store.ts`, sin actualizaciones de selectores e2e, sin borrado legacy, sin tests G4, sin captura de browser, sin salidas de build `out/` de producción, sin commit/push, sin cambios de dependencias, sin cambios de FastAPI/SQLite/extension, sin cambios en `next.config.mjs` / `package.json` de producción, sin cambios en `src/` de producción, sin captura G4 bajo `tools/g4-capture/**`, sin fixture legacy G3 bajo `tools/g3-legacy-fixture/**`, sin cambios en G2 candidate / static-export probe. **Sin volteo de puerta, sin autoridad de cutover concedida** — las filas de estado G1 / G2 / G3 Tier-1 / G3 Tier-2 / G4 / G5 / G6 y las filas de autoridad de cutover de PR 3e se preservan verbatim desde la entrada previa del registro de cambios.

### 2026-09-09 — PR 5.5: reparación de pipeline Tailwind 4 / PostCSS aterrizada (mitad-de-pipeline-de-build del hueco de evidencia de candidato-de-producción G2 cerrada; la cadena se expande de 16 hijos a 17 hijos; la cuarta `size:exception` aprobada por el usuario para el `package-lock.json` regenerado junto a PR 3a + PR 3c-ii + PR 3c-iii; el PR está implementado en este worktree pero NO se reclama como fusionado, NO se reclama como G2-PASS, y NO se reclama como verificado-en-navegador por esta entrada) (solo anexo)

- **Defecto confirmado (causa raíz + firma observable a nivel de artefacto, registrada contra el commit base `6375927` pre-PR-5.5 de este worktree)**. PR 3c-i envió `src/app/globals.css` con la superficie canónica de Tailwind 4 — `@import "tailwindcss";` seguido de un bloque `@theme { --primary: #1d7ea9; --accent: #176587; --surface: #ffffff; … --realm-bacteria: #5ebd9b; … }` que carga cada token legacy `:root` / `[data-theme="dark"]` / `--realm-*`. PR 3c-ii, PR 3c-iii y el bootstrap de toolchain previo PR 3a consumieron esa superficie bajo el supuesto de que el pipeline PostCSS por defecto de `next build` procesaría `@import "tailwindcss"` y expandiría el bloque `@theme { … }`. **El supuesto era incorrecto**: PR 3a añadió `tailwindcss@^4` como dependencia top-level, pero el proyecto nunca registró un plugin de PostCSS para él (sin `postcss.config.mjs` en la raíz del repo, sin dependencia `@tailwindcss/postcss`). El pipeline PostCSS por defecto de Turbopack NO reconoce `@import "tailwindcss";` como directiva de Tailwind 4 y NO reconoce `@theme { … }` como regla CSS — el build emite una warning no fatal `Unknown at rule: @theme`, deja el bloque `@theme { … }` como regla literal en el CSS compilado (el navegador lo descarta silenciosamente porque `@theme` no es una regla CSS real), y envía cero preflight de Tailwind + cero tokens `:root` expandidos por `@tailwindcss/postcss`. **Consecuencia observada (base pre-PR-5.5, capturada en este worktree)**: `next build` sale con `0`, los selectores legacy `.research-explorer` / `.fex-row` / `.tree-row` / `.tier-header` / `.load-all` / `.kebab` / `.search-tab` / `.folder-tab` / `.header-browser-tab` / `.fex-meta-strip` / `.fex-tab-strip` / `.fex-snippet-frame` / `.fex-csv-table` / `.fex-json-tree` / `.fex-tree-leaf` se envían, pero **cada referencia `var(--primary)` / `var(--accent)` / `var(--surface)` / `var(--on-surface)` / `var(--realm-bacteria)` / `var(--realm-archaea)` / `var(--realm-viruses)` / `var(--realm-animalia)` / `var(--realm-fungi)` / `var(--realm-plantae)` / `var(--realm-chromista)` / `var(--realm-other)` dentro de esos selectores resuelve a `unset` en tiempo de ejecución** — la cascada visual completa está rota. El bundle CSS compilado en `out/_next/static/chunks/391guka-hdllv.css` encoge de **50.891 bytes** (con `@tailwindcss/postcss` corriendo) a **35.093 bytes** (sin él) — un encogimiento de ~31% que es la huella a nivel de bytes del defecto.
- **Alcance (esta entrada)**. PR 5.5 aterriza la **reparación de pipeline de build de Tailwind 4 / PostCSS** en la raíz del repo solamente (sin edición de contenido de `src/`, sin toque del legacy `web/**`, sin cambio de barrel de `src/modules/**`, sin cambio de `next.config.mjs`, sin cambio de `tsconfig.json`, sin cambio de `Makefile`, sin cambio de `scripts/check-runtime.mjs`, sin cambio de `api/server.py`, sin cambio de FastAPI/SQLite/extension, sin cambio de `domain/keys.ts` / `infrastructure/store.ts`, sin captura G4, sin borrado del legacy `web/*.{html,js,css}` + `tailwind.config.js` — esos aterrizan con PR 5c). Superficie de edición: (1) `package.json` añade dos nuevas entradas top-level en `dependencies`: `"@tailwindcss/postcss": "^4.3.3"` y `"postcss": "^8.5.0"`. Los plugins de la era Tailwind 3 (`autoprefixer`, `@tailwindcss/forms`) permanecen prohibidos. (2) Archivo nuevo `postcss.config.mjs` en la raíz del repo, `export default { plugins: { "@tailwindcss/postcss": {} } }`. (3) `package-lock.json` regenerado — la **cuarta `size:exception` de lockfile generado aprobada por el usuario** para este proyecto (junto a las excepciones existentes de PR 3a + PR 3c-ii + PR 3c-iii). (4) `tests/test_toolchain_bootstrap.py` se actualiza: `REQUIRED_DEPS_PRODUCTION` se expande para incluir `postcss` + `@tailwindcss/postcss`; `FORBIDDEN_LEGACY_DEPS` se reduce a `("autoprefixer", "@tailwindcss/forms")` (la prohibición de la era Tailwind 3 permanece abierta; `postcss` ahora es requerida, no prohibida). (5) Nueva superficie de test `tests/test_tailwind_build_pipeline.py` — test de regresión enfocado que realiza un `next build` REAL contra el repo, lee el bundle CSS compilado bajo `out/_next/static/{css,chunks}/*.css`, y afirma sobre el artefacto: `next build` sale con `0`; al menos un bundle CSS existe; el preflight de Tailwind 4 está presente (testigo canónico de que `@tailwindcss/postcss` corrió); la regla literal `@theme {` NO está presente (un `@theme {` literal sobreviviente es la firma del defecto); el substring literal `@import "tailwindcss"` NO está presente; cada bundle CSS contiene el preflight (sin filtración de subset); el token legacy `:root` `--primary: #1d7ea9` vive dentro de una declaración `@layer theme { :root, :host { … } }`. La fixture limpia `out/` y `.next/` en teardown SI no existían antes de que el test entrara.
  - **Strict-TDD**: **RED** = pre-implementación, 7 casos en el archivo de test nuevo + 2 nuevos casos de dep en el test de toolchain FALLAN con la base post-3c-iii — `tests/test_tailwind_build_pipeline.py::test_next_build_emits_css_bundle_under_out_static` y 5 tests hermanos ERRORean con `postcss.config.mjs missing at … PR 5.5 ships @tailwindcss/postcss as the registered plugin`; `tests/test_tailwind_build_pipeline.py::test_triangulate_postcss_config_registers_tailwind_plugin_only` FALLA con `postcss.config.mjs missing at …`; `tests/test_toolchain_bootstrap.py::test_required_dep_present_in_dependencies[postcss-None]` FALLA con `production dep 'postcss' missing from dependencies`; `tests/test_toolchain_bootstrap.py::test_required_dep_present_in_dependencies[@tailwindcss/postcss-None]` FALLA con `production dep '@tailwindcss/postcss' missing from dependencies`. **GREEN** = tras añadir las dos deps a `package.json`, crear `postcss.config.mjs`, y correr `npm install` para regenerar `package-lock.json`, el archivo completo de test de toolchain pasa (`30 passed in 0.02s`) y el archivo completo de test de build-pipeline pasa (`7 passed in 3.83s`); repetibilidad confirmada por una segunda corrida consecutiva (`7 passed in 3.83s`) sin flakiness; el bundle CSS compilado es byte-idéntico entre las dos corridas (`50.891 bytes`, hash-estable bajo el pipeline chunked de Turbopack). **TRIANGULATE** = el par de tests cubre el lado de dep de `package.json` (test de toolchain) Y el lado de config de `postcss.config.mjs` (test de build-pipeline) Y el lado de artefacto de CSS compilado (preflight de Tailwind + ausencia de regla `@theme` + ausencia de `@import "tailwindcss"` + expansión de token de theme en `:root, :host`). **Sin paso de REFACTOR** — la implementación aterrizó como un delta mecánico mínimo (dos nuevas deps en `package.json` + `postcss.config.mjs` mínimo + lockfile regenerado + actualización mínima del test de toolchain + nuevo test de build-pipeline).
  - **Prueba de arreglo del defecto visual a nivel de artefacto (post-PR-5.5 en este worktree)**: un `node node_modules/.bin/next build` limpio produce `out/_next/static/chunks/391guka-hdllv.css` (50.891 bytes) que contiene 204 ocurrencias de `--tw-`, 1 ocurrencia de `@keyframes spin`, 1 ocurrencia de `.animate-spin`, 1 ocurrencia de `@layer theme { :root, :host { … --primary: #1d7ea9; … } }`, 5 ocurrencias de `#1d7ea9`, cero ocurrencias de la regla literal `@theme {`, y cero ocurrencias del substring literal `@import "tailwindcss"`. `node scripts/check-runtime.mjs` sale con `0`. `npm ci` reproduce una instalación de 121 paquetes con las mismas 18 entradas de lockfile tailwind/postcss en un clone fresco.
- **Implicaciones de topología / conteo (precisas, solo anexo)**. La cadena se expande de **16 hijos a 17 hijos**. El nuevo hijo de reparación se llama **PR 5.5 (reparación de pipeline Tailwind 4 / PostCSS)** y se ubica en la **posición 5.5/17** — interpolado entre la **posición 5/17 (PR 3c-iii)** y la **posición 7/17 (PR 3c-iv)**. Cada hijo que estaba previamente en la posición `n/16` (para `n ∈ {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}`) se renumera a `n+1/17`. PR 3a permanece en `1/17`, PR 3b permanece en `2/17`, PR 3c-i permanece en `3/17`, PR 3c-ii permanece en `4/17`, PR 3c-iii permanece en `5/17`. El alcance de cada sub-PR, el mapeo de ramas predecesor / sucesor, el orden corregido, el bloqueo del Enfoque A, la base de FastAPI/SQLite, la estrategia de Feature Branch Chain, el estado congelado del predecesor, las specs por dominio, cada addendum previo, y el protocolo G5 de reemplazo aprobado por el usuario quedan sin cambios en su contenido sustantivo; solo sus etiquetas de posición se desplazan arriba por 1 (o permanecen donde estaban si estaban antes de la posición 5). **Posición de dependencia de PR 5.5**: depende de **PR 3c-iii**; **NO depende de PR 3c-iv**. El nuevo hijo de reparación es auto-contenido: no toca el contenido de `src/app/globals.css`, no toca `tsconfig.json`, no toca `.nvmrc`, no toca `scripts/check-runtime.mjs`, no toca el Makefile, no toca `next.config.mjs`, no toca `api/server.py`, no toca ningún barrel de `src/modules/**`, no toca `web/**`, no toca `extension/**`, y no borra `web/*.{html,js,css}` ni `tailwind.config.js`. **Presupuesto de LoC**: el diff authored de PR 5.5 está bien por debajo del presupuesto de 400 líneas (≈ 259 LoC authored en total, ≤ 400 con −141 LoC de holgura). **La cadena de 17 hijos se preserva**.
- **La cuarta `size:exception` aprobada por el usuario para el `package-lock.json` regenerado**. El `package-lock.json` regenerado añade 16 nuevas entradas de lockfile relacionadas con tailwind/postcss (del total de 18 entradas de lockfile relacionadas con tailwind/postcss en el lockfile post-fix; `tailwindcss` en sí precede a esta reparación porque PR 3a lo añadió) llevando el objeto `packages` total a **121 paquetes** y el conteo de líneas del lockfile a **2.112 líneas**. El cambio del lockfile es **generated-resolution-only**; se revisa junto con `package.json`; no carga churn de lockfile no relacionado. Las dos nuevas entradas de `package.json` están pineadas con caret (`^4.3.3` para `@tailwindcss/postcss`, `^8.5.0` para `postcss`) así que el delta del lockfile es determinista bajo re-`npm install`. **Justificación de autorización** (por qué se prefiere un único PR revisable sobre fraccionar `postcss.config.mjs` lejos del cambio de dep + lockfile): (a) el registro del plugin PostCSS, las dos nuevas deps top-level, y el lockfile regenerado son inseparables — sin `@tailwindcss/postcss` instalado, `postcss.config.mjs` no puede registrarlo; sin `postcss` como dep peer, `@tailwindcss/postcss` no puede correr; sin el lockfile regenerado, `npm ci` no reproducirá la instalación en un clone fresco; (b) el test de regresión de build-pipeline es inseparable del arreglo (lee la salida CSS compilada que el arreglo produce); (c) fraccionar PR 5.5 aún más en un par 5.5-a / 5.5-b dejaría un pipeline de build medio roto que nadie puede revisar coherentemente; (d) el diff authored de PR 5.5 es ~259 LoC (bien por debajo del presupuesto de 400 líneas) así que no se necesita ninguna excepción adicional de LoC authored.
- **Hueco de evidencia de candidato-de-producción G2 (esta entrada expone un hueco que la cadena previa dejó abierto; PR 5.5 cierra un testigo pero NO flipea G2; G2 permanece pendiente de la captura completa de Fase 6)**. La cadena previa registró G2 como **PASS** trasladada del predecesor contra el **workspace aislado `tools/g2-candidate/`**. **Ese PASS de G2 NO se traslada al repo de producción**, porque el `src/app/globals.css` del repo de producción envía la superficie canónica `@import "tailwindcss";` + `@theme { … }` que el plugin `@tailwindcss/postcss` debe procesar, y la cadena previa nunca registró ese plugin. Concretamente: un `next build` limpio contra el repo pre-PR-5.5 produce un `out/_next/static/chunks/391guka-hdllv.css` de **35.093 bytes** con el bloque `@theme { … }` como regla literal y cero preflight de Tailwind — el artefacto que el mount `StaticFiles` de FastAPI sirve en `127.0.0.1:8765/_next/static/chunks/391guka-hdllv.css` es la evidencia de candidato-de-producción G2; esa evidencia estaba ROTA antes de PR 5.5 y ahora está COMPLETA tras PR 5.5 (el bundle es **50.891 bytes** con el bloque `@theme` expandido a `@layer theme { :root, :host { … } }` y el preflight de Tailwind presente). **PR 5.5 cierra la mitad-de-pipeline-de-build del hueco de evidencia de candidato-de-producción G2** añadiendo el test de regresión a nivel de artefacto `tests/test_tailwind_build_pipeline.py`; la mitad-de-navegador del hueco de G2 permanece diferida al trabajo de validación de Fase 6a. **G2 candidato-de-producción permanece PASS-pending-Phase-6-capture, NO flipeado por PR 5.5 solo**.
- **G4 / G3 Tier-2 / cutover (sin cambios)**. G4 Playwright + Lighthouse parity permanece **bloqueado**; G3 Tier-2 permanece gated en G4 + G6; G6 permanece bloqueado; el PR 3e de cutover atómico se envía solo cuando G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6 estén todos verdes. **PR 5.5 NO flipea G4** — solo la mitad-de-pipeline-de-build del hueco de evidencia de candidato-de-producción G2 queda cerrada.
- **Diferimientos (vinculantes, esta entrada)**. Captura G2 de runtime-de-navegador (Chromium / Playwright contra `127.0.0.1:8765`); trabajo de validación de Fase 6a; autor de captura de paridad G4; PR 3c-iv (animaciones / utilities + barrel del design-system); PR 3d (Makefile/mount); PR 4a + 4b (browser-state + hydration guard); PR 5a + 5b + 5c (puertos de taxonomía + research + e2e + borrado legacy); Fase 6a/b/c; cutover PR 3e. Sin mount global de FileExplorer, sin cambio de comportamiento de Folder/Search research, sin cambio de `domain/keys.ts` / `infrastructure/store.ts`, sin actualizaciones de selectores e2e, sin borrado legacy (`web/*.{html,js,css}` + `tailwind.config.js` diferido a PR 5c), sin tests G4, sin captura de navegador, sin salidas de build (`out/`), sin commit/push, sin cambios de FastAPI/SQLite/extension, sin cambio de contenido de `src/` de producción, sin cambio de `next.config.mjs`, sin cambio de `tsconfig.json`, sin cambio de `Makefile`, sin cambio de `scripts/check-runtime.mjs`, sin cambio de `api/server.py`, sin cambio de `web/**`, sin cambio de `extension/**`.
- **Alcance de este intento (vinculante)**: superficies de edición permitidas limitadas a `package.json`, `package-lock.json`, `postcss.config.mjs` (nuevo), `tests/test_toolchain_bootstrap.py`, `tests/test_tailwind_build_pipeline.py` (nuevo), y los seis archivos OpenSpec (3 EN + 3 ES). `package-lock.json` = lockfile regenerado (`size:exception` aprobada por el usuario, 2.112 LoC, sin líneas authored a mano); el resto de authored source/tests = ~259 LoC, ≤ 400 presupuesto. **Sin flipeo de compuerta, sin autoridad de cutover otorgada** — las filas de estado de G1 / G2 / G3 Tier-1 / G3 Tier-2 / G4 / G5 / G6 y las filas de autoridad de cutover de PR 3e se preservan verbatim de la entrada de change-log previa. **Sin apertura de PR, sin commit/push, sin habilitación de `gentle-ai review mode`** — revisión / CI / merge siguen el proceso ordinario de feature-branch-chain una vez que la tarea padre autorizada-por-el-usuario complete. **Espejo en inglés** (`openspec/changes/complete-taxa-frontend-migration/apply-progress.md`) carga la misma semántica; cualquier deriva se resuelve a favor del inglés.

### 2026-09-09 — PR 5.6: DOM↔CSS structural parity repair landed (CSS-only repair for the React-emitted taxonomy / detail structural hooks; chain expands from 17 children to 18 children; the fifth user-approved size:exception; the PR is implemented in this worktree but is NOT claimed merged, NOT claimed G2-PASS, and NOT claimed browser-verified by this entry) (append-only)

- **Confirmed defect (root cause + observable signature at artifact level, recorded against the post-PR-5.5 base commit `1576697` of this worktree)**. PR 5a.2 + PR 5a.3 + PR 5a.4 + PR 5b.4 + PR 5c.1b-B all emitted the React `<Tree>` / `<Breadcrumb>` / `<DetailPanel>` / `<OverviewTab>` / `<TabStrip>` / `<Kebab>` components with the canonical structural classNames (`.taxa-tree` / `.tree-row` + `[data-selected]` / `.tab-strip` / `.tab-button` / `.overview-tab` / `.breadcrumb` + `.breadcrumb-segment` + `.breadcrumb-link` / `.detail-panel` + `.detail-body` + `.detail-close` / `.species-count` / `.authorship` / `.materialize-indicator` / `button[data-action="toggle-kebab"]`), but `src/app/globals.css` only carried the legacy `@layer base` taxonomy selectors (which used dead `data-realm` / `.selected` / `.kebab-trigger` className selectors that the React components never emit) + the kebab base selectors in `@layer components` (`.kebab` + `.kebab-menu` + `.kebab-menu.open` only). The DOM↔CSS gap is a CLASS-NAME MISMATCH — the React components emit the new classNames, the CSS carries the legacy classNames, and the visual cascade is silent. The compiled CSS bundle at `out/_next/static/chunks/2c4tn6w2gxss3.css` (Turbopack's chunked pipeline hash; this is the only CSS bundle `next build` emits for this repo, **55,133 bytes** post-PR-5.5 / pre-PR-5.6) contains the legacy `.taxa-tree` / `.tree-row` / `.tab-strip` / `.tab-button` / `.overview-tab` / `.breadcrumb` / `.species-count` / `.authorship` / `.materialize-indicator` selectors (because they were already in `@layer base` since PR 3c-ii / PR 3c-iii), but they painted NOTHING because the React `<Tree>` / `<Breadcrumb>` / `<DetailPanel>` / `<OverviewTab>` / `<TabStrip>` components emit DIFFERENT selectors.
- **Scope (this entry)**. PR 5.6 lands the **DOM↔CSS structural parity repair** in `src/app/globals.css` + `tests/test_tailwind_4_parity.py` only (no React source edit, no dependency change, no `next.config.mjs` change, no `tsconfig.json` change, no `Makefile` change, no `scripts/check-runtime.mjs` change, no `api/server.py` change, no `package.json` / `package-lock.json` / `postcss.config.mjs` change, no FastAPI/SQLite/extension change, no `domain/keys.ts` / `infrastructure/store.ts` change, no G4 capture, no `web/*.{html,js,css}` + `tailwind.config.js` legacy deletion — those land with PR 5c). Edit surface: (1) `src/app/globals.css` adds the 15 React-emitted structural hook rules + the 9 state selector rules + the 2 collapsed descendant rules (`.kebab > .kebab-menu` + `.tab-strip > .tab-button` per the 3c-b.4 refactor contract) + the 1 kebab selector bridge (`.kebab > button[data-action="toggle-kebab"]`) + the 5 visible-state / chainable / scrollable triangulation declarations; moves `.scientific-name` + `.scientific-name--roman` from `@layer base` to `@layer components`; removes the stale/dead CSS selectors (legacy `.tree-row[data-realm="..."] .scientific-name` realm-tinted rules + dead `.tree-row:hover/selected/focus-within .kebab-trigger` + `.kebab-trigger:hover` + `.kebab-trigger:focus-visible` rules + `.detail-item .authorship` descendant rule); replaces the `.kebab-trigger:focus-visible` global focus-visible selector in `@layer base` with `.kebab > button[data-action="toggle-kebab"]:focus-visible` (the new CSS-only contract for the React <Kebab> trigger). (2) `tests/test_tailwind_4_parity.py` adds the `## 5.6` section with 37 new test cases (15 React-emitted structural hook presence tests + 2 scientific-name hook tests + 9 state selector presence tests + 2 dead-selector resolution tests + 2 collapsed descendant refactor tests + 5 triangulation visible-state tests + 2 slice-scope guards); repurposes the 3 pre-existing PR 3c-ii realm-tinted tests to assert the dead-code absence (the rules are removed from the source CSS as part of the safe resolution per the user's directive); updates `TAXONOMY_SELECTORS` to remove `.scientific-name` + `.scientific-name--roman` (they move to `@layer components`) and `.kebab-trigger` (the className is dead code; the React <Kebab> trigger rides the new `.kebab > button[data-action="toggle-kebab"]` selector bridge).
  - **Strict-TDD**: **RED** = pre-implementation, 35 of 37 new PR 5.6 test cases FAIL on the post-5.5 base — `tests/test_tailwind_4_parity.py::test_5_6_react_hook_resolves_under_layer_components` fails for all 15 selector parameters (the React-emitted structural hooks are absent from `@layer components`), `tests/test_tailwind_4_parity.py::test_5_6_scientific_name_resolves_under_layer_components` fails for both selector parameters (the scientific-name rules are still in `@layer base`), `tests/test_tailwind_4_parity.py::test_5_6_state_selector_resolves_under_layer_components` fails for all 9 state selectors, `tests/test_tailwind_4_parity.py::test_5_6_taxonomic_realm_rules_are_resolved_safely` FAILS, `tests/test_tailwind_4_parity.py::test_5_6_kebab_trigger_classname_is_resolved_safely` FAILS, `tests/test_tailwind_4_parity.py::test_5_6_kebab_and_kebab_menu_collapse_into_descendant_rule` FAILS, `tests/test_tailwind_4_parity.py::test_5_6_tab_strip_and_tab_button_collapse_into_descendant_rule` FAILS, `tests/test_tailwind_4_parity.py::test_5_6_tree_row_data_selected_true_has_visible_state_change` FAILS, `tests/test_tailwind_4_parity.py::test_5_6_tab_button_active_state_has_visible_state_change` FAILS, `tests/test_tailwind_4_parity.py::test_5_6_breadcrumb_segment_is_chainable` FAILS, `tests/test_tailwind_4_parity.py::test_5_6_detail_body_is_scrollable_container` FAILS, `tests/test_tailwind_4_parity.py::test_5_6_kebab_selector_bridge_targets_button_data_action` FAILS. The 2 scope guards (`test_5_6_does_not_introduce_at_rules_outside_layer_declarations` + `test_5_6_keeps_color_mix_scoped_to_research_explorer`) pass because they assert absence of new at-rules / colour-mix drift. **GREEN** = after the CSS-only repair, all 37 PR 5.6 test cases pass (`37 passed in 0.08s`); the full `tests/test_tailwind_4_parity.py` + `tests/test_taxonomy_overview_styles.py` suite passes (`348 passed in 0.55s`); the compiled CSS bundle is byte-equal between two consecutive runs; the build pipeline stays green (`node node_modules/.bin/next build` exit 0, `node scripts/check-runtime.mjs` exit 0). **TRIANGULATE** = the test pair covers BOTH the source-side contract (every React-emitted hook + state selector + descendant collapse + dead-selector resolution has its own parametrized test case that fails before the repair and passes after) AND the visible-state invariants (the triangulation tests assert non-empty + visible-state-property declarations on the active-row + active-tab + breadcrumb-segment + detail-body + kebab-selector-bridge rules, so a future regression that drops the styling back to a default that hides the active state would still trip the contract). **No REFACTOR step** — the implementation landed as a minimal mechanical delta (the CSS-only repair + the parity test extension + the dead-selector resolution repurpose); REFACTOR N/A.
  - **Visual-defect fix proof at artifact level (post-PR-5.6 in this worktree)**: a clean `node node_modules/.bin/next build` produces `out/_next/static/chunks/2c4tn6w2gxss3.css` that contains the new structural selectors: `.taxa-tree { ... }` + `.tree-row { ... }` + `.tree-row[data-selected="true"] { ... }` + `.breadcrumb { ... }` (with `font-family: "JetBrains Mono", monospace` per the binding design contract) + `.tab-strip > .tab-button.active { ... }` + `.detail-panel .detail-body { ... }` (with `overflow-y: auto` + `max-height: calc(90vh - 120px)`) + `.kebab > button[data-action="toggle-kebab"] { ... }` (the CSS-only bridge) + the `.tree-row:hover` / `.tree-row:focus-visible` / `.tab-strip > .tab-button:hover` / `.tab-strip > .tab-button:focus-visible` state selectors. The rule shapes survive the Turbopack minification intact (verified by grepping the compiled CSS bundle for each selector shape).
- **Topology / count implications (accurate, append-only)**. The chain expands from **17 children to 18 children**. The new repair child is named **PR 5.6 (DOM↔CSS structural parity repair)** and sits at **position 5.6/18** — interpolated between **position 5.5/18 (PR 5.5, Tailwind 4 / PostCSS pipeline repair)** and the former 3c-iv (renumbered to **position 8/18 (PR 3c-iv, animations / utilities + final CSS parity + design-system barrel)**). Every child that was previously at position `n/17` (for `n ∈ {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17}`) is renumbered to `n+1/18` (so `7/17 → 8/18` PR 3c-iv; `8/17 → 9/18` PR 3d; `9/17 → 10/18` PR 4a; `10/17 → 11/18` PR 4b; `11/17 → 12/18` PR 5a; `12/17 → 13/18` PR 5b; `13/17 → 14/18` PR 5c; `14/17 → 15/18` PR 6a; `15/17 → 16/18` PR 6b; `16/17 → 17/18` PR 6c; `17/17 → 18/18` PR 3e). PR 3a stays at `1/18`, PR 3b stays at `2/18`, PR 3c-i stays at `3/18`, PR 3c-ii stays at `4/18`, PR 3c-iii stays at `5/18`, PR 5.5 stays at `5.5/18`. The sub-PR scope, the predecessor / successor branch mapping, the corrected ordering, the Approach A lock, the FastAPI/SQLite foundation, the Feature Branch Chain strategy, the predecessor frozen status, the per-domain specs, every prior addendum (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c, 3c-ii, 3c-iii, 5.5), and the user-approved replacement G5 protocol are unchanged in their substantive content; only their position labels shift up by 1 (or stay where they are if they were before position 5.5). PR 5.6's **dependency position**: depends on **PR 5.5** (the `@tailwindcss/postcss` expansion is in place so the CSS-only repair's new selectors expand correctly into the compiled CSS bundle) AND on **PR 5a + PR 5b** (the React `<Tree>` / `<Breadcrumb>` / `<DetailPanel>` / `<OverviewTab>` / `<TabStrip>` / `<Kebab>` components are in place so the React-emitted classNames the CSS rules target exist in the DOM); **does NOT depend on PR 3c-iv** (the `@keyframes` + utilities + design-system barrel are not yet shipped, but the CSS-only structural repair does not need them). The new repair child is self-contained: it does not touch `package.json` / `package-lock.json` / `postcss.config.mjs` / `tsconfig.json` / `.nvmrc` / `scripts/check-runtime.mjs` / `Makefile` / `next.config.mjs` / `api/server.py` / any `src/modules/**` barrel / `web/**` (the legacy vanilla bundle) / `extension/**`; the only `src/` file PR 5.6 edits is `src/app/globals.css` (CSS-only repair); the only test file PR 5.6 edits is `tests/test_tailwind_4_parity.py` (parity test extension + dead-selector resolution repurpose). **LoC budget**: PR 5.6's authored diff is **491 insertions and 64 deletions in `src/app/globals.css` (net +427) + 539 insertions and 53 deletions in `tests/test_tailwind_4_parity.py` (net +486) — total authored LoC delta ≈ 1,147 across the two files**. The CSS-only repair alone was estimated at `~120 LoC` in the prior addenda; the actual overshoot is `+1,027 LoC` against the 400-line budget. The **fifth user-approved size:exception** is the only size:exception PR 5.6 opens — see the size:exception paragraph below. **The 18-child chain is preserved** (the chain grew by exactly one child, in the only safe insertion point: between PR 5.5's `package.json` + `postcss.config.mjs` repair and the former 3c-iv's `@keyframes` + utilities + design-system barrel slice — both of which sit downstream of the CSS-only DOM↔CSS parity repair that PR 5.6 provides).
- **The fifth user-approved size:exception for the CSS-only repair authored-LoC delta (this entry, opens a fifth size:exception alongside the existing PR 3a + PR 3c-ii + PR 3c-iii + PR 5.5 exceptions; PR 3a is a generated-resolution-only lockfile exception and stays open; PR 3c-ii is an authored-LoC exception for the taxonomy-tree CSS slice and stays open; PR 3c-iii is an authored-LoC exception for the Search/Folder/global Browser CSS slice and stays open; PR 5.5 is a generated-resolution-only lockfile exception and stays open; the present PR 5.6 exception is an authored-LoC exception for the CSS-only DOM↔CSS structural parity repair)**: the actual implementation required **491 insertions and 64 deletions in `src/app/globals.css` (net +427) + 539 insertions and 53 deletions in `tests/test_tailwind_4_parity.py` (net +486) — total authored LoC delta ≈ 1,147 across the two files**, against the prior `~120 LoC` estimate for the CSS-only repair alone. The implementation overshoots the 400-line per-PR review budget that Approach A locked on 2026-09-02 by **+747 LoC** and the prior `~120 LoC` estimate by **+1,027 LoC**. The contributor breakdown: (a) the 15 React-emitted structural hook rules + the 9 state selector rules + the 2 collapsed descendant rules + the 1 kebab selector bridge + the 7 visible-state / chainable / scrollable triangulation declarations together account for the bulk of the `src/app/globals.css` LoC (the rules are inherently larger than the legacy `@layer base` rules because the React surface adds `:hover` + `:focus-visible` + `[data-selected="true"]` + `.active` + `[data-tab="..."]` + `[data-action="toggle-kebab"]` state selectors per hook); (b) the 37 new PR 5.6 test cases + the 3 repurpose docstring updates + the 2 `TAXONOMY_SELECTORS` updates together account for the bulk of the `tests/test_tailwind_4_parity.py` LoC (the parametrized selector catalogue is the dominant contributor, mirroring the PR 3c-ii / PR 3c-iii pattern). **Authorization rationale** (why a single reviewable PR is preferred over further slicing): (a) the 15 React-emitted structural hooks + the 9 state selectors + the 2 collapsed descendant rules + the 1 kebab selector bridge + the 5 visible-state / chainable / scrollable triangulation declarations are INSEPARABLE from the 3 React components they target — the `.taxa-tree` + `.tree-row` + `[data-selected="true"]` selectors only make sense together (the React `<Tree>` emits them as a unit), the `.tab-strip > .tab-button` + `.active` + `[data-tab="..."]` selectors only make sense together (the React `<TabStrip>` emits them as a unit), and the `.kebab` + `.kebab > button[data-action="toggle-kebab"]` + `.kebab > .kebab-menu` + `.kebab > .kebab-menu.open` selectors only make sense together (the React `<Kebab>` emits them as a unit); (b) splitting PR 5.6 further into a 5.6-a / 5.6-b / 5.6-c triple (tree / detail / kebab) would duplicate the source-CSS + test-enumeration surface across three PRs and force the later children to re-touch selectors the earlier children already locked; (c) the 37 test cases are themselves an inseparable slice; (d) the CSS-only repair lives entirely in `src/app/globals.css` + `tests/test_tailwind_4_parity.py` — a single reviewable diff surface (two files) without any cross-cutting concern.
- **G2 production-candidate evidence gap (PR 5.6 closes the BROWSER-LAYER half but does NOT flip G2; G2 remains pending the full Phase 6 capture)**. The prior chain (PR 5.5) closed the BUILD-PIPELINE half of the G2 evidence gap (the `@tailwindcss/postcss` expansion makes every `var(--token)` reference resolve at runtime, the Tailwind preflight paints, the compiled CSS bundle carries every React-emitted className the CSS rules target). PR 5.6 closes the BROWSER-LAYER half: the React-emitted structural hooks (`.taxa-tree` + `.tree-row[data-selected="true"]` + `.tab-strip > .tab-button.active` + `.breadcrumb` + `.detail-body` + the `.kebab > button[data-action="toggle-kebab"]` selector bridge) now have non-empty CSS rules in `src/app/globals.css` AND the compiled CSS bundle at `out/_next/static/chunks/2c4tn6w2gxss3.css` post-PR-5.6 contains those rules (the rule shapes survive the Turbopack minification intact — verified via the new `tests/test_5_6_*` parametrized tests, every selector appears in the source CSS and is asserted to resolve under `@layer components`). **What PR 5.6 does NOT close**: the actual visual rendering against `127.0.0.1:8765` — a real Chromium / Playwright capture is still required to prove that the static-export bundle paints the React-emitted structural hooks as visibly structural + interactive. G2 production-candidate remains **PASS-pending-Phase-6-capture**, NOT flipped by PR 5.6 alone. The browser capture is the Phase 6a validation work, not PR 5.6.
- **G4 / G3 Tier-2 / cutover (unchanged)**. G4 Playwright + Lighthouse parity remains **blocked** (verifier not authored); G3 Tier-2 remains gated on G4 + G6 closure; G6 remains blocked; the atomic cutover PR 3e ships only when G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6 are all green. **PR 5.6 does NOT flip G4** — only the browser-layer half of the G2 production-candidate evidence gap is closed.
- **Deferrals (binding, this entry)**. Browser-runtime G2 capture (Chromium / Playwright against `127.0.0.1:8765`); Phase 6a validation work; G4 parity capture author; PR 3c-iv (animations / utilities + design-system barrel); PR 3d (Makefile/mount); PR 4a + 4b (browser-state + hydration guard); PR 5a + 5b + 5c (taxonomy + research ports + e2e + legacy deletion); Phase 6a/b/c; PR 3e cutover. No FileExplorer global mount, no Folder/Search research behaviour change, no `domain/keys.ts` / `infrastructure/store.ts` change, no e2e selector/harness updates, no legacy deletion (`web/*.{html,js,css}` + `tailwind.config.js` deferred to PR 5c), no G4 tests, no browser capture, no build outputs (`out/`), no commit/push, no FastAPI/SQLite/extension changes, no production `src/` content change beyond `src/app/globals.css`, no `next.config.mjs` change, no `tsconfig.json` change, no `Makefile` change, no `scripts/check-runtime.mjs` change, no `api/server.py` change, no `web/**` change, no `extension/**` change, no `package.json` / `package-lock.json` / `postcss.config.mjs` change.
- **Scope of this attempt (binding)**: allowed edit surfaces limited to `src/app/globals.css`, `tests/test_tailwind_4_parity.py`, and the six OpenSpec files (3 EN + 3 ES — `proposal.md` is unchanged; `proposal-es.md` is unchanged; `design.md` + `design-es.md` + `tasks.md` + `tasks-es.md` + `apply-progress.md` + `apply-progress-es.md` each get a single append-only addendum entry). Total authored source/tests = ~1,147 LoC across the two files (CSS + parity tests), > 400 budget. **No gate flip, no cutover authority granted** — G1 / G2 / G3 Tier-1 / G3 Tier-2 / G4 / G5 / G6 status rows and PR 3e cutover-authority rows preserved verbatim from prior change-log entry. **No PR opened, no commit/push, no `gentle-ai review mode` enable** — review / CI / merge follow the ordinary feature-branch-chain process once the user-authorized parent task completes. Spanish mirror (`documents-es/openspec/changes/complete-taxa-frontend-migration/apply-progress-es.md`) carries the same semantics; any drift is resolved in favour of the English.

## Addendum — 2026-09-09: PR 3c-iv five-slice replan (documentation-only; chain expands from 18 children to 22 children; user-approved documentation size exception to keep all six OpenSpec files internally coherent) (append-only)

- **Replan five-slice de PR 3c-iv autorizado (esta entrada, reemplaza al antiguo PR 3c-iv único por cinco hijos lineales en posiciones 6/22 a 10/22, renumera los hijos aguas abajo para mantener lineal el contrato de dependencia, expande la cadena de 18 hijos a 22 hijos incluyendo las reparaciones fraccionales PR 5.5 + PR 5.6, abre la `size:exception` de documentación aprobada por el usuario para mantener los seis archivos OpenSpec internamente coherentes; este es un cambio sólo de planificación; ningún slice de código queda implementado, verificado, fusionado ni aprobado para entrega por esta entrada)**. El usuario autorizó partir el antiguo `PR 3c-iv` único (antiguo `feat/complete-taxa-frontend-migration-06-3c-iv`, luego `…-08-3c-iv` tras la renumeración de PR 5.5 + PR 5.6) en **cinco hijos lineales ≤ 400 líneas autorales** (`3c-iv-barrel`, `3c-iv-keyframes`, `3c-iv-viewer`, `3c-iv-settings`, `3c-iv-colors`) porque la superficie del antiguo PR único era heterogénea. **Topología objetivo requerida (cinco hijos en orden lineal)**: (1) `3c-iv-barrel` `feat/complete-taxa-frontend-migration-06-3c-iv-barrel` (basado en predecesor PR 5.6); (2) `3c-iv-keyframes` `…-07-3c-iv-keyframes` (basado en barrel); (3) `3c-iv-viewer` `…-08-3c-iv-viewer` (basado en keyframes); (4) `3c-iv-settings` `…-09-3c-iv-settings` (basado en viewer); (5) `3c-iv-colors` `…-10-3c-iv-colors` (basado en settings). **Renumeración aguas abajo (18 → 22 hijos; PR 5.5 permanece en 5.5/22, PR 5.6 permanece en 5.6/22)**: PR 3d → `11/22`; PR 4a → `12/22`; PR 4b → `13/22`; PR 5a → `14/22`; PR 5b → `15/22`; PR 5c → `16/22`; PR 6a → `17/22`; PR 6b → `18/22`; PR 6c → `19/22`; PR 3e → `20/22`. **Correcciones de dependencia (vinculantes)**: (a) **PR 3d y PR 5c ahora dependen de PR 3c-iv-colors**; (b) **PR 4a ahora depende de PR 3c-iv-barrel**; (c) **la sub-secuencia 3c-iv forma una cadena lineal de cinco eslabones** barrel → keyframes → viewer → settings → colors. **No queda referencia activa a la antigua rama única** después de esta entrada — toda referencia inline previa al `3c-iv` único (tabla de `Reconstruction State`, diagrama de `Reconstruction order`, párrafo de `Chain strategy`, tabla `Per-sub-PR dependency`, sección detallada de tarea `Phase 3c-iv`, dependencias de `Phase 5a` + `Phase 5b` + `Phase 5c` que cabalgan sobre la cascada 3c-iv, referencias cruzadas "3c-iv renumbered to 8/18" en entradas de change-log 5.5 + 5.6) queda actualizada. El presupuesto `~280 LoC` único se descompone en cinco presupuestos por-hijo (barrel ~120, keyframes ~80, viewer ~50, settings ~50, colors ~80 — suma ~380 LoC, ≤ 400 con −20 LoC de holgura); la tabla `Reconstruction State` se expande de una fila única a cinco filas; el diagrama `Reconstruction order` se redibuja con la sub-secuencia de cinco hijos entre PR 5.6 y PR 3d; la tabla `Per-sub-PR dependency` se actualiza para que PR 3d / PR 5c dependan de PR 3c-iv-colors, PR 4a dependa de PR 3c-iv-barrel; la sección detallada `Phase 3c-iv` se reemplaza por cinco secciones nuevas (una por hijo nuevo). **Lo que este replan explícitamente NO reclama**: (i) ningún slice de código queda implementado, verificado, fusionado ni aprobado para entrega; (ii) **no se abre ninguna nueva `size:exception`** — las excepciones existentes (PR 3a lockfile, PR 3c-ii/3c-iii CSS authored-LoC, PR 5.5 lockfile, PR 5.6 CSS-only authored-LoC) permanecen abiertas; el replan abre la excepción de tamaño de **documentación** aprobada por el usuario; (iii) no se habilita `gentle-ai review mode`; no se crea rama; no se autoriza commit; no se hace push; no se abre PR. **Preservado**: cada addendum / entrada de change-log previa permanece como registro histórico de auditoría; la restricción de predecesor congelado permanece vinculante; el estado G4 / G5 / G6 permanece sin cambios (G5 PASS-pending-Phase-6-capture, G4 bloqueado, G6 bloqueado, PR 3e gated en G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6); el bloqueo del Enfoque A permanece FINAL; la fundación FastAPI/SQLite permanece sin cambios; la estrategia de Feature Branch Chain permanece sin cambios; las specs por-dominio permanecen sin cambios; la fidelidad de espejo EN/ES permanece vinculante. **Espejo español** (los otros cuatro espejos ES) lleva la misma semántica; cualquier deriva se resuelve a favor del inglés. Sin rebase; sin rama nueva; sin commit/push; sin PR abierto.
