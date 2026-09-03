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
> de pre-flight del portón de apply identificó que el
> PR 3c previo (posición 3/13), según su ámbito en la
> revisión correctiva del defecto de dependencia, era
> **insatisfacible** — se le había encargado migrar el
> bloque `<style>` inline de **1.963 líneas** del
> `web/index.html` legacy en un único sub-PR mientras se
> mantenía bajo el presupuesto de revisión por PR de
> 400 líneas; la migración no cabe. Por tanto la porción
> de CSS se **re-divide en cuatro hijos encadenados**
> (PR 3c-a / PR 3c-b / PR 3c-c / PR 3c-d), cada uno ≤
> 400 líneas authored y particionado por concern:
> tokens / base / modo oscuro; estilos de árbol + Overview
> inline; estilos de Search / Folder / Browser global;
> animaciones / utilidades + paridad final. El ámbito
> del PR 3c previo se particiona entre los cuatro hijos
> sin duplicar código de producción; el bloque
> `<style>` legacy se retira en PR 5c (el borrado del
> `web/index.html` legacy); los cuatro hijos autorizan
> código nuevo en `src/app/globals.css` sin tocar el
> archivo legacy directamente. El **PR #146** tracker es
> el punto de partida fusionado para el primer nuevo
> hijo CSS (PR 3c-a). Cada PR hijo posterior cambia de
> posición por +3 para acomodar los cuatro hijos CSS
> (3d 4→7; 4a 5→8; 4b 6→9; 5a 7→10; 5b 8→11; 5c 9→12;
> 6a 10→13; 6b 11→14; 6c 12→15; 3e 13→16). Las
> etiquetas semánticas (3a, 3b, 3c-a, 3c-b, 3c-c, 3c-d,
> 3d, 4a, 4b, 5a, 5b, 5c, 6a, 6b, 6c, 3e) se preservan;
> solo cambian el contador de posición (NN en
> `feat/complete-taxa-frontend-migration-NN-XXX`) y las
> referencias a las ramas base. **El conteo de 16
> hijos** reemplaza al conteo previo de 13 hijos. Los
> presupuestos LoC por sub-PR se quedan muy por debajo
> del presupuesto de revisión de 400 líneas; **solo
> permanece la excepción previa de `package-lock.json`
> regenerado de PR 3a**.

| Sub-PR | Alcance | Presupuesto LoC (authored) | Archivos fuente | Estado |
|--------|---------|----------------------------|-----------------|--------|
| PR 3a | **Bootstrap de toolchain** (NUEVA posición 1) | ~210 authored; excepción de lockfile generado aprobada por el usuario | `package.json` + `package-lock.json` regenerado (la excepción queda restringida a cambios de resolución requeridos por este manifiesto, y ambos se revisan juntos; `next@^16` / `react@^19` / `react-dom@^19` / `tailwindcss@^4` / toolchain TS / `engines.node ">=20.9.0"` / `scripts.check-runtime` / `scripts.build:web`; deps legacy de Tailwind 3.4 eliminadas) + `scripts/check-runtime.mjs` (nuevo, Node ≥ 20.9.0) + `tsconfig.json` (modificado en su lugar; el predecesor ya está en la raíz del repo; config base + aliases de ruta `@taxa/<capability>`) + `.nvmrc` (nuevo, pin `20`) + `tests/test_toolchain_bootstrap.py` (nuevo) + `tests/test_check_runtime.py` (nuevo) | pendiente de reconstrucción |
| PR 3b | **Bootstrap autocontenido de exportación estática del App Router** (posición 2; la corrección del defecto de dependencia re-ambia la entrada estilo-3a original del App Router a un bootstrap autocontenido que NO importa `@taxa/app-shell` ni `./globals.css`) | ~150 | `src/app/{layout,page}.tsx` (nuevos, **cuerpo marcador semántico mínimo**; **sin montaje de AppShell, sin import de globals.css**) + `next.config.mjs` (nuevo, `output: "export"` + `images.unoptimized: true` + `trailingSlash: false` + `reactStrictMode: true`) + `tests/test_app_shell_render.py` (nuevo, lee `out/index.html` después de `npx next build`; verifica meta de viewport + preload Raleway + archivo Raleway `.woff2` en `out/_next/static/media/`) | pendiente de reconstrucción |
| PR 3c-a | **Tokens / base / modo oscuro** (NUEVA posición 3; el primer nuevo hijo CSS de la re-división del CSS; la corrección del defecto de dependencia mueve la línea `import "./globals.css";` a este sub-PR; el ámbito del PR 3c previo se particiona entre 3c-a / 3c-b / 3c-c / 3c-d) | ~400 | `src/app/globals.css` (nuevo, andamio inicial: `@import "tailwindcss"` + `@theme` reflejando cada token legacy `:root` / `[data-theme="dark"]` / `--realm-*` + placeholder vacío de `@layer base` para hijos posteriores) + `src/app/layout.tsx` (modificado, delta de 1 línea: añade `import "./globals.css";`) + `src/modules/design-system/{infrastructure/index.ts,presentation/Icon.tsx,presentation/Button.tsx}` (nuevos) + `tests/test_tailwind_4_tokens.py` (nuevo; enumera tokens legacy `:root` / `[data-theme="dark"]` / `--realm-*` contra `globals.css::@theme`) + `tests/test_design_system_purity.py` (nuevo) | pendiente de reconstrucción |
| PR 3c-b | **Estilos de árbol + Overview inline** (NUEVA posición 4; el segundo nuevo hijo CSS; depende del andamio de `globals.css` + placeholder de `@layer base` de 3c-a) | ~400 | `src/app/globals.css` (extendido, bloque `@layer components` con selectores de taxonomía: `.taxa-tree`, `.tree-row`, `.kebab`, `.kebab-menu`, `.tree-search-icon`, `.materialize-indicator`, `.detail-panel`, `.tab-strip`, `.tab-button`, `.overview-tab`, `.breadcrumb`) + `tests/test_taxonomy_styles.py` (nuevo; enumera selectores `@layer components` de taxonomía contra `globals.css`) | pendiente de reconstrucción |
| PR 3c-c | **Estilos de Search / Folder / Browser global** (NUEVA posición 5; el tercer nuevo hijo CSS; depende del bloque `@layer components` de taxonomía de 3c-b) | ~400 | `src/app/globals.css` (extendido, bloque `@layer components` con selectores de research / chrome: `.search-tab`, `.search-category-section`, `.search-link-list`, `.search-link`, `.folder-tab`, `.header-browser-tab`, `.research-explorer`, `.file-explorer-pane`, `.file-viewer-pane`) + `tests/test_research_styles.py` (nuevo; enumera selectores `@layer components` de research / chrome contra `globals.css`) | pendiente de reconstrucción |
| PR 3c-d | **Animaciones / utilidades + paridad final** (NUEVA posición 6; el cuarto y último nuevo hijo CSS; depende del bloque `@layer components` de research / chrome de 3c-c; envía el test de paridad final consolidado `tests/test_tailwind_4_parity.py`) | ~300 | `src/app/globals.css` (extendido, bloque `@layer base` con `@keyframes` (`spin`), selectores de `color-mix()`, superficie de clases de utilidad (`bg-primary`, `text-on-surface`, `border-outline-variant`, `bg-surface-container-lowest`, `shadow-sm`, `rounded-r-md`, `bg-primary-fixed`, `text-on-primary-fixed`, …), regla `body { overscroll-behavior: none; … }`, reset `main > :first-child { margin-top: 0 !important; }` — todo en orden de fuente) + `tests/test_tailwind_4_parity.py` (nuevo; test de paridad final consolidado parametrizado) | pendiente de reconstrucción |
| PR 3d | **Makefile/mount** (NUEVA posición 7; fusiona 3c + 3d originales; depende de `next build` de 3b + tokens de Tailwind 4 + `@layer base` + `@layer components` de 3c-d) | ~240 | `Makefile` (modificado, target `api:` ejecuta `check-runtime.mjs` → `npm ci` → `npm run build:web` → `uvicorn … --port 8765`; `make css` se vuelve shim no-op) + `api/server.py` (modificado, delta de 1 línea en línea 54, `WEB_DIR = Path(__file__).parent.parent / "out"`) + `src/data/search-engines.js` (nuevo, copia byte a byte de `web/search_urls.js` con export nombrado `SEARCH_ENGINES`) + `tests/test_smoke.py` (modificado, actualización de ruta `open()`) + `tests/test_static_mount.py` (nuevo) + `tests/test_make_api_build.py` (nuevo) | pendiente de reconstrucción |
| PR 4a | Typed store + 4 lecturas + 4 escrituras (sin cambios) | ~180 | `src/modules/browser-state/{domain/keys.ts,infrastructure/store.ts,index.ts}` (nuevos) + `tests/test_browser_state_keys.py` (nuevo) | pendiente de reconstrucción |
| PR 4b | Guardia de hidratación + integración de AppShell + cero warnings Playwright (la corrección del defecto de dependencia mueve la integración de `<AppShell>` en `src/app/{layout,page}.tsx` a este sub-PR) | ~120 | `src/modules/app-shell/{presentation/AppShell.tsx,infrastructure/page-chrome.tsx}` (nuevos) + `src/app/{layout,page}.tsx` (modificados, integra `<AppShell>` desde `@taxa/app-shell` en el host del App Router; la corrección del defecto de dependencia) + `tests/test_hydration_console.py` (nuevo, Playwright) | pendiente de reconstrucción |
| PR 5a | Port del módulo taxonomy (extendido; absorbe el strip de pestañas de DetailPanel + OverviewTab + Kebab Search-online fuerza) | ~310 | `src/modules/taxonomy/{domain/taxon.ts,infrastructure/api.ts,application/useTaxonTree.ts,presentation/{Tree,DetailPanel,OverviewTab,Kebab,Breadcrumb}.tsx}` (nuevo + extensión; `DetailPanel` envía el strip de tres pestañas `Overview` / `Search` / `Folder` según la superficie UI verificada, con `Overview` siempre disponible/visible; la capa de presentation de taxonomía se monta sobre los selectores de `@layer components` de PR 3c-b) + `tests/test_taxonomy_infra.py` (nuevo; incluye el testigo de regresión Playwright `Search online` → pestaña `Search`) | pendiente de reconstrucción |
| PR 5b | Port del módulo research + pin CDN (extendido; absorbe SearchTab + FolderTab + SearchLinkList + re-anclaje de la pestaña `Browser` del header como Research global) | ~395 | `src/modules/research/{domain/{research-file,engine,file-node}.ts,infrastructure/{api,search-engines}.{ts,js},application/{useFileExplorer,useFileViewer}.ts,presentation/{FileExplorer,FileViewer,RawTableTreeTabs,MetaStrip,BreadcrumbPanel,Banners,SearchLinkList,SearchTab,FolderTab}.tsx}` (nuevo; `SearchTab` renderiza las cinco secciones de categoría `General` / `Taxonomic` / `Academic` / `Multimedia` / `Documents` en orden fijo; `FolderTab` es un cuerpo separado; `SearchLinkList` mapea cada `Engine` a un anchor con `target="_blank"` + `rel="noopener noreferrer"`; la capa de presentation de research se monta sobre los selectores de `@layer components` de PR 3c-c) + `src/modules/app-shell/infrastructure/page-chrome.tsx` (modificado; pestaña `Browser` del header re-anclada como Research global / file explorer, NO scoped por taxón) + `tests/test_research_infra.py` (nuevo; incluye la triangulación de la lista categorizada de enlaces salientes y el testigo de Browser-global) | pendiente de reconstrucción |
| PR 5c | Selectores E2E + contrato `data-*` + borrar legacy (extendido; depende de PR 5b + PR 3c-d; el borrado del `web/index.html` legacy retira el CSS inline legacy de 1.963 líneas que los cuatro hijos CSS migraron a `src/app/globals.css`) | ~200 | `tests/test_e2e_file_explorer.py` (modificado, actualización de selectores DOM) + `tests/test_web_toggle.py` (modificado, actualización de toggle de tema) + `tests/test_evidence_baseline.py` (modificado, aserción de roster legacy voltea a "ausente") + borrado de `web/{index.html,index.css}` + borrado de `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,help,keymap,settings,search,file_explorer,file_viewer,format,search_urls}.js` (18 archivos) + borrado de `tailwind.config.js` + `web/dist/tailwind.css` ya no se rastrea | pendiente de reconstrucción |
| Fase 6a | Cierre de baseline de hidratación G5 (sin cambios) | ~50 (mayormente medición) | `scripts/reconstruct_hydration_baseline.py` (nuevo) + `scripts/g5_close.sh` (nuevo) + `web/dist/evidence-baseline.json` (regenerado, esquema fijado por `tests/test_hydration_timing.py`) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| Fase 6b | Ensayo de cutover G6 (sin cambios) | ~120 | `scripts/rehearse_cutover.py` (nuevo) + `tests/test_rehearse_cutover.py` (nuevo) + `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json` (copia de trabajo; la copia del predecesor queda byte-idéntica congelada) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| Fase 6c | Paridad G4 Playwright + Lighthouse (sin cambios) | ~20 (mayormente medición) | `scripts/g4_measure.sh` (nuevo) + `out/g4-parity-report.json` (artefacto Playwright + Lighthouse) + delta de `apply-progress.md` §Registro de cambios | pendiente de reconstrucción (trabajo de validación tras camino candidato) |
| PR 3e | Cutover atómico (sin cambios) | ~120 (mayormente delta de `apply-progress.md`) | `apply-progress.md` (flip de footer de estado de puertas + entrada de registro de cambios) + re-corridas de `tests/test_verify_consumers.py`, `tests/test_verify_build.py`, `make api`, `make smoke` | pendiente de reconstrucción (con compuerta en las seis puertas verdes) |

**Conteo de sub-PRs**: **16** (1 bootstrap de toolchain +
1 exportación estática del App Router + **4 hijos CSS
(3c-a / 3c-b / 3c-c / 3c-d)** + 1 Makefile/mount + 2
browser-state + 2 puertos de capability + 1 e2e + borrar
legacy + 3 validación de Fase 6 + 1 cutover atómico).

**Total authored**: ~3.615 LoC a través de los 16
sub-PRs (Δ ~+1.333 LoC del pronóstico previo de ~2.282;
la re-división del CSS particiona la migración del CSS
inline legacy de 1.963 líneas en 4 hijos totalizando
~1.500 líneas authored (reemplazando los ~232 LoC del
PR 3c único previo) y añade 4 tests de triangulación
separados; la corrección del defecto de dependencia
redistribuye ~30 LoC entre PR 3b (-25), PR 3c-a (+2) y
PR 4b (+30) sin cambiar la topología de la cadena). Los
sub-PRs más grandes son los **cuatro hijos CSS 3c-a /
3c-b / 3c-c** a ≤ 400 LoC cada uno (justo en el
presupuesto de revisión de 400 líneas por PR con 0 LoC
de holgura en el hijo más ajustado); **5b** queda a
~395 LoC (-5 LoC de holgura). PR 3d queda a ~240 LoC
(-160 LoC / -40 % de holgura contra el presupuesto de
400 líneas). La única `size:exception` está aprobada
por el usuario para el `package-lock.json` regenerado
de PR 3a; su trabajo authored permanece ≤400 y se
rechaza churn de lockfile no relacionado. El borrado
del `web/index.html` en PR 5c retira el CSS inline
legacy de 1.963 líneas que los cuatro hijos CSS
migraron a `src/app/globals.css`.

### Orden de reconstrucción (determinístico, secuencial a lo largo de la cadena)

```
3a (bootstrap de toolchain) →
3b (exportación estática del App Router) →
3c-a (tokens / base / modo oscuro) →
3c-b (estilos de árbol + Overview inline) →
3c-c (estilos de Search / Folder / Browser global) →
3c-d (animaciones / utilidades + paridad final) →
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
apunta al tracker; cada hijo posterior apunta a su
**rama predecesora inmediata**. El primer nuevo hijo
CSS (PR 3c-a) trata al PR #146 tracker como el punto
de partida fusionado para la re-división del CSS en
cuatro hijos. Esto sustituye, para este cambio, el
default de `AGENTS.md` §4 de apuntar directo a
`develop`.

| Posición | Sub-PR | Rama | Base (destino del PR) |
|---|---|---|---|
| Tracker | — | `docs/complete-taxa-frontend-migration-plan` (PR #146) | `develop` — **draft / no-merge** |
| 1 / 16 | 3a | `feat/complete-taxa-frontend-migration-01-3a` | `docs/complete-taxa-frontend-migration-plan` (tracker) |
| 2 / 16 | 3b | `feat/complete-taxa-frontend-migration-02-3b` | `feat/complete-taxa-frontend-migration-01-3a` |
| 3 / 16 | 3c-a | `feat/complete-taxa-frontend-migration-03-3c-a` | `feat/complete-taxa-frontend-migration-02-3b` |
| 4 / 16 | 3c-b | `feat/complete-taxa-frontend-migration-04-3c-b` | `feat/complete-taxa-frontend-migration-03-3c-a` |
| 5 / 16 | 3c-c | `feat/complete-taxa-frontend-migration-05-3c-c` | `feat/complete-taxa-frontend-migration-04-3c-b` |
| 6 / 16 | 3c-d | `feat/complete-taxa-frontend-migration-06-3c-d` | `feat/complete-taxa-frontend-migration-05-3c-c` |
| 7 / 16 | 3d | `feat/complete-taxa-frontend-migration-07-3d` | `feat/complete-taxa-frontend-migration-06-3c-d` |
| 8 / 16 | 4a | `feat/complete-taxa-frontend-migration-08-4a` | `feat/complete-taxa-frontend-migration-07-3d` |
| 9 / 16 | 4b | `feat/complete-taxa-frontend-migration-09-4b` | `feat/complete-taxa-frontend-migration-08-4a` |
| 10 / 16 | 5a | `feat/complete-taxa-frontend-migration-10-5a` | `feat/complete-taxa-frontend-migration-09-4b` |
| 11 / 16 | 5b | `feat/complete-taxa-frontend-migration-11-5b` | `feat/complete-taxa-frontend-migration-10-5a` |
| 12 / 16 | 5c | `feat/complete-taxa-frontend-migration-12-5c` | `feat/complete-taxa-frontend-migration-11-5b` |
| 13 / 16 | 6a | `feat/complete-taxa-frontend-migration-13-6a` | `feat/complete-taxa-frontend-migration-12-5c` |
| 14 / 16 | 6b | `feat/complete-taxa-frontend-migration-14-6b` | `feat/complete-taxa-frontend-migration-13-6a` |
| 15 / 16 | 6c | `feat/complete-taxa-frontend-migration-15-6c` | `feat/complete-taxa-frontend-migration-14-6b` |
| 16 / 16 | 3e | `feat/complete-taxa-frontend-migration-16-3e` | `feat/complete-taxa-frontend-migration-15-6c` |

Los hijos se fusionan **en orden** dentro del tracker; a
medida que cada hijo se fusiona, el siguiente se
reapunta al tracker (GitHub reapunta automáticamente
cuando la rama base se fusiona y se borra). El tracker
acumula la feature completa y se fusiona a `develop`
solo después de que PR 3e — el último hijo — aterrice.

**Dependencia por sub-PR (contrato de la revisión
correctiva del plan + corrección del defecto de
dependencia + re-división del CSS)**:

| Posición | Depende de | Satisface (testigo) |
|---|---|---|
| 1 / 3a (bootstrap de toolchain) | — | `npm ci` exit 0; `node scripts/check-runtime.mjs` exit 0 en Node ≥ 20.9.0; `npx tsc --noEmit` resuelve todos los aliases `@taxa/*` |
| 2 / 3b (exportación estática del App Router) | 1 | `npx next build` exit 0; `out/index.html` no vacío con meta de viewport + preload de Raleway |
| 3 / 3c-a (tokens / base / modo oscuro) | 1 + 2 | `src/app/globals.css::@theme` lleva cada token legacy `:root` / `[data-theme="dark"]` / `--realm-*`; integración de `import "./globals.css";` en `src/app/layout.tsx`; barrel de design-system exportado |
| 4 / 3c-b (estilos de árbol + Overview inline) | 3 | `globals.css::@layer components` lleva selectores de taxonomía (`.taxa-tree`, `.tree-row`, `.kebab`, `.detail-panel`, `.tab-strip`, `.overview-tab`, `.breadcrumb`, …) |
| 5 / 3c-c (estilos de Search / Folder / Browser global) | 4 | `globals.css::@layer components` lleva selectores de research / chrome (`.search-tab`, `.search-link`, `.folder-tab`, `.header-browser-tab`, `.research-explorer`, …) |
| 6 / 3c-d (animaciones / utilidades + paridad final) | 5 | `globals.css::@layer base` lleva `@keyframes` (`spin`), selectores de `color-mix()`, superficie de clases de utilidad, reset de body, reset de primer hijo; el test de paridad final `tests/test_tailwind_4_parity.py` enumera el CSS inline legacy de 1.963 líneas de extremo a extremo |
| 7 / 3d (Makefile/mount) | 2 + 6 | `make api` exit 0; uvicorn vincula solo `127.0.0.1:8765`; `curl /index.html` devuelve `out/index.html`; contrato AC-21 preservado |
| 8 / 4a (typed store) | 3 | 4 sitios de lectura + 4 de escritura en `src/modules/browser-state/`; ningún otro módulo toca `localStorage` |
| 9 / 4b (guardia de hidratación + integración de AppShell) | 8 + 2 + 3 | Playwright cero warnings de hidratación; `AppShell` integrado en `src/app/{layout,page}.tsx`; la corrección del defecto de dependencia y el barrel de design-system de PR 3c-a están en vivo |
| 10 / 5a (port de taxonomy) | 9 + 4 | View-models de taxonomía renderizan; toggle de tree-source rehidrata vía `localStorage`; la capa de presentation de taxonomía se monta sobre los selectores de `@layer components` de PR 3c-b |
| 11 / 5b (port de research + pin CDN) | 10 + 7 + 5 | Archivos de research renderizan vía despachador de 9 formatos; URLs CDN pineadas; la capa de presentation de research se monta sobre los selectores de `@layer components` de PR 3c-c |
| 12 / 5c (e2e + borrar legacy) | 11 + 6 | Selectores e2e actualizados; contrato `data-*` preservado; `web/*` legacy borrado (el borrado del `web/index.html` retira el CSS inline legacy de 1.963 líneas que los cuatro hijos CSS migraron a `src/app/globals.css`) |
| 13–15 / 6a, 6b, 6c (validación) | 12 | G5 reproducible; G6 PASS; G4 PASS; `apply-progress.md` §Registro de cambios flipa para cada uno |
| 16 / 3e (cutover atómico) | 13, 14, 15 + G1/G2/G3 Tier-1 trasladado | Las seis puertas verdes; flip de cutover-manifest Tier-2; uvicorn sirve `out/index.html` desde la build de producción |

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
  de dos tests nuevos); **3b** ~150 (bootstrap
  autocontenido de exportación estática del App Router
  — **layout/page marcadores semánticos mínimos**; sin
  montaje de AppShell, sin import de globals.css; la
  corrección del defecto de dependencia); **3c-a** ~400
  (tokens / base / modo oscuro — `src/app/globals.css`
  andamio inicial con `@theme` + barrel de design-system
  + integración de 1 línea `import "./globals.css";` en
  `src/app/layout.tsx`; la costura de corrección del
  defecto de dependencia); **3c-b** ~400 (estilos de
  árbol + Overview inline — selectores de taxonomía en
  `@layer components`); **3c-c** ~400 (estilos de Search
  / Folder / Browser global — selectores de research /
  chrome en `@layer components`); **3c-d** ~300
  (animaciones / utilidades + paridad final — `@layer
  base` con `@keyframes` / `color-mix()` / clases de
  utilidad / reset de body / reset de primer hijo + el
  `tests/test_tailwind_4_parity.py` consolidado);
  **3d** ~240 (el sub-PR re-posicionado más pesado en la
  frontera de posición 7, fusionando Makefile + WEB_DIR
  + AC-21); **4a** ~180; **4b** ~120 (guardia de
  hidratación + integración de AppShell en
  `src/app/{layout,page}.tsx`; la corrección del defecto
  de dependencia); **5a** ~310; **5b** ~395; **5c**
  ~200; **6a** ~50; **6b** ~120; **6c** ~20; **3e**
  ~120 (mayormente delta de `apply-progress.md`).
  **Total**: ~3.615 LoC authored a través de **16**
  sub-PRs (Δ ~+1.333 LoC de las ~2.282 previas; la
  re-división del CSS particiona la migración del CSS
  inline legacy de 1.963 líneas en 4 hijos totalizando
  ~1.500 LoC (reemplazando los ~232 LoC del PR 3c único
  previo) y añade 4 tests de triangulación separados; la
  corrección del defecto de dependencia quita ~25 LoC del
  PR 3b (sin cableado de AppShell/globals.css) y añade
  ~30 LoC al PR 4b (costura de integración del AppShell)
  más ~2 LoC al PR 3c-a (línea `import "./globals.css";`);
  cada sub-PR queda muy por debajo de 400).
- Los sub-PRs más grandes son los **cuatro hijos CSS
  3c-a / 3c-b / 3c-c** a ≤ 400 LoC cada uno (justo en el
  presupuesto de revisión de 400 líneas por PR con 0
  LoC de holgura en el hijo más ajustado); **5b** queda
  a ~395 LoC (-5 LoC de holgura). PR 3d queda a ~240 LoC
  (-160 LoC / -40 % de holgura contra el presupuesto de
  400 líneas). **No se requiere nueva `size:exception`**
  — solo permanece la excepción previa de
  `package-lock.json` regenerado de PR 3a.
- **PRs encadenados recomendados**: **Sí** — cada
  sub-PR cabe por sí solo en el presupuesto por PR, pero
  el total de ~3.615 líneas y el cutover atómico (la
  feature DEBE integrarse antes de llegar a `develop`)
  sitúan este cambio en la compuerta de Feature Branch
  Chain.
- **Estrategia de cadena**:
  **`feature-branch-chain`** (elegida por el usuario).
  El tracker `docs/complete-taxa-frontend-migration-plan`
  (referido como PR #146) es draft/no-merge y es el
  **único** PR que apunta a `develop`; el PR hijo 3a
  apunta al tracker; cada hijo posterior apunta a su
  rama predecesora inmediata. El primer nuevo hijo CSS
  (PR 3c-a) trata al PR #146 tracker como el punto de
  partida fusionado para la re-división del CSS en
  cuatro hijos. Sustituye, para este cambio, el default
  de `AGENTS.md` §4 de apuntar directo a `develop` y el
  precedente de apply-progress del predecesor.
- **Estrategia de entrega**: **`ask-on-risk`** (según
  preflight; sin flag de riesgo abierto — el Enfoque A
  es FINAL, el predecesor está congelado, cada sub-PR
  cabe bajo 400 líneas, la re-división del CSS satisface
  la migración del CSS inline legacy de 1.963 líneas que
  el PR 3c único previo no podía).
- **Decision needed before apply**: **No** (Enfoque A
  bloqueado, estrategia de cadena conocida, cada sub-PR
  dentro del presupuesto, orden de dependencia
  corregido, re-división del CSS resuelve la migración de
  1.963 líneas).

---

## Carga / Frontera de PR

- **Modo**: **Feature Branch Chain** — 1 tracker
  draft/no-merge
  (`docs/complete-taxa-frontend-migration-plan` →
  `develop`) más **16** PRs hijos secuenciales (bootstrap
  de toolchain → exportación estática del App Router →
  **4 hijos CSS (3c-a / 3c-b / 3c-c / 3c-d)** →
  Makefile/mount → 4a → 4b → 5a → 5b → 5c, seguidos de
  los eslabones de validación de la Fase 6, seguidos del
  cutover atómico PR 3e como último hijo).
- **Total sub-PRs**: **16** (3a, 3b, 3c-a, 3c-b, 3c-c,
  3c-d, 3d, 4a, 4b, 5a, 5b, 5c, 6a, 6b, 6c, 3e — notar
  que 6a, 6b, 6c son trabajo de validación tras el
  camino candidato; 3e tiene compuerta en las seis
  puertas verdes).
- **Cada sub-PR ≤ 400 LoC authored** (los cuatro hijos
  CSS van al presupuesto de 400 líneas con 0 LoC de
  holgura en el hijo más ajustado; **5b** a ~395 LoC con
  -5 LoC de holgura; 3d a ~240 LoC con -160 LoC de
  holgura). **Ningún sub-PR excede el presupuesto de
  revisión de 400 líneas por PR.** **No se espera ni
  planifica ninguna `size:exception`.**
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

**Corrección del defecto de dependencia aplicada el
2026-09-02** (esta nota de estado): la re-auditoría de
pre-flight del portón de apply identificó un segundo defecto
de dependencia dentro de la topología corregida — el
`src/app/layout.tsx` del PR 3b importaba `@taxa/app-shell`
(un módulo que el PR 4b envía en la posición 9/16) y
`./globals.css` (un archivo que el PR 3c-a envía en la
posición 3/16), ninguno de los cuales existía cuando el
testigo de `next build` del PR 3b tenía que correr. La
misma auditoría marcó la aserción de triangulación
insatisfacible a `@taxa/browser-state` de PR 3b.5 (el
archivo de barrel no existe hasta el PR 4a). **El PR 3b se
re-ambia a un bootstrap autocontenido de exportación
estática del App Router** (sin AppShell, sin import de
globals.css); la línea `import "./globals.css";` se mueve
al PR 3c-a; la integración de `<AppShell>` en
`src/app/{layout,page}.tsx` se mueve al PR 4b. **El total
authored tras la corrección del defecto de dependencia es
~2.282 LoC** (Δ ~+37 LoC de las ~2.245 previas; PR 3b se
reduce ~25 LoC, PR 3c-a crece ~2 LoC, PR 4b crece ~30
LoC); cada sub-PR queda muy por debajo de 400; **solo
permanece la excepción previa de `package-lock.json`
regenerado de PR 3a**.

**Re-división del CSS aplicada el 2026-09-02** (esta nota
de estado): la re-auditoría de pre-flight del portón de
apply identificó que el PR 3c, según su ámbito en la
revisión correctiva del defecto de dependencia, era
**insatisfacible** — se le había encargado migrar el
bloque `<style>` inline de **1.963 líneas** del
`web/index.html` legacy en un único sub-PR mientras se
mantenía bajo el presupuesto de revisión por PR de 400
líneas; la migración no cabe. Por tanto la porción de
CSS se **re-divide en cuatro hijos encadenados** (PR
3c-a / PR 3c-b / PR 3c-c / PR 3c-d) en posiciones
3 / 16, 4 / 16, 5 / 16, 6 / 16, cada uno ≤ 400 líneas
authored y particionado por concern: tokens / base /
modo oscuro; estilos de árbol + Overview inline;
estilos de Search / Folder / Browser global;
animaciones / utilidades + paridad final. El **PR
#146** tracker es el punto de partida fusionado para
el primer nuevo hijo CSS (PR 3c-a). Cada PR hijo
posterior cambia de posición por +3 (3d 4→7; 4a 5→8;
4b 6→9; 5a 7→10; 5b 8→11; 5c 9→12; 6a 10→13; 6b
11→14; 6c 12→15; 3e 13→16). Las etiquetas semánticas
se preservan; solo cambian el contador de posición y
las referencias a las ramas base. Los cuatro hijos CSS
migran colectivamente las 1.963 líneas legacy del CSS
inline a `src/app/globals.css` (≤ 1.500 líneas
authored más el reset base de Tailwind 4, bien dentro
del presupuesto del predecesor para
`out/_next/static/chunks/*.css`); el bloque
`<style>` legacy se retira en PR 5c. **El total
authored es ahora ~3.615 LoC a través de 16 sub-PRs**
(Δ ~+1.333 LoC de las ~2.282 previas; la re-división
del CSS particiona la migración del CSS inline legacy
de 1.963 líneas en 4 hijos totalizando ~1.500 LoC
(reemplazando los ~232 LoC del PR 3c único previo) y
añade 4 tests de triangulación separados; cada
sub-PR queda muy por debajo de 400); **solo permanece
la excepción previa de `package-lock.json` regenerado
de PR 3a**.

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
