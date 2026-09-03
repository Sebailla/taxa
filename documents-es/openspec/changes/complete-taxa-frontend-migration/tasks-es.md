# Tareas: complete-taxa-frontend-migration

> TDD estricto: ROJO → VERDE → TRIANGULAR → REFACTORIZAR. Las
> reglas del monolito modular de
> `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
> aplican a cada unidad de UI/archivo. **El Enfoque A es FINAL**
> (bloqueado el 2026-09-02; registrado en `design.md::§1`); no
> hay ruta de anulación abierta. **El predecesor
> `migrate-nextjs-tailwind4/` está congelado** — sus archivos
> DEBEN permanecer byte-idénticos durante toda la fase de
> apply de este cambio.

> **2026-09-02 — revisión correctiva del plan**. La topología
> de cadena de 13 PRs hijos fue reordenada y re-ambiada después
> de que el portón de apply identificara un defecto de orden
> de dependencia: el PR 3a original requería
> `next build`/`out/index.html` antes de que existieran el
> toolchain de Next/React/Tailwind/TypeScript y el contrato de
> runtime de Node (esos aterrizaban en el PR 3c original,
> DESPUÉS del PR 3a original). La topología corregida
> introduce un **PR de bootstrap de toolchain en la posición
> 1** (que absorbe los pins de deps de `package.json` y
> `scripts/check-runtime.mjs` previamente atribuidos al PR 3c
> original), degrada la **exportación estática del App Router**
> a la posición 2 (ahora segura porque el toolchain ya existe),
> mantiene **Tailwind/tokens** en la posición 3, fusiona la
> **reescritura del Makefile** con el repoint de `WEB_DIR` +
> AC-21 en la posición 4, y sigue con **state → ports → e2e →
> validation → cutover atómico** en orden de dependencia
> correcto. El conteo de 13 hijos se preserva; solo cambian la
> topología de la cadena, el ámbito por hijo y los testigos por
> hijo. **El Enfoque A, FastAPI/SQLite y el predecesor
> congelado quedan sin cambios.**

> **2026-09-02 — corrección de defecto de dependencia (esta
> revisión)**. La re-auditoría de pre-flight del portón de apply
> identificó un segundo defecto de dependencia dentro de la
> topología corregida: el `src/app/layout.tsx` del PR 3b
> importaba `@taxa/app-shell` (un módulo que el PR 4b envía en
> la posición 9/16 — *más tarde* en la cadena) y `./globals.css`
> (un archivo que el PR 3c-a envía en la posición 3/16 — *más
> tarde* en la cadena). En su testigo de `next build`, ninguno
> de los dos archivos objetivo existía todavía, por lo que el
> testigo era insatisfacible. La misma auditoría marcó la
> aserción de triangulación de PR 3b.5 que dice que la salida
> de build referencia la ruta del barrel del typed store
> `@taxa/browser-state` — ese archivo de barrel no existe
> hasta que el PR 4a aterriza. **PR 3b se re-ambia a un
> bootstrap autocontenido de exportación estática del App
> Router**: `src/app/{layout,page}.tsx` se convierten en
> marcadores semánticos mínimos (solo preload de Raleway) que
> no importan **ni** `@taxa/app-shell` **ni** `./globals.css`;
> la línea `import "./globals.css";` se mueve al PR 3c-a (que ya
> posee `globals.css`); la integración de `<AppShell>` en
> `src/app/layout.tsx` / `src/app/page.tsx` se mueve al PR 4b
> (que ya posee `src/modules/app-shell/**`). La referencia
> insatisfacible a `@taxa/browser-state` de PR 3b.5 se elimina
> (el contrato de alias de ruta ya lo verifica
> `tests/test_toolchain_bootstrap.py::3a.7`) y se reemplaza con
> la aserción del archivo Raleway `.woff2`. **La topología y el
> orden de 13 hijos se preservan**; la evidencia de prueba de
> PR 3b (`out/index.html` / viewport / preload Raleway) se
> mantiene. Los presupuestos se recalculan: PR 3b se reduce a
> ~150 LoC (-25), PR 3c-a crece ~2 LoC (1 línea de import de
> `globals.css`), PR 4b crece ~30 LoC (costura de integración
> de AppShell); total authored ~2.282 LoC en los 13 sub-PRs;
> cada sub-PR queda muy por debajo de 400; **solo permanece la
> excepción previa de `package-lock.json` regenerado de PR
> 3a**. El Enfoque A, FastAPI/SQLite, el predecesor congelado,
> los specs por dominio y las puertas de validación quedan sin
> cambios.

> **2026-09-02 — re-división del CSS (esta revisión)**. La
> re-auditoría de pre-flight del portón de apply identificó
> que el PR 3c, según su ámbito en la revisión correctiva
> anterior, era **insatisfacible**: se le había encargado
> migrar el bloque `<style>` inline de **1.963 líneas** del
> `web/index.html` legacy en un único sub-PR mientras se
> mantenía bajo el presupuesto de revisión por PR de 400
> líneas — la migración no cabe. Por tanto la porción de CSS
> de la migración se **re-divide en cuatro hijos encadenados**,
> cada uno ≤ 400 líneas authored, con el ámbito del PR 3c
> anterior particionado por concern:
>
> - **PR 3c-a — tokens / base / modo oscuro** (posición
>   3/16): crea `src/app/globals.css` (andamio inicial con
>   `@import "tailwindcss";` + `@theme` + placeholder vacío
>   de `@layer base`), envía el barrel de design-system
>   (`<Icon>`, `<Button>`), cablea `import "./globals.css";`
>   en `src/app/layout.tsx` (la costura de corrección del
>   defecto de dependencia), y migra **cada** token legacy
>   `:root` / `[data-theme="dark"]` / `--realm-*` dentro de
>   `@theme`. El test de triangulación
>   `tests/test_tailwind_4_tokens.py` enumera los nombres
>   de tokens legacy contra `globals.css::@theme`.
> - **PR 3c-b — estilos de árbol + Overview inline**
>   (posición 4/16): extiende `src/app/globals.css` con las
>   reglas de `@layer components` para el **módulo taxonomy**
>   (`.taxa-tree`, `.tree-row`, `.kebab`, `.kebab-menu`,
>   `.tree-search-icon`, `.materialize-indicator`,
>   `.detail-panel`, `.tab-strip`, `.tab-button`,
>   `.overview-tab`, `.breadcrumb`). El test de triangulación
>   `tests/test_taxonomy_styles.py` lee el
>   `out/_next/static/chunks/*.css` generado y verifica que
>   cada selector de taxonomy resuelve.
> - **PR 3c-c — estilos de Search / Folder / Browser global**
>   (posición 5/16): extiende `globals.css` con los
>   selectores del módulo research y del shell de chrome
>   (`.search-tab`, `.search-category-section`,
>   `.search-link-list`, `.search-link`, `.folder-tab`,
>   `.header-browser-tab`, `.research-explorer`,
>   `.file-explorer-pane`, `.file-viewer-pane`). El test
>   de triangulación `tests/test_research_styles.py`
>   enumera cada selector de research / chrome.
> - **PR 3c-d — animaciones / utilidades + paridad final**
>   (posición 6/16): extiende `globals.css` con `@keyframes`
>   (`spin`), los selectores de `color-mix()`, la superficie
>   de clases de utilidad (`bg-primary`, `text-on-surface`,
>   `border-outline-variant`, `bg-surface-container-lowest`,
>   `shadow-sm`, `rounded-r-md`, `bg-primary-fixed`,
>   `text-on-primary-fixed`, …), la regla
>   `body { overscroll-behavior: none; … }`, y el reset
>   `main > :first-child { margin-top: 0 !important; }`.
>   Envía el test de paridad **final**
>   `tests/test_tailwind_4_parity.py` (parametrizado sobre
>   cada token `:root` legacy, cada referencia
>   `var(--token)`, cada clase de utilidad legacy, y cada
>   selector `@keyframes` / `color-mix()`).
>
> **El PR #146 tracker es el punto de partida fusionado**
> para el primer nuevo hijo CSS (PR 3c-a) — lo que significa
> que la rama tracker es el punto de integración al que el
> PR 3c-a apunta una vez que su predecesor (PR 3b) se haya
> fusionado; el tracker sigue en draft / no-merge hasta que
> la cadena completa.
>
> **Renumeración**: cada PR hijo posterior cambia de posición
> para acomodar los cuatro nuevos hijos CSS insertados en
> las posiciones 3–6. Las etiquetas semánticas (3a, 3b,
> 3c-a/b/c/d, 3d, 4a, 4b, 5a, 5b, 5c, 6a, 6b, 6c, 3e) se
> preservan; solo cambian el contador de posición (NN en
> `feat/complete-taxa-frontend-migration-NN-XXX`) y las
> referencias a las ramas base.
>
> **Impacto topológico**:
>
> - `PR 3a` se queda en posición 1/16.
> - `PR 3b` se queda en posición 2/16.
> - `PR 3c-a`, `PR 3c-b`, `PR 3c-c`, `PR 3c-d` son los
>   nuevos hijos en posiciones 3/16, 4/16, 5/16, 6/16
>   respectivamente.
> - `PR 3d` (Makefile/mount) pasa de 4/13 a **7/16**.
> - `PR 4a` (typed store) pasa de 5/13 a **8/16**.
> - `PR 4b` (guardia de hidratación + integración de
>   AppShell) pasa de 6/13 a **9/16**.
> - `PR 5a` (port de taxonomy) pasa de 7/13 a **10/16**.
> - `PR 5b` (port de research + pin CDN) pasa de 8/13 a
>   **11/16**.
> - `PR 5c` (selectores e2e + borrar legacy) pasa de 9/13 a
>   **12/16**.
> - `PR 6a` (cierre de baseline de hidratación G5) pasa de
>   10/13 a **13/16**.
> - `PR 6b` (ensayo de cutover G6) pasa de 11/13 a
>   **14/16**.
> - `PR 6c` (medición de paridad G4 Playwright + Lighthouse)
>   pasa de 12/13 a **15/16**.
> - `PR 3e` (cutover atómico) pasa de 13/13 a **16/16**.
>
> **Conteo de 16 hijos**, **estrategia
> feature-branch-chain**, y el contrato de "el tracker es el
> único PR que apunta a `develop`" se mantienen. Los
> presupuestos LoC por sub-PR se quedan muy por debajo del
> presupuesto de revisión de 400 líneas; **solo permanece la
> excepción previa de `package-lock.json` regenerado de PR
> 3a**. El Enfoque A, FastAPI/SQLite, el predecesor
> congelado, los specs por dominio y las puertas de
> validación quedan sin cambios.

> **2026-09-02 — División por insatisfacibilidad de 3c-d
> (revisión correctiva del plan; sustituye únicamente al viejo
> PR 3c-d monolítico)**. PR 3c-d según el re-ámbito previo
> (animaciones / utilidades + test de paridad final en un solo
> sub-PR) era **insatisfacible**: tres concerns heterogéneos +
> un test de paridad final de alta cardinalidad superaban el
> presupuesto de 400 líneas por sub-PR. La porción CSS se
> **re-divide otra vez en tres hijos secuenciales**, cada uno
> con ≤ 400 líneas authored:
>
> - **PR 3c-d (posición 6/18; reducido)** — base / reset /
>   affordances de estado. Extiende
>   `globals.css::@layer base` con `@keyframes` (`spin`),
>   selectores `color-mix()`, `body { overscroll-behavior:
>   none; … }`, y `main > :first-child { margin-top: 0
>   !important; }`. **Sin clases de utilidad, sin test de
>   paridad.** Superficie de producción permitida:
>   `src/app/globals.css`. Superficie de test permitida:
>   `tests/test_tailwind_4_base_resets.py`.
> - **PR 3c-e (posición 7/18; nuevo)** — clases de utilidad +
>   paridad de animación restante. Extiende
>   `globals.css::@layer base` con la superficie de clases de
>   utilidad (`bg-primary`, `text-on-surface`,
>   `border-outline-variant`, `bg-surface-container-lowest`,
>   `shadow-sm`, `rounded-r-md`, `bg-primary-fixed`,
>   `text-on-primary-fixed`, …) y cualquier `@keyframes` /
>   `color-mix()` restante. **Sin test de paridad.**
>   Superficie de producción permitida:
>   `src/app/globals.css`. Superficie de test permitida:
>   `tests/test_tailwind_4_utilities.py`.
> - **PR 3c-f (posición 8/18; nuevo; solo test de paridad
>   final consolidado)** — **no se envía nuevo código de
>   producción en `globals.css`**. Test parametrizado final
>   `tests/test_tailwind_4_parity.py` que consolida los cinco
>   tests enfocados previos (3c-a tokens / 3c-b taxonomía /
>   3c-c research / 3c-d base-resets / 3c-e utilidades).
>   **La paridad final queda sin cambios en el contrato; ahora
>   pertenece solo al PR 3c-f.**
>
> **Renumeración determinista (corrimiento de +2)**:
> 3d 7/16 → **9/18**; 4a 8/16 → **10/18**; 4b 9/16 → **11/18**;
> 5a 10/16 → **12/18**; 5b 11/16 → **13/18**; 5c 12/16 →
> **14/18**; 6a (G5) 13/16 → **15/18**; 6b (G6) 14/16 →
> **16/18**; 6c (G4) 15/16 → **17/18**; 3e 16/16 → **18/18**.
> 3a / 3b / 3c-a / 3c-b / 3c-c se quedan; **3c-d se queda
> en 6/18** (misma rama, alcance reducido). Ramas nuevas:
> `…-07-3c-e` (base `…-06-3c-d`), `…-08-3c-f` (base
> `…-07-3c-e`). **Recuento de 18 hijos** reemplaza al previo
> de 16; estrategia feature-branch-chain y contrato "tracker
> es el único PR que apunta a `develop`" se mantienen. Los
> presupuestos LoC por sub-PR se quedan muy por debajo de
> 400; solo permanece la excepción previa de
> `package-lock.json` regenerado de PR 3a. El Enfoque A,
> FastAPI/SQLite, el predecesor congelado, G4 / G5 / G6 (ahora
> en 17/18, 15/18, 16/18), los specs por dominio y las
> puertas de validación quedan sin cambios. Los PRs fusionados
> 3c-a/#147, 3c-b/#148, 3c-c/#149 quedan preservados sin
> cambios. **Los cinco hijos CSS (3c-a / 3c-b / 3c-c / 3c-d /
> 3c-e) más el PR 3c-f no pueden colapsarse sin violar el
> presupuesto de revisión de 400 líneas por sub-PR.**

## Frontera de alcance para este archivo de tareas

- **En alcance**: cada sub-PR bajo el Enfoque A listado en
  `design.md` §"Sub-PR slice under Approach A" (posiciones
  1 / 16 a 16 / 16 en la cadena corregida: bootstrap de
  toolchain, exportación estática del App Router, los cuatro
  hijos CSS 3c-a / 3c-b / 3c-c / 3c-d, Makefile/mount, 4a,
  4b, 5a, 5b, 5c, 6a, 6b, 6c, 3e) más el **bloque de
  validación de Fase 6** (reconstrucción G5 / autoría de
  ensayo G6 / medición G4) que corre **después de que el
  camino candidato completo esté acumulado en la rama
  tracker `docs/complete-taxa-frontend-migration-plan`**
  pero **antes** de que PR 3e pueda aterrizar. PR 3e
  (cutover atómico) se publica solo cuando las seis puertas
  están verdes.
- **Los cuatro hijos CSS (3c-a / 3c-b / 3c-c / 3c-d)**
  migran colectivamente el **CSS inline legacy de 1.963
  líneas** del bloque `<style>` de `web/index.html` hacia
  `src/app/globals.css`, particionado por concern para que
  cada hijo publique ≤ 400 líneas authored y sea
  independientemente revisable. El bloque `<style>` legacy
  mismo se borra en PR 5c (el borrado del `web/index.html`
  legacy), por lo que los cuatro hijos CSS escriben código
  nuevo en `src/app/globals.css` sin tocar el archivo legacy
  directamente — los tests
  `tests/test_tailwind_4_tokens.py` /
  `tests/test_taxonomy_styles.py` /
  `tests/test_research_styles.py` /
  `tests/test_tailwind_4_parity.py` leen el `web/index.html`
  legacy para los nombres de tokens / selectores y
  verifican declaraciones no vacías en el nuevo
  `src/app/globals.css` y en el
  `out/_next/static/chunks/*.css` generado.
- **El cierre de G4 / G5 / G6 es trabajo de validación**,
  no un objetivo de migración independiente: sus artefactos
  se registran en `apply-progress.md` §Registro de cambios
  como flips de puertas, y NO DEBEN generar código nuevo en
  `web/**`, handlers de ruta nuevos en `api/server.py`, ni
  archivos nuevos en `extension/**`. Los verificadores /
  medidores de cierre corren contra la build candidata ya
  aterrizada (posiciones 1–12) bajo el fixture de chromium
  que el predecesor capturó.
- **Predecesor congelado**: `openspec/changes/migrate-nextjs-tailwind4/**`
  es historia de solo lectura. La protección de rama
  rechaza cualquier PR que lo edite. La Fase 6 referencia el
  `apply-progress.md` y el `cutover-manifest.json` del
  predecesor solo como entradas de planificación.
- **Invariantes del backend FastAPI preservadas**: los
  handlers de ruta, la lógica SQLite/WAL, el flujo de
  materialize, la defensa SSRF de `save-url` y las formas
  byte a byte de `/api/*` quedan sin cambios. La constante
  `WEB_DIR` en `api/server.py:54` es la única línea que
  puede cambiar en `api/server.py` bajo el Enfoque A, más
  el middleware de fallback SPA de `next/font` `<link
  rel="preload">` / `StaticFiles` estrictamente necesario
  para servir `out/index.html` desde el montaje
  `StaticFiles(html=True)` existente.
- **TDD estricto aplicado**: cada tarea de implementación
  escribe su test que falla PRIMERO. Las tareas siguen los
  marcadores `R` (ROJO), `G` (VERDE), `T` (TRIANGULAR —
  escenarios extra más allá del mínimo que falla el primer
  VERDE), `Refactor` (limpieza sin deriva de comportamiento).
- **Contrato de orden de dependencia**: ningún sub-PR puede
  requerir un archivo que sus predecesores aún no han
  producido. La cadena corregida impone: `toolchain
  bootstrap` → `App Router bootstrap autocontenido de
  static export` → `hijos CSS (3c-a → 3c-b → 3c-c → 3c-d)` →
  `Makefile/mount` → `state` → `ports` → `e2e` →
  `validation` → `atomic cutover`. PR 3a (bootstrap de
  toolchain) aterriza antes que cualquier PR que llame a
  `next build`; el bootstrap autocontenido de exportación
  estática del App Router depende de que `next`, `react`,
  `react-dom`, `typescript`, `tailwindcss` estén instalados
  y de que exista la verificación de Node ≥ 20.9.0; PR 3b
  **no** importa `@taxa/app-shell` (PR 4b) ni
  `./globals.css` (PR 3c-a) — ambos son cierres de defecto
  de dependencia; PR 3c-a posee el archivo `globals.css`, el
  barrel de design-system, y la integración del
  `import "./globals.css";` en layout.tsx; PR 3c-b / 3c-c /
  3c-d extienden `globals.css` incrementalmente y publican
  tests de paridad enfocados por concern; la reescritura del
  Makefile depende de que el toolchain + Tailwind + un
  `src/app/globals.css` no vacío estén en su lugar para que
  `npm run build:web` resuelva; el repoint de `WEB_DIR`
  depende de que `out/index.html` sea producido por el
  target `api` del Makefile; el typed store + guardia de
  hidratación dependen de que el App Router + Tailwind + el
  design system estén en vivo; los puertos de capability
  dependen de que el typed store esté en vivo (para
  `tree-source` y `last-taxon-id`); las actualizaciones
  e2e dependen de los puertos de capability; la validación
  de Fase 6 depende del camino candidato completo; PR 3e
  depende de que las seis puertas estén verdes.

## Pronóstico de carga de revisión

| Campo | Valor |
|-------|-------|
| Líneas modificadas estimadas | ~3.615 authored a través de **16** sub-PRs (bootstrap de toolchain + bootstrap autocontenido de exportación estática del App Router + **4 hijos CSS (3c-a / 3c-b / 3c-c / 3c-d)** + Makefile/mount + 2 browser-state + 2 puertos de capability + e2e/borrar-legacy + 3 validación Fase 6 + 1 cutover atómico). La re-división del CSS particiona la migración del CSS inline legacy de 1.963 líneas en 4 hijos totalizando ~1.500 líneas authored (≤ 400 cada uno); el único PR 3c anterior era ~232 authored. La corrección del defecto de dependencia redistribuye ~30 LoC entre PR 3b (-25), PR 3c-a (+2) y PR 4b (+30) sin cambiar la topología de la cadena. |
| Riesgo de presupuesto de 400 líneas | Bajo para el trabajo authored (los mayores son 3c-a / 3c-b / 3c-c a ≤ 400 cada uno; 5b a ~395; 3d a ~240; 12 / 16 son ≤ 230). PR 3a tiene una excepción aprobada por el usuario únicamente para líneas regeneradas de `package-lock.json`; su trabajo authored de fuente/tests/config permanece ≤400 y no se permite churn de lockfile no relacionado. |
| PRs encadenados recomendados | **Sí** — **16** PRs hijos encadenados (~3.615 líneas authored en total ≫ 400, y el cutover atómico exige que la feature se integre antes de llegar a `develop`) |
| División sugerida | PR 3a (bootstrap de toolchain) → 3b (bootstrap autocontenido de exportación estática del App Router) → **3c-a** (tokens / base / modo oscuro) → **3c-b** (estilos de árbol + Overview inline) → **3c-c** (estilos de Search / Folder / Browser global) → **3c-d** (animaciones / utilidades + paridad final) → 3d (Makefile/mount) → 4a → 4b (guardia de hidratación + integración de AppShell) → 5a → 5b → 5c → Fase 6a (G5) → Fase 6b (G6) → Fase 6c (medición G4) → PR 3e (cutover atómico, con compuerta) |
| Estrategia de entrega | ask-on-risk (según preflight; el Enfoque A ya está bloqueado, sin anulación abierta) |
| Estrategia de cadena | **feature-branch-chain** (elegida por el usuario). El tracker `docs/complete-taxa-frontend-migration-plan` es draft/no-merge y es el **único** PR que apunta a `develop`; el PR hijo 3a apunta al tracker; cada hijo posterior apunta a su rama predecesora inmediata. El primer nuevo hijo CSS (PR 3c-a) trata al PR #146 tracker como el punto de partida fusionado. Sustituye, para este cambio, el default de `AGENTS.md` §4 de apuntar directo a `develop`. |

```text
Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Low (PR 3a generated package-lock.json exception approved)
```

### Topología de la cadena (Feature Branch Chain)

La rama tracker ya existe:
**`docs/complete-taxa-frontend-migration-plan`** (referida
como **PR #146** en la numeración de PRs del proyecto, el
punto de partida fusionado para el primer nuevo hijo CSS).
Permanece en **draft / no-merge** hasta que los 16 PRs hijos
estén revisados e integrados. **Nada llega a `develop`
hasta que el tracker se fusiona.**

> **Justificación del reordenamiento (revisión correctiva
> del plan)**. El `apply-progress.md` original colocaba la
> entrada del App Router en la posición 1 con un testigo de
> `next build` → `out/index.html` que requería que `next`,
> `react`, `tailwindcss`, `typescript` estuvieran instalados
> y que la verificación de Node ≥ 20.9.0 existiera; el
> toolchain mismo estaba programado para la posición 3,
> DESPUÉS de que el testigo del App Router tuviera que estar
> verde. La topología corregida mueve el toolchain a la
> posición 1, degrada el testigo del App Router a la posición
> 2 (ahora satisfacible), mantiene Tailwind/tokens en la
> posición 3, fusiona la reescritura del Makefile con el
> repoint de `WEB_DIR` en la posición 4, y sigue con state,
> ports, e2e, validación de Fase 6 y cutover atómico. El
> conteo de 13 hijos se preserva.

> **Corrección del defecto de dependencia (revisión
> anterior)**. Después del reordenamiento, la re-auditoría
> de pre-flight del portón de apply encontró un segundo
> defecto de dependencia dentro de la topología corregida:
> el PR 3b en la posición 2 importaba `@taxa/app-shell` (un
> módulo que el PR 4b envía en la posición 9/16) y
> `./globals.css` (un archivo que el PR 3c-a envía en la
> posición 3/16). En su testigo de `next build`, ninguno de
> los dos archivos objetivo existía todavía. La misma
> auditoría marcó la aserción de triangulación de PR 3b.5
> que dice que la salida de build referencia la ruta del
> barrel del typed store `@taxa/browser-state` — ese archivo
> de barrel no existe hasta que el PR 4a aterriza. La
> corrección re-ambia el PR 3b a un bootstrap autocontenido
> de exportación estática del App Router (marcadores
> semánticos mínimos; sin AppShell, sin globals.css), mueve
> la línea `import "./globals.css";` al PR 3c-a, y mueve la
> integración de `<AppShell>` al PR 4b. La referencia
> insatisfacible a `@taxa/browser-state` de PR 3b.5 se
> elimina. La topología y el orden de 13 hijos quedan sin
> cambios; la evidencia de prueba de PR 3b (`out/index.html`
> / viewport / preload Raleway) se mantiene; los
> presupuestos LoC por sub-PR se quedan muy por debajo de
> 400.

> **Re-división del CSS (esta revisión)**. La topología
> previa de 13 hijos colocaba al PR 3c en la posición 3 como
> un único sub-PR encargado de migrar el bloque `<style>`
> inline de **1.963 líneas** del `web/index.html` legacy
> mientras se mantenía bajo el presupuesto de revisión por
> PR de 400 líneas — insatisfacible. Por tanto la porción
> de CSS se **re-divide en cuatro hijos encadenados** en
> posiciones 3 / 16, 4 / 16, 5 / 16, 6 / 16 (3c-a / 3c-b /
> 3c-c / 3c-d), cada uno ≤ 400 líneas authored y
> particionado por concern: tokens / base / modo oscuro;
> estilos de árbol + Overview inline; estilos de Search /
> Folder / Browser global; animaciones / utilidades +
> paridad final. El ámbito del PR 3c anterior se particiona
> entre los cuatro hijos sin duplicar código de producción.
> El bloque `<style>` legacy mismo se borra en PR 5c (el
> borrado del `web/index.html` legacy); los cuatro hijos CSS
> autorizan código nuevo en `src/app/globals.css` sin tocar
> el archivo legacy directamente. El **PR #146** tracker es
> el punto de partida fusionado para el primer nuevo hijo
> CSS (PR 3c-a). Cada PR hijo posterior cambia de posición
> por +3 para acomodar los cuatro hijos CSS (3d pasa 4→7;
> 4a 5→8; 4b 6→9; 5a 7→10; 5b 8→11; 5c 9→12; 6a 10→13; 6b
> 11→14; 6c 12→15; 3e 13→16). El **conteo de 16 hijos**
> reemplaza al conteo previo de 13 hijos; las etiquetas
> semánticas (3a, 3b, 3c-a, 3c-b, 3c-c, 3c-d, 3d, 4a, 4b,
> 5a, 5b, 5c, 6a, 6b, 6c, 3e) se preservan; solo cambian el
> contador de posición (NN en
> `feat/complete-taxa-frontend-migration-NN-XXX`) y las
> referencias a las ramas base. **Los presupuestos LoC por
> sub-PR se quedan muy por debajo de 400**; **solo permanece
> la excepción previa de `package-lock.json` regenerado de
> PR 3a**.

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

```text
develop
 └── docs/complete-taxa-frontend-migration-plan   ← PR #146 tracker (draft / no-merge)
      ↑ base del PR 3a: docs/complete-taxa-frontend-migration-plan
      └── feat/complete-taxa-frontend-migration-01-3a   ← bootstrap de toolchain
           ↑ base del PR 3b: …-01-3a
           └── feat/complete-taxa-frontend-migration-02-3b   ← bootstrap autocontenido de exportación estática del App Router
                ↑ base del PR 3c-a: …-02-3b
                └── feat/complete-taxa-frontend-migration-03-3c-a   ← tokens / base / modo oscuro
                     ↑ base del PR 3c-b: …-03-3c-a
                     └── feat/complete-taxa-frontend-migration-04-3c-b   ← estilos de árbol + Overview inline
                          ↑ base del PR 3c-c: …-04-3c-b
                          └── feat/complete-taxa-frontend-migration-05-3c-c   ← estilos de Search / Folder / Browser global
                               ↑ base del PR 3c-d: …-05-3c-c
                               └── feat/complete-taxa-frontend-migration-06-3c-d   ← animaciones / utilidades + paridad final
                                    ↑ base del PR 3d: …-06-3c-d
                                    └── feat/complete-taxa-frontend-migration-07-3d   ← Makefile/mount
                                         ↑ … 4a → 4b → 5a → 5b → 5c → 6a → 6b → 6c …
                                         └── feat/complete-taxa-frontend-migration-16-3e
                                              ← cutover atómico, último hijo de la cadena
```

**Dependencia por sub-PR (el contrato que la revisión
correctiva del plan + corrección del defecto de dependencia
+ re-división del CSS impone)**:

- **PR 3a — bootstrap de toolchain**. Autocontenido.
  Produce `package.json` (con `next`, `react`, `react-dom`,
  `tailwindcss`, `typescript`, `@types/react`,
  `@types/react-dom`, `@types/node` pineados;
  `engines.node ">=20.9.0"`; scripts `check-runtime` y
  `build:web`), `scripts/check-runtime.mjs`,
  `tsconfig.json` (modificado en su lugar; el predecesor ya
  existe en la raíz del repo; config base + aliases de ruta
  `@taxa/<capability>`) y `.nvmrc`. Verificación: `npm ci`
  exit 0; `node scripts/check-runtime.mjs` exit 0 en Node ≥
  20.9.0, exit distinto de cero abajo; `npx tsc --noEmit`
  resuelve cada alias `@taxa/*` (contra un mapa de aliases
  vacío; PRs subsiguientes pueblan los módulos).
- **PR 3b — exportación estática del App Router**. Depende
  de **3a**: deps instaladas + contrato Node ≥ 20.9.0.
  Produce `src/app/{layout,page}.tsx`, `next.config.mjs` y
  el testigo `tests/test_app_shell_render.py` que corre
  `npx next build` y lee `out/index.html`. Este testigo es
  satisfacible aquí porque el toolchain está en vivo; no
  pudo satisfacerse en el ordenamiento original porque
  `npx next build` aún no tenía el binario `next`.
- **PR 3c-a — tokens / base / modo oscuro**. Depende de
  **3a** (`tailwindcss@^4` instalado) y de **3b** (el
  `src/app/layout.tsx` marcador en el que el PR 3c-a
  importa `./globals.css`). Crea `src/app/globals.css`
  (andamio inicial: `@import "tailwindcss";` + bloque
  `@theme { … }` reflejando cada token `:root` legacy —
  paleta clara, paleta oscura `[data-theme="dark"]`, familia
  `--realm-*` — + placeholder vacío `@layer base { … }` para
  que los hijos posteriores (3c-b / 3c-c / 3c-d) extiendan
  con reglas de `@layer components` de taxonomía, reglas
  de research / chrome, y reglas de `@keyframes` /
  `color-mix()` / utilidad / reset respectivamente), envía
  el barrel de design-system
  (`src/modules/design-system/{infrastructure/index.ts,
  presentation/Icon.tsx, presentation/Button.tsx}`), y
  cablea `import "./globals.css";` en `src/app/layout.tsx`
  (delta de 1 línea — la costura de corrección del defecto
  de dependencia). El test de triangulación
  `tests/test_tailwind_4_tokens.py` lee el bloque
  `<style>` legacy del `web/index.html` y verifica que cada
  token `:root` / `[data-theme="dark"]` / `--realm-*`
  resuelve a una declaración no vacía en
  `globals.css::@theme`.
- **PR 3c-b — estilos de árbol + Overview inline**. Depende
  de **3c-a** (el andamio inicial de `src/app/globals.css`
  existe + el placeholder de `@layer base` está en su
  lugar). Extiende `globals.css` con las reglas de
  `@layer components` para el **módulo taxonomy**
  (`.taxa-tree`, `.tree-row`, `.kebab`, `.kebab-menu`,
  `.tree-search-icon`, `.materialize-indicator`,
  `.detail-panel`, `.tab-strip`, `.tab-button`,
  `.overview-tab`, `.breadcrumb` — cada uno lleva el kebab
  por fila, el icono de búsqueda por fila, el indicador de
  materialize por fila, la familia monoespaciada del
  breadcrumb para los segmentos de nombre científico, y el
  styling del strip de tres pestañas `Overview` / `Search` /
  `Folder` desde la superficie de UI verificada). El test
  de triangulación `tests/test_taxonomy_styles.py` lee el
  `out/_next/static/chunks/*.css` generado y verifica que
  cada selector de taxonomía resuelve.
- **PR 3c-c — estilos de Search / Folder / Browser
  global**. Depende de **3c-b** (el bloque de
  `@layer components` de taxonomía está en su lugar).
  Extiende `globals.css` con los selectores del módulo
  research y del shell de chrome (`.search-tab`,
  `.search-category-section`, `.search-link-list`,
  `.search-link`, `.folder-tab`, `.header-browser-tab`,
  `.research-explorer`, `.file-explorer-pane`,
  `.file-viewer-pane` — cada uno lleva la fuerza kebab
  `Search online` → pestaña `Search`, las cinco secciones
  de categoría en orden fijo `General` / `Taxonomic` /
  `Academic` / `Multimedia` / `Documents`, el contrato de
  anchor `target="_blank"` / `rel="noopener noreferrer"` del
  `SearchLinkList`, y la pestaña `Browser` del header del
  Research / file explorer global que NO está scoped por
  taxón). El test de triangulación
  `tests/test_research_styles.py` enumera cada selector de
  research / chrome.
- **PR 3c-d — animaciones / utilidades + paridad final**.
  Depende de **3c-c** (el bloque de `@layer components` de
  research / chrome está en su lugar). Extiende
  `globals.css` con `@keyframes` (`spin`), los selectores de
  `color-mix()`, la superficie de clases de utilidad
  (`bg-primary`, `text-on-surface`,
  `border-outline-variant`, `bg-surface-container-lowest`,
  `shadow-sm`, `rounded-r-md`, `bg-primary-fixed`,
  `text-on-primary-fixed`, …), la regla
  `body { overscroll-behavior: none; … }`, y el reset
  `main > :first-child { margin-top: 0 !important; }` —
  todo bajo `@layer base` en orden de fuente. Envía el test
  de paridad **final** `tests/test_tailwind_4_parity.py`
  (parametrizado sobre cada token `:root` legacy, cada
  referencia `var(--token)`, cada clase de utilidad legacy,
  y cada selector `@keyframes` / `color-mix()`). El test de
  paridad final de PR 3c-d es el testigo de consolidación de
  que el CSS inline legacy de **1.963 líneas** ha sido
  migrado a `src/app/globals.css` de extremo a extremo.
- **PR 3d — Makefile/mount**. Depende de **3b** (el App
  Router produce `out/index.html` cuando `next build`
  corre) y de **3c-d** (los tokens de Tailwind 4 +
  `@layer base` fluyen a través de `next build`; el test de
  paridad final está en disco). Produce la reescritura de
  `Makefile::api` (`check-runtime.mjs` → `npm run build:web`
  → `uvicorn … --port 8765` en orden, con `make css`
  volviéndose un shim no-op), el repoint de 1 línea
  `api/server.py:54` `WEB_DIR`, `src/data/search-engines.js`
  (copia byte a byte de `web/search_urls.js` con export
  nombrado `SEARCH_ENGINES`), la actualización de ruta
  `open()` de `tests/test_smoke.py` (contrato AC-21
  preservado), y los testigos `tests/test_make_api_build.py`
  más `tests/test_static_mount.py`.
- **PR 4a — typed store**. Depende de **3c-a** (barrel de
  design-system cargado); produce
  `src/modules/browser-state/**` typed store con cuatro
  sitios de lectura + cuatro de escritura.
- **PR 4b — guardia de hidratación + integración de
  AppShell**. Depende de **4a** (store disponible), **3b**
  (los marcadores `src/app/{layout,page}.tsx` en los que el
  PR 4b integra `<AppShell>`), y **3c-a** (los tokens
  `@theme` de Tailwind 4 + barrel de design-system cargados
  para `next build`). Produce
  `src/modules/app-shell/{presentation/AppShell.tsx,
  infrastructure/page-chrome.tsx}` Y modifica
  `src/app/layout.tsx` para `import { AppShell } from
  "@taxa/app-shell"` y envolver el contenido del body en
  `<AppShell>`; integra el flag `mounted` seguro de
  hidratación y la frontera `"use client"` en
  `src/app/page.tsx`. El testigo Playwright de cero warnings
  de hidratación verifica el AppShell integrado.
- **PR 5a — port de taxonomy**. Depende de **4b**
  (lectura de estado segura de hidratación para
  `tree-source`) y de **3c-b** (el bloque de
  `@layer components` de taxonomía está en su lugar — los
  selectores de taxonomía se montan sobre el CSS de PR
  3c-b). Produce `src/modules/taxonomy/**` + el port de
  `web/{tree,detail,breadcrumb}.js` a React. PR 5a también
  envía el andamio del strip de pestañas de `DetailPanel`
  (strip de 3 pestañas `Overview` / `Search` / `Folder`) y
  el cuerpo de `OverviewTab` (nombre científico, estado de
  aceptación, autoría, conteo de especies); los selectores
  del strip de pestañas y el styling de OverviewTab
  correspondientes se montan sobre el bloque de
  `@layer components` de PR 3c-b.
- **PR 5b — port de research + pin CDN**. Depende de
  **5a** (flujos de lectura de estado de taxonomía
  compartidos con research y el andamio del strip de
  pestañas de `DetailPanel` en el que la acción `Search
  online` se enchufa), de **3d**
  (`src/data/search-engines.js` para el export nombrado
  `Engine`), y de **3c-c** (el bloque de `@layer components`
  de research / chrome está en su lugar — los selectores de
  research se montan sobre el CSS de PR 3c-c). Produce
  `src/modules/research/**` + pin CDN. PR 5b también envía
  el cuerpo de `SearchTab` (lista categorizada de enlaces
  salientes en orden fijo `General` / `Taxonomic` /
  `Academic` / `Multimedia` / `Documents`), el cuerpo de
  `FolderTab`, el presentador `SearchLinkList` que mapea
  cada `Engine` a un anchor con `target="_blank"` y
  `rel="noopener noreferrer"`, y el re-anclaje de la
  pestaña `Browser` del header como el Research / file
  explorer global (NO scoped por taxón); los selectores
  correspondientes se montan sobre el bloque de
  `@layer components` de PR 3c-c.
- **PR 5c — selectores E2E + contrato `data-*` + borrar
  legacy**. Depende de **5b** (todos los componentes UI en
  vivo) y de **3c-d** (el test de paridad final de Tailwind
  4 está en disco). Actualiza los selectores DOM de Playwright
  para el árbol de componentes React (el contrato de
  atributos `data-*` se preserva; las clases CSS subyacentes
  cambian a clases de utilidad de Tailwind 4); borra
  `web/*.{html,js,css}` + `tailwind.config.js` (el borrado
  del `web/index.html` legacy retira el CSS inline legacy de
  1.963 líneas que los cuatro hijos CSS (3c-a / 3c-b / 3c-c
  / 3c-d) migraron a `src/app/globals.css`).
- **PR 6a / 6b / 6c — validación de Fase 6**. Depende de
  **5c** (camino candidato completo). Autoriza los tres
  verificadores de cierre de puerta contra la build
  candidata.
- **PR 3e — cutover atómico**. Depende de que las seis
  puertas estén verdes. Flipa la copia de trabajo de
  `cutover-manifest.json`, re-corre el verificador G3
  Tier-2 contra la selección activada, flipa el footer de
  §Status de `apply-progress.md`.

**Flujo de integración**: los hijos se fusionan **en orden**
dentro del tracker. A medida que cada hijo se fusiona, el
siguiente se reapunta al tracker (GitHub reapunta
automáticamente cuando la rama base se fusiona y se borra);
el tracker acumula la feature completa. Una vez que PR 3e
(el último hijo) se fusiona, el tracker sale de draft y se
fusiona a `develop` como único punto de integración.

**El cuerpo de cada PR hijo DEBE llevar** la sección
`## Chain Context` (Chain / Tracker PR / Position / Base /
Depends on / Follow-up / Review budget / Starts at / Ends
with) más un diagrama de dependencias que marque el PR
actual con `📍`. La sección Chain Context se **añade** a la
plantilla de PR del repo — no reemplaza las secciones
requeridas `## Resumen` / `## Cambios` / `## Validación` /
`## Lo que NO cambió`.

**Higiene de diff**: un PR hijo cuyo diff muestre archivos
fuera de su propia rebanada es un **bug de base**, no un
hallazgo de revisión. Reapuntar o rebasear sobre el
predecesor correcto hasta que solo aparezca la unidad de
trabajo actual.

> Orden: **3a → 3b → 3c-a → 3c-b → 3c-c → 3c-d → 3d → 4a
> → 4b → 5a → 5b → 5c → 6a (G5) → 6b (G6) → 6c (medición
> G4) → 3e**. Cada PR hijo apunta a su **rama predecesora
> inmediata**; solo el tracker apunta a `develop`. La Fase
> 6 corre **después** de que el camino candidato completo
> (posiciones 1–12) esté verde y acumulado en el tracker, y
> **antes** de que PR 3e pueda aterrizar. PR 3e tiene
> compuerta en G1 + G2 + G3 Tier-1 (todos registrados del
> predecesor) más el cierre de G4 + G5 + G6 (los tres
> entregados por la Fase 6). Reversión = `git revert
> <pr3e-sha>` (ver §"Reversión bajo la cadena").

## Marcadores de TDD estricto

Cada tarea usa uno de cuatro marcadores, en línea con el
vocabulario de tareas del predecesor y el precedente
strict-TDD de `tests/test_module_layers.py` /
`tests/test_no_restricted_imports.py`:

- `R` — ROJO. Autora el test que falla (o aserción
  expandida) PRIMERO. El repo DEBE permanecer verde antes
  de añadir el test; el test nuevo DEBE fallar por la
  razón correcta antes de escribir cualquier código de
  producción.
- `G` — VERDE. Implementa el código de producción mínimo
  que invierte ROJO a VERDE. Sin expansión de alcance más
  allá del test que falla.
- `T` — TRIANGULAR. Añade los escenarios adicionales que
  atrapan el siguiente modo de fallo (matriz
  parametrizada, casos de borde, cláusulas "y / y / y"
  estilo RFC-2119). Cada escenario de triangulación
  aterriza con su propio ciclo de
  test-falla-luego-pasa.
- `Refactor` — Limpia el código VERDE (renombrar,
  extraer, deduplicar). Los tests DEBEN seguir verdes; el
  refactor NO DEBE cambiar el comportamiento observable
  ni empujar el diff por encima del presupuesto de
  revisión de 400 líneas.

## Fase 3a: Bootstrap de toolchain (PR 3a → rama tracker)

Instala el toolchain de Next 16 / React 19 / Tailwind 4 /
TypeScript, pinea el contrato de runtime de Node ≥ 20.9.0
y escribe las convenciones de repo de las que depende cada
sub-PR subsiguiente. **Este PR DEBE aterrizar antes que
cualquier otro sub-PR en la cadena** — la exportación
estática del App Router en la posición 2 no puede
satisfacer su testigo de `next build` sin el toolchain
instalado aquí.

Re-ambiado del `tasks.md` original del 2026-09-02 (que
colocaba este trabajo en la `Fase 3c` DESPUÉS de la
entrada del App Router): el defecto de orden de dependencia
que el portón de apply identificó movió los pins de deps
de `package.json`, la verificación de runtime de Node de
`scripts/check-runtime.mjs`, la config base + aliases de
ruta de `tsconfig.json` y el helper `.nvmrc` a la posición
1. La reescritura de `Makefile::api` sola del PR 3c
original se mueve a la posición 7 (`Fase 3d` en la
topología corregida, con los cuatro hijos CSS insertados
en las posiciones 3–6).

- [ ] 3a.1 R — `tests/test_toolchain_bootstrap.py` (nuevo):
      lee `package.json` y verifica (a) que el literal
      `engines.node` es `">=20.9.0"`, (b) que cada
      dependencia requerida está presente en
      `dependencies` o `devDependencies` —
      `next@^16`, `react@^19`, `react-dom@^19`,
      `tailwindcss@^4`, `typescript@>=5.1.0`,
      `@types/react@^19`, `@types/react-dom@^19`,
      `@types/node` — y que los legacy `autoprefixer`,
      `postcss`, `@tailwindcss/forms` están ausentes;
      verifica que `scripts.check-runtime` y
      `scripts.build:web` están definidos; verifica que
      `tsconfig.json` existe en la raíz del repo con
      `compilerOptions.paths` conteniendo los aliases
      `@taxa/<capability>` que coinciden con el conjunto
      `CAPABILITIES` del predecesor
      `tests/test_module_layers.py`; verifica que
      `.nvmrc` existe y pinea Node ≥ 20.9.0 (literal). El
      test DEBE fallar en un clon fresco del repo (sin
      deps de `package.json` aún).
      <!-- sdd-owner: implementation -->
- [ ] 3a.2 G — `package.json` (modificado, ~50 LoC de
      delta) más `package-lock.json` regenerado (la única excepción de tamaño aprobada por el usuario; debe contener únicamente cambios de resolución requeridos por este manifiesto y revisarse junto con él): bumpea `next`, `react`, `react-dom`,
      `tailwindcss` a las versiones mayores pineadas
      arriba; añade el toolchain de TypeScript; elimina los
      `autoprefixer`, `postcss`, `@tailwindcss/forms`
      legacy; configura
      `engines.node = ">=20.9.0"`; añade
      `scripts.check-runtime = "node scripts/check-runtime.mjs"`
      y `scripts.build:web = "next build"`. Ningún otro
      campo cambia. <!-- sdd-owner: implementation -->
- [ ] 3a.3 G — `scripts/check-runtime.mjs` (nuevo, ~25
      LoC): compara `process.versions.node` contra el piso
      requerido `20.9.0` (codificado como literal en el
      script para que el test lo verifique); sale
      distinto de cero con un error claro que nombra la
      versión observada vs requerida de Node cuando está
      por debajo del piso; sale 0 en ≥ 20.9.0.
      <!-- sdd-owner: implementation -->
- [ ] 3a.4 G — `tsconfig.json` (modificado en su lugar;
      el predecesor ya existe en la raíz del repo;
      ~50 LoC de delta): config base de TypeScript —
      `compilerOptions.target`, `module`, `moduleResolution`,
      `jsx`, `strict`, `noUncheckedIndexedAccess`, `paths`
      (los aliases `@taxa/<capability>` mapeados a
      `src/modules/<capability>`), `baseUrl`. El contrato
      de aliases coincide con el conjunto `CAPABILITIES`
      que el predecesor publica en
      `tests/test_module_layers.py`. Sin archivos
      `src/**` aún — `npx tsc --noEmit` contra un
      `include: ["src/**/*.ts", "src/**/*.tsx"]` vacío es
      un no-op (el mapa de aliases está en su lugar
      incluso antes de que exista cualquier archivo de
      módulo; PRs subsiguientes añaden archivos de módulo).
      <!-- sdd-owner: implementation -->
- [ ] 3a.5 G — `.nvmrc` (nuevo, 1 LoC): contiene el
      literal `20` (nvm resolverá al último 20.x.y, que es
      ≥ 20.9.0 una vez que Node 20.9 publique; la
      declaración `engines.node` es el contrato vinculante,
      `.nvmrc` es una pista de conveniencia).
      <!-- sdd-owner: implementation -->
- [ ] 3a.6 R — `tests/test_check_runtime.py` (nuevo):
      mockea `process.versions.node` (vía un pequeño shim
      de tiempo de `require` o parchando `process.versions`
      dentro de un proceso hijo de Node) a (a) un valor
      por debajo de `20.9.0` y verifica que
      `scripts/check-runtime.mjs` sale distinto de cero
      con una línea de stderr clara que nombra la versión
      observada; (b) un valor en o por encima de `20.9.0` y
      verifica que sale 0. El test corre vía
      `subprocess.run([node, scripts/check-runtime.mjs])` en
      dos escenarios pasando un pequeño archivo override
      `scripts/_test-check-runtime.mjs` que lanza antes
      de llegar a la verificación del piso.
      <!-- sdd-owner: implementation -->
- [ ] 3a.7 T — triangulación de
      `tests/test_toolchain_bootstrap.py`: verifica (a)
      que el literal `engines.node` es `">=20.9.0"`
      exactamente (sin `~`, `^`, ni deriva de subversión
      pineada); (b) que cada dep pineada satisface
      `^MAJOR` con la versión mayor listada arriba (sin
      que `next@^15` se cuele de vuelta); (c) que
      `scripts.check-runtime` comienza con el literal
      `node scripts/check-runtime.mjs` (no `nodejs` y sin
      ruta con espacios en blanco); (d) que
      `tsconfig.json::paths` resuelve cada entrada en el
      conjunto `CAPABILITIES` que el predecesor pinea;
      (e) que `.nvmrc` es exactamente el literal `20`
      (línea única, salto de línea final).
      <!-- sdd-owner: implementation -->
- [ ] 3a.8 Refactor — alfabetizar las claves de
      dependencias de `package.json`; asegurar que el
      orden de campos de `tsconfig.json` coincide con la
      plantilla canónica de TS 5.x; asegurar que
      `scripts/check-runtime.mjs` lee el piso de un
      parse de `package.json::engines.node` (en lugar de
      un literal hardcoded) para que un bump futuro sea
      un cambio de un solo archivo.
      <!-- sdd-owner: implementation -->

**Evidencia por tarea (test enfocado + harness de runtime +
reversión)**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3a.1 | `.venv/bin/python3 -m pytest tests/test_toolchain_bootstrap.py -v` | `ls package.json scripts/check-runtime.mjs tsconfig.json .nvmrc` no vacío | `git revert <3a-sha>` elimina `scripts/check-runtime.mjs`, `.nvmrc`, restaura `tsconfig.json` a su estado del predecesor, restaura `package.json` y `package-lock.json` a deps legacy; nada más tocado |
| 3a.2 | mismo | `node -e "const p=require('./package.json'); assert(p.engines.node === '>=20.9.0')"`; `npm ci` exit 0 | mismo |
| 3a.3 | `.venv/bin/python3 -m pytest tests/test_check_runtime.py -v` | `node scripts/check-runtime.mjs` exit 0 en Node ≥ 20.9.0, exit 1 abajo | mismo |
| 3a.4 | mismo que 3a.1 (verificaciones de aliases) | `npx tsc --noEmit` exit 0 contra el árbol `src/**` (vacío) | mismo |
| 3a.5 | mismo que 3a.1 (verificación del literal `.nvmrc`) | `cat .nvmrc` devuelve el literal `20` | mismo |
| 3a.6 | `.venv/bin/python3 -m pytest tests/test_check_runtime.py -v` | los dos escenarios de arriba | mismo |
| 3a.7 | mismo que 3a.1 | mismo que 3a.1 | mismo |
| 3a.8 | mismo que 3a.1 + 3a.3 | mismo que 3a.1 + 3a.3 | mismo |

## Fase 3b: Bootstrap autocontenido de exportación estática del App Router (PR 3b → rama del PR 3a)

Rebana la tarea 3.1 del predecesor
(`src/app/{layout,page}.tsx` + `next.config.mjs`) en un
**bootstrap autocontenido de exportación estática del App
Router** cuyo testigo de `out/index.html` es satisfacible
SOLO porque (a) el toolchain del PR 3a ya existe **y** (b)
el PR 3b no importa nada que sus sucesores produzcan. El PR
3b **no** importa `@taxa/app-shell` (el PR 4b lo envía) ni
`./globals.css` (el PR 3c-a lo envía); los archivos
layout/page renderizan un cuerpo marcador semántico mínimo
para que `npx next build` tenga éxito. Esta es la
resolución del defecto de dependencia que la revisión
correctiva identifica: en la topología corregida (toolchain
en la posición 1, hijos CSS en posiciones 3–6), el testigo
del PR 3b tenía toolchain pero sus imports aún apuntaban a
archivos que aterrizaban más tarde en la cadena (AppShell
en 9/16, globals.css en 3/16). Re-ambiar 3b a un bootstrap
autocontenido cierra el defecto sin cambiar la topología
de la cadena.

- [ ] 3b.1 R — `tests/test_app_shell_render.py` (nuevo):
      invoca `npx next build` en un clon `tmp_path` (o vía
      shim de subproceso) y verifica que la build emite
      `out/index.html` con `<html lang="en">`, `<head>`
      lleva un `<meta name="viewport" content="width=device-width,
      initial-scale=1">`, y un `<link rel="preload" …>`
      para la fuente Raleway que produce `next/font/google`.
      El test lee `out/index.html` después de `next build`
      y verifica el contrato de marcado. El test DEBE
      fallar en una rama PR 3b fresca (sin
      `src/app/{layout,page}.tsx` aún).
      <!-- sdd-owner: implementation -->
- [ ] 3b.2 G — `src/app/layout.tsx` (nuevo, ~40 LoC): shell
      host de `<html>` / `<body>`, importa
      `next/font/google` para `Raleway`, `JetBrains Mono`,
      `Material Symbols Outlined`, renderiza un cuerpo
      marcador semántico mínimo (por ej. un shell
      `<main><h1>Taxa</h1></main>`).
      **NO monta `<AppShell>`** (aterriza en PR 4b) **y
      NO importa `./globals.css`** (aterriza en PR 3c-a) —
      PR 3b es autocontenido para que `npx next build`
      tenga éxito en su posición.
      <!-- sdd-owner: implementation -->
- [ ] 3b.3 G — `src/app/page.tsx` (nuevo, ~30 LoC): una
      página marcadora semántica mínima (renderiza el
      cuerpo marcador dentro del `<body>` de
      `layout.tsx`). **NO envuelve `<AppShell>`**
      (aterriza en PR 4b) **y NO incluye una frontera
      `"use client"`** (aterriza en PR 4b cuando el
      AppShell la necesita) — PR 3b es autocontenido. La
      integración del AppShell en PR 4b reemplaza este
      cuerpo marcador con la composición completa del
      AppShell.
      <!-- sdd-owner: implementation -->
- [ ] 3b.4 G — `next.config.mjs` (nuevo, ~30 LoC):
      declara `output: "export"`,
      `images: { unoptimized: true }`,
      `trailingSlash: false`, `reactStrictMode: true`;
      coincide con el contrato G2 en `design.md` §"Static
      build / start lifecycle". <!-- sdd-owner: implementation -->
- [ ] 3b.5 T — triangulación de
      `tests/test_app_shell_render.py`: verifica que el
      `out/.next/build-manifest.json` generado lleva la
      entrada esperada para `src/app/layout.tsx` y
      `src/app/page.tsx`; verifica que el elemento
      `<body>` en el primer paint NO lleva un atributo
      `data-theme` (sin lectura de localStorage antes de
      la hidratación); verifica que el
      `out/_next/static/media/*.woff2` generado lleva el
      archivo de fuente Raleway que produjo
      `next/font/google` (el pipeline de preload Raleway
      está activo de extremo a extremo). El contrato de
      alias de ruta del PR 3a lo verifica
      `tests/test_toolchain_bootstrap.py::3a.7` y no
      necesita re-verificarse aquí (los imports del PR 3b
      resuelven contra el mapa de aliases vacío; los
      archivos de barrel aterrizan en sus sub-PRs dueños).
      <!-- sdd-owner: implementation -->
- [ ] 3b.6 Refactor — asegurar que el par layout/page es
      el marcador semántico mínimo necesario para
      satisfacer el testigo 3b.1 / 3b.5 (solo preload
      Raleway, sin AppShell, sin globals.css); asegurar
      que la build de Next.js + Turbopack completa dentro
      del presupuesto del predecesor registrado (sin
      regresión más allá del requisito de paridad ≤ 0 %
      en `design.md` §"Parity / evidence plan").
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3b.1, 3b.5 | `.venv/bin/python3 -m pytest tests/test_app_shell_render.py -v` | `npx next build` exit 0; `out/index.html` no vacío; `out/.next/build-manifest.json` lleva las entradas esperadas | `git revert <3b-sha>` elimina `src/app/{layout,page}.tsx`, `next.config.mjs`; el toolchain del PR 3a se queda; nada más tocado |
| 3b.2, 3b.3 | mismo | mismo | mismo |
| 3b.4 | mismo | mismo | mismo |
| 3b.6 | mismo | `npx tsc --noEmit` exit 0 contra `src/` | mismo |

## Fase 3c-a: Tokens / base / modo oscuro (PR 3c-a → rama del PR 3b)

Posición 3/16 — el **primer nuevo hijo CSS** de la
re-división del CSS. El único PR 3c previo en la posición
3/13 intentó migrar el bloque `<style>` inline de 1.963
líneas del `web/index.html` legacy en un sub-PR mientras
se mantenía bajo el presupuesto de revisión por PR de 400
líneas — insatisfacible. PR 3c-a por tanto posee la
**fundación de CSS**: el andamio del archivo
`src/app/globals.css` con `@theme` (cada token legacy
`:root` / `[data-theme="dark"]` / `--realm-*`), el barrel
de design-system (`<Icon>`, `<Button>`), y la integración
de `import "./globals.css";` en `src/app/layout.tsx` (la
costura de corrección del defecto de dependencia). Las 1.963
líneas legacy restantes se particionan entre PR 3c-b
(selectores de taxonomía), PR 3c-c (selectores de research
/ chrome), y PR 3c-d (animaciones / utilidades + paridad
final). Depende de PR 3a (`tailwindcss@^4` instalado) y PR
3b (el `src/app/layout.tsx` marcador en el que el PR 3c-a
importa `./globals.css`).

- [ ] 3c-a.1 R — `tests/test_tailwind_4_tokens.py`
      (nuevo): lee `web/index.html` (fuente legacy) y
      verifica que cada token `:root { --x }` (paleta
      clara), cada token `[data-theme="dark"] { --x }`
      (paleta oscura), y cada token de la familia
      `--realm-*` está declarado con el mismo nombre y un
      valor no vacío en el bloque `@theme` de
      `src/app/globals.css`; verifica que cada referencia
      `var(--x)` en el bloque `<style>` legacy resuelve a
      una declaración no vacía (testigo inicial para el
      subconjunto solo-tokens; el test de paridad final
      de PR 3c-d cubre la superficie completa).
      <!-- sdd-owner: implementation -->
- [ ] 3c-a.2 G — `src/app/globals.css` (nuevo, ~250
      LoC): el andamio inicial —
 `@import "tailwindcss";` + bloque `@theme { … }`
      reflejando cada token `:root` legacy (paleta clara,
      paleta oscura `[data-theme="dark"]`, familia
      `--realm-*`) + placeholder vacío `@layer base { … }`
      para que los hijos posteriores (3c-b / 3c-c / 3c-d)
      extiendan con reglas de `@layer components` de
      taxonomía, reglas de research / chrome, y reglas de
      `@keyframes` / `color-mix()` / utilidad / reset
      respectivamente. El bloque `@theme` de PR 3c-a es la
      traducción con namespace de Tailwind 4 de los bloques
      `:root { … }` y `[data-theme="dark"] { … }` legacy;
      los tokens legacy `--primary`, `--bg-surface`,
      `--realm-*` resuelven sin cambios vía aliases de
      `@theme` (cumple el requisito de estabilidad de
      namespace de `design.md` §"Design tokens").
      <!-- sdd-owner: implementation -->
- [ ] 3c-a.3 G — `src/app/layout.tsx` (modificado, delta
      de 1 línea): añade `import "./globals.css";` cerca
      del tope para que las directivas `@import "tailwindcss"`
      de Tailwind 4 fluyan en la build de Next.js. PR 3c-a
      posee este import porque posee `src/app/globals.css`;
      el defecto de dependencia (PR 3b importando un archivo
      que el PR 3c-a envía) se cierra aquí. El test de
      paridad 3c-a.1 T existente (`@theme` lleva las
      declaraciones de tokens esperadas) es el testigo de
      regresión de que el import cablea `globals.css` en la
      build.
      <!-- sdd-owner: implementation -->
- [ ] 3c-a.4 G —
      `src/modules/design-system/infrastructure/index.ts`
      (nuevo, ~20 LoC): el barrel de design-system
      exporta el `<Icon>` (envoltorio de glyphs Material
      Symbols Outlined, nombres congelados: `search`,
      `folder_open`, `folder`, `chevron_right`,
      `expand_more`, `close`, `settings`, `help`,
      `science`, `science_off`, `download`) más la
      primitiva de layout `<Button>`. El barrel se envía
      aquí para que PR 4a / 5a / 5b puedan consumirlo; el
      archivo de barrel es lo suficientemente pequeño
      para caber dentro del presupuesto ≤ 400 líneas de
      PR 3c-a. <!-- sdd-owner: implementation -->
- [ ] 3c-a.5 G — `src/modules/design-system/presentation/Icon.tsx`
      (nuevo, ~60 LoC): el componente React `<Icon
      name="…" />` que renderiza un envoltorio
      `<span class="material-symbols-outlined">{name}</span>`;
      acepta solo el conjunto `name` congelado listado en
      3c-a.4 (tipo parametrizado); renderiza con
      `aria-hidden` por defecto y un `role="img"` opt-in.
      <!-- sdd-owner: implementation -->
- [ ] 3c-a.6 G — `src/modules/design-system/presentation/Button.tsx`
      (nuevo, ~40 LoC): la primitiva de layout React
      `<Button variant="…" size="…">`; renderiza un
      `<button>` con clases de utilidad de Tailwind 4
      (`bg-primary`, `text-on-primary`, `rounded-r-md`,
      `shadow-sm`, …) que se montan sobre la superficie de
      clases de utilidad de PR 3c-d (las clases de
      utilidad de Tailwind 4 las emite `next build` desde
      los tokens de `@theme` que PR 3c-a envía; el bloque
      `@layer base` de PR 3c-d finaliza la superficie).
      <!-- sdd-owner: implementation -->
- [ ] 3c-a.7 T — extender la triangulación de
      `tests/test_tailwind_4_tokens.py`: verifica (a) que
      los aliases del namespace `--color-primary` de
      Tailwind 4 resuelven al valor legacy `--primary`
      (atrapa deriva silenciosa del namespace); (b) que
      cada token de la paleta oscura bajo
      `[data-theme="dark"]` está reflejado en el bloque
      `@theme` bajo el selector `dark` (para que las
      variantes `dark:` de Tailwind 4 resuelvan en tiempo
      de build); (c) que cada token `--realm-*` resuelve
      sin cambios desde el bloque `<style>` legacy; (d)
      que el placeholder vacío `@layer base { … }` existe
      y está vacío (PR 3c-b / 3c-c / 3c-d poseen su
      población). <!-- sdd-owner: implementation -->
- [ ] 3c-a.8 Refactor — alfabetizar las claves de
      `@theme`; asegurar que los exports de
      `src/modules/design-system/infrastructure/index.ts`
      están ordenados `<Icon>` luego `<Button>` (siguiendo
      el nombrado canónico que el predecesor PR 2a
      scaffoldingó); asegurar que `src/app/globals.css`
      abre con `@import "tailwindcss";` en la línea 1 (sin
      BOM, sin comentario líder) para que la build cablee
      tokens deterministamente.
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c-a.1, 3c-a.7 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_tokens.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` lleva cada alias de Tailwind 4 de los tokens legacy `:root` bajo `@theme` | `git revert <3c-a-sha>` elimina `src/app/globals.css`, `src/modules/design-system/**`, Y elimina la línea `import "./globals.css";` de `src/app/layout.tsx`; Fases 3a + 3b intactas |
| 3c-a.2 | mismo | mismo | mismo |
| 3c-a.3 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_tokens.py -v` | `npx next build` exit 0; el `out/_next/static/chunks/*.css` generado lleva las utilidades de Tailwind 4 derivadas de `globals.css::@theme` (la línea `import "./globals.css";` en layout.tsx cablea `globals.css` en la build) | mismo |
| 3c-a.4, 3c-a.5, 3c-a.6 | `.venv/bin/python3 -m pytest tests/test_design_system_purity.py -v` | `npx tsc --noEmit` contra `src/modules/design-system/` | mismo |
| 3c-a.8 | mismo que 3c-a.1 + 3c-a.4 | mismo que 3c-a.1 + 3c-a.4 | mismo |

## Fase 3c-b: Estilos de árbol + Overview inline (PR 3c-b → rama del PR 3c-a)

Posición 4/16 — el **segundo nuevo hijo CSS**. PR 3c-b
extiende `src/app/globals.css` (creado por PR 3c-a) con las
reglas de `@layer components` para el **módulo taxonomy**:
`.taxa-tree`, `.tree-row`, `.kebab`, `.kebab-menu`,
`.tree-search-icon`, `.materialize-indicator`,
`.detail-panel`, `.tab-strip`, `.tab-button`, `.overview-tab`,
`.breadcrumb`. Estos selectores son la superficie inline para
el árbol de taxonomía, los affordances por fila, el andamio
del panel de detalle (el styling del strip de 3 pestañas
`Overview` / `Search` / `Folder`), y el breadcrumb (familia
monoespaciada para los segmentos de nombre científico).
Depende de PR 3c-a (el andamio de `src/app/globals.css`
existe con el bloque `@theme` + placeholder vacío
`@layer base { … }`).

- [ ] 3c-b.1 R — `tests/test_taxonomy_styles.py` (nuevo):
      lee el bloque `<style>` legacy del `web/index.html`
      y el nuevo bloque `@layer components` de
      `src/app/globals.css`, verifica que cada selector
      de taxonomía legacy (`.taxa-tree`, `.tree-row`,
      `.kebab`, `.kebab-menu`, `.tree-search-icon`,
      `.materialize-indicator`, `.detail-panel`,
      `.tab-strip`, `.tab-button`, `.overview-tab`,
      `.breadcrumb`, `.scientific-name`, `.authorship`,
      `.species-count`) resuelve a una declaración no
      vacía en el nuevo `globals.css`. El test DEBE
      fallar en una rama PR 3c-b fresca (sin bloque
      `@layer components` de taxonomía aún).
      <!-- sdd-owner: implementation -->
- [ ] 3c-b.2 G — `src/app/globals.css` (modificado, ~250
      LoC de delta dentro de `@layer components { … }`):
      añade los selectores de taxonomía — `.taxa-tree`
      (la columna izquierda del `<main>` con layout
      `display: grid`), `.tree-row` (layout por fila con
      columnas de grid `rank / name / source /
      species-count`), `.kebab` + `.kebab-menu` (glyph
      de kebab por fila + popover flotante anclado al
      kebab), `.tree-search-icon` (glyph de búsqueda por
      fila), `.materialize-indicator` (indicador de
      materialize por fila), `.detail-panel` (panel
      contextual inline con `<header>` de rango + nombre
      científico + strip de pestañas), `.tab-strip` +
      `.tab-button` (el styling del strip de 3 pestañas
      `Overview` / `Search` / `Folder` — tres botones en
      orden fijo, los tres alcanzables desde cada
      selección, `Overview` siempre disponible según la
      política de usuario), `.overview-tab` (el cuerpo
      `Overview` — nombre científico, estado de
      aceptación, autoría, conteo de especies),
      `.breadcrumb` (familia monoespaciada para los
      segmentos de nombre científico, glyph separador,
      affordance de click por segmento). Todas las reglas
      bajo `@layer components` para que las clases de
      utilidad de Tailwind 4 (entregadas en PR 3c-d)
      puedan override cuando se necesite; el orden de
      fuente coincide con el requisito de orden de cascada
      en `design.md` §"Design tokens".
      <!-- sdd-owner: implementation -->
- [ ] 3c-b.3 T — extender la triangulación de
      `tests/test_taxonomy_styles.py`: verifica (a) que
      cada selector de taxonomía aparece bajo
      `@layer components` (no `@layer base` — PR 3c-d
      posee `@layer base`); (b) que los selectores del
      strip de tres pestañas renderizan las tres pestañas
      en orden fijo (`Overview` / `Search` / `Folder`);
      (c) que `Overview` siempre está visible (sin
      `display: none` / `visibility: hidden` /
      `aria-hidden="true"` / atributo `[hidden]` en las
      declaraciones de selectores); (d) que la familia
      monoespaciada del breadcrumb resuelve contra la
      fuente `JetBrains Mono` que produce
      `next/font/google` (el pipeline de preload Raleway /
      JetBrains Mono / Material Symbols Outlined de PR
      3b está activo de extremo a extremo).
      <!-- sdd-owner: implementation -->
- [ ] 3c-b.4 Refactor — alfabetizar los selectores dentro
      de `@layer components`; colapsar `.kebab` +
      `.kebab-menu` en una sola regla `.kebab` con
      descendiente `> .kebab-menu`; colapsar `.tab-strip`
      + `.tab-button` en una sola regla `.tab-strip` con
      descendiente `> .tab-button`; asegurar que el orden
      de fuente coincide con el orden del bloque
      `<style>` legacy (cumple el requisito de orden de
      cascada en `design.md` §"Design tokens").
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c-b.1, 3c-b.3 | `.venv/bin/python3 -m pytest tests/test_taxonomy_styles.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` lleva cada selector de taxonomía bajo `@layer components` | `git revert <3c-b-sha>` elimina el bloque `@layer components { … }` de taxonomía de `src/app/globals.css`; Fases 3a + 3b + 3c-a intactas |
| 3c-b.2 | mismo | mismo | mismo |
| 3c-b.4 | mismo | mismo | mismo |

## Fase 3c-c: Estilos de Search / Folder / Browser global (PR 3c-c → rama del PR 3c-b)

Posición 5/16 — el **tercer nuevo hijo CSS**. PR 3c-c
extiende `src/app/globals.css` (con el bloque `@theme` de
PR 3c-a y el bloque `@layer components` de taxonomía de PR
3c-b) con los selectores del **módulo research** y del
**shell de chrome** (`.search-tab`,
`.search-category-section`, `.search-link-list`,
`.search-link`, `.folder-tab`, `.header-browser-tab`,
`.research-explorer`, `.file-explorer-pane`,
`.file-viewer-pane`). Estos selectores son la superficie
inline para el cuerpo de la pestaña `Search` (lista
categorizada de enlaces salientes en orden fijo `General` /
`Taxonomic` / `Academic` / `Multimedia` / `Documents`), el
cuerpo de la pestaña `Folder` (indicador de materialize por
taxón), y la pestaña `Browser` del header (re-anclada como
Research / file explorer global, NO scoped por taxón).
Depende de PR 3c-b (el bloque `@layer components` de
taxonomía está en su lugar; el archivo se publica sin los
tokens `:root` que PR 3c-a posee).

- [ ] 3c-c.1 R — `tests/test_research_styles.py` (nuevo):
      lee el bloque `<style>` legacy del `web/index.html`
      y el nuevo bloque de `@layer components` de research
      / chrome de `src/app/globals.css`, verifica que cada
      selector de research / chrome legacy (`.search-tab`,
      `.search-category-section`, `.search-link-list`,
      `.search-link`, `.folder-tab`, `.header-browser-tab`,
      `.research-explorer`, `.file-explorer-pane`,
      `.file-viewer-pane`) resuelve a una declaración no
      vacía en el nuevo `globals.css`. El test DEBE
      fallar en una rama PR 3c-c fresca (sin bloque de
      `@layer components` de research / chrome aún).
      <!-- sdd-owner: implementation -->
- [ ] 3c-c.2 G — `src/app/globals.css` (modificado, ~250
      LoC de delta dentro de `@layer components { … }`):
      añade los selectores de research / chrome —
      `.search-tab` (el cuerpo de la pestaña `Search` con
      las cinco secciones de categoría en orden fijo
      `General` / `Taxonomic` / `Academic` / `Multimedia`
      / `Documents`), `.search-category-section` (el
      encabezado + lista de cada categoría),
      `.search-link-list` (la lista de anchors dentro de
      cada sección), `.search-link` (cada anchor con
      `target="_blank"`, `rel="noopener noreferrer"`, y la
      plantilla de URL resuelta del literal `SEARCH_ENGINES`
      — cierra la regresión donde `Search online` aterriza
      en `Overview`), `.folder-tab` (indicador de
      materialize por taxón; cuerpo separado de `Search`),
      `.header-browser-tab` (la pestaña del header del
      Research / file explorer global — NO una pestaña del
      panel de detalle y NO scoped por taxón; seleccionar
      un taxón mientras `Browser` está activo NO DEBE
      acotar el explorer), `.research-explorer` (el par
      global de panel de árbol de carpetas / visor de
      archivos), `.file-explorer-pane` + `.file-viewer-pane`
      (la división entre árbol y visor; misma superficie
      que enviaban los legacy `web/file_explorer.js` +
      `web/file_viewer.js`). Todas las reglas bajo
      `@layer components` para que las clases de utilidad
      de Tailwind 4 (entregadas en PR 3c-d) puedan override
      cuando se necesite; el orden de fuente coincide con
      el requisito de orden de cascada en `design.md`
      §"Design tokens". <!-- sdd-owner: implementation -->
- [ ] 3c-c.3 T — extender la triangulación de
      `tests/test_research_styles.py`: verifica (a) que
      cada selector de research / chrome aparece bajo
      `@layer components` (no `@layer base` — PR 3c-d
      posee `@layer base`); (b) que las secciones de
      categoría de la pestaña `Search` renderizan en el
      orden fijo (`General` / `Taxonomic` / `Academic` /
      `Multimedia` / `Documents`); (c) que cada anchor
      del `SearchLinkList` lleva `target="_blank"` y
      `rel="noopener noreferrer"` (el contrato de
      seguridad); (d) que el `FolderTab` se renderiza
      separado del `SearchTab` (sin colapso compartido de
      `display: none` / `visibility: hidden`); (e) que la
      pestaña `Browser` del header abre el explorer de
      Research global sin un filtro `taxonId` (el selector
      `.header-browser-tab` NO lleva un selector
      descendiente que acote el explorer a un taxón).
      <!-- sdd-owner: implementation -->
- [ ] 3c-c.4 Refactor — alfabetizar los selectores dentro
      de `@layer components`; colapsar `.search-tab` +
      `.search-category-section` + `.search-link-list` +
      `.search-link` en una sola regla `.search-tab` con
      selectores descendientes; colapsar
      `.research-explorer` + `.file-explorer-pane` +
      `.file-viewer-pane` en una sola regla
      `.research-explorer` con selectores descendientes;
      asegurar que el orden de fuente coincide con el
      orden del bloque `<style>` legacy (cumple el
      requisito de orden de cascada en `design.md` §"Design
      tokens"). <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c-c.1, 3c-c.3 | `.venv/bin/python3 -m pytest tests/test_research_styles.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` lleva cada selector de research / chrome bajo `@layer components` | `git revert <3c-c-sha>` elimina el bloque `@layer components { … }` de research / chrome de `src/app/globals.css`; Fases 3a + 3b + 3c-a + 3c-b intactas |
| 3c-c.2 | mismo | mismo | mismo |
| 3c-c.4 | mismo | mismo | mismo |

## Fase 3c-d: Base / reset / affordances de estado (PR 3c-d → rama del PR 3c-c, posición 6/18)

Posición 6/18 — alcance **reducido** (ver adenda correctiva 2026-09-02; el 3c-d monolítico obsoleto queda sustituido). Depende de **3c-c**. Extiende `src/app/globals.css::@layer base` con `@keyframes` (`spin`), selectores `color-mix()`, `body { overscroll-behavior: none; … }`, y `main > :first-child { margin-top: 0 !important; }`. **Sin clases de utilidad, sin test de paridad.** Superficie de producción permitida: `src/app/globals.css` (~80 LoC). Superficie de test permitida: `tests/test_tailwind_4_base_resets.py`.

- [ ] 3c-d.1 R — `tests/test_tailwind_4_base_resets.py` (cada selector `@keyframes`/`color-mix()` + resets de body / primer hijo resuelven en el CSS generado)
- [ ] 3c-d.2 G — adiciones de `@layer base` en `src/app/globals.css` (~80 LoC, orden de fuente)
- [ ] 3c-d.3 T — triangulación (orden de fuente, resolución de selectores, presupuesto de bytes)
- [ ] 3c-d.4 Refactor — alfabetizar, deduplicar

**Evidencia**: `.venv/bin/python3 -m pytest tests/test_tailwind_4_base_resets.py -v`; runtime `npx next build` exit 0. **Reversión**: `git revert <3c-d-sha>`; Fases 3a + 3b + 3c-a + 3c-b + 3c-c intactas.

## Fase 3c-e: Clases de utilidad + paridad de animación restante (PR 3c-e → rama del PR 3c-d, posición 7/18)

Posición 7/18 — hijo nuevo (rama `…-07-3c-e`, base `…-06-3c-d`). Depende de **3c-d**. Extiende `globals.css::@layer base` con la superficie de clases de utilidad (`bg-primary`, `text-on-surface`, `border-outline-variant`, `bg-surface-container-lowest`, `shadow-sm`, `rounded-r-md`, `bg-primary-fixed`, `text-on-primary-fixed`, …) y cualquier `@keyframes`/`color-mix()` restante que no estuviera en 3c-d. **Sin test de paridad.** Superficie de producción permitida: `src/app/globals.css` (~180 LoC). Superficie de test permitida: `tests/test_tailwind_4_utilities.py`.

- [ ] 3c-e.1 R — `tests/test_tailwind_4_utilities.py` (cada utilidad legacy resuelve)
- [ ] 3c-e.2 G — adiciones de utilidades en `src/app/globals.css` (~180 LoC, orden de fuente)
- [ ] 3c-e.3 T — triangulación (sin pérdida silenciosa de clases, presupuesto de bytes)
- [ ] 3c-e.4 Refactor — alfabetizar

**Evidencia**: `.venv/bin/python3 -m pytest tests/test_tailwind_4_utilities.py -v`; runtime `npx next build` exit 0. **Reversión**: `git revert <3c-e-sha>`; Fases 3a + 3b + 3c-a + 3c-b + 3c-c + 3c-d intactas.

## Fase 3c-f: Solo test de paridad final consolidado (PR 3c-f → rama del PR 3c-e, posición 8/18)

Posición 8/18 — hijo nuevo (rama `…-08-3c-f`, base `…-07-3c-e`). Depende de **3c-e**. **No se envía código de producción nuevo en `globals.css`.** Test parametrizado final `tests/test_tailwind_4_parity.py` que consolida los cinco tests enfocados previos (3c-a tokens / 3c-b taxonomía / 3c-c research / 3c-d base-resets / 3c-e utilidades) — testigo de consolidación del **CSS inline legacy de 1.963 líneas** migrado a `src/app/globals.css` de extremo a extremo. **La paridad final queda sin cambios en el contrato; ahora pertenece solo al PR 3c-f.** Superficie de producción permitida: **ninguna**. Superficie de test permitida: `tests/test_tailwind_4_parity.py`.

- [ ] 3c-f.1 R — `tests/test_tailwind_4_parity.py` (el testigo consolidado final)
- [ ] 3c-f.2 G — `pytest.mark.parametrize` sobre la unión de los tests enfocados 3c-a / 3c-b / 3c-c / 3c-d / 3c-e
- [ ] 3c-f.3 T — triangulación (superficie completa: tokens `@theme`, `var(--token)`, `@keyframes`/`color-mix()`, clases de utilidad, selectores `@layer components`)

**Evidencia**: `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v`; runtime `npx next build` exit 0. **Reversión**: `git revert <3c-f-sha>`; Fases 3a + 3b + 3c-a + 3c-b + 3c-c + 3c-d + 3c-e intactas.

## Fase 3d: Reescritura del Makefile + repoint de `WEB_DIR` + lector AC-21 (PR 3d → rama del PR 3c-f, posición 9/18)

Depende de PR 3b (`next build` produce `out/index.html`) y
PR 3c-f (los tokens de Tailwind 4 + `@layer base` +
`@layer components` fluyen a través de `next build`; el test
de paridad final de Tailwind 4 está en disco). Fusiona la
reescritura de `Makefile::api` del PR 3c original + el
repoint de `WEB_DIR` del PR 3d original + la actualización
del lector AC-21 en un solo sub-PR dimensionado a ~240 LoC
authored (muy por debajo de 400). El contrato de runtime de
Node ≥ 20.9.0 aterriza aquí como un paso de receta del
`Makefile` (el script mismo fue autoría del PR 3a).

- [ ] 3d.1 R — `tests/test_make_api_build.py` (nuevo):
      invoca `make api` en un clon `tmp_path` (o vía shim
      de subproceso) y verifica que el target de Makefile
      invoca `node scripts/check-runtime.mjs` **primero**,
      luego `npm run build:web`, luego uvicorn vincula
      solo después de que `out/index.html` exista; verifica
      que uvicorn no vincula cuando `check-runtime.mjs`
      sale distinto de cero (Node < 20.9.0).
      <!-- sdd-owner: implementation -->
- [ ] 3d.2 R — `tests/test_make_api_build.py` (bloque de
      orden build/uvicorn): verifica que el target de
      Makefile invoca `npm run build:web` (`next build`)
      **antes** de que uvicorn vincule el puerto; verifica
      que uvicorn no vincula cuando `next build` sale
      distinto de cero; verifica que uvicorn falla rápido
      si `out/index.html` falta incluso después de una
      `next build` exitosa. <!-- sdd-owner: implementation -->
- [ ] 3d.3 R — `tests/test_static_mount.py` (nuevo):
      verifica que `api/server.py:54` declara
      `WEB_DIR = Path(__file__).parent.parent / "out"`
      (repointed). Verifica que la signature del mount en
      `api/server.py:1815` permanece byte-idéntica
      (`app.mount("/", StaticFiles(directory=str(WEB_DIR),
      html=True), name="web")`). Verifica el contrato de
      origen único: `uvicorn.run(…)` vincula solo a
      `127.0.0.1:8765`;
      `extension/manifest.json::host_permissions` queda
      `["http://localhost:8765/*"]`;
      `content_scripts.matches` queda
      `["http://localhost:8765/*"]`.
      <!-- sdd-owner: implementation -->
- [ ] 3d.4 G — `Makefile` (modificado, ~50 LoC de delta
      en los bloques `api:` y `css:`): el target `api:`
      ejecuta `node scripts/check-runtime.mjs` → `npm ci`
      → `npm run build:web` → `uvicorn … --port 8765` en
      ese orden; el paso `make css` de Tailwind-3.4 legacy
      se elimina (la build de Tailwind 4 vive dentro de
      `next build`); `make css` se vuelve un shim no-op
      que sale 0 (se conserva por compatibilidad con
      scripts externos; documentado en el encabezado de
      `Makefile`). <!-- sdd-owner: implementation -->
- [ ] 3d.5 G — `api/server.py` (modificado, delta de 1
      línea en línea 54 + middleware mínimo para cablear
      el preload de `next/font` en la respuesta
      `out/index.html` si Next no inlinea el `<link>` —
      solo se añade si la triangulación de Fase 3b lo
      marca): `WEB_DIR = Path(__file__).parent.parent /
      "out"`. Ninguna otra línea de `api/server.py`
      cambia. <!-- sdd-owner: implementation -->
- [ ] 3d.6 G — `src/data/search-engines.js` (nuevo, ~100
      LoC): copia byte a byte de `web/search_urls.js` con
      el nombre de export cambiado a `SEARCH_ENGINES`
      (coincide con el literal canónico que refleja
      `api/server.py::_SEARCH_ENGINES`). La forma byte —
      `key`, `label`, `with_authorship`, ordering —
      queda idéntica; `template` e `icon` quedan intactos
      según el contrato AC-21 de `tests/test_smoke.py`.
      <!-- sdd-owner: implementation -->
- [ ] 3d.7 G — `tests/test_smoke.py` (modificado, ~5 LoC
      de delta): el `open("web/search_urls.js").read()`
      del test `test_search_engine_contract` se actualiza a
      `open("src/data/search-engines.js").read()`. El
      `open("api/server.py").read()` del lado Python
      queda sin cambios. Contrato AC-21 preservado.
      <!-- sdd-owner: implementation -->
- [ ] 3d.8 T — triangulación de
      `tests/test_static_mount.py`: verifica que el
      movimiento del archivo no rompe el test contractual
      ejecutándolo en un clon `tmp_path` limpio; verifica
      que los campos coincidentes del literal en
      `api/server.py::_SEARCH_ENGINES` son byte-idénticos
      a `src/data/search-engines.js` en cada entrada.
      <!-- sdd-owner: implementation -->
- [ ] 3d.9 T — triangulación de
      `tests/test_make_api_build.py`: verifica el modo de
      fallo donde `out/index.html` falta incluso después
      de una `next build` exitosa (`out/` corrupto) causa
      que `make api` salga distinto de cero antes de que
      uvicorn vincule; verifica que uvicorn vincula
      **solo** a `127.0.0.1:8765` (sin segundo listener
      en `0.0.0.0` ni en cualquier otro puerto).
      <!-- sdd-owner: implementation -->
- [ ] 3d.10 Refactor — orden alfabético de deps en
      `package.json` (este PR cierra cualquier
      alfabetización de deps que el PR 3a difirió); tabs
      de recetas de `Makefile` preservados (sin
      espacios); fines de línea de
      `src/data/search-engines.js` coinciden con los de
      `web/search_urls.js`. <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3d.1–3d.3 | `.venv/bin/python3 -m pytest tests/test_make_api_build.py -v tests/test_static_mount.py -v` | `make api` exit 0 en Node ≥ 20.9.0; `lsof -i :8765` muestra solo uvicorn | `git revert <3d-sha>` restaura `Makefile::api` (cadena `make css` legacy), restaura `api/server.py:54` al valor legacy, elimina `src/data/search-engines.js`, revierte el parche `open()` de `tests/test_smoke.py`; Fases 3a/3b/3c-a/3c-b/3c-c/3c-d intactas |
| 3d.4 | mismo | mismo | mismo |
| 3d.5 | mismo | mismo | mismo |
| 3d.6–3d.7 | `.venv/bin/python3 -m pytest tests/test_smoke.py::test_search_engine_contract -v` | `make api` arranca uvicorn; `curl http://127.0.0.1:8765/index.html` devuelve 200 con el contenido de `out/index.html` | mismo |
| 3d.8–3d.9 | mismo que 3d.1–3d.3 | mismo | mismo |
| 3d.10 | n/a (refactor) | mismo | mismo |

## Fase 4a: Typed store + 4 sitios de lectura + 4 sitios de escritura (PR 4a → rama del PR 3d, posición 8/16)

Rebana las tareas 4.1 + 4.2 del predecesor
(`src/modules/browser-state/{store,keys,defaults}.ts` + 4
sitios de lectura + 4 sitios de escritura dentro de
`useEffect`). Depende de PR 3c-a (barrel de design-system
cargado); produce `src/modules/browser-state/**` typed
store con cuatro sitios de lectura + cuatro de escritura.

- [ ] 4a.1 R — `tests/test_browser_state_keys.py` (nuevo):
      grepea `src/modules/browser-state/**` y verifica que
      hay exactamente cuatro sitios de llamada
      `localStorage.getItem(…)` + exactamente cuatro
      `localStorage.setItem(…)` + cero
      `localStorage.removeItem(…)` fuera del `reset()`
      tipado. Verifica que ningún otro módulo
      (`src/modules/taxonomy/**`, `src/modules/research/**`,
      `src/modules/app-shell/**`,
      `src/modules/design-system/**`) lee o escribe
      `localStorage` directamente.
      <!-- sdd-owner: implementation -->
- [ ] 4a.2 G — `src/modules/browser-state/domain/keys.ts`
      (nuevo, ~30 LoC): constantes `LocalStorageKey`
      tipadas (`"taxa.settings.theme"`,
      `"taxa.tree.source"`, `"taxa.tree.lastTaxonId"`,
      `"taxa.tree.kebabOpenId"`) más valores por defecto
      tipados según la tabla del spec
      `browser-state-hydration` (`theme: "light" | "dark"`
      default `light`, `tree-source: "col" | "worms" |
      "freshwater"` default `col`,
      `last-taxon-id: number | null` default `null`,
      `kebab-open-id: number | null` default `null`).
      <!-- sdd-owner: implementation -->
- [ ] 4a.3 G —
      `src/modules/browser-state/infrastructure/store.ts`
      (nuevo, ~80 LoC): cuatro funciones `read(key)` y
      cuatro `write(key, value)`, una por clave, cada una
      envolviendo `try/catch` para tragar excepciones de
      `localStorage` (modo privado / cuota excedida).
      Exporta un `subscribe(key, cb)` tipado que devuelve
      un handle de unsubscribe; exporta un `reset()`
      tipado que llama a `localStorage.removeItem` para
      cada clave. TS plano en `domain/`; las llamadas a
      `localStorage` viven en `infrastructure/` según la
      regla 4 de modular-architecture.
      <!-- sdd-owner: implementation -->
- [ ] 4a.4 G — `src/modules/browser-state/index.ts`
      (nuevo barrel, ~10 LoC): reexporta los cuatro
      `read`, cuatro `write`, `subscribe`, `reset`, los
      defaults tipados, y el tipo de listener tipado. **No**
      exporta getter/setter raw de `localStorage`.
      <!-- sdd-owner: implementation -->
- [ ] 4a.5 T — triangulación de
      `tests/test_browser_state_keys.py`: parametriza la
      matriz de 4 claves; verifica que no existe
      `localStorage.getItem` / `setItem` en
      `src/modules/research/infrastructure/` (la clave
      splitter `taxa.fex.treeWidth` queda poseída por el
      módulo file explorer según la sección §Notes del
      spec). <!-- sdd-owner: implementation -->
- [ ] 4a.6 Refactor — extraer las excepciones de
      read/write en un helper `safeStorage` que envuelve
      `getItem` / `setItem` / `removeItem` con el
      try/catch; reutilizarlo entre los cuatro sitios de
      lectura y cuatro de escritura.
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 4a.1, 4a.5 | `.venv/bin/python3 -m pytest tests/test_browser_state_keys.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.js` lleva el bundle del store tipado | `git revert <4a-sha>` elimina `src/modules/browser-state/**`; nada más tocado |
| 4a.2–4a.4, 4a.6 | `.venv/bin/python3 -m pytest tests/test_browser_state_keys.py -v` | `npx tsc --noEmit` contra `src/modules/browser-state/` | mismo |

## Fase 4b: Guardia de hidratación + integración de AppShell + test de cero warnings de Playwright (PR 4b → rama del PR 4a, posición 9/16)

Rebana las tareas 4.3 + 4.4 del predecesor
(`useSyncExternalStore` detrás de flag `mounted` + aserción
Playwright de cero warnings de hidratación) más la
**integración del AppShell en
`src/app/{layout,page}.tsx`** (la corrección del defecto de
dependencia que mueve el cableado del AppShell del PR 3b al
PR 4b — PR 4b posee tanto el módulo
`src/modules/app-shell/**` **como** la costura de integración
en el host del App Router). Depende de PR 4a (store
disponible), PR 3b (los marcadores
`src/app/{layout,page}.tsx` en los que el PR 4b integra
`<AppShell>`), y PR 3c-a (los tokens `@theme` de Tailwind 4
+ barrel de design-system cargados para `next build`).

- [ ] 4b.1 R — `tests/test_hydration_console.py` (nuevo,
      Playwright): carga el fixture de chromium contra
      `make api`, verifica que la consola del browser emite
      cero `Warning: Text content did not match`, cero
      `Warning: Expected server HTML to contain`, y cero
      `Warning: Hydration failed` mensajes después del
      primer paint + ciclo de rehidratación.
      <!-- sdd-owner: implementation -->
- [ ] 4b.2 G —
      `src/modules/app-shell/presentation/AppShell.tsx`
      (nuevo, ~50 LoC): importa `useSyncExternalStore`
      del módulo `browser-state`; lee el store tipado
      detrás de un flag `mounted` configurado dentro de
      `useEffect`; en el primer paint, devuelve el estado
      vacío (`selected: null`, `tree: null`,
      `last-taxon-id: null`); en la rehidratación, aplica
      los defaults tipados desde `localStorage` y
      actualiza la URL al `last-taxon-id` si hay uno
      almacenado. <!-- sdd-owner: implementation -->
- [ ] 4b.3 G —
      `src/modules/app-shell/infrastructure/page-chrome.tsx`
      (nuevo, ~30 LoC): pestañas del header (Browser /
      Classification / Settings) con atributos
      `data-action="nav-tab"` y `data-path="<tab>"`;
      toggle de tema stampa / unstampa `data-theme` en
      `<html>` vía el store tipado; help shell, settings
      view, banner host.
      <!-- sdd-owner: implementation -->
- [ ] 4b.4 T — triangulación de
      `tests/test_hydration_console.py`: verifica que la
      consola del fixture de chromium después de un reload
      forzado (donde `localStorage` tiene un `theme: "dark"`
      almacenado) muestra `data-theme="dark"` en `<html>`
      después del ciclo de rehidratación; verifica que no
      se dispara ningún warning cuando el usuario toggle
      el tema entre paints. <!-- sdd-owner: implementation -->
- [ ] 4b.5 Refactor — extraer el flag `mounted` en un
          pequeño hook `useMounted()` en
          `src/modules/browser-state/` para que el patrón
          sea reusable; reutilizarlo en `AppShell.tsx` y
          cualquier componente descendiente que lea estado
          tipado. <!-- sdd-owner: implementation -->
      - [ ] 4b.6 G — `src/app/{layout,page}.tsx`
          (modificados, ~10 LoC de delta combinada):
          integrar `<AppShell>` desde `@taxa/app-shell` en
          el host del App Router. `src/app/layout.tsx`
          añade `import { AppShell } from "@taxa/app-shell";`
          y envuelve el cuerpo marcador en
          `<AppShell>{children}</AppShell>`;
          `src/app/page.tsx` añade la frontera `"use client"`
          que el AppShell necesita (el módulo AppShell
          importa `useSyncExternalStore` y `useEffect`).
          PR 4b posee la integración porque posee
          `src/modules/app-shell/**`; el defecto de
          dependencia (PR 3b importando un módulo que el
          PR 4b envía) se cierra aquí. El testigo
          Playwright 4b.1 R existente de cero warnings de
          hidratación es la guardia de regresión para la
          integración (el fixture de chromium carga el
          AppShell integrado y verifica cero warnings de
          hidratación después del primer paint + ciclo de
          rehidratación).
          <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 4b.1, 4b.4 | `.venv/bin/python3 -m pytest tests/test_hydration_console.py -v` | `make api` arranca uvicorn; Playwright corre el fixture de chromium de extremo a extremo | `git revert <4b-sha>` elimina `src/modules/app-shell/presentation/AppShell.tsx` y `infrastructure/page-chrome.tsx`; el store de Fase 4a se queda |
| 4b.2–4b.3 | mismo | `npx next build` exit 0; `npx tsc --noEmit` contra `src/modules/app-shell/` | mismo |
| 4b.5 | mismo | mismo | mismo |
| 4b.6 | `.venv/bin/python3 -m pytest tests/test_hydration_console.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.js` referencia el barrel `@taxa/app-shell`; Playwright cero warnings de hidratación contra el AppShell integrado | `git revert <4b-sha>` revierte el delta de integración del AppShell en `src/app/{layout,page}.tsx` Y elimina `src/modules/app-shell/**`; el store de Fase 4a se queda |

## Fase 5a: Port del módulo taxonomy (PR 5a → rama del PR 4b, posición 10/16)

Rebana las tareas 5.1 + 5.2 + 5.3 del predecesor
(`src/modules/taxonomy/{domain,application,infrastructure,
presentation}` + port de `web/{tree,detail,breadcrumb}.js`).
Depende de PR 4b (lectura de estado segura de hidratación
para `tree-source`) y de PR 3c-b (el bloque de
`@layer components` de taxonomía está en su lugar — los
selectores de taxonomía se montan sobre el CSS de PR 3c-b).

Este sub-PR también envía el **strip de pestañas de
`DetailPanel`** (`Overview` / `Search` / `Folder`), el
**cuerpo de la pestaña `Overview`**, y el menú **`Kebab`**
incluyendo la acción `Search online` que **fuerza la pestaña
`Search`** (cerrando la regresión actual en vivo donde los
taxones de nivel superior aterrizan en `Overview` cuando se
invoca `Search online`). El re-anclaje de la pestaña `Browser`
del header (Research / file explorer global) y los cuerpos de
`SearchTab` / `FolderTab` aterrizan en PR 5b para mantener el
port de taxonomía enfocado en la superficie de árbol y
detalle; PR 5a solo posee el **andamio del strip de
pestañas** más el **contrato de fuerza-Search** en el que se
enchufa el `SearchTab` de PR 5b.

- [ ] 5a.1 R — `tests/test_taxonomy_infra.py` (nuevo):
      mockea `fetchTaxon`, `fetchChildren`,
      `fetchDomains`; verifica que la capa application
      expone solo view-models (sin JSON crudo en la capa
      presentation); verifica que la forma de los tipos
      `Taxon`, `TaxonTree`, `Breadcrumb` coincide con la
      capa `domain` de `taxonomy`; verifica que el strip
      de pestañas de `DetailPanel` expone tres pestañas en
      orden fijo (`Overview`, `Search`, `Folder`); verifica
      que `Overview` siempre está disponible / siempre
      visible según la política de usuario; verifica que
      la acción kebab `Search online` fuerza la pestaña
      `Search` activa (NO `Overview`, incluso para
      taxones de nivel superior — cierra la regresión
      actual en vivo). <!-- sdd-owner: implementation -->
- [ ] 5a.2 G — `src/modules/taxonomy/domain/taxon.ts`
      (~60 LoC): tipos TS planos para `Taxon`,
      `TaxonTree`, `Breadcrumb`, `DomainId`; invariantes
      (walker de cadena de padres, ordenamiento de rango,
      inclusión de conjunto materializado). El predecesor
      PR 2d ya envió la superficie de tipos; PR 5a la
      extiende con el walker de cadena de padres que el
      diseño especifica. <!-- sdd-owner: implementation -->
- [ ] 5a.3 G —
      `src/modules/taxonomy/infrastructure/api.ts`
      (~50 LoC): `fetchTaxon(id)` → `GET /api/taxon/{id}`;
      `fetchChildren(id, source)` →
      `GET /api/taxon/{id}/children?source=<col|worms|
      freshwater>`; `fetchDomains()` → `GET /api/domains`.
      Todos retornan promesas tipadas; los errores de red
      surgen como `NetworkError` tipado.
      <!-- sdd-owner: implementation -->
- [ ] 5a.4 G —
      `src/modules/taxonomy/application/useTaxonTree.ts`
      (~80 LoC): el hook `useTaxonTree()`; consume las
      funciones `fetch*` tipadas desde `infrastructure`;
      emite view-models que consume la capa presentation;
      sin imports de React en las capas `domain` o
      `infrastructure`. <!-- sdd-owner: implementation -->
- [ ] 5a.5 G —
      `src/modules/taxonomy/presentation/{Tree,DetailPanel,
      OverviewTab, Breadcrumb}.tsx` (~220 LoC combinados):
      porta el layout por fila del legacy
      `web/{tree,detail,breadcrumb}.js` (kebab por fila,
      icono de búsqueda por fila, indicador de
      materialize por fila, familia monoespaciada del
      breadcrumb para segmentos de nombre científico)
      **y envía el strip de pestañas de `DetailPanel`**.
      El strip de pestañas renderiza **tres pestañas en
      orden fijo: `Overview`, `Search`, `Folder`**, las
      tres alcanzables desde cada selección; `Overview`
      **siempre está disponible y siempre visible** según
      la política de usuario. El componente `OverviewTab`
      renderiza nombre científico, estado de aceptación,
      autoría, conteo de especies. El `DetailPanel`
      exporta un callback tipado de activación de pestaña
      que la acción `Search online` del `Kebab` invoca
      para forzar la pestaña `Search` activa. Cada
      atributo legacy `data-action="nav-tab"`,
      `data-path="<tab>"`, `data-theme` se preserva. La
      capa de presentation de taxonomía se monta sobre
      los selectores de `@layer components` de PR 3c-b
      (`.taxa-tree`, `.tree-row`, `.kebab`,
      `.detail-panel`, `.tab-strip`, `.overview-tab`,
      `.breadcrumb`, …).
      <!-- sdd-owner: implementation -->
- [ ] 5a.6 G — `src/modules/taxonomy/presentation/Kebab.tsx`
      (~40 LoC): menú kebab por fila. Incluye la acción
      `Search online` cableada para despachar el callback
      de activación de pestaña que **fuerza la pestaña
      `Search` activa** sobre el taxón seleccionado (NO
      DEBE defaultear a `Overview`, ni siquiera para
      taxones de nivel superior). La acción es el cierre
      de la regresión actual en vivo donde `Search
      online` sobre taxones de nivel superior aterriza en
      `Overview`. <!-- sdd-owner: implementation -->
- [ ] 5a.7 T — triangulación de
      `tests/test_taxonomy_infra.py`: parametriza sobre
      las tres fuentes (`col`, `worms`, `freshwater`);
      verifica que el toggle de tree-source re-renderiza
      el árbol con la fuente coincidente; verifica que el
      walker del breadcrumb maneja taxones raíz (sin
      padre) y taxones huérfanos (padre faltante en la
      fuente) sin lanzar excepciones; verifica que el
      strip de pestañas de `DetailPanel` renderiza las
      tres pestañas (`Overview`, `Search`, `Folder`) para
      cada selección incluyendo taxones de nivel
      superior; verifica que `Overview` siempre está
      visible; verifica que la acción kebab `Search
      online` fuerza la pestaña `Search` activa (cierra
      la regresión actual). <!-- sdd-owner: implementation -->
- [ ] 5a.8 T — extiende `tests/test_taxonomy_infra.py`
      con un testigo Playwright de strip de pestañas:
      carga el fixture de chromium, selecciona un taxón
      de nivel superior (por ej. `Archaea`), click la
      acción kebab `Search online` por fila, verifica que
      el strip de pestañas del panel de detalle ahora
      muestra `Search` como la pestaña activa (NO
      `Overview`). El testigo es la guardia de regresión
      contra el comportamiento actual en vivo.
      <!-- sdd-owner: implementation -->
- [ ] 5a.9 Refactor — extraer el menú kebab por fila en
      `<Kebab>`; reutilizarlo entre `Tree` y `DetailPanel`;
      colapsar el rendering del strip de pestañas de
      `DetailPanel` en una sola primitiva
      `<TabStrip tabs={["Overview", "Search", "Folder"]}
      active={...} onChange={...} />` exportada desde
      `src/modules/design-system/`.
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 5a.1, 5a.7, 5a.8 | `.venv/bin/python3 -m pytest tests/test_taxonomy_infra.py -v` | `make api` arranca uvicorn; `curl /api/domains` devuelve la forma JSON; el testigo Playwright del strip de pestañas sale 0 | `git revert <5a-sha>` elimina `src/modules/taxonomy/**` (excepto `domain/taxon.ts` enviado por el predecesor PR 2d — ese se queda); nada más tocado |
| 5a.2–5a.6, 5a.9 | mismo | `npx next build` exit 0; `npx tsc --noEmit` contra `src/modules/taxonomy/` | mismo |

## Fase 5b: Port del módulo research + pin CDN (PR 5b → rama del PR 5a, posición 11/16)

Rebana las tareas 5.4 + 5.5 + 5.6 del predecesor
(`src/modules/research/{domain,application,infrastructure,
presentation}` + port de `web/{file_explorer,file_viewer,format,
keymap}.js` + pin CDN). Depende de PR 5a (flujos de lectura
de estado de taxonomía compartidos con research y el andamio
del strip de pestañas de `DetailPanel` en el que se enchufa
la acción `Search online`), de PR 3d
(`src/data/search-engines.js` para el export nombrado
`Engine`), y de PR 3c-c (el bloque de `@layer components`
de research / chrome está en su lugar — los selectores de
research se montan sobre el CSS de PR 3c-c). Este es el
sub-PR más grande a ~395 LoC; queda bajo el presupuesto de
400 líneas según `design.md` §"Sub-PR slice under Approach A"
con holgura ajustada — mantenibilidad rastreada y la
frontera queda dentro del presupuesto de revisión de 400
líneas por PR.

Este sub-PR también envía el cuerpo de **`SearchTab`**
(lista categorizada de enlaces salientes en orden fijo
`General` / `Taxonomic` / `Academic` / `Multimedia` /
`Documents`), el cuerpo de **`FolderTab`** (indicador de
materialize por taxón; **separado** de `SearchTab`), el
presentador **`SearchLinkList`** que mapea cada `Engine` a
un anchor con `target="_blank"` y `rel="noopener noreferrer"`,
y la **pestaña `Browser` del header re-anclada como
Research / file explorer global** (NO scoped por taxón;
seleccionar un taxón mientras `Browser` está activo NO DEBE
acotar el explorer a ese taxón).

- [ ] 5b.1 R — `tests/test_research_infra.py` (nuevo):
      mockea `fetchFiles`, `fetchServe` contra
      `/api/taxon/{id}/files{,/serve}`; verifica que el
      despachador de formatos (PDF / HTML / TXT / MD /
      DOCX / XLS / XLSX / EPUB) enruta al lazy loader
      correcto; verifica que las URLs CDN están pineadas a
      `mammoth@1.8.0`, `xlsx@0.18.5`, `epubjs@0.3.93`;
      verifica que `SearchTab` renderiza las cinco
      secciones de categoría en orden fijo (`General`,
      `Taxonomic`, `Academic`, `Multimedia`, `Documents`);
      verifica que `FolderTab` es un cuerpo separado de
      `SearchTab`; verifica que la pestaña `Browser` del
      header abre el file explorer de Research global sin
      filtro `taxonId`. <!-- sdd-owner: implementation -->
- [ ] 5b.2 G —
      `src/modules/research/domain/{research-file,engine,
      file-node}.ts` (~90 LoC combinados): `ResearchFile`,
      `Engine`, `FileNode` tipados; el tipo `Engine`
      refleja la forma del literal `SEARCH_ENGINES` (key,
      label, with_authorship, ordering); la unión
      discriminada `ResearchFile` cubre los nueve
      formatos soportados más los fallbacks `Unsupported`
      y `LegacyDoc`. <!-- sdd-owner: implementation -->
- [ ] 5b.3 G —
      `src/modules/research/infrastructure/api.ts`
      (~80 LoC): `fetchFiles(id)` → `GET /api/taxon/{id}/files`;
      `fetchServe(id, rel)` →
      `GET /api/taxon/{id}/files/serve?path=<rel>`;
      `loadScriptOnce(name, src)` lazy-loader para
      bibliotecas CDN (URLs pineadas; idempotente).
      <!-- sdd-owner: implementation -->
- [ ] 5b.4 G —
      `src/modules/research/infrastructure/search-engines.js`
      (re-export desde `src/data/search-engines.js`
      enviado por Fase 3d para el barrel del módulo
      research, con el export nombrado `SEARCH_ENGINES`
      sin cambios). <!-- sdd-owner: implementation -->
- [ ] 5b.5 G —
      `src/modules/research/application/{useFileExplorer,
      useFileViewer}.ts` (~120 LoC combinados): los dos
      hooks; consumen las funciones `fetch*` tipadas;
      emiten view-models que consume la capa
      presentation. <!-- sdd-owner: implementation -->
- [ ] 5b.6 G —
      `src/modules/research/presentation/{FileExplorer,
      FileViewer, RawTableTreeTabs, MetaStrip,
      BreadcrumbPanel, Banners, SearchLinkList,
      SearchTab, FolderTab}.tsx` (~290 LoC combinados):
      porta el layout de dos paneles del legacy
      `web/{file_explorer,file_viewer,format,keymap}.js`;
      el strip de pestañas Raw / Table / Tree; el meta
      strip `FORMAT | SIZE | ENCODING`; el despachador de
      nueve formatos con carga perezosa pineada por CDN;
      los fallbacks DOC y unsupported legacy; el banner de
      falla CDN `"Viewer offline — raw download
      unavailable"`; la búsqueda de árbol (200 ms de
      debounce, modos filter / highlight,
      `state.explorer.search.{query, mode, hideEmpty}`
      persistido); el reset del estado del explorer en
      cambio de taxón. El `SearchTab` renderiza las cinco
      secciones de categoría (`General` / `Taxonomic` /
      `Academic` / `Multimedia` / `Documents`) en orden
      fijo; el presentador `SearchLinkList` mapea cada
      `Engine` a un anchor con `target="_blank"` y
      `rel="noopener noreferrer"`, resolviendo la plantilla
      de URL desde `SEARCH_ENGINES`. El `FolderTab` es un
      cuerpo separado (indicador de materialize por taxón);
      NO DEBE ser un subconjunto de `SearchTab`. La capa
      de presentation de research se monta sobre los
      selectores de `@layer components` de PR 3c-c
      (`.search-tab`, `.search-category-section`,
      `.search-link-list`, `.search-link`,
      `.folder-tab`, `.header-browser-tab`,
      `.research-explorer`, `.file-explorer-pane`,
      `.file-viewer-pane`, …).
      <!-- sdd-owner: implementation -->
- [ ] 5b.7 G —
      `src/modules/app-shell/infrastructure/page-chrome.tsx`
      (~30 LoC de delta): la pestaña `Browser` del header
      se re-ancla como el **Research / file explorer
      global** — abre el explorer sin filtro `taxonId`, y
      seleccionar un taxón mientras `Browser` está activo
      NO DEBE acotar el explorer a ese taxón (el explorer
      continúa mostrando el corpus de research activo). El
      contrato de atributos `data-path="browser"` y
      `data-action="nav-tab"` se preserva.
      <!-- sdd-owner: implementation -->
- [ ] 5b.8 T — triangulación de
      `tests/test_research_infra.py`: parametriza sobre
      los nueve formatos (PDF, HTML, TXT, MD, DOCX, XLS,
      XLSX, EPUB, más fallback DOC, más una extensión
      unsupported como `.zip`); verifica que cada formato
      despacha al renderer legacy coincidente; verifica
      que `Content-Type` coincide con la extensión del
      archivo; verifica que el meta strip renderiza el
      `FORMAT=<EXT> | SIZE=<bytes> | ENCODING=UTF-8`
      coincidente; verifica que las secciones de categoría
      del `SearchTab` renderizan en el orden fijo
      (`General` / `Taxonomic` / `Academic` /
      `Multimedia` / `Documents`); verifica que cada
      anchor del `SearchLinkList` lleva `target="_blank"`
      y `rel="noopener noreferrer"`; verifica que el
      `FolderTab` se renderiza separado del `SearchTab`;
      verifica que la pestaña `Browser` del header abre
      el explorer de Research global sin scope de taxón.
      <!-- sdd-owner: implementation -->
- [ ] 5b.9 Refactor — extraer el meta strip en un solo
      componente `<MetaStrip format={…} size={…}
      encoding="UTF-8" />`; extraer el banner de falla
      CDN en `<BannerHost>` para que pueda reutilizarse en
      `app-shell`; colapsar el rendering de categorías
      del `SearchTab` en un presentador `<SearchLinkList>`
      que toma el literal `SEARCH_ENGINES` y renderiza
      las cinco secciones de categoría.
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 5b.1, 5b.8 | `.venv/bin/python3 -m pytest tests/test_research_infra.py -v` | `make api` arranca uvicorn; `curl /api/taxon/<id>/files` devuelve la forma JSON; URLs CDN devuelven 200 | `git revert <5b-sha>` elimina `src/modules/research/**` y el delta de la pestaña `Browser` en `src/modules/app-shell/infrastructure/page-chrome.tsx`; `src/data/search-engines.js` (Fase 3d) se queda |
| 5b.2–5b.7, 5b.9 | mismo | `npx next build` exit 0; `npx tsc --noEmit` contra `src/modules/research/` | mismo |

## Fase 5c: Selectores E2E + contrato `data-*` + borrar legacy (PR 5c → rama del PR 5b, posición 12/16)

Rebana las tareas 5.7 + 5.8 + 5.9 del predecesor
(Playwright + actualizaciones de selectores e2e +
preservación del contrato `data-*` + borrar
`web/*.{html,js,css}` + `tailwind.config.js`). Depende de
PR 5b (todos los componentes UI en vivo) y de PR 3c-d (el
test de paridad final de Tailwind 4 está en disco; el CSS
inline legacy de 1.963 líneas ha sido migrado a
`src/app/globals.css` de extremo a extremo y está listo
para retirarse).

- [ ] 5c.1 R — `tests/test_e2e_file_explorer.py`
      (modificado, el test existe pero los selectores son
      anteriores al árbol de componentes React): verifica
      que cada selector legacy
      (`data-action="nav-tab"`, `data-path="<tab>"`,
      `data-theme`, el atributo kebab por fila, el
      atributo icono de búsqueda por fila, el atributo
      indicador de materialize por fila, los atributos
      data del meta strip) sigue resolviendo en el nuevo
      árbol de componentes. <!-- sdd-owner: implementation -->
- [ ] 5c.2 R — `tests/test_web_toggle.py` (modificado):
      verifica que el toggle de tema persiste vía
      `localStorage.taxa.settings.theme` y stampa
      `data-theme` en `<html>`; verifica que la media
      query `prefers-color-scheme` del SO se honra como
      el default cuando no existe preferencia
      almacenada. <!-- sdd-owner: implementation -->
- [ ] 5c.3 G — `tests/test_e2e_file_explorer.py`
      (actualización de selectores, ~120 LoC de delta):
      actualiza cada selector DOM al nuevo árbol de
      componentes (el contrato de atributos `data-*` se
      preserva; las clases CSS subyacentes cambian a
      clases de utilidad de Tailwind 4). Re-corre el
      fixture de chromium contra `make api`; captura el
      artefacto de trace de Playwright.
      <!-- sdd-owner: implementation -->
- [ ] 5c.4 G — `tests/test_web_toggle.py` (actualización
      de selectores, ~80 LoC de delta): mismo patrón que
      5c.3 para el toggle de tema.
      <!-- sdd-owner: implementation -->
- [ ] 5c.5 T — integración del harness Playwright +
      Lighthouse: parametriza sobre las rutas URL del
      fixture chromium legacy (`/`, `/index.html`,
      `/_next/static/<h>.js`) y verifica que los traces
      del fixture chromium coinciden con el nuevo árbol
      de componentes. <!-- sdd-owner: implementation -->
- [ ] 5c.6 G — borrado de `web/index.html` (archivo
      eliminado del repo); borrado de `web/{app,state,api,
      tree,breadcrumb,detail,nav,dom,banner,help,keymap,
      settings,search,file_explorer,file_viewer,format,
      search_urls}.js` (18 archivos eliminados); borrado
      de `web/index.css`; `web/dist/tailwind.css` ya no
      se rastrea (regenerado por el `make css` revertido
      tras el rollback, nunca por la nueva build);
      borrado de `tailwind.config.js`. El borrado del
      `web/index.html` retira el CSS inline legacy de
      1.963 líneas que los cuatro hijos CSS (3c-a / 3c-b /
      3c-c / 3c-d) migraron a `src/app/globals.css`.
      <!-- sdd-owner: implementation -->
- [ ] 5c.7 Refactor — el test
      `test_legacy_module_count_matches_exploration` de
      `tests/test_evidence_baseline.py` se actualiza para
      verificar que el roster legacy `web/*.js` está
      **ausente** (el test se queda en la suite como
      guardia de regresión contra módulos vanilla legacy
      que se cuelen de vuelta en el árbol).
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 5c.1, 5c.3 | `.venv/bin/python3 -m pytest tests/test_e2e_file_explorer.py -v` | Playwright corre el fixture de chromium de extremo a extremo contra `make api` | `git revert <5c-sha>` restaura `web/*.{html,js,css}` + `tailwind.config.js`; las actualizaciones de selectores de test revierten; sin cambio en `src/` |
| 5c.2, 5c.4 | `.venv/bin/python3 -m pytest tests/test_web_toggle.py -v` | mismo | mismo |
| 5c.5 | mismo | mismo; se emiten trace de Playwright + JSON de Lighthouse | mismo |
| 5c.6 | mismo | `make api` arranca uvicorn; `ls web/` vacío | mismo |
| 5c.7 | `.venv/bin/python3 -m pytest tests/test_evidence_baseline.py::test_legacy_module_count_matches_exploration -v` | mismo | mismo |

## Fase 6: Trabajo de validación (después del camino candidato completo, antes de PR 3e)

El camino candidato es el conjunto completo de sub-PRs en
posiciones 1–12 (bootstrap de toolchain, exportación
estática del App Router, los cuatro hijos CSS 3c-a / 3c-b /
3c-c / 3c-d, Makefile/mount, 4a, 4b, 5a, 5b, 5c) acumulado
en la rama tracker `docs/complete-taxa-frontend-migration-plan`
(nada ha llegado a `develop` todavía — el tracker queda
draft/no-merge hasta que la cadena completa). La Fase 6
corre **después** de eso, **antes** de PR 3e. Es **trabajo
de validación**, no un objetivo de migración — no genera
código nuevo en `web/**`, handlers de ruta nuevos en
`api/server.py`, ni archivos nuevos en `extension/**`. Sus
artefactos se registran en `apply-progress.md` §Registro de
cambios como flips de puertas (G5 reproducible, G6 PASS, G4
PASS).

La Fase 6 tiene tres sub-pasos (6a, 6b, 6c) — uno por cierre
de puerta — y PUEDEN entregarse como tres eslabones de la
cadena (el default: posiciones 13 / 14 / 15) o colapsar en un
único PR hijo en la posición 13 según si `apply-progress.md`
los registra juntos o separados. Colapsarla acorta la cadena
sin cambiar la topología (el batch sigue apuntando a la
rama del PR 5c, y PR 3e sigue apuntando al último eslabón
de la Fase 6). La política `ask-on-risk` del mantenedor
aplica si el batch excede el presupuesto de 400 líneas
(estimado ~190 LoC authored repartidos entre los tres
sub-pasos; cómodamente bajo).

### Fase 6a: Cierre de baseline de hidratación G5 (PR 6a → rama del PR 5c, posición 13/16)

- [ ] 6a.1 R — `tests/test_hydration_timing.py` (ya
      enviado por el predecesor PR 1b.3b): el test
      verifica que `scripts/measure_hydration.py` sale
      distinto de cero cuando el JSON del baseline legacy
      falta o es esquema-inválido. El test se queda; sin
      cambio de código de producción. Nuevo script helper
      `scripts/reconstruct_hydration_baseline.py` lee los
      números documentados `delta_server_to_tree_first_paint_ms`
      del predecesor desde
      `openspec/changes/migrate-nextjs-tailwind4/design.md`
      §"Migration Evidence Baseline" y emite
      `web/dist/evidence-baseline.json` con el mismo
      esquema que pinea el test de hidratación.
      <!-- sdd-owner: implementation -->
- [ ] 6a.2 G — `scripts/reconstruct_hydration_baseline.py`
      (~50 LoC): lee los números del baseline legacy
      verbatim del design.md del predecesor (la entrada es
      la fuente markdown parseada para la tabla; la salida
      es un archivo JSON que coincide con el esquema que
      pinea `tests/test_hydration_timing.py`).
      <!-- sdd-owner: implementation -->
- [ ] 6a.3 G — corre `python scripts/measure_hydration.py
      --baseline web/dist/evidence-baseline.json --candidate
      out/` contra la build candidata aterrizada en
      posiciones 1–12; emite el nuevo JSON de hidratación
      junto al baseline; registra el delta en
      `apply-progress.md` §Registro de cambios.
      <!-- sdd-owner: implementation -->
- [ ] 6a.4 T — verifica que el delta ≤ 0 % en paint
      inicial y latencia de interacción; si lo excede,
      falla cerrado y escribe la solicitud de exención en
      `design.md` §"Risk register" antes de que G5 pueda
      flipar. <!-- sdd-owner: implementation -->
- [ ] 6a.5 Refactor — colapsa el script + corrida +
      verificación en un solo shim `scripts/g5_close.sh`
      que el apply worker invoca una vez y registra el
      resultado en `apply-progress.md`.
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 6a.1–6a.5 | `.venv/bin/python3 -m pytest tests/test_hydration_timing.py -v` | `scripts/g5_close.sh` exit 0; `apply-progress.md` §Registro de cambios registra el flip de puerta | `git revert <6a-sha>` elimina `scripts/reconstruct_hydration_baseline.py` y el delta de `apply-progress.md`; el JSON del baseline legacy se queda (regenerado en la próxima corrida de 6a) |

### Fase 6b: Ensayo de cutover G6 (PR 6b → rama del PR 6a, posición 14/16)

- [ ] 6b.1 R — `tests/test_rehearse_cutover.py` (nuevo):
      verifica que `scripts/rehearse_cutover.py` sale 0
      contra el manifiesto activado; parametriza sobre los
      cuatro subconjuntos de la unidad de cutover
      (`web_dir_only`, `consumers_only`, `makefile_only`,
      `artifact_only`) y verifica el invariante de
      fail-closed (un ensayo de solo-subconjunto **falla**).
      <!-- sdd-owner: implementation -->
- [ ] 6b.2 G — `scripts/rehearse_cutover.py` (~120 LoC):
      dry-runs la unidad de cutover atómico (repoint de
      WEB_DIR + 26 actualizaciones de consumidores +
      reescritura del Makefile + artefacto de build
      `out/`) contra un clon `tmp_path` del candidato.
      Corre el verificador G3 Tier-2
      (`scripts/verify_consumers.py`) contra el manifiesto
      activado; emite `cutover-rehearsal.json` con
      `activation_complete: true`, `unselected_count: 0`,
      y `silent_fallback_paths: []`. Sale distinto de cero
      en cualquier dry-run de solo-subconjunto.
      <!-- sdd-owner: implementation -->
- [ ] 6b.3 G — flipa cada `activation_status` y
      `replacement.status` en
      `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
      de `selected` (legacy pre-cut, Tier-1) al
      **registro de activación post-cut** (Tier-2) para
      cada uno de los 26 consumidores §3.1. El flip es un
      artefacto de planificación autoría del apply worker
      en el mismo release que el script de ensayo. **El
      `cutover-manifest.json` del predecesor vive bajo
      `migrate-nextjs-tailwind4/` (directorio congelado)
      — el flip se escribe en una copia de trabajo en
      `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
      según la guía §"Cutover-manifest activation" del
      spec.** La copia de trabajo es lo que PR 3e lee en
      el momento del cutover; la copia del predecesor
      queda byte-idéntica (congelada).
      <!-- sdd-owner: implementation -->
- [ ] 6b.4 T — verifica que el script de ensayo reporta
      cero silent fallback paths (no existe ninguna ruta
      de código "fall back to legacy `web/` on build
      failure" en `Makefile::api` o `api/server.py`).
      <!-- sdd-owner: implementation -->
- [ ] 6b.5 Refactor — extrae la invocación G3 Tier-2 en un
      pequeño helper `run_g3_tier2(manifest, out)` para
      que el script de ensayo y la verificación de PR 3e
      del apply worker compartan la misma ruta de código.
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 6b.1, 6b.4 | `.venv/bin/python3 -m pytest tests/test_rehearse_cutover.py -v` | `scripts/rehearse_cutover.py` exit 0 contra el manifiesto activado; `cutover-rehearsal.json` lleva `activation_complete: true` | `git revert <6b-sha>` elimina `scripts/rehearse_cutover.py`, `tests/test_rehearse_cutover.py`, y la copia de trabajo de `cutover-manifest.json`; sin cambio en `src/` o `api/` |
| 6b.2 | mismo | mismo | mismo |
| 6b.3 | `python scripts/verify_consumers.py --manifest openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json --out out/ --serve --fixture-web-root <candidate>` | El verificador G3 Tier-2 sale 0; `CONSUMER-READINESS.json` reporta los 26 consumidores §3.1 `selected` | mismo |

### Fase 6c: Medición de paridad G4 Playwright + Lighthouse (PR 6c → rama del PR 6b, posición 15/16)

- [ ] 6c.1 R — `tests/test_e2e_file_explorer.py` (ya
      actualizado por Fase 5c) y `tests/test_web_toggle.py`
      (ya actualizado por Fase 5c): los tests se quedan;
      sin cambio de código de producción. La medición G4
      es el delta entre el trace Playwright + Lighthouse
      de Fase 5c sobre la nueva build candidata y el
      fixture chromium legacy que el predecesor capturó.
      <!-- sdd-owner: implementation -->
- [ ] 6c.2 G — corre Playwright + Lighthouse contra la
      build candidata aterrizada en posiciones 1–12;
      captura `out/g4-parity-report.json` con los números
      de paint inicial y latencia de interacción.
      Registra el delta en `apply-progress.md`
      §Registro de cambios. <!-- sdd-owner: implementation -->
- [ ] 6c.3 T — verifica que el delta ≤ 0 % en paint
      inicial y latencia de interacción; si lo excede,
      falla cerrado y escribe la solicitud de exención en
      `design.md` §"Risk register" antes de que G4 pueda
      flipar. <!-- sdd-owner: implementation -->
- [ ] 6c.4 Refactor — extrae la medición en
      `scripts/g4_measure.sh` para que el apply worker lo
      invoque una vez y registre el resultado en
      `apply-progress.md`. <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 6c.1–6c.4 | `.venv/bin/python3 -m pytest tests/test_e2e_file_explorer.py tests/test_web_toggle.py -v` | `scripts/g4_measure.sh` exit 0; `out/g4-parity-report.json` lleva paint inicial + latencia de interacción; `apply-progress.md` §Registro de cambios registra el flip de puerta | `git revert <6c-sha>` elimina el delta de `apply-progress.md`; sin cambio en `tests/` o `scripts/` (el script de medición se queda como guardia de regresión futura) |

## Fase 3e: Cutover atómico (PR 3e → rama del PR 6c, posición 16/16, con compuerta en las seis puertas verdes)

La unidad de cutover atómico (según
`design.md` §"Atomic cutover unit") cambia **exactamente lo
siguiente** en un solo release. **No se permite revertir un
subconjunto.** PR 3e se envía solo cuando:

- [ ] **G1 PASS** (registrado del predecesor).
      <!-- sdd-owner: parent -->
- [ ] **G2 PASS** (registrado contra la build limpia
      verificada de Next 16.3.3 / Turbopack; entrada del
      `apply-progress.md` del predecesor del 2026-08-30).
      <!-- sdd-owner: parent -->
- [ ] **G3 Tier-1 PASS** (registrado: los 26 consumidores
      §3.1 en verde contra el runtime legacy pre-cut vía
      el fixture controlado y `scripts/verify_consumers.py`;
      PR #109 + #111 + #115 + #116).
      <!-- sdd-owner: parent -->
- [ ] **G4 PASS** (Fase 6c medida; registrada en
      `apply-progress.md` §Registro de cambios).
      <!-- sdd-owner: parent -->
- [ ] **G5 reproducible** (Fase 6a reconstruida; registrada
      en `apply-progress.md` §Registro de cambios).
      <!-- sdd-owner: parent -->
- [ ] **G6 PASS** (Fase 6b ensayada; registrada en
      `apply-progress.md` §Registro de cambios).
      <!-- sdd-owner: parent -->

Si cualquier puerta está ausente, falla, es obsoleta (> 7
días) o incomparable, PR 3e está **bloqueado**, nunca en
éxito. El cutover de cuatro conjuntos:

1. **`WEB_DIR` constant** en `api/server.py:54` (ya
   repointed en Fase 3d; PR 3e flipa el artefacto de
   build bajo `out/` desde la build candidata a la build
   de producción con el check de runtime
   `engines.node >= 20.9.0` en vivo).
2. **Every active-consumer update** en §3.1 del design.md
   del predecesor (ya autoría por Fase 3d para la ruta del
   lector AC-21; PR 3e flipa los 25 consumidores §3.1
   restantes para que lean del árbol de componentes React
   en lugar de las rutas legacy `web/*`). El flip es el
   registro de activación post-cut en
   `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`
   (copia de trabajo; la copia del predecesor queda
   congelada).
3. **The `Makefile::api` and `Makefile::web` targets**
   (ya reescritos por Fase 3d; PR 3e flipa el paso legacy
   `make css` de Tailwind-3.4 desde "regenerar
   `web/dist/tailwind.css`" a "exit 0 no-op" — la build de
   Tailwind 4 vive dentro de `next build`).
4. **The build artifact** — el directorio `out/` mismo
   (`out/index.html`, `out/_next/static/chunks/**`,
   `out/.next/build-manifest.json`, la clasificación de
   página de error si se emite `404.html` / `500.html`).
   El artefacto se regenera por la build de producción en
   el momento del cutover.

La lista de tareas de PR 3e (solo después de que las seis
puertas estén verdes):

- [ ] 3e.1 R — `tests/test_verify_consumers.py` (ya
      enviado por el predecesor PR #109 + #111 + #115 +
      #116): el test se queda; PR 3e lo re-corre contra
      el manifiesto activado en
      `openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json`.
      <!-- sdd-owner: implementation -->
- [ ] 3e.2 G — corre
      `python scripts/verify_consumers.py --manifest openspec/changes/complete-taxa-frontend-migration/cutover-manifest.json
      --out out/` contra la build candidata; verifica que
      `CONSUMER-READINESS.json` sale 0 con
      `activation_complete: true`, `unselected_count: 0`.
      <!-- sdd-owner: implementation -->
- [ ] 3e.3 G — re-corre `make api` contra la build de
      cutover; verifica que uvicorn vincula
      `127.0.0.1:8765` solo; verifica que
      `curl http://127.0.0.1:8765/index.html` devuelve
      `out/index.html`; verifica que
      `extension/manifest.json::host_permissions` queda
      `["http://localhost:8765/*"]`.
      <!-- sdd-owner: implementation -->
- [ ] 3e.4 G — re-corre `make smoke` contra la build de
      cutover; verifica 63 pasados, 8 saltados baseline
      preservado. <!-- sdd-owner: implementation -->
- [ ] 3e.5 G — flipa el footer de estado de puertas en
      `apply-progress.md` §Status desde "bloqueado /
      no reproducible / bloqueado" a "PASS registrado (G4
      / G5 / G6 cerrados por Fase 6a / 6b / 6c)".
      <!-- sdd-owner: implementation -->
- [ ] 3e.6 T — `tests/test_verify_build.py` (ya enviado
      por la evidencia G2 del predecesor): el test se
      queda; re-corre contra `out/BUILD-INVENTORY.json`
      de la build de cutover; verifica que ninguna clase
      de asset falta. <!-- sdd-owner: implementation -->
- [ ] 3e.7 Refactor — `apply-progress.md` §Registro de
      cambios registra el hash de commit del cutover, las
      fechas de flip de puertas, y la salida del
      verificador G3 Tier-2. <!-- sdd-owner: implementation -->

### Reversión bajo la cadena

PR 3e es el **último hijo**, no un PR de `develop`. Existen
dos ventanas de reversión:

| Ventana | Estado | Reversión |
|---|---|---|
| Antes de que el tracker se fusione | Nada está en `develop`; el cutover vive solo en la rama tracker | Mantener o cerrar el PR tracker — `develop` queda intacto por construcción |
| Después de que el tracker se fusiona | Toda la cadena aterriza en `develop` en una integración | `git revert <pr3e-sha>` restaura el build vanilla legacy atómicamente (según `design.md` §"Rollback unit") |

Para que `<pr3e-sha>` quede direccionable en `develop`, el
tracker DEBE fusionarse con un **commit de merge** (sin
squash), para que los commits individuales de la cadena
sobrevivan a la integración. Si el tracker se squash-mergea
en su lugar, la unidad de reversión atómica se vuelve el
merge del tracker mismo: `git revert -m 1 <tracker-merge-sha>`.
De cualquier manera la reversión es **una** revert cubriendo
el cutover completo de cuatro conjuntos — **no se permite
revertir un subconjunto**.

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3e.1–3e.2 | `.venv/bin/python3 -m pytest tests/test_verify_consumers.py -v` | El verificador G3 Tier-2 sale 0; `CONSUMER-READINESS.json` lleva `activation_complete: true` | `git revert <pr3e-sha>` restaura el build vanilla legacy atómicamente (según `design.md` §"Rollback unit"): `web/index.html`, `web/app.js`, los 18 módulos `web/*.js`, `web/dist/tailwind.css`, `tailwind.config.js`, el `package.json` + `package-lock.json` legacy, el `Makefile::api` legacy, el `api/server.py:54` legacy |
| 3e.3 | `curl http://127.0.0.1:8765/index.html` devuelve `out/index.html` | `make api` arranca uvicorn en 8765; `lsof -i :8765` muestra solo uvicorn | mismo |
| 3e.4 | `make smoke` sale 0 | mismo | mismo |
| 3e.5 | n/a (artefacto de planificación) | n/a | mismo |
| 3e.6 | `.venv/bin/python3 -m pytest tests/test_verify_build.py -v` | `out/BUILD-INVENTORY.json` lleva ninguna clase faltante | mismo |
| 3e.7 | n/a | n/a | mismo |

## Fuera de alcance (según `AGENTS.md` y la propuesta)

- **No `git push`, `git commit`, `gh pr create`, `git stash`**
  en esta fase de tareas. La fase de apply posee esas
  acciones.
- **No nuevos worktrees** — el apply worker crea worktrees
  según `AGENTS.md` §4.
- **No ediciones en `openspec/changes/migrate-nextjs-tailwind4/**`**
  (predecesor congelado).
- **No reescritura del backend** (handlers de ruta de
  `api/server.py`, lógica SQLite/WAL, flujo de materialize,
  defensa SSRF en `save-url`).
- **No ediciones del pipeline ETL** (`etl/parse_textree`,
  `etl/load_coldp`, `etl/load_worms`,
  `etl/load_freshwater`, migraciones).
- **No trabajo de paridad de la extensión de Chrome** — un
  cambio separado rastrea cualquier adaptación de la
  extensión consciente de React.
- **No trabajo de SEO / metadata / sitemap / robots**.
- **No rutas nuevas** (Settings, About, Help) más allá de
  lo que la UI legacy expone hoy.
- **No tooling de cobertura** (`coverage.available: false`).
- **No rediseño visual** (impeccable / Stitch follow-up).
- **No consolidación de un solo PR de los cuatro hijos
  CSS** — la re-división del CSS es vinculante; no
  colapsar 3c-a / 3c-b / 3c-c / 3c-d en un solo sub-PR
  (el PR 3c único anterior era insatisfacible porque
  intentaba migrar el CSS inline legacy de 1.963 líneas
  en un sub-PR bajo el presupuesto de revisión de 400
  líneas por PR).

## Contrato de congelación del predecesor (vinculante)

Cada sub-PR en Fases 3a–6c y PR 3e DEBE satisfacer:

- [ ] `git diff --stat origin/develop -- openspec/changes/migrate-nextjs-tailwind4/`
      muestra cero cambios. <!-- sdd-owner: parent -->
- [ ] `git diff --stat <immediate-base-branch>` muestra
      **solo** los archivos de esta rebanada (higiene de
      diff de cadena; un diff contaminado es un bug de
      base — reapuntar o rebasear, no revisar alrededor).
      <!-- sdd-owner: parent -->
- [ ] El check de protección de rama del PR rechaza
      cualquier PR que modifique
      `openspec/changes/migrate-nextjs-tailwind4/**`.
      <!-- sdd-owner: parent -->
- [ ] El hook de CI / lint del PR rechaza lo mismo.
      <!-- sdd-owner: parent -->

Si un sub-PR edita accidentalmente el directorio del
predecesor, el sub-PR está **bloqueado** y el apply worker
debe revertir la edición accidental antes de que el PR
pueda fusionarse. No hay ruta `size:exception` para
ediciones del predecesor.

## Reconciliación del pronóstico

- **3a** ~210 LoC authored (bootstrap de toolchain —
  pins de deps de `package.json` +
  `scripts/check-runtime.mjs` + base de `tsconfig.json`
  + `.nvmrc` + 2 tests nuevos); **3b** ~150 (bootstrap
  autocontenido de exportación estática del App Router
  — **layout/page marcadores semánticos mínimos** +
  `next.config.mjs` + `tests/test_app_shell_render.py`;
  sin montaje de AppShell, sin import de globals.css; la
  corrección del defecto de dependencia); **3c-a** ~400
  (tokens / base / modo oscuro — andamio inicial de
  `src/app/globals.css` con `@theme` + barrel de
  design-system + integración del
  `import "./globals.css";`; la costura de corrección del
  defecto de dependencia); **3c-b** ~400 (estilos de
  árbol + Overview inline — selectores de taxonomía en
  `@layer components`); **3c-c** ~400 (estilos de
  Search / Folder / Browser global — selectores de
  research / chrome en `@layer components`); **3c-d**
  ~300 (animaciones / utilidades + paridad final —
  `@layer base` con `@keyframes` / `color-mix()` /
  clases de utilidad / reset de body / reset de primer
  hijo + el `tests/test_tailwind_4_parity.py`
  consolidado); **3d** ~240 (el sub-PR re-posicionado
  más pesado en la frontera de posición 7, fusionando
  Makefile + WEB_DIR + AC-21); **4a** ~180; **4b**
  ~120 (guardia de hidratación + integración de AppShell
  en `src/app/{layout,page}.tsx`; la corrección del
  defecto de dependencia); **5a** ~310; **5b** ~395;
  **5c** ~200; **6a** ~50; **6b** ~120; **6c** ~20;
  **3e** ~120. **Total**: ~3.615 LoC authored a través
  de **16** sub-PRs (Δ ~+1.333 LoC del ~2.282 previo;
  la re-división del CSS particiona la migración del CSS
  inline legacy de 1.963 líneas en 4 hijos totalizando
  ~1.500 LoC (reemplazando los ~232 LoC del PR 3c único
  previo) y añade 4 tests de triangulación separados;
  cada sub-PR queda muy por debajo de 400).
- Los sub-PRs más grandes son los **cuatro hijos CSS
  3c-a / 3c-b / 3c-c** a ≤ 400 LoC cada uno (justo en
  el presupuesto de revisión de 400 líneas por PR con 0
  LoC de holgura en el hijo más ajustado); **5b** queda
  a ~395 LoC (-5 LoC de holgura). PR 3d queda a ~240
  LoC (-160 LoC / -40 % de holgura contra el presupuesto
  de 400 líneas).
- La Fase 6 colectivamente (6a + 6b + 6c) totaliza ~190
  LoC authored y ~120 LoC de artefacto de medición. Si
  el mantenedor prefiere un único batch encadenado para
  la Fase 6, los LoC combinados se quedan bien debajo de
  400; si prefiere tres sub-PRs separados para foco de
  revisión, cada uno también está debajo.
- **PRs encadenados recomendados: Sí** — cada sub-PR cabe
  por sí solo en el presupuesto por PR, pero el total de
  ~3.615 líneas y el cutover atómico (la feature DEBE
  integrarse antes de llegar a `develop`) sitúan este
  cambio en la compuerta de Feature Branch Chain.
- **Estrategia de cadena: `feature-branch-chain`**
  (elegida por el usuario). El tracker
  `docs/complete-taxa-frontend-migration-plan` (referido
  como PR #146) es draft/no-merge y es el **único** PR
  que apunta a `develop`; el PR hijo 3a apunta al
  tracker; cada hijo posterior apunta a su rama
  predecesora inmediata. Esto sustituye, para este
  cambio, el default de `AGENTS.md` §4 de apuntar directo
  a `develop` y el precedente de apply-progress del
  predecesor. El primer nuevo hijo CSS (PR 3c-a) trata al
  PR #146 tracker como el punto de partida fusionado para
  la re-división del CSS en cuatro hijos.
- **Longitud de la cadena: 16 PRs hijos + 1 tracker.** El
  presupuesto de revisión por hijo son los LoC authored
  listados arriba; el tracker no lleva presupuesto de
  revisión propio (es el punto de acumulación).
- **Estrategia de entrega: `ask-on-risk`** (según
  preflight; sin flag de riesgo abierto — el Enfoque A
  es FINAL, el predecesor está congelado, cada sub-PR
  cabe bajo 400 líneas, la re-división del CSS satisface
  la migración del CSS inline legacy de 1.963 líneas que
  el PR 3c único previo no podía).
- **Sobrecarga de la revisión correctiva del plan +
  corrección del defecto de dependencia + re-división del
  CSS**: la corrección del defecto de dependencia re-ambia
  el PR 3b a un bootstrap autocontenido, desplaza el
  cableado del `import "./globals.css";` al PR 3c-a, y
  desplaza la integración de `<AppShell>` al PR 4b. PR
  3b pierde ~25 LoC; PR 3c-a gana ~2 LoC; PR 4b gana
  ~30 LoC; el total authored se mueve ~+37 LoC (de
  ~2.245 a ~2.282). La re-división del CSS añade los
  cuatro hijos CSS (3c-a / 3c-b / 3c-c / 3c-d) en
  posiciones 3–6, reemplazando el PR 3c único previo en
  posición 3; renumera cada hijo posterior por +3
  posiciones (3d 4→7; 4a 5→8; 4b 6→9; 5a 7→10; 5b 8→11;
  5c 9→12; 6a 10→13; 6b 11→14; 6c 12→15; 3e 13→16); el
  total authored se mueve ~+1.333 LoC (de ~2.282 a
  ~3.615). Los presupuestos LoC por sub-PR se quedan muy
  por debajo de 400; solo permanece la excepción previa
  de `package-lock.json` regenerado de PR 3a. La
  corrección del defecto de dependencia y la re-división
  del CSS juntas preservan el presupuesto de 400 líneas
  por PR en cada sub-PR.
- **Riesgo / decisión (si el mantenedor prefiere una
  cadena más plana)**: las posiciones 1–2 (bootstrap de
  toolchain + exportación estática del App Router)
  podrían colapsarse en un único sub-PR a ~385 LoC
  authored — debajo de 400 pero ajustado. La topología
  de la cadena preserva el bootstrap como un foco de
  revisión separado para que los pins del toolchain y el
  contrato del App Router puedan revisarse
  independientemente; colapsar no es el default. Los
  cuatro hijos CSS (3c-a / 3c-b / 3c-c / 3c-d) NO
  PUEDEN colapsarse sin violar el presupuesto de revisión
  de 400 líneas por PR — la migración del CSS inline
  legacy de 1.963 líneas requiere cuatro hijos.