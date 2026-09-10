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
> introdujo un **PR de bootstrap de toolchain en la posición
> 1** (que absorbió los pins de deps de `package.json` y
> `scripts/check-runtime.mjs` previamente atribuidos al PR 3c
> original), degradó la **exportación estática del App Router**
> a la posición 2 (ahora segura porque el toolchain ya existe),
> mantuvo **Tailwind/tokens** en la posición 3, fusionó la
> **reescritura del Makefile** con el repoint de `WEB_DIR` +
> AC-21 en la posición 4, y siguió con **state → ports → e2e →
> validation → cutover atómico** en orden de dependencia
> correcto. El conteo de 13 hijos se preservó en esa revisión;
> solo cambiaron la topología de la cadena, el ámbito por hijo y
> los testigos por hijo. **El Enfoque A, FastAPI/SQLite y el
> predecesor congelado quedaron sin cambios.**

> **2026-09-02 — replan de la sub-secuencia del PR 3c (esta
> entrada)**. Después de que PR #144 (3a), PR #145 (3b) y PR
> #146 (reconciliación de 3b) aterrizaran en el tracker, el
> PR 3c original único fue diagnosticado como insatisfacible:
> reclamaba ~230 LoC mientras porteaba cada token `:root`
> legacy, la paleta `[data-theme="dark"]`, la familia
> `--realm-*`, los `@keyframes`, los selectores `color-mix()`,
> las reglas a medida del bloque `<style>` inline legacy de
> `web/index.html` (líneas 14–1972 = **1.963 líneas**), y el
> barrel del design-system — muy por encima del presupuesto de
> revisión de 400 líneas. El usuario autorizó una sub-secuencia
> encadenada que reemplaza el PR 3c único con **cuatro hijos
> revisables en las posiciones 3–6** (`3c-i`, `3c-ii`, `3c-iii`,
> `3c-iv`), cada uno ≤ 400 líneas authored incluyendo tests.
> Cada hijo posterior se **renumera** para mantener el contrato
> de dependencia lineal: `3d → 7`, `4a → 8`, `4b → 9`,
> `5a → 10`, `5b → 11`, `5c → 12`, `6a → 13`, `6b → 14`,
> `6c → 15`, `3e → 16`. La nueva cadena de **16 hijos**
> comienza con **3c-i apuntando al tracker** (es decir, la rama
> `docs/complete-taxa-frontend-migration-plan` **después** de
> que la reconciliación del PR #146 se fusione), de modo que la
> sub-secuencia del 3c recoge el 3a + 3b + reconcile ya
> fusionados sin un paso extra de reconciliación. El total
> authored en LoC sube de ~2.245 a ~3.485 porque cada regla CSS
> legacy se porta; el sub-PR nuevo más grande por plan es **3c-i
> a ~390 LoC** (-10 LoC de holgura bajo 400). PR 3a retiene la
> `size:exception` de `package-lock.json` regenerado
> (generated-resolution-only) como la `size:exception`
> documentada previa; **PR 3c-ii abre subsecuentemente una
> segunda `size:exception` aprobada por el usuario** para la
> rebanada completa de CSS de árbol / detalle de taxonomía
> (implementación real totaliza **831 LoC = 822 inserciones +
> 9 deletions**, sobrepaso +442 LoC sobre la estimación previa
> de `~380 LoC` y +431 LoC contra el presupuesto de
> 400 líneas — véase el addendum dedicado abajo para la
> justificación de autorización; la cadena de 16 hijos se
> preserva). **El Enfoque A, FastAPI/SQLite, el predecesor
> congelado y la estrategia de Feature Branch Chain quedan
> sin cambios.**

> **2026-09-02 — corrección de defecto de dependencia (esta
> revisión)**. La re-auditoría de pre-flight del portón de apply
> identificó un segundo defecto de dependencia dentro de la
> topología corregida: el `src/app/layout.tsx` del PR 3b
> importaba `@taxa/app-shell` (un módulo que el PR 4b envía en
> la posición 9/16 — *más tarde* en la cadena) y `./globals.css`
> (un archivo que el PR 3c-i envía en la posición 3/16 — *más
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
> la línea `import "./globals.css";` se mueve al PR 3c-i (que ya
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
> ~150 LoC (-25), PR 3c-i crece ~2 LoC (1 línea de import de
> `globals.css`), PR 4b crece ~30 LoC (costura de integración
> de AppShell); total authored ~2.282 LoC en los 13 sub-PRs;
> cada sub-PR queda muy por debajo de 400; **solo permanece la
> excepción previa de `package-lock.json` regenerado de PR
> 3a**. El Enfoque A, FastAPI/SQLite, el predecesor congelado,
> los specs por dominio y las puertas de validación quedan sin
> cambios.

## Frontera de alcance para este archivo de tareas

- **En alcance**: cada sub-PR bajo el Enfoque A listado en
  `design.md` §"Sub-PR slice under Approach A" (posiciones
  1 / 16 a 16 / 16 en la cadena corregida: bootstrap de
  toolchain, exportación estática del App Router,
  **3c-i tokens / base / dark mode, 3c-ii styling de árbol /
  detalle de taxonomía, 3c-iii styling de Search / Folder /
  global Browser, 3c-iv animations / utilities + paridad CSS
  final + barrel del design-system**, Makefile/mount, 4a, 4b,
  5a, 5b, 5c, 6a, 6b, 6c, 3e) más el **bloque de validación
  de Fase 6**
  (reconstrucción G5 / autoría de ensayo G6 / medición G4)
  que corre **después de que el camino candidato completo
  esté acumulado en la rama tracker
  `docs/complete-taxa-frontend-migration-plan`** pero
  **antes** de que PR 3e pueda aterrizar. PR 3e (cutover
  atómico) se publica solo cuando las seis puertas están
  verdes.
- **El cierre de G4 / G5 / G6 es trabajo de validación**, no
  un objetivo de migración independiente: sus artefactos se
  registran en `apply-progress.md` §Registro de cambios
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
  bootstrap` → `App Router static export` → **`3c-i tokens /
  base / dark mode` → `3c-ii styling de árbol / detalle de
  taxonomía` → `3c-iii styling de Search / Folder / global
  Browser` → `3c-iv animations / utilities + paridad CSS
  final`** → `Makefile/mount` → `state` → `ports` → `e2e` →
  `validation` → `atomic cutover`. PR 3a (bootstrap de
  toolchain) aterriza antes que cualquier PR que llame a
  `next build`; la exportación estática del App Router
  depende de que `next`, `react`, `react-dom`, `typescript`,
  `tailwindcss` estén instalados y de que exista la
  verificación de Node ≥ 20.9.0; PR 3c-i depende de que
  `tailwindcss@^4` esté instalado; PRs 3c-ii / 3c-iii /
  3c-iv dependen de que el hijo 3c previo haya enviado sus
  tokens / selectores / utilidades en orden de fuente; la
  reescritura del Makefile depende de que el toolchain +
  Tailwind + la cascada CSS completa estén instalados para
  que `npm run build:web` resuelva; el repoint de `WEB_DIR`
  depende de que `out/index.html` sea producido por el
  target `api` del Makefile; el typed store + guardia de
  hidratación dependen de que el App Router + Tailwind estén
  en vivo; los puertos de capability dependen de que el
  typed store esté en vivo (para `tree-source` y
  `last-taxon-id`); las actualizaciones e2e dependen de los
  puertos de capability; la validación de Fase 6 depende del
  camino candidato completo; PR 3e depende de que las seis
  puertas estén verdes.

## Pronóstico de carga de revisión

| Campo | Valor |
|-------|-------|
| Líneas modificadas estimadas | ~3.485 authored a través de **16 sub-PRs** (bootstrap de toolchain + exportación estática del App Router + **3c-i tokens / base / dark mode + 3c-ii styling de árbol / detalle de taxonomía + 3c-iii styling de Search / Folder / global Browser + 3c-iv animations / utilities + paridad CSS final** + Makefile/mount + 2 browser-state + 2 puertos de capability + e2e/borrar-legacy + 3 validación Fase 6 + 1 cutover atómico). El delta de +1.240 LoC sobre la estimación previa de ~2.245 viene completamente de la sub-secuencia del 3c: el bloque `<style>` inline legacy en `web/index.html` (1.963 líneas) debe portarse literalmente a Tailwind 4 `@theme` + `@layer base`, y un test de paridad debe enumerar cada token `:root` legacy, cada referencia `var(--name)`, cada selector `--realm-*`, cada `@keyframes`, cada selector `.animate-spin` y `color-mix()`, y cada clase utility. |
| Riesgo de presupuesto de 400 líneas | **Bajo** para el trabajo authored en cada hijo **excepto PR 3c-ii, que carga una `size:exception` aprobada por el usuario para la rebanada completa de CSS de árbol / detalle de taxonomía — véase el addendum dedicado abajo**. El sub-PR nuevo más grande por diff real es **PR 3c-ii a 831 LoC** (822 inserciones + 9 deletions; sobrepaso +431 LoC contra el presupuesto de 400 líneas); los otros hijos del 3c son 3c-i ~390, 3c-iii ~390, 3c-iv ~280. El previamente-mayor 5b queda en ~360 LoC; 3d queda en ~240 LoC. **Los 16 sub-PRs ≤ 400 LoC authored excepto PR 3c-ii**, que carga la `size:exception` aprobada por el usuario (la excepción previa de `package-lock.json` regenerado de PR 3a es generated-resolution-only y queda abierta como la segunda `size:exception` documentada junto a PR 3c-ii). |
| PRs encadenados recomendados | **Sí** — 16 PRs hijos encadenados (~3.485 líneas authored en total ≫ 400, y el cutover atómico exige que la feature se integre antes de llegar a `develop`). La sub-secuencia del 3c es ahora cuatro hijos revisables, cada uno cargando ~280–390 LoC, de modo que ningún hijo cargue con las 1.963 líneas del CSS inline. |
| División sugerida | PR 3a (bootstrap de toolchain) → 3b (exportación estática del App Router) → **3c-i (tokens / base / dark mode)** → **3c-ii (styling de árbol / detalle de taxonomía)** → **3c-iii (styling de Search / Folder / global Browser)** → 5.5 (reparación de pipeline PostCSS) → 5.6 (reparación de paridad estructural DOM↔CSS) → **3c-iv-barrel (barrel del design-system + Icon/Button + purity test)** → **3c-iv-keyframes (cinco `@keyframes` + `.animate-spin`)** → **3c-iv-viewer (visor de imagen / video)** → **3c-iv-settings (vista Settings)** → **3c-iv-colors (aliases `--color-*` de Tailwind + paridad de utility)** → 3d (Makefile/mount) → 4a → 4b → 5a → 5b → 5c → Fase 6a (G5) → Fase 6b (G6) → Fase 6c (medición G4) → PR 3e (cutover atómico, con compuerta) |
| Estrategia de entrega | ask-on-risk (según preflight; el Enfoque A ya está bloqueado, sin anulación abierta) |
| Estrategia de cadena | **feature-branch-chain** (elegida por el usuario, sin cambios por el replan del 3c). El tracker `docs/complete-taxa-frontend-migration-plan` es draft/no-merge y es el **único** PR que apunta a `develop`. PR 3a apunta al tracker; PR 3b apunta al PR 3a; **PR 3c-i apunta al tracker** (es decir, la rama **después** de que la reconciliación del PR #146 se fusione, recogiendo el 3a + 3b + reconcile ya fusionados sin un paso extra de reconciliación); cada hijo posterior apunta a su rama predecesora inmediata. Sustituye, para este cambio, el default de `AGENTS.md` §4 de apuntar directo a `develop`. |

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
> entrada del App Router en la posición 1 con un testigo
> de `next build` → `out/index.html` que requería que
> `next`, `react`, `tailwindcss`, `typescript` estuvieran
> instalados y que la verificación de Node ≥ 20.9.0
> existiera; el toolchain mismo estaba programado para la
> posición 3, DESPUÉS de que el testigo del App Router
> tuviera que estar verde. La topología corregida movió el
> toolchain a la posición 1, degradó el testigo del App
> Router a la posición 2 (ahora satisfacible), mantuvo
> Tailwind/tokens en la posición 3 (depende de Tailwind
> instalado), fusionó la reescritura del Makefile con el
> repoint de `WEB_DIR` en la posición 4 (depende de que
> `next build` produzca `out/`), y siguió con state,
> ports, e2e, validación de Fase 6 y cutover atómico. El
> conteo de 13 hijos se preservó en esa revisión.

> **Justificación del replan de la sub-secuencia del PR 3c
> (esta entrada)**. El PR 3c original único en la posición 3
> reclamaba ~230 LoC pero tenía que portar cada token
> `:root` legacy, la paleta `[data-theme="dark"]`, la familia
> `--realm-*`, las animaciones `@keyframes` a medida,
> `.animate-spin`, los selectores `color-mix()`, y el barrel
> del design-system — es decir, la mayor parte del bloque
> `<style>` inline de 1.963 líneas en `web/index.html`. PR
> #144 (3a), PR #145 (3b) y PR #146 (reconciliación de 3b)
> ya habían aterrizado en el tracker. El usuario autorizó
> una sub-secuencia encadenada que reemplaza el PR 3c único
> con **cuatro hijos revisables en las posiciones 3–6**
> (`3c-i`, `3c-ii`, `3c-iii`, `3c-iv`), cada uno ≤ 400
> líneas authored incluyendo tests, y renumera los hijos
> posteriores para mantener el contrato de dependencia
> lineal (3d → 7, 4a → 8, 4b → 9, 5a → 10, 5b → 11,
> 5c → 12, 6a → 13, 6b → 14, 6c → 15, 3e → 16). PR 3c-i
> **apunta al tracker** (la rama
> `docs/complete-taxa-frontend-migration-plan` **después**
> de que la reconciliación del PR #146 se fusione) de modo
> que la sub-secuencia del 3c recoge el 3a + 3b + reconcile
> ya fusionados sin un paso extra de reconciliación; los
> hijos posteriores en la sub-secuencia apuntan a la rama
> predecesora inmediata del 3c. El total authored en LoC
> sube de ~2.245 a ~3.485 porque cada regla CSS legacy se
> porta; el sub-PR nuevo más grande es **3c-i a ~390 LoC**
> (-10 LoC de holgura bajo 400); **la implementación
> real de PR 3c-ii totaliza 831 LoC (822 inserciones
> + 9 deletions), sobrepasando la estimación previa
> de `~380 LoC` en +442 LoC y el presupuesto de revisión por PR
> de 400 líneas en +431 LoC — el usuario aprobó una segunda
> `size:exception` para esta rebanada (la excepción
> de `package-lock.json` regenerado de PR 3a queda
> abierta como la `size:exception` documentada
> previa); véase el addendum append-only dedicado
> abajo para la justificación de autorización; la
> cadena de 16 hijos se preserva.**

> **Corrección del defecto de dependencia (revisión
> anterior)**. Después del reordenamiento, la re-auditoría
> de pre-flight del portón de apply encontró un segundo
> defecto de dependencia dentro de la topología corregida:
> el PR 3b en la posición 2 importaba `@taxa/app-shell` (un
> módulo que el PR 4b envía en la posición 9/16) y
> `./globals.css` (un archivo que el PR 3c-i envía en la
> posición 3/16). En su testigo de `next build`, ninguno de
> los dos archivos objetivo existía todavía. La misma
> auditoría marcó la aserción de triangulación de PR 3b.5
> que dice que la salida de build referencia la ruta del
> barrel del typed store `@taxa/browser-state` — ese archivo
> de barrel no existe hasta que el PR 4a aterriza. La
> corrección re-ambia el PR 3b a un bootstrap autocontenido
> de exportación estática del App Router (marcadores
> semánticos mínimos; sin AppShell, sin globals.css), mueve
> la línea `import "./globals.css";` al PR 3c-i, y mueve la
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
> posiciones 3 / 16, 4 / 16, 5 / 16, 6 / 16 (3c-i / 3c-ii /
> 3c-iii / 3c-iv), cada uno ≤ 400 líneas authored y
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
> CSS (PR 3c-i). Cada PR hijo posterior cambia de posición
> por +3 para acomodar los cuatro hijos CSS (3d pasa 4→7;
> 4a 5→8; 4b 6→9; 5a 7→10; 5b 8→11; 5c 9→12; 6a 10→13; 6b
> 11→14; 6c 12→15; 3e 13→16). El **conteo de 16 hijos**
> reemplaza al conteo previo de 13 hijos; las etiquetas
> semánticas (3a, 3b, 3c-i, 3c-ii, 3c-iii, 3c-iv, 3d, 4a, 4b,
> 5a, 5b, 5c, 6a, 6b, 6c, 3e) se preservan; solo cambian el
> contador de posición (NN en
> `feat/complete-taxa-frontend-migration-NN-XXX`) y las
> referencias a las ramas base. **Los presupuestos LoC por
> sub-PR se quedan muy por debajo de 400**; **solo permanece
> la excepción previa de `package-lock.json` regenerado de
> PR 3a**.

| Posición | Sub-PR | Rama | Base (destino del PR) |
|---|---|---|---|
| Tracker | — | `docs/complete-taxa-frontend-migration-plan` | `develop` — **draft / no-merge** (ahora carga las fusiones de PR #144 + #145 + #146) |
| 1 / 22 | 3a | `feat/complete-taxa-frontend-migration-01-3a` | `docs/complete-taxa-frontend-migration-plan` (tracker, **PR #144 ya fusionado**) |
| 2 / 22 | 3b | `feat/complete-taxa-frontend-migration-02-3b` | `feat/complete-taxa-frontend-migration-01-3a` (**PR #145 ya fusionado**) |
| 3 / 22 | 3c-i | `feat/complete-taxa-frontend-migration-03-3c-i` | `docs/complete-taxa-frontend-migration-plan` (tracker, **después de que la reconciliación del PR #146 se fusione**) |
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

    ```text
    develop
     └── docs/complete-taxa-frontend-migration-plan   ← PR tracker (draft / no-merge; carga PR #144 + PR #145 + PR #146)
          ↑ base del PR 3a: docs/complete-taxa-frontend-migration-plan
          └── feat/complete-taxa-frontend-migration-01-3a   ← bootstrap de toolchain (PR #144 fusionado)
               ↑ base del PR 3b: …-01-3a
               └── feat/complete-taxa-frontend-migration-02-3b   ← exportación estática del App Router (PR #145 fusionado)
                    ↑ base del PR 3b-reconcile: …-02-3b
                    └── feat/complete-taxa-frontend-migration-02-3b-reconcile   ← reconciliación de 3b (PR #146 fusionado)
                         ↑ base del PR 3c-i: tracker (después de PR #146)
                         └── feat/complete-taxa-frontend-migration-03-3c-i   ← tokens / base / dark mode
                              ↑ base del PR 3c-ii: …-03-3c-i
                              └── feat/complete-taxa-frontend-migration-04-3c-ii   ← styling de árbol / detalle de taxonomía
                                   ↑ base del PR 3c-iii: …-04-3c-ii
                                   └── feat/complete-taxa-frontend-migration-05-3c-iii   ← styling de Search / Folder / global Browser
                                        ↑ base del PR 3c-iv: …-05-3c-iii
                                                      └── feat/complete-taxa-frontend-migration-05-5-3c-iv-predecessor   ← PR 5.5 (reparación de pipeline Tailwind 4 / PostCSS)
                                                 ↑ base del PR 5.6: …-05-5-3c-iv-predecessor   (hijo de reparación interpolado)
                                                 └── feat/complete-taxa-frontend-migration-05-6-3c-iv-predecessor   ← PR 5.6 (reparación de paridad estructural DOM↔CSS)
                                                      ↑ base del PR 3c-iv-barrel: …-05-6-3c-iv-predecessor   (3c-iv-barrel es el primer hijo de la sub-secuencia 3c-iv)
                                                      └── feat/complete-taxa-frontend-migration-06-3c-iv-barrel   ← barrel del design-system + Icon/Button + purity test
                                                           ↑ base del PR 3c-iv-keyframes: …-06-3c-iv-barrel
                                                           └── feat/complete-taxa-frontend-migration-07-3c-iv-keyframes   ← cinco @keyframes + .animate-spin
                                                                ↑ base del PR 3c-iv-viewer: …-07-3c-iv-keyframes
                                                                └── feat/complete-taxa-frontend-migration-08-3c-iv-viewer   ← paridad CSS del visor de imagen / video
                                                                     ↑ base del PR 3c-iv-settings: …-08-3c-iv-viewer
                                                                     └── feat/complete-taxa-frontend-migration-09-3c-iv-settings   ← paridad CSS de la vista Settings
                                                                          ↑ base del PR 3c-iv-colors: …-09-3c-iv-settings
                                                                          └── feat/complete-taxa-frontend-migration-10-3c-iv-colors   ← aliases del namespace --color-* de Tailwind + paridad de utility
                                                                               ↑ base del PR 3d: …-10-3c-iv-colors   (los consumidores CSS finales dependen de colors)
                                                                               └── feat/complete-taxa-frontend-migration-11-3d   ← Makefile/mount
                                                                                    ↑ base del PR 4a: …-06-3c-iv-barrel   (los consumidores de design-system dependen de barrel)
                                                                                    └── feat/complete-taxa-frontend-migration-12-4a   ← typed store
                                                                                         ↑ base del PR 4b: …-12-4a
                                                                                         └── feat/complete-taxa-frontend-migration-13-4b   ← guardia de hidratación
                                                                                              ↑ … 5a → 5b → 5c → 6a → 6b → 6c …
                                                                                              └── feat/complete-taxa-frontend-migration-20-3e
                                                                                                   ← cutover atómico, último hijo de la cadena
                                             ↑ base del PR 3d: …-06-3c-iv
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
- **PR 3c-i — tokens / base / dark mode**. Depende de
  **3a** (`tailwindcss@^4` instalado). Bases off del
  tracker (la rama `docs/complete-taxa-frontend-migration-plan`
  **después** de que la reconciliación del PR #146 se
  fusione; el `src/app/layout.tsx` marcador en el que el PR
  3c-i importa `./globals.css`). Crea `src/app/globals.css`
  (andamio inicial: `@import "tailwindcss";` + bloque
  `@theme { … }` reflejando cada token `:root` legacy —
  paleta clara, paleta oscura `[data-theme="dark"]`, familia
  `--realm-*` — + bloque inicial de `@layer base` con los
  resets body / html / `main > :first-child` y los
  selectores `:focus-visible` globales), para que los hijos
  posteriores (3c-ii / 3c-iii / 3c-iv) extiendan con
  selectores de taxonomía, de research / chrome, y con
  `@keyframes` / `color-mix()` / utilidad / Settings /
  viewer respectivamente). El test de triangulación
  `tests/test_tailwind_4_parity.py` lee el bloque
  `<style>` legacy del `web/index.html` y verifica que cada
  token `:root` / `[data-theme="dark"]` / `--realm-*`
  resuelve a una declaración no vacía en
  `globals.css::@theme`.
- **PR 3c-ii — styling de árbol / detalle de taxonomía**.
  Depende de **3c-i** (los tokens + base layer + cascada
  dark-mode están en vivo, así que cada selector de este
  slice resuelve sus referencias `var(--token)`). Extiende
  `globals.css` con los selectores legacy de taxonomía
  (`.tier-header`, `.tree-row`, `.rank-badge`,
  `.scientific-name`, `.tree-source-toggle`,
  `#detail-panel`, `.detail-card`, `.detail-section`,
  `.overview-section`, `.detail-item`, `.search-pulse`,
  `.detail-tabs`, `.search-icon-btn`,
  `.materialize-btn`, kebab, modal de materialize,
  variantes de tinte de reino `.tree-row[data-realm="…"]`).
  El test de triangulación `tests/test_tailwind_4_parity.py`
  lee el `out/_next/static/chunks/*.css` generado y verifica
  que cada selector de taxonomía resuelve.
  **`size:exception`**: la implementación real totaliza
  **831 LoC (822 inserciones + 9 deletions)**, sobrepasando
  la estimación previa de `~380 LoC` en +442 LoC y el presupuesto
  de revisión por PR de 400 líneas en +431 LoC; el
  usuario aprobó una segunda `size:exception` para
  esta rebanada — véase el addendum append-only dedicado
  abajo para la justificación de autorización (la cadena
  de 16 hijos se preserva; el PR NO se reclama como
  fusionado ni verificado por esta nota).
- **PR 3c-iii — styling de Search / Folder / global
  Browser**. Depende de **3c-ii** (los selectores de
  taxonomía están en vivo; las referencias `var(--token)` en
  los selectores de browser resuelven). Extiende
  `globals.css` con los selectores del módulo research y del
  shell de chrome (`.toast`, `.search-engines-grid`,
  `.search-category-header`, `.search-engine-btn`,
  `.fex-meta-strip`, `.fex-tab-strip`,
  `.fex-snippet-frame`, `.fex-shell`,
  `.fex-tree-pane`, `.fex-viewer-pane`,
  `.fex-splitter`, `.fex-row`, `.fex-tree-header`,
  `.fex-children`, `.fex-banner`, `.fex-empty-state`,
  `.fex-search-*`, `.fex-csv-*`, `.fex-json-*`,
  `.fex-tree-truncated`). El test de triangulación
  `tests/test_tailwind_4_parity.py` enumera cada selector
  de research / chrome.
- **PR 3c-iv — animations / utilities + paridad CSS final +
  barrel del design-system**. Depende de **3c-iii** (la
  cascada CSS legacy completa ya está portada excepto
  `@keyframes` + utilidades + barrel del design-system).
  Extiende `globals.css` con las reglas `@keyframes`, la
  utility `.animate-spin`, los frames del visor de
  imagen + video, y los selectores de la vista de
  Settings; envía el barrel de design-system
  (`src/modules/design-system/{infrastructure/index.ts,
  presentation/Icon.tsx, presentation/Button.tsx}`);
  extiende `tests/test_tailwind_4_parity.py` con la
  enumeración de `@keyframes` + cada clase de utilidad
  legacy (`bg-primary`, `text-on-surface`, …) y envía
  `tests/test_design_system_purity.py` (grep guard sobre
  literales hex). El test de paridad final de PR 3c-iv es
  el testigo de consolidación de que el CSS inline legacy
  de **1.963 líneas** ha sido migrado a
  `src/app/globals.css` de extremo a extremo.
- **PR 3d — Makefile/mount**. Depende de **3b** (el App
  Router produce `out/index.html` cuando `next build`
  corre) y de **3c-iv** (los tokens de Tailwind 4 +
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
- **PR 4a — typed store**. Depende de **3c-iv** (barrel de
  design-system cargado); produce
  `src/modules/browser-state/**` typed store con cuatro
  sitios de lectura + cuatro de escritura.
- **PR 4b — guardia de hidratación + integración de
  AppShell**. Depende de **4a** (store disponible), **3b**
  (los marcadores `src/app/{layout,page}.tsx` en los que el
  PR 4b integra `<AppShell>`), y **3c-iv** (los tokens
  `@theme` de Tailwind 4 enviados por PR 3c-i + barrel de
  design-system enviado por PR 3c-iv, ambos cargados para
  `next build`). Produce
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
  `tree-source`) y de **3c-ii** (los selectores de
  taxonomía están en su lugar — los selectores de taxonomía
  se montan sobre el CSS de PR 3c-ii). Produce
  `src/modules/taxonomy/**` + el port de
  `web/{tree,detail,breadcrumb}.js` a React. PR 5a también
  envía el andamio del strip de pestañas de `DetailPanel`
  (strip de 3 pestañas `Overview` / `Search` / `Folder`) y
  el cuerpo de `OverviewTab` (nombre científico, estado de
  aceptación, autoría, conteo de especies); los selectores
  del strip de pestañas y el styling de OverviewTab
  correspondientes se montan sobre los selectores de
  taxonomía de PR 3c-ii.
- **PR 5b — port de research + pin CDN**. Depende de
  **5a** (flujos de lectura de estado de taxonomía
  compartidos con research y el andamio del strip de
  pestañas de `DetailPanel` en el que la acción `Search
  online` se enchufa), de **3d**
  (`src/data/search-engines.js` para el export nombrado
  `Engine`), y de **3c-iii** (los selectores de Search /
  Folder / global Browser están en su lugar — los
  selectores de research se montan sobre el CSS de PR
  3c-iii). Produce `src/modules/research/**` + pin CDN. PR
  5b también envía el cuerpo de `SearchTab` (lista
  categorizada de enlaces salientes en orden fijo
  `General` / `Taxonomic` / `Academic` / `Multimedia` /
  `Documents`), el cuerpo de `FolderTab`, el presentador
  `SearchLinkList` que mapea cada `Engine` a un anchor con
  `target="_blank"` y `rel="noopener noreferrer"`, y el
  re-anclaje de la pestaña `Browser` del header como el
  Research / file explorer global (NO scoped por taxón);
  los selectores correspondientes se montan sobre el
  bloque de selectores de PR 3c-iii.
- **PR 5c — selectores E2E + contrato `data-*` + borrar
  legacy**. Depende de **5b** (todos los componentes UI en
  vivo) y de **3c-iv** (el test de paridad final de Tailwind
  4 está en disco). Actualiza los selectores DOM de Playwright
  para el árbol de componentes React (el contrato de
  atributos `data-*` se preserva; las clases CSS subyacentes
  cambian a clases de utilidad de Tailwind 4); borra
  `web/*.{html,js,css}` + `tailwind.config.js` (el borrado
  del `web/index.html` legacy retira el CSS inline legacy de
  1.963 líneas que los cuatro hijos CSS (3c-i / 3c-ii /
  3c-iii / 3c-iv) migraron a `src/app/globals.css`).
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

> Orden: **3a → 3b → 3c-i → 3c-ii → 3c-iii → 3c-iv → 3d →
> 4a → 4b → 5a → 5b → 5c → 6a (G5) → 6b (G6) → 6c (medición
> G4) → 3e**. Cada PR hijo apunta a su **rama predecesora
> inmediata**, excepto PR 3c-i que **apunta al tracker** (la
> rama `docs/complete-taxa-frontend-migration-plan` después de
> que la reconciliación del PR #146 se fusione, recogiendo
> el 3a + 3b + reconcile ya fusionados). Solo el tracker
> apunta a `develop`. La Fase 6 corre **después** de que el
> camino candidato completo (posiciones 1–12) esté verde y
> acumulado en el tracker, y **antes** de que PR 3e pueda
> aterrizar. PR 3e tiene compuerta en G1 + G2 + G3 Tier-1
> (todos registrados del predecesor) más el cierre de G4 +
> G5 + G6 (los tres entregados por la Fase 6). Reversión =
> `git revert <pr3e-sha>` (ver §"Reversión bajo la cadena").

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
      delta) más `package-lock.json` regenerado (la única excepción de tamaño aprobada por el usuario para el `package-lock.json` regenerado de este PR; debe contener únicamente cambios de resolución requeridos por este manifiesto y revisarse junto con él — **PR 3c-ii abre subsecuentemente una segunda `size:exception` aprobada por el usuario para la rebanada completa de CSS de árbol / detalle de taxonomía, 831 LoC = 822 inserciones + 9 deletions; véase el addendum dedicado en este archivo para la justificación de autorización**): bumpea `next`, `react`, `react-dom`,
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
`./globals.css` (el PR 3c-i lo envía); los archivos
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
      NO importa `./globals.css`** (aterriza en PR 3c-i) —
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

## Sub-secuencia de la Fase 3c: cascada de Tailwind 4 (posiciones 3–6, reemplaza el PR 3c único original)

> **Por qué es una sub-secuencia de cuatro hijos, no un
> PR único** (replan del 2026-09-02). El original Fase 3c
> fue autoría como un único sub-PR a ~230 LoC, pero el
> bloque `<style>` inline legacy en `web/index.html`
> (líneas 14–1972) totaliza **1.963 líneas** de CSS a
> medida que debe portarse literalmente a Tailwind 4
> (`@theme` para tokens, `@layer base` para la cascada,
> más el barrel de design-system). PR #144 (3a), PR #145
> (3b), y PR #146 (reconciliación de 3b) ya aterrizaron
> en el tracker, de modo que el siguiente PR se abre
> desde el slot del 3c sin más reconciliación necesaria.
> El usuario autorizó dividir el slot del 3c en cuatro
> hijos revisables en las posiciones 3–6, cada uno ≤ 400
> líneas authored incluyendo tests. PR 3c-i **apunta al
> tracker** (la rama
> `docs/complete-taxa-frontend-migration-plan`
> **después** de que la reconciliación del PR #146 se
> fusione) de modo que la sub-secuencia del 3c recoge el
> 3a + 3b + reconcile ya fusionados sin un paso extra de
> reconciliación; los hijos posteriores en la sub-secuencia
> apuntan a la rama predecesora inmediata del 3c. El barrel
> de design-system + utilities + paridad CSS final
> aterrizan juntos en PR 3c-iv de modo que la cadena sigue
> en 16 hijos y los puertos de Fase 5 (4a, 4b, 5a, 5b, 5c)
> vean un `globals.css` completamente poblado + un módulo
> de design-system poblado al momento de ejecutarse. Los
> aliases del namespace `--color-*` de Tailwind 4 se
> verifican en cada hijo de modo que la deriva silenciosa
> del namespace no pueda acumularse a través de la
> sub-secuencia.

### Fase 3c-i: Tokens / base / dark mode (PR 3c-i → tracker después de PR #146)

Depende de PR 3a (`tailwindcss@^4` instalado). PR 3b ya está
en el tracker (PR #145 fusionado) con la reconciliación PR
#146 fusionada, así que PR 3c-i **apunta al tracker** para
recoger el estado de 3a + 3b + reconcile. Este es el
**primer hijo de la sub-secuencia del 3c**: aterriza los
design tokens, los resets de body / html, y la cascada de
dark mode. Los hijos 3c subsiguientes (3c-ii, 3c-iii,
3c-iv) añaden a `src/app/globals.css` y heredan la capa de
tokens + base que este PR envía.

- [ ] 3c-i.1 R — `tests/test_tailwind_4_parity.py` (nuevo,
      rebanada de tokens `:root`): lee `web/index.html`
      líneas 14–300 y verifica que cada token `:root { --x }`
      legacy (`--primary`, `--accent`, `--surface`,
      `--elevated`, `--on-surface`, `--on-surface-variant`,
      `--outline`, `--outline-variant`,
      `--surface-container-low`, `--surface-container`,
      `--surface-container-high`, …) está declarado con el
      mismo nombre y un valor no vacío en
      `src/app/globals.css::@theme`. Verifica que cada
      referencia `var(--x)` en el bloque `<style>` legacy
      resuelve a una declaración no vacía en el
      `out/_next/static/chunks/*.css` generado. El test
      DEBE fallar en el tracker fusionado (sin
      `src/app/globals.css` todavía).
      <!-- sdd-owner: implementation -->
- [ ] 3c-i.2 G — `src/app/globals.css` (nuevo, ~250 LoC):
      `@import "tailwindcss";` + bloque `@theme { … }`
      reflejando cada token `:root` legacy (paleta clara);
      aliases del namespace `--color-*` de Tailwind 4 de
      modo que `bg-primary`, `text-on-surface`,
      `border-outline-variant`,
      `bg-surface-container-lowest`, `bg-primary-fixed`,
      `text-on-primary-fixed` resuelvan vía utilidades de
      Tailwind 4; bloque `@layer base { … }` conteniendo
      los resets de body / html / `main > :first-child`
      más la cascada de dark mode
      (`[data-theme="dark"] { … }` con las
      sobreescrituras de tokens de la paleta oscura
      legacy); familia `--realm-*` (bacteria, archaea,
      viruses, animalia, fungi, plantae, chromista)
      declarada en `@theme` de modo que los selectores
      `.tree-row[data-realm="…"]` en 3c-ii puedan
      referenciarlos. Cumple el requisito de orden de
      cascada de `design.md` §"Design tokens".
      <!-- sdd-owner: implementation -->
- [ ] 3c-i.3 T — extiende `tests/test_tailwind_4_parity.py`
      para verificar que los aliases del namespace
      `--color-*` de Tailwind 4 resuelven a los valores
      legacy de los tokens `:root` (atrapa deriva
      silenciosa del namespace); verifica que la familia
      `--realm-*` está declarada con los siete colores de
      realm coincidiendo con los valores legacy;
      verifica que la regla
      `body { overscroll-behavior: none; … }` y el reset
      `main > :first-child { margin-top: 0 !important; }`
      están presentes bajo `@layer base` en orden de
      origen; verifica que la cascada de dark mode cubre
      cada token legacy que el bloque `<style>` legacy
      sobreescribe bajo `[data-theme="dark"]`.
      <!-- sdd-owner: implementation -->
- [ ] 3c-i.4 G — `src/app/globals.css` (extendido, ~80 LoC
      de delta): añade los selectores globales
      focus-visible del bloque `<style>` legacy
      (`.fex-row:focus-visible`, `.fex-chevron:focus-visible`,
      `.fex-splitter:focus-visible`,
      `.tier-header:focus-visible`,
      `.search-icon-btn:focus-visible`,
      `.materialize-btn:focus-visible`,
      `.load-all:focus-visible`,
      `.kebab-trigger:focus-visible`,
      `.kebab-item:focus-visible`,
      `#nav-help:focus-visible`,
      `#collapse-all:focus-visible`) bajo `@layer base` de
      modo que cada elemento interactivo tenga el contrato
      de outline legacy. <!-- sdd-owner: implementation -->
- [ ] 3c-i.5 Refactor — alfabetiza las declaraciones de
      tokens dentro de `@theme` de modo que los hijos 3c
      posteriores puedan localizar tokens por escaneo de
      prefijo; asegura que el bloque de cascada de dark
      mode quede después del bloque `@theme` claro y
      antes de cualquier regla de layer, coincidiendo con
      el orden de cascada legacy.
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c-i.1, 3c-i.3 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` lleva los tokens `:root` esperados + la cascada de dark mode | `git revert <3c-i-sha>` elimina el nuevo `src/app/globals.css`; el estado del tracker revierte a la línea base 3a + 3b + reconcile (sin payload CSS, pero el toolchain + el App Router siguen vivos); 3c-ii / 3c-iii / 3c-iv aún no han aterrizado |
| 3c-i.2, 3c-i.4 | mismo | mismo | mismo |
| 3c-i.5 | mismo | mismo | mismo |

### Fase 3c-ii: Styling de árbol / detalle de taxonomía (PR 3c-ii → rama del PR 3c-i)

Depende de PR 3c-i (tokens + capa base + cascada de dark
mode en vivo, de modo que cada selector en esta rebanada
resuelve las referencias `var(--token)`). Produce la
segunda rebanada de `src/app/globals.css` cubriendo la
superficie de taxonomía legacy: chrome del header, filas
del árbol, panel de detalle, y las variantes del árbol
teñidas por realm.

- [ ] 3c-ii.1 R — extiende `tests/test_tailwind_4_parity.py`
      (rebanada de selectores de taxonomía): lee
      `web/index.html` líneas 96–512 y verifica que cada
      selector legacy
      (`.tier-header`, `.tier-header h2`, `.load-all`,
      `.load-all:hover`, `.load-all:disabled`,
      `#search-results`, `#search-results.open`,
      `.search-hit`, `.search-hit:hover`,
      `.search-hit:last-child`, `.search-hit .tag`,
      `.tag-vernacular`, `.tag-scientific`,
      `.tag-authorship`, `.tree-source-toggle`,
      `.tree-source-toggle .tree-source-btn`,
      `.tree-source-toggle .tree-source-btn:hover:not(.active)`,
      `.tree-source-toggle .tree-source-btn.active`,
      `.rank-badge`, `.scientific-name`,
      `.scientific-name--roman`, `#detail-panel`,
      `#detail-panel.closing`, `.detail-card`,
      `.detail-header`, `.detail-header h2`,
      `.detail-section`, `.detail-section:last-child`,
      `.detail-section h3`, `.detail-section .count`,
      `.overview-section`, `.overview-rank`,
      `.overview-grid`, `.overview-row`,
      `.overview-label`, `.overview-value`,
      `.overview-chain`, `.overview-chain-segment`,
      `.overview-chain-segment:hover`, `.detail-item`,
      `.detail-item:hover`, `.detail-item .lang`,
      `.detail-item .country`,
      `.detail-item .authorship`, `.detail-item .means`,
      `.means-native`, `.means-introduced`,
      `.means-uncertain`, `.means-unknown`,
      `.search-pulse`, `.detail-tabs`, `.detail-tab`,
      `.detail-tab:hover`, `.detail-tab.active`,
      `.search-icon-btn`, `.search-icon-btn:hover`,
      `.materialize-btn`, `.materialize-btn:hover`,
      `.kebab`, `.kebab-trigger`,
      `.tree-row:hover .kebab-trigger`,
      `.tree-row.selected .kebab-trigger`,
      `.tree-row:focus-within .kebab-trigger`,
      `.kebab-trigger:focus-visible`,
      `.kebab-trigger:hover`,
      `.kebab-trigger:focus-visible`, `.kebab-menu`,
      `.kebab-menu.open`, `.kebab-item`,
      `.kebab-item:hover`, `.kebab-item:focus-visible`,
      `.kebab-item-label`, `.materialize-tab-content`,
      `.materialize-tab-loading`, `.materialize-tab-error`,
      `.materialize-modal-section-title`,
      `.materialize-modal-list`,
      `.materialize-modal-list-item`,
      `.materialize-modal-list-item:last-child`,
      `.materialize-modal-marker`,
      `.materialize-modal-marker-exists`,
      `.materialize-modal-marker-new`,
      `.materialize-modal-segment-path`,
      `.materialize-modal-counts`,
      `.materialize-modal-info-banner`,
      `.materialize-modal-actions`,
      `.materialize-modal-btn`,
      `.materialize-modal-btn:disabled`,
      `.materialize-modal-btn-primary`,
      `.materialize-modal-btn-primary:hover:not(:disabled)`,
      `.materialize-modal-btn-secondary`,
      `.materialize-modal-btn-secondary:hover:not(:disabled)`,
      `.materialize-modal-path-actions`,
      `.materialize-modal-path-actions .materialize-modal-btn`)
      está presente en `src/app/globals.css` bajo `@layer
      base` (o `@layer components` si se extrae en
      3c-ii.5) con un bloque de declaración no vacío.
      <!-- sdd-owner: implementation -->
- [ ] 3c-ii.2 G — `src/app/globals.css` (extendido, ~200 LoC
      de delta): añade los selectores de taxonomía legacy
      bajo `@layer base` en orden de fuente, preservando
      cada referencia `var(--token)` y cada llamada a
      `color-mix(in srgb, var(--token) NN%, transparent)`.
      Los selectores teñidos por realm
      (`.tree-row[data-realm="bacteria"] .scientific-name`,
      …, `.tree-row[data-realm="chromista"] .scientific-name`,
      `.tree-row.selected .scientific-name`,
      `.tree-row.focused .scientific-name`) también se
      añaden; dependen de la familia `--realm-*` enviada
      por PR 3c-i.1. <!-- sdd-owner: implementation -->
- [ ] 3c-ii.3 T — extiende `tests/test_tailwind_4_parity.py`
      para verificar que el toggle de tree-source respeta
      `aria-pressed="true"` (comportamiento legacy: solo
      el botón de fuente activo mantiene el styling
      activo); verifica que el menú kebab solo se abre
      bajo `.kebab-menu.open` (sin deriva de nombre de
      clase); verifica que el estado deshabilitado del
      botón del modal de materialize coincide con la regla
      legacy `:disabled`; verifica que el teñido por realm
      usa los valores de la familia `--realm-*` literalmente
      (atrapa cualquier mapeo erróneo de `--realm-*`).
      <!-- sdd-owner: implementation -->
- [ ] 3c-ii.4 G — `src/app/globals.css` (extendido, ~50 LoC
      de delta): añade los estilos del menú kebab, modal
      de materialize y strip de tabs exactamente como el
      bloque legacy los envía, preservando el orden de
      cascada que design.md §"Design tokens" especifica.
      <!-- sdd-owner: implementation -->
- [ ] 3c-ii.5 Refactor — extrae el menú kebab en un
      bloque `@layer components { .kebab { … } .kebab-menu {
      … } }` de modo que el componente React `<Kebab>` en
      PR 5a pueda consumirlo vía un nombre de layer
      estable; mantiene las referencias `var(--token)` sin
      cambios. <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c-ii.1, 3c-ii.3 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` lleva los selectores de taxonomía esperados | `git revert <3c-ii-sha>` revierte los selectores de taxonomía añadidos en `src/app/globals.css`; 3c-i tokens + base + dark mode se quedan; 3c-iii / 3c-iv aún no han aterrizado |
| 3c-ii.2, 3c-ii.4 | mismo | mismo | mismo |
| 3c-ii.5 | mismo | mismo | mismo |

### Fase 3c-iii: Styling de Search / Folder / global Browser (PR 3c-iii → rama del PR 3c-ii)

Depende de PR 3c-ii (selectores de taxonomía en vivo).
Produce la tercera rebanada de `src/app/globals.css`
cubriendo la rejilla de motores de búsqueda legacy, el
toast de materialize, el chrome del file explorer, la fila
de input + toggle de búsqueda del árbol, el scroller de
CSV, y el visor de árbol JSON. Esta es la **rebanada de
CSS más grande** del bloque `<style>` inline legacy (el
file explorer + viewer toman ~500 líneas del CSS legacy),
así que vive en su propio hijo para mantenerse ≤ 400 LoC
authored.

- [ ] 3c-iii.1 R — extiende `tests/test_tailwind_4_parity.py`
      (rebanada de selectores de Browser): lee
      `web/index.html` líneas 514–1800 y verifica que cada
      selector legacy (`.toast`, `.toast-error`,
      `.search-engines-grid`, `.search-category-header`,
      `.search-category-header:first-child`,
      `.search-category-header .material-symbols-outlined`,
      `.search-engine-btn`, `.search-engine-btn:hover`,
      `.search-engine-btn:focus-visible`,
      `.search-engine-btn:active`,
      `.search-engine-btn .material-symbols-outlined`,
      `.search-engine-btn:hover .material-symbols-outlined`,
      `.search-engine-btn-label`, `.fex-meta-strip`,
      `.fex-meta-strip > .fex-meta-spacer`,
      `.fex-tab-strip`, `.fex-tab-strip button`,
      `.fex-tab-strip button.active`,
      `.fex-snippet-frame`, `.fex-snippet-title`,
      `.fex-snippet-dots`, `.fex-snippet-dots span`,
      `.fex-snippet-dots .dot-r`,
      `.fex-snippet-dots .dot-y`,
      `.fex-snippet-dots .dot-g`,
      `.fex-snippet-body`, `.fex-snippet-actions`,
      `.fex-snippet-btn`, `.fex-snippet-btn:hover`,
      `.fex-snippet-btn:disabled`, `.fex-shell`,
      `.fex-tree-pane`, `.fex-viewer-pane`,
      `.fex-splitter`, `.fex-splitter::after`,
      `.fex-splitter:hover`, `.fex-splitter.dragging`,
      `.fex-tree-header`, `.fex-tree-header h2`,
      `.fex-row`, `.fex-row:hover`,
      `.fex-row .fex-chevron`, `.fex-row .fex-icon`,
      `.fex-row.file.selected`,
      `.fex-row.file.selected .fex-icon`,
      `.fex-row.file.selected .fex-meta`,
      `.fex-row.file.selected .fex-label`,
      `.fex-row.folder.selected`,
      `.fex-row.folder[data-realm] .fex-icon`,
      `.fex-row.folder[data-realm] .fex-label`,
      `.fex-row.folder[data-realm="bacteria"] .fex-icon`,
      …, `.fex-row.folder[data-realm="chromista"] .fex-icon`,
      `.fex-row .fex-label`, `.fex-row .fex-meta`,
      `.fex-children`, `.fex-banner`,
      `.fex-empty-state`,
      `.fex-empty-state .fex-empty-state-icon`,
      `.fex-tree-header-search`, `.fex-search-row`,
      `.fex-search-row .fex-search-icon`,
      `.fex-search-input`, `.fex-search-input:focus`,
      `.fex-search-clear`,
      `.fex-search-clear .material-symbols-outlined`,
      `.fex-search-clear:hover`,
      `.fex-search-input:not(:placeholder-shown) ~ .fex-search-clear`,
      `.fex-search-toggles`, `.fex-search-mode-btn`,
      `.fex-search-hide-empty-btn`,
      `.fex-search-mode-btn[aria-pressed="true"]`,
      `.fex-search-hide-empty-btn[aria-pressed="true"]`,
      `.fex-search-mode-btn .material-symbols-outlined`,
      `.fex-search-hide-empty-btn .material-symbols-outlined`,
      `.fex-row.search-match`, `.fex-search-empty`,
      `.fex-csv-scroller`, `.fex-csv-table`,
      `.fex-csv-table thead th`,
      `.fex-csv-table tbody td`,
      `.fex-csv-table tbody tr:nth-child(even) td`,
      `.fex-csv-table tbody tr:hover td`,
      `.fex-json-tree`, `.fex-json-children`,
      `.fex-json-node`, `.fex-json-summary`,
      `.fex-json-summary:hover`,
      `.fex-json-summary:focus-visible`,
      `.fex-json-caret`,
      `.fex-json-node.open > .fex-json-summary > .fex-json-caret`,
      `.fex-json-key`, `.fex-tree-leaf`,
      `.fex-tree-leaf.type-string`,
      `.fex-tree-leaf.type-number`,
      `.fex-tree-leaf.type-boolean`,
      `.fex-tree-leaf.type-null`,
      `.fex-tree-leaf.type-meta`,
      `.fex-tree-truncated`,
      `.fex-tree-truncated .material-symbols-outlined`)
      está presente en `src/app/globals.css` con un
      bloque de declaración no vacío.
      <!-- sdd-owner: implementation -->
- [ ] 3c-iii.2 G — `src/app/globals.css` (extendido, ~250
      LoC de delta): añade la rejilla de motores de
      búsqueda legacy, el toast de materialize, el chrome
      del file explorer, la fila de input + toggle de
      búsqueda del árbol, el scroller de CSV, y los
      estilos del visor de árbol JSON bajo `@layer base`
      (o `@layer components` para las reglas específicas
      del file explorer). Preserva cada llamada a
      `color-mix(in srgb, var(--token) NN%, transparent)`
      y cada referencia `var(--realm-*)`.
      <!-- sdd-owner: implementation -->
- [ ] 3c-iii.3 T — extiende `tests/test_tailwind_4_parity.py`
      para verificar que los headers de categoría de la
      rejilla de motores de búsqueda mantienen el styling
      `:first-child` (comportamiento legacy); verifica
      que los estados hover/dragging del splitter del file
      explorer coinciden con las reglas legacy; verifica
      que los pills de tipo de leaf del árbol JSON
      (`.fex-tree-leaf.type-{string,number,boolean,null,meta}`)
      referencian la familia `--realm-*` correctamente;
      verifica que la regla de visibilidad
      `:not(:placeholder-shown) ~ .fex-search-clear` del
      input de búsqueda se preserva.
      <!-- sdd-owner: implementation -->
- [ ] 3c-iii.4 G — `src/app/globals.css` (extendido, ~80
      LoC de delta): añade el banner de truncamiento
      (`.fex-tree-truncated`), el aviso de archivo grande
      (`.fex-image-advisory`, añadido en 3c-iv pero los
      selectores helper van aquí), el chrome de estado
      vacío (`.fex-search-empty`), y la toolbar de
      acciones de snippet (`.fex-snippet-actions`,
      `.fex-snippet-btn`, `.fex-snippet-btn:hover`,
      `.fex-snippet-btn:disabled`).
      <!-- sdd-owner: implementation -->
- [ ] 3c-iii.5 Refactor — extrae el chrome del file
      explorer en un bloque `@layer components { .fex-* {
      … } }` de modo que el componente React
      `<FileExplorer>` en PR 5b pueda consumirlo vía un
      nombre de layer estable; mantiene los selectores
      `.fex-row.folder[data-realm="…"]` teñidos por realm
      en el mismo layer de modo que las referencias
      `--realm-*` permanezcan co-localizadas con los
      selectores coincidentes
      `.tree-row[data-realm="…"]` de PR 3c-ii.
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c-iii.1, 3c-iii.3 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` lleva los selectores de Browser esperados | `git revert <3c-iii-sha>` revierte los selectores de Browser añadidos; 3c-i + 3c-ii se quedan; 3c-iv aún no ha aterrizado |
| 3c-iii.2, 3c-iii.4 | mismo | mismo | mismo |
| 3c-iii.5 | mismo | mismo | mismo |

### Fase 3c-iv-barrel: Barrel del design-system + primitivas Icon/Button + purity test (PR 3c-iv-barrel → predecesor de reparación de paridad estructural DOM↔CSS de PR 5.6, posición 6/22)

Depende del **predecesor de reparación de paridad estructural DOM↔CSS de PR 5.6** (la expansión `@tailwindcss/postcss` + los ganchos estructurales emitidos por React están en su lugar; el módulo design-system es el siguiente módulo a poblar según el addendum del replan five-slice de 3c-iv). Se basa en `feat/complete-taxa-frontend-migration-05-6-3c-iv-predecessor` (el commit base post-PR-5.6). Este es el **primer hijo de la sub-secuencia 3c-iv**: envía el barrel del design-system + las primitivas `<Icon>` + `<Button>` + el purity test del design-system. Los hijos subsiguientes (3c-iv-keyframes / 3c-iv-viewer / 3c-iv-settings / 3c-iv-colors) extienden `src/app/globals.css` y heredan el módulo design-system que este PR envía.

- [ ] 3c-iv-barrel.1 R — `tests/test_design_system_purity.py` (nuevo, parametrizado): grepea cada archivo bajo `src/modules/design-system/{infrastructure,presentation}/` por patrones de literales hexadecimales (`#[0-9a-fA-F]{6}` / `#[0-9a-fA-F]{3}\b`) y verifica que los únicos archivos que contienen literales hexadecimales están dentro del módulo design-system (el módulo design-system posee la tabla de tokens). Verifica que **cada otro módulo bajo `src/modules/{taxonomy,research,browser-state,app-shell}/` está libre de literales hexadecimales** (sin `#1d7ea9` / `#5ebd9b` / etc. filtrados fuera del módulo design-system). El test DEBE fallar en la base post-PR-5.6 (no existe `src/modules/design-system/` todavía). <!-- sdd-owner: implementation -->
- [ ] 3c-iv-barrel.2 G — `src/modules/design-system/infrastructure/index.ts` (nuevo, ~20 LoC): el barrel exporta el `<Icon>` (envoltorio de glyphs Material Symbols Outlined, nombres congelados: `search`, `folder_open`, `folder`, `chevron_right`, `expand_more`, `close`, `settings`, `help`, `science`, `science_off`, `download`) más la primitiva de layout `<Button>` + los tokens de tema tipados (`--primary`, `--accent`, `--surface`, `--elevated`, `--on-surface`, `--on-surface-variant`, `--outline`, `--outline-variant`, `--surface-container-low`, `--surface-container`, `--surface-container-high`, `--surface-container-highest`, `--primary-fixed`, `--on-primary-fixed`, `--realm-bacteria`, `--realm-archaea`, `--realm-viruses`, `--realm-animalia`, `--realm-fungi`, `--realm-plantae`, `--realm-chromista`, `--realm-other`). <!-- sdd-owner: implementation -->
- [ ] 3c-iv-barrel.3 G — `src/modules/design-system/presentation/Icon.tsx` (nuevo, ~20 LoC): el componente `<Icon>` renderiza `<span class="material-symbols-outlined">` con el nombre de glyph congelado; el nombre de glyph se reduce tipológicamente contra la unión congelada de nombres; el componente acepta una prop `className` para consumidores de layout. <!-- sdd-owner: implementation -->
- [ ] 3c-iv-barrel.4 G — `src/modules/design-system/presentation/Button.tsx` (nuevo, ~20 LoC): `<Button>` es un envoltorio delgado alrededor de `<button>` con la clase `.fex-snippet-btn` para paridad con el visual del botón del file explorer legacy; el componente acepta props `onClick` + `disabled` + `children`. <!-- sdd-owner: implementation -->
- [ ] 3c-iv-barrel.5 T — triangulación de `tests/test_design_system_purity.py`: verifica que cada nombre de glyph Material Symbols Outlined congelado (`search`, `folder_open`, `folder`, `chevron_right`, `expand_more`, `close`, `settings`, `help`, `science`, `science_off`, `download`) se exporta desde el barrel del módulo design-system; verifica que el componente `<Button>` acepta la prop `disabled` y renderiza la clase `.fex-snippet-btn`; verifica que el componente `<Icon>` reduce tipológicamente la prop de glyph contra la unión congelada. <!-- sdd-owner: implementation -->
- [ ] 3c-iv-barrel.6 Refactor — ordena alfabéticamente los tokens de tema tipados en el barrel `infrastructure/index.ts` del módulo design-system para que los hijos subsiguientes de 3c-iv puedan localizar tokens por escaneo de prefijo; extrae la tabla de literales hexadecimales a `infrastructure/tokens.ts` para que los consumidores importen el token tipado (no el literal). <!-- sdd-owner: implementation -->

**Evidencia por tarea (3c-iv-barrel)**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c-iv-barrel.1, 3c-iv-barrel.5 | `.venv/bin/python3 -m pytest tests/test_design_system_purity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.js` lleva el barrel del módulo design-system | `git revert <3c-iv-barrel-sha>` elimina el módulo design-system; estado base post-PR-5.6 restaurado; 3c-i / 3c-ii / 3c-iii / 5.5 / 5.6 se quedan |
| 3c-iv-barrel.2, 3c-iv-barrel.3, 3c-iv-barrel.4 | mismo | `npx tsc --noEmit` contra `src/modules/design-system/` exit 0 | mismo |
| 3c-iv-barrel.6 | mismo | mismo | mismo |

### Fase 3c-iv-keyframes: Cinco `@keyframes` legacy + paridad de `.animate-spin` (PR 3c-iv-keyframes → rama del PR 3c-iv-barrel, posición 7/22)

Depende de PR 3c-iv-barrel (el módulo design-system + las primitivas Icon/Button están en su lugar para que un contrato de paridad `@keyframes` funcional cabalgue sobre la superficie design-system viva). Se basa en `feat/complete-taxa-frontend-migration-06-3c-iv-barrel`. Produce la siguiente rebanada de `src/app/globals.css` cubriendo las cinco reglas `@keyframes` legacy + la clase de utilidad `.animate-spin`.

- [ ] 3c-iv-keyframes.1 R — extiende `tests/test_tailwind_4_parity.py` (rebanada `@keyframes`): lee `web/index.html` líneas 273, 500, 834, 874 (las definiciones de reglas `@keyframes` legacy) y verifica que cada regla `@keyframes` legacy (`detail-card-enter`, `detail-card-leave`, `search-pulse-anim`, `materialize-spin`, `toast-slide-in`) está presente en `src/app/globals.css`; verifica que la regla de utilidad `.animate-spin { animation: materialize-spin 1s linear infinite; }` está presente. El test DEBE fallar en la base post-PR-3c-iv-barrel (todavía no hay reglas `@keyframes`). <!-- sdd-owner: implementation -->
- [ ] 3c-iv-keyframes.2 G — `src/app/globals.css` (extendido, ~50 LoC de delta): añade las cinco reglas `@keyframes` (`detail-card-enter`, `detail-card-leave`, `search-pulse-anim`, `materialize-spin`, `toast-slide-in`) bajo `@layer base` en orden de cascada; añade la clase de utilidad `.animate-spin`. La regla `@keyframes materialize-spin` es la fuente canónica para la animación `materialize-spin` que `.animate-spin` consume. <!-- sdd-owner: implementation -->
- [ ] 3c-iv-keyframes.3 T — extiende `tests/test_tailwind_4_parity.py` para verificar que cada regla `@keyframes` lleva los keyframes de transform / opacity verbatim (sin drift de keyframes entre el bloque legacy y `src/app/globals.css`); verifica que la utilidad `.animate-spin` se vincula a `materialize-spin` específicamente (no a un keyframe `spin` genérico — el bloque legacy usa `materialize-spin` como nombre de animación); verifica que la función de temporización `1s linear infinite` se preserva. <!-- sdd-owner: implementation -->
- [ ] 3c-iv-keyframes.4 Refactor — ordena alfabéticamente las declaraciones de reglas `@keyframes` para que los hijos subsiguientes de 3c-iv puedan localizar los keyframes por escaneo de prefijo; asegura que la utilidad `.animate-spin` se sitúa después de la declaración `@keyframes materialize-spin` (requisito de orden-fuente CSS para la vinculación de animación). <!-- sdd-owner: implementation -->

**Evidencia por tarea (3c-iv-keyframes)**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c-iv-keyframes.1, 3c-iv-keyframes.3 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` lleva cada regla `@keyframes` + la utilidad `.animate-spin` | `git revert <3c-iv-keyframes-sha>` revierte las reglas `@keyframes` añadidas; 3c-iv-barrel se queda; viewer / settings / colors aún no han aterrizado |
| 3c-iv-keyframes.2 | mismo | mismo | mismo |
| 3c-iv-keyframes.4 | mismo | mismo | mismo |

### Fase 3c-iv-viewer: Paridad CSS del visor de imagen / video (PR 3c-iv-viewer → rama del PR 3c-iv-keyframes, posición 8/22)

Depende de PR 3c-iv-keyframes (las reglas `@keyframes` + `.animate-spin` están vivas para que las referencias `animation:` de los frames del visor resuelvan). Se basa en `feat/complete-taxa-frontend-migration-07-3c-iv-keyframes`. Produce la siguiente rebanada de `src/app/globals.css` cubriendo los frames del visor de imagen + video.

- [ ] 3c-iv-viewer.1 R — extiende `tests/test_tailwind_4_parity.py` (rebanada del visor): lee `web/index.html` líneas 1750–1900 (los selectores legacy del visor de imagen / video) y verifica que cada selector legacy del visor (`.fex-image-frame`, `.fex-image`, `.fex-image-advisory`, `.fex-video-frame`, `.fex-video-el`) está presente en `src/app/globals.css` con un bloque de declaración no vacío. El test DEBE fallar en la base post-PR-3c-iv-keyframes (todavía no hay selectores del visor). <!-- sdd-owner: implementation -->
- [ ] 3c-iv-viewer.2 G — `src/app/globals.css` (extendido, ~30 LoC de delta): añade los frames legacy del visor de imagen (`.fex-image-frame` + `.fex-image` + `.fex-image-advisory`) y los frames del visor de video (`.fex-video-frame` + `.fex-video-el`) bajo `@layer base` en orden de cascada. Los frames reusan los tokens `--surface-container-low`, `--outline-variant`, `--on-surface-variant` de PR 3c-i. <!-- sdd-owner: implementation -->
- [ ] 3c-iv-viewer.3 T — extiende `tests/test_tailwind_4_parity.py` para verificar que `.fex-image-frame` y `.fex-video-frame` declaran declaraciones de layout no vacías (`display: flex` / `flex-direction: column` / `padding` / `overflow`); verifica que `.fex-image-advisory` lleva una declaración de estado visible (el advisory legacy tiene un fondo tintado que señala riesgo de archivo grande). <!-- sdd-owner: implementation -->
- [ ] 3c-iv-viewer.4 Refactor — extrae los frames del visor a un bloque `@layer components { .fex-image-frame, .fex-video-frame { … } }` para que el componente React `<FileViewer>` en PR 5b pueda consumirlos vía un nombre de capa estable. <!-- sdd-owner: implementation -->

**Evidencia por tarea (3c-iv-viewer)**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c-iv-viewer.1, 3c-iv-viewer.3 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` lleva los selectores esperados del visor | `git revert <3c-iv-viewer-sha>` revierte los selectores del visor añadidos; 3c-iv-barrel + 3c-iv-keyframes se quedan; settings / colors aún no han aterrizado |
| 3c-iv-viewer.2, 3c-iv-viewer.4 | mismo | mismo | mismo |

### Fase 3c-iv-settings: Paridad CSS de la vista Settings (PR 3c-iv-settings → rama del PR 3c-iv-viewer, posición 9/22)

Depende de PR 3c-iv-viewer (los frames del visor están vivos para que la vista Settings reuse la misma superficie de tokens). Se basa en `feat/complete-taxa-frontend-migration-08-3c-iv-viewer`. Produce la siguiente rebanada de `src/app/globals.css` cubriendo la vista Settings.

- [ ] 3c-iv-settings.1 R — extiende `tests/test_tailwind_4_parity.py` (rebanada Settings): lee `web/index.html` líneas 1900–1972 (los selectores legacy de la vista Settings) y verifica que cada selector legacy de Settings (`.settings-shell`, `.settings-header`, `.settings-list`, `.settings-row`, `.settings-row-text`, `.settings-row-title`, `.settings-row-description`, `.settings-row-control`, `.settings-theme-toggle`, `.settings-theme-btn`, `.settings-theme-btn:hover`, `.settings-theme-btn .material-symbols-outlined`, `.settings-theme-btn-active`, `.settings-theme-btn-active:hover`, `.settings-action-btn`, `.settings-action-btn:hover`, `.settings-action-btn .material-symbols-outlined`, `.settings-link-btn`, `.settings-link-btn:hover`, `.settings-link-btn .material-symbols-outlined`) está presente en `src/app/globals.css` con un bloque de declaración no vacío. El test DEBE fallar en la base post-PR-3c-iv-viewer (todavía no hay selectores de Settings). <!-- sdd-owner: implementation -->
- [ ] 3c-iv-settings.2 G — `src/app/globals.css` (extendido, ~30 LoC de delta): añade los selectores legacy de la vista Settings (`.settings-shell` + `.settings-header` + `.settings-list` + `.settings-row` + `.settings-row-text` + `.settings-row-title` + `.settings-row-description` + `.settings-row-control` + `.settings-theme-toggle` + `.settings-theme-btn` + variantes `:hover` + envoltorios de glyph `.material-symbols-outlined` + `.settings-theme-btn-active` + `.settings-action-btn` + variantes `:hover` + `.settings-link-btn` + variantes `:hover`) bajo `@layer base` en orden de cascada. La vista Settings reusa los tokens `--surface-container-low`, `--outline-variant`, `--primary`, `--on-surface`, `--on-surface-variant` de PR 3c-i. <!-- sdd-owner: implementation -->
- [ ] 3c-iv-settings.3 T — extiende `tests/test_tailwind_4_parity.py` para verificar que `.settings-row` declara declaraciones de layout no vacías (`display: flex` / `flex-direction: row` / `align-items: center` / `padding` / `border-bottom`); verifica que `.settings-theme-btn-active` lleva una declaración de estado visible (el botón de tema activo tiene un fondo tintado); verifica que `.settings-link-btn:hover` lleva una declaración de estado visible (el estado hover del botón de enlace). <!-- sdd-owner: implementation -->
- [ ] 3c-iv-settings.4 Refactor — ordena alfabéticamente las declaraciones de selectores de Settings para que el hijo colors pueda localizarlas por escaneo de prefijo; asegura que la declaración `.settings-theme-btn-active` se sitúa antes de la declaración `.settings-action-btn` en orden de fuente. <!-- sdd-owner: implementation -->

**Evidencia por tarea (3c-iv-settings)**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c-iv-settings.1, 3c-iv-settings.3 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` lleva los selectores esperados de Settings | `git revert <3c-iv-settings-sha>` revierte los selectores de Settings añadidos; 3c-iv-barrel + 3c-iv-keyframes + 3c-iv-viewer se quedan; colors aún no ha aterrizado |
| 3c-iv-settings.2, 3c-iv-settings.4 | mismo | mismo | mismo |

### Fase 3c-iv-colors: Aliases del namespace `--color-*` de Tailwind + paridad de utility (PR 3c-iv-colors → rama del PR 3c-iv-settings, posición 10/22)

Depende de PR 3c-iv-settings (los selectores de Settings están vivos, compartiendo la superficie consumidora `--color-*`). Se basa en `feat/complete-taxa-frontend-migration-09-3c-iv-settings`. Produce la rebanada final de `src/app/globals.css` cargando los aliases del namespace `--color-*` de Tailwind + el contrato de paridad de clases de utilidad legacy.

- [ ] 3c-iv-colors.1 R — extiende `tests/test_tailwind_4_parity.py` (rebanada `--color-*` + utility): lee `web/index.html` líneas 1975–2109 (el marcado legacy `<body>` / `<header>`) y `web/dist/tailwind.css` (la salida compilada de Tailwind 3.4); verifica que cada alias del namespace `--color-*` de Tailwind (`--color-primary`, `--color-on-surface`, `--color-outline-variant`, `--color-surface-container-lowest`, `--color-surface-container`, `--color-surface-container-high`, `--color-primary-fixed`, `--color-on-primary-fixed`, `--color-surface`, `--color-outline`, `--color-on-surface-variant`, `--color-elevated`) está declarado en `src/app/globals.css::@theme`; verifica que cada clase de utilidad legacy (`bg-primary`, `text-on-surface`, `border-outline-variant`, `bg-surface-container-lowest`, `bg-primary-fixed`, `text-on-primary-fixed`, `bg-surface`, `text-outline`, `text-on-surface-variant`, `hover:text-on-surface`, `focus:border-primary`, `focus:ring-primary/20`, `transition-all`, `transition-colors`, `font-h1`, `text-h1`, `font-body-md`, `text-body-sm`, `fixed`, `top-0`, `w-full`, `z-50`, `bg-surface/95`, `backdrop-blur-md`, `shadow-[0_1px_8px_rgba(0,0,0,0.04)]`, `h-16`, `px-row-padding-x`, `flex`, `items-center`, `justify-between`, `gap-gutter`, `min-w-0`, `whitespace-nowrap`, `relative`, `w-64`, `lg:w-96`, `absolute`, `left-3`, `top-1/2`, `-translate-y-1/2`, `text-[18px]`, `py-2`, `pl-10`, `pr-4`, `rounded-xl`, `focus:outline-none`, `focus:ring-2`, `shrink-0`, `aria-pressed`, `role="group"`) resuelve a una declaración CSS no vacía en `out/_next/static/chunks/*.css`. El test DEBE fallar en la base post-PR-3c-iv-settings (todavía no hay aliases `--color-*`). <!-- sdd-owner: implementation -->
- [ ] 3c-iv-colors.2 G — `src/app/globals.css` (extendido, ~60 LoC de delta): extiende el bloque `@theme` con cada alias del namespace `--color-*` de Tailwind mapeado a los valores legacy de tokens `:root` (`--color-primary: var(--primary)`, `--color-on-surface: var(--on-surface)`, `--color-outline-variant: var(--outline-variant)`, etc.); los aliases se sitúan junto a los tokens legacy `:root` / `[data-theme="dark"]` existentes para que cada utilidad de Tailwind 4 (`bg-primary`, `text-on-surface`, `border-outline-variant`, etc.) resuelva vía la expansión `@tailwindcss/postcss` que PR 5.5 registra. <!-- sdd-owner: implementation -->
- [ ] 3c-iv-colors.3 T — extiende `tests/test_tailwind_4_parity.py` para verificar que cada alias del namespace `--color-*` resuelve al valor legacy del token `:root` (atrapa drift silencioso del namespace); verifica que cada clase de utilidad referenciada por el marcado legacy `<body>` / `<header>` de `web/index.html` (líneas 1975–2109) se emite en el bundle CSS compilado; verifica que la superficie de clases de utilidad es byte-estable entre ejecuciones consecutivas de `next build` (sin filtración de subconjunto). <!-- sdd-owner: implementation -->
- [ ] 3c-iv-colors.4 Refactor — ordena alfabéticamente los aliases del namespace `--color-*` dentro de `@theme` para que el purity test del design-system pueda localizarlos por escaneo de prefijo; asegura que los aliases se sitúan después de las declaraciones de tokens `:root` / `[data-theme="dark"]` y antes de cualquier regla `@layer base`, coincidiendo con el orden de cascada legacy. <!-- sdd-owner: implementation -->

**Evidencia por tarea (3c-iv-colors)**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 3c-iv-colors.1, 3c-iv-colors.3 | `.venv/bin/python3 -m pytest tests/test_tailwind_4_parity.py -v` | `npx next build` exit 0; `out/_next/static/chunks/*.css` lleva cada alias `--color-*` + cada clase de utilidad | `git revert <3c-iv-colors-sha>` revierte los aliases `--color-*` añadidos; 3c-iv-barrel + 3c-iv-keyframes + 3c-iv-viewer + 3c-iv-settings se quedan; 3d / 4a / 5c aguas abajo aún no han aterrizado |
| 3c-iv-colors.2, 3c-iv-colors.4 | mismo | mismo | mismo |

## Fase 3d: Reescritura del Makefile + repoint de `WEB_DIR` + lector AC-21 (PR 3d → rama del PR 3c-iv-colors, posición 11/22)

Depende de PR 3b (`next build` produce `out/index.html`) y
PR 3c-iv-colors (los tokens de Tailwind 4 + aliases del
namespace `--color-*` + `@layer base` +
`@layer components` fluyen a través de `next build`; el test
de paridad final de Tailwind 4 está en disco — **según el replan
five-slice de 3c-iv, los consumidores CSS finales dependen de
colors, NO del antiguo PR 3c-iv único**). Fusiona la
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
| 3d.1–3d.3 | `.venv/bin/python3 -m pytest tests/test_make_api_build.py -v tests/test_static_mount.py -v` | `make api` exit 0 en Node ≥ 20.9.0; `lsof -i :8765` muestra solo uvicorn | `git revert <3d-sha>` restaura `Makefile::api` (cadena `make css` legacy), restaura `api/server.py:54` al valor legacy, elimina `src/data/search-engines.js`, revierte el parche `open()` de `tests/test_smoke.py`; Fases 3a/3b/3c-i/3c-ii/3c-iii/3c-iv intactas |
| 3d.4 | mismo | mismo | mismo |
| 3d.5 | mismo | mismo | mismo |
| 3d.6–3d.7 | `.venv/bin/python3 -m pytest tests/test_smoke.py::test_search_engine_contract -v` | `make api` arranca uvicorn; `curl http://127.0.0.1:8765/index.html` devuelve 200 con el contenido de `out/index.html` | mismo |
| 3d.8–3d.9 | mismo que 3d.1–3d.3 | mismo | mismo |
| 3d.10 | n/a (refactor) | mismo | mismo |

## Fase 4a: Typed store + 4 sitios de lectura + 4 sitios de escritura (PR 4a → rama del PR 3c-iv-barrel, posición 12/22)

Rebana las tareas 4.1 + 4.2 del predecesor
(`src/modules/browser-state/{store,keys,defaults}.ts` + 4
sitios de lectura + 4 sitios de escritura dentro de
`useEffect`). Depende de PR 3c-iv-barrel (barrel de design-system
+ primitivas Icon/Button cargadas; **según el replan five-slice
de 3c-iv, los consumidores de design-system dependen de barrel,
NO del antiguo PR 3c-iv único**); produce
`src/modules/browser-state/**` typed store con cuatro sitios
de lectura + cuatro de escritura.

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
`<AppShell>`), y PR 3c-iv-barrel (animations / utilities + barrel
de design-system + Icon/Button cargados para `next build`;
PR 3c-i envía los tokens `@theme` que el barrel referencia;
**según el replan five-slice de 3c-iv, los consumidores
de design-system dependen de barrel, NO del antiguo PR
3c-iv único**).

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

## Fase 5a: Port del módulo taxonomy (PR 5a → rama del PR 4b, posición 14/22)

Rebana las tareas 5.1 + 5.2 + 5.3 del predecesor
(`src/modules/taxonomy/{domain,application,infrastructure,
presentation}` + port de `web/{tree,detail,breadcrumb}.js`).
Depende de PR 4b (lectura de estado segura de hidratación
para `tree-source`) y de PR 3c-ii (los selectores de
taxonomía están en su lugar — los selectores de taxonomía
se montan sobre el CSS de PR 3c-ii).

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
      los selectores de taxonomía de PR 3c-ii
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

## Fase 5b: Port del módulo research + pin CDN (PR 5b → rama del PR 5a, posición 15/22)

Rebana las tareas 5.4 + 5.5 + 5.6 del predecesor
(`src/modules/research/{domain,application,infrastructure,
presentation}` + port de `web/{file_explorer,file_viewer,format,
keymap}.js` + pin CDN). Depende de PR 5a (flujos de lectura
de estado de taxonomía compartidos con research y el andamio
del strip de pestañas de `DetailPanel` en el que se enchufa
la acción `Search online`), de PR 3d
(`src/data/search-engines.js` para el export nombrado
`Engine`), y de PR 3c-iii (los selectores de Search /
Folder / global Browser están en su lugar — los selectores
de research se montan sobre el CSS de PR 3c-iii). Este es el
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
      selectores de Search / Folder / global Browser de
      PR 3c-iii
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

## Fase 5c: Selectores E2E + contrato `data-*` + borrar legacy (PR 5c → rama del PR 5b, posición 16/22)

Rebana las tareas 5.7 + 5.8 + 5.9 del predecesor
(Playwright + actualizaciones de selectores e2e +
preservación del contrato `data-*` + borrar
`web/*.{html,js,css}` + `tailwind.config.js`). Depende de
PR 5b (todos los componentes UI en vivo) y de PR 3c-iv (el
test de paridad final de Tailwind 4 está en disco; el CSS
inline legacy de 1.963 líneas ha sido migrado a
`src/app/globals.css` de extremo a extremo y está listo
para retirarse).

**Re-rebanado de PR 5c (esta entrada, supersede la enumeración
in-line 5c.1–5c.7 para el próximo worktree de código)**. Los siete
sub-PRs TDD de abajo colapsan en una única rebanada **`5c.1b`
(diferida)** para que la fundación tipada pueda aterrizar primero.
El registro de evidencia vive en `apply-progress-es.md` §registro
de cambios entrada "2026-09-07 — PR 5c.1a: fundación tipada de
browser-state aterrizada"; la adenda vinculante vive en
`design-es.md`; **G4 permanece bloqueada**.

- [x] **5c.1a (aterrizada)** — fundación tipada:
      `versionBannerDismissed: "taxa.settings.versionBannerDismissed"`
      (booleano, default `false`); `TreeSource` se extiende a
      `col | worms | freshwater`; contrato de llamadas de
      almacenamiento **5 + 5** restaurado (1 `getItem(` inline + 1
      `setItem(` inline para la nueva llave, todos en
      `infrastructure/store.ts`); 27/27 tests pasan bajo TDD
      estricto.
- [x] **5c.1b-A (aterrizada)** — UI de fuente de árbol + ids de nav/breadcrumb
      + cableado de contexto de store único (page.tsx se suscribe vía
      `useBrowserStateStore`); sin cambios en `domain/keys.ts` /
      `infrastructure/store.ts`.
- [x] **5c.1b-B (aterrizada)** — render de VersionBanner + trabajo de cierre/
      sticky de panel + pulido de hidratación de fuente de árbol; sin
      cambios en `domain/keys.ts` / `infrastructure/store.ts`.
- [x] **5c.2-A (aterrizada)** — alineación del contrato de motores
      de búsqueda: `api/server.py::_SEARCH_ENGINES` y
      `src/data/search-engines.js::SEARCH_ENGINES` ahora albergan
      exactamente los 14 motores canónicos (google, imagen,
      documentos, pdf, wikipedia, bhl, researchgate, plos,
      academia, scielo, scholar, youtube, zootaxa, scribd) en los
      mismos campos ordenados; las tres entradas retiradas de
      `general` social/share (`threads_acipenser`,
      `facebook_acipenser_baerii`, `threads_shared_post`) se
      eliminan de ambos espejos. `tests/test_smoke.py::test_search_engine_contract`
      ahora fija el conteo exacto (14) y la lista ordenada de
      llaves además de la verificación de paridad key/label/with_authorship
      existente.
- [x] **5c.2-B.1b-i (aterrizada)** — CLI de captura + runner Chromium para exportación React: `tools/react-e2e-harness/scripts/run.mjs` requiere `--origin` + `--output-root`, rechaza `file://` / no-http(s) / rutas en el origen / flags faltantes / colisiones de salida, inyecta dinámicamente el `runFn` (default `./chromium-driver.mjs` que importa dinámicamente `playwright` desde el `node_modules/` local), escribe un `evidence.json` atómico con timestamp SOLO tras una captura exitosa (fail-closed); `chromium-driver.mjs` lanza Chromium sin cabeza contra el origen explícito, valida los contratos de datos de React (`data-harness-root`, `data-harness-surface`, `data-harness-taxon-id` no nulo, `[data-explorer="ready"]`, ambos slots `[data-pane]`, `input[data-search-input]`, ≥1 `[data-file-path]`), captura trazas concisas `pageerror`/`console.error`/navegación/aserciones, cierra el navegador de forma fiable vía `finally`; `package.json` añade `scripts.capture = "node scripts/run.mjs"`; `tools/react-e2e-harness/README.md` documenta el flujo del origen provisto por el caller + lista de diferimientos. Sin servidor fixture de API, sin servidor HTTP de exportación, sin target de Makefile, sin tests herméticos del driver, sin cambios de fuente/API de producción, sin modernización de selectores E2E legacy, sin borrado `web/*.{html,js,css}` + `tailwind.config.js`, sin agregación G4. **Sin superficie de test** en esta sub-rebanada; la verificación negativa de contrato de fuente pre-implementación corrió RED (CLI + dir scripts ausentes), el `node --check` post-implementación + el rechazo de CLI de `--origin` faltante / `file://` / ruta en origen corrió GREEN. **G4 / G3 Tier-2 / cutover permanecen bloqueadas; G4 NO se voltea con el aterrizaje de la CLI de captura.**
- [x] **5c.2-B.1b-ii-a (aterrizada)** — API fixture Node hermética en-proceso para el arnés aislado React `FileExplorer`: `tools/react-e2e-harness/scripts/fixture-server.mjs` es Node puro built-ins (`node:http` + `node:buffer`); cero deps npm; puerto elegido por el caller (CLI `--port N`) o asignado por el OS (`--port 0`); nunca hard-coded 8765; solo id de taxon sintético `1` servido; refleja la forma FastAPI de producción `/api/taxon/1/files` + `/files/serve?path=…` (`FilesEnvelope` de `src/modules/research/domain/research-file.ts`); corpus fixture determinista en memoria (HTML, Markdown, texto, PDF; `Papers/lynx.pdf` recursivo); Content-Type refleja `api/server.py::_CONTENT_TYPE_BY_EXT`; `Content-Disposition: inline; filename="<basename>"`; rechaza fail-closed rutas desconocidas / taxon desconocido / `..` / `.` / absolutas / traversal codificado URL / método incorrecto; importable por la próxima rebanada de composición vía `startServer({port, host}) → {baseUrl, port, close}`; `tests/test_5c_2_b_react_harness.py` (21 tests herméticos; `subprocess` Node + Python `urllib`) prueba contrato de fuente (archivo existe, `node --check`, cero-dep), ciclo de vida start/stop, forma del envelope, tipos de contenido de cuatro formatos + magic `%PDF-`, fail-closed traversal, rechazo de taxon/ruta/método desconocido. **RED** = verificación de contrato de fuente pre-implementación (`fixture-server.mjs` ausente) FALLÓ sobre la fuente previa a `5c.2-B.1b-ii-a`. **GREEN** = `node --check` exit `0` + los 21 tests herméticos pasan. Sin servidor HTTP de exportación, sin `make capture-react-e2e`, sin target de Makefile, sin agregación G4, sin flip G4; servidor de exportación estático + rebanada de composición + tests herméticos del driver de captura + modernización de selectores e2e + borrado legacy `web/*.{html,js,css}` + `tailwind.config.js` aún diferidos. **G4 / G3 Tier-2 / cutover permanecen bloqueadas; G4 NO se voltea con el aterrizaje del fixture API.**
- [x] **5c.2-B.1b-ii-b (aterrizada)** — servidor HTTP de **exportación estática** Node en-proceso hermético para el arnés aislado React: `tools/react-e2e-harness/scripts/export-server.mjs` es Node puro built-ins (`node:http` + `node:fs/promises` + `node:path` + `node:url`); cero deps npm; `--root` absoluto provisto por el caller (obligatorio, absoluto, directorio existente; fail-closed antes de bindear cualquier listener); puerto elegido por el caller (CLI `--port N`) o asignado por el OS (`--port 0`); default loopback `127.0.0.1`; nunca hard-coded 8765; `/` mapea a `index.html`; archivos exactos bajo la raíz servidos con el Content-Type apropiado (HTML/JS/MJS/CSS/JSON/imágenes/fonts caen a `application/octet-stream`); HEAD refleja los headers de GET sin cuerpo; `..` / `.` / absolutas / traversal codificado URL / leakage de directorio / rutas desconocidas / métodos no-GET todos fail-closed (404 / 405); importable por la próxima rebanada de composición vía `startServer({port, host, root}) → {schema, root, host, port, baseUrl, server, close}`. `tests/test_5c_2_b_react_harness.py` gana un bloque del export-server (añadido dentro del mismo archivo que el bloque existente del fixture; constante `EXPORT_SERVER` + `_spawn_export` + `_wait_export_ready` + fixtures `exptree` / `exp` + 18 nuevos tests herméticos; archivo total ahora 39 tests herméticos; mismo enfoque `subprocess` Node + Python `urllib`) prueba contrato de fuente (archivo existe, exporta `startServer`, `node --check`, cero-dep), gating CLI (`--root` faltante/relativo/inexistente todos exit non-zero), ciclo de vida start/stop, `/` → `index.html`, siete familias de Content-Type + fallback `application/octet-stream`, archivo anidado bajo la raíz, HEAD refleja GET, fail-closed traversal parametrizado sobre `..` / `../../etc/passwd` / `%2Fetc%2Fpasswd` / `%2E%2E%2Fpasswd`, directorio-no-servido, ruta-desconocida 404, no-GET 405 con `Allow: GET, HEAD`. **RED** = verificación de contrato de fuente pre-implementación (`export-server.mjs` ausente) FALLÓ sobre la fuente previa a `5c.2-B.1b-ii-b`. **GREEN** = `node --check` exit `0` + los 39 tests herméticos pasan. Aún sin wiring de la rebanada de composición, sin target `make capture-react-e2e`, sin tests herméticos del driver de captura, sin modernización de selectores e2e, sin borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`. **G4 / G3 Tier-2 / cutover permanecen bloqueadas; G4 NO se voltea con el aterrizaje del servidor de exportación estática.**
- [x] **5c.2-B.1b-ii-c (aterrizada)** — orquestador de composición + driver CLI + target de Makefile + `capture:composed` package-script + rebanada de tests de composición hermética: `tools/react-e2e-harness/scripts/composed-capture.mjs` es Node puro built-ins; cablea `fixture-server.mjs` (5c.2-B.1b-ii-a) → `npm run build` (vía `buildFn` inyectado, `NEXT_PUBLIC_HARNESS_BASE_URL` fijado al origen del fixture) → sonda de acceso `out/index.html` → `export-server.mjs` (5c.2-B.1b-ii-b) → `run.mjs::capture` (5c.2-B.1b-i, vía `captureFn` inyectado) en un único orquestador `composeCapture({harnessDir, outputRoot, taxonId, host, buildFn, captureFn, startFixtureFn, startExportFn, now})`. La CLI requiere `--output-root`; rechaza host no-loopback (`0.0.0.0`, `10.0.0.1`, `example.com`, …) y cualquier `--taxon-id` distinto del `1` sintético que sirven la app y el fixture del arnés; ambas primitivas de validación (`validateTaxonId`, `validateHost`) exportadas para la rebanada de tests. `startFixtureFn` / `startExportFn` inyectados preservan el camino `startServer` en-proceso por defecto mientras permiten a la rebanada de tests hermética observar el orden de cierre. Nunca hard-codes un puerto (`--port 0` para ambos servidores); limpieza en orden inverso bajo `finally` anidados (export cerrado antes que fixture). `Makefile::capture-react-e2e` requiere `OUTPUT_ROOT` (sin default; sin puertos de producción horneados) y reenvía `HARNESS_DIR`; `package.json` añade `scripts.capture:composed = "node scripts/composed-capture.mjs"`. Superficie de test: `tests/test_5c_2_b_react_harness.py` gana un bloque de composición (11 casos herméticos; `subprocess` Node + Python; sin Playwright / Chromium / FastAPI / SQLite / red) cubriendo contrato de fuente (archivo existe + `node --check` + cero-dep), gating de CLI (`--output-root` obligatorio; `--host 0.0.0.0` rechazado; `--taxon-id 2` rechazado), primitivas de validación (`validateTaxonId("1") → 1`; cualquier otro entero positivo / cero / negativo / no-numérico lanza; `validateHost` acepta `127.0.0.1` / `::1` / `localhost` y rechaza todo lo demás), orquestación en-proceso con `out/index.html` sintético + `buildFn` inyectado + `captureFn` inyectado (devuelve sobre estructurado `taxa.react-e2e-composed-capture/1` con baseUrls loopback asignados por el OS), bypass de build → fail-closed (`buildFn` reclama éxito pero no hay `out/index.html` → `composeCapture` lanza ANTES de iniciar el servidor de exportación o invocar `captureFn`), y limpieza en orden inverso en fallo de captura (secuencia `close()` rastreada por espías: export `seq=1`, fixture `seq=2`). **RED** = verificación de contrato de fuente pre-`5c.2-B.1b-ii-c` (módulo de composición + seams `startFixtureFn`/`startExportFn` inyectados + `validateTaxonId`/`validateHost` endurecidos) habría FALLADO — observado en vivo desactivando la comprobación `n !== HARNESS_TAXON_ID` y confirmando que `test_composed_capture_validate_taxon_id_accepts_one_only` + `test_composed_capture_cli_rejects_other_taxon_id` van a RED con un fallo de aserción "taxon" claro y la CLI cayendo hasta una invocación real de `npm run build` que surfacea la validación faltante. **GREEN** = `node --check` exit `0` sobre `composed-capture.mjs` + los 65 tests herméticos pasan (21 fixture + 27 export-server + 11 composición + 6 source-contract parametrizados). **Sin éxito de runtime de navegador reclamado** (`chromium-driver.mjs` es alcanzable vía el `captureFn` por defecto pero la rebanada de tests de composición nunca lo invoca; el fixture en-proceso usa un stub de captura inyectado que devuelve evidencia sintética); sin agregación G4; sin flip G3 Tier-2; sin borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`. El resto más estrecho de `5c.2-B` (tests herméticos del driver de captura que ejercitan `chromium-driver.mjs` end-to-end, modernización de selectores e2e sobre el nuevo árbol de componentes, borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`) sigue diferido. **G4 / G3 Tier-2 / cutover permanecen bloqueadas; G4 NO se voltea con el aterrizaje de la composición** (sin flip end-to-end de `scripts/verify_parity.py`; sin artefacto de build de producción; sin éxito de runtime de navegador; solo se enviaron orquestador + CLI + target de Makefile + package-script + rebanada de tests hermética).
- [ ] **5c.2-B resto (diferida)** — tests herméticos del driver de captura que ejercitan `chromium-driver.mjs` end-to-end contra un fixture real + servidor de exportación (la rebanada de tests de composición usa un stub de captura inyectado; el driver de captura completo aún no se ejercita), modernización de selectores e2e sobre el nuevo árbol de componentes, borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`. G4 / G3 Tier-2 / cutover permanecen bloqueadas.

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
      1.963 líneas que los cuatro hijos CSS (3c-i / 3c-ii /
      3c-iii / 3c-iv) migraron a `src/app/globals.css`.
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
estática del App Router, los cuatro hijos CSS 3c-i / 3c-ii /
3c-iii / 3c-iv, Makefile/mount, 4a, 4b, 5a, 5b, 5c) acumulado
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

### Fase 6a: Cierre de baseline de hidratación G5 (PR 6a → rama del PR 5c, posición 17/22)

- [x] 6a.1 R — `tests/test_hydration_timing.py` (ya
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
      esquema que pinea el test de hidratación. (Atado al
      protocolo de reemplazo aprobado por el usuario en
      intentos previos.) <!-- sdd-owner: implementation -->
- [x] 6a.2 G — `scripts/reconstruct_hydration_baseline.py`
      (~50 LoC): lee los números del baseline legacy
      verbatim del design.md del predecesor (la entrada es
      la fuente markdown parseada para la tabla; la salida
      es un archivo JSON que coincide con el esquema que
      pinea `tests/test_hydration_timing.py`). (Atado al
      protocolo de reemplazo aprobado por el usuario en
      intentos previos; captura del fixture legacy servido
      por HTTP contra `http://127.0.0.1:64809/` en la
      captura fresca.) <!-- sdd-owner: implementation -->
- [x] 6a.3 G — corre `python scripts/measure_hydration.py
      --baseline web/dist/evidence-baseline.json --candidate
      out/` contra la build candidata aterrizada en
      posiciones 1–12; emite el nuevo JSON de hidratación
      junto al baseline; registra el delta en
      `apply-progress.md` §Registro de cambios. (Captura
      fresca bajo el protocolo de reemplazo aprobado por
      el usuario: mediana baseline `3.3 ms`, mediana
      candidato `3.2 ms`, delta `−0.1 ms`, umbral `10 ms`,
      ambos `captured`; `scripts/g5_close.sh` exit `0`.)
      <!-- sdd-owner: implementation -->
- [x] 6a.4 T — verifica que el delta ≤ 0 % en paint
      inicial y latencia de interacción; si lo excede,
      falla cerrado y escribe la solicitud de exención en
      `design.md` §"Risk register" antes de que G5 pueda
      flipar. (Tolerancia del protocolo fresco = absoluta
      (candidato − baseline) ≤ 10 ms bajo el protocolo de
      reemplazo aprobado por el usuario; satisfecha;
      tolerancia registrada en
      `evidence/g5/{status,regression-report}.json`. La
      regla previa de porcentaje ≤ 0 % está superada por
      el protocolo de reemplazo aprobado por el usuario y
      se retiene en el registro de cambios de
      `apply-progress.md` como historial de auditoría
      únicamente.) <!-- sdd-owner: implementation -->
- [x] 6a.5 Refactor — colapsa el script + corrida +
      verificación en un solo shim `scripts/g5_close.sh`
      que el apply worker invoca una vez y registra el
      resultado en `apply-progress.md`. (`scripts/g5_close.sh`
      es el arnés canónico de captura; la captura fresca
      bajo este script salió `0`; la entrada del registro
      de cambios del 2026-09-07 de `apply-progress.md`
      registra el cierre de G5. La regla previa de
      porcentaje/mediana 5+2 está superada y se retiene
      como historial de auditoría únicamente; la
      **solicitud** de excepción metodológica está
      superada por el protocolo de reemplazo aprobado por
      el usuario y la evidencia del protocolo fresco.)
      <!-- sdd-owner: implementation -->

**Evidencia por tarea**:

| Tarea | Comando de test enfocado | Harness de runtime | Frontera de reversión |
|------|--------------------------|--------------------|------------------------|
| 6a.1–6a.5 | `.venv/bin/python3 -m pytest tests/test_hydration_timing.py -v` | `scripts/g5_close.sh` exit 0; `apply-progress.md` §Registro de cambios registra el flip de puerta | `git revert <6a-sha>` elimina `scripts/reconstruct_hydration_baseline.py` y el delta de `apply-progress.md`; el JSON del baseline legacy se queda (regenerado en la próxima corrida de 6a) |

### Fase 6b: Ensayo de cutover G6 (PR 6b → rama del PR 6a, posición 18/22)

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

### Fase 6c: Medición de paridad G4 Playwright + Lighthouse (PR 6c → rama del PR 6b, posición 19/22)

La Fase 6c entrega la medición de paridad G4 de extremo a
extremo a través de los cinco sub-reportes (`navigation`,
`api`, `search`, `a11y`, `browser-state`). Se divide en
sub-slices; el **primero** es el productor solo de
navegación (ya aterrizado — ver slice 6c.0 abajo). Los
sub-slices restantes (6c.2–6c.5) capturan los otros cuatro
reportes. **Ningún sub-slice flipa G4 a PASS**; la
compuerta permanece bloqueada hasta que los cinco reportes
se capturen y el agregador por pares salga 0. El script
umbrella `scripts/g4_measure.sh` llega al final para que
el apply worker tenga un único punto de entrada.

#### Slice 6c.0 — productor solo de navegación (aterrizado, no cierra)

- [x] 6c.0.1 R — `tests/test_capture_parity.py` carga 25
      tests herméticos de paridad de navegación (`runFn`
      inyectado + `now()` fijo; sin navegador, sin red en
      vivo). <!-- sdd-owner: implementation -->
- [x] 6c.0.2 G — `tools/g4-capture/scripts/parity_navigation.mjs`
      (driver Playwright; dynamic-imported; `playwright@1.49.1`
      pinned aislado junto a `lighthouse@12.2.1` +
      `chrome-launcher@1.2.1`; sin cambios en dependencias
      raíz). Escribe `<outputRoot>/<UTC-timestamp>/{legacy,
      candidate}/` atómicamente (la estrategia sibling-backup
      refleja `capture.mjs`). <!-- sdd-owner: implementation -->
- [x] 6c.0.3 T — salida atómica verificada; ambos lados
      escritos en un solo run; fail-closed en orígenes
      faltantes/inválidos, runner no disponible, errores 5xx /
      de red, desajuste de path del manifest, colisión de
      salida, y drift de outcome por path. <!-- sdd-owner: implementation -->
- [x] 6c.0.4 Refactor — `make parity-navigation` acepta
      `LEGACY_ORIGIN` / `CANDIDATE_ORIGIN` / `PATHS` /
      `MANIFEST` / `OUTPUT_ROOT` explícitos; sin puertos de
      producción horneados; sin `make parity` umbrella aún.
      README documenta el slice como no-cierre.
      <!-- sdd-owner: implementation -->

#### Slice 6c.1+ — api / search / a11y / browser-state + flip de compuerta (pendiente)

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
| 6c.0 (aterrizado) | `.venv/bin/python -m pytest tests/test_capture_parity.py -k parity_navigation -v` | `make parity-navigation` (sin puertos de producción horneados); `<outputRoot>/<UTC-timestamp>/{legacy,candidate}/{navigation,manifest.snapshot,run}.json`; `apply-progress.md` registra el slice 6c.0 como no-cierre | `git revert <6c-sha>` elimina el delta del productor + tests + Makefile + lockfile; slice 6c.1–6c.4 queda intacto; sin flip G4 / G3 Tier-2 / cutover-status |
| 6c.1–6c.4 (pendiente) | `.venv/bin/python3 -m pytest tests/test_e2e_file_explorer.py tests/test_web_toggle.py -v` | `scripts/g4_measure.sh` exit 0; `out/g4-parity-report.json` lleva paint inicial + latencia de interacción; `apply-progress.md` §Registro de cambios registra el flip de puerta | `git revert <6c-sha>` elimina el delta de `apply-progress.md`; sin cambio en `tests/` o `scripts/` (el script de medición se queda como guardia de regresión futura) |

## Fase 3e: Cutover atómico (PR 3e → rama del PR 6c, posición 20/22, con compuerta en las seis puertas verdes)

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
- [ ] **G5 PASS registrado** (Fase 6a capturada bajo el
      protocolo de reemplazo aprobado por el usuario;
      registrada en la entrada del registro de cambios
      2026-09-07 de `apply-progress.md`; nuevo
      `evidence/g5/{status,regression-report}.json` con
      `status: "ready"`, `regression: false`, `pass: true`,
      mediana baseline `3.3 ms`, mediana candidato `3.2 ms`,
      delta `−0.1 ms`, umbral `10 ms`, ambos `captured`).
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
      `apply-progress.md` §Status de "bloqueado /
      bloqueado / bloqueado" (G4 / G6 / G3-Tier2 aún
      bloqueados; G5 ya PASS registrado bajo el
      protocolo de reemplazo aprobado por el usuario)
      a "PASS registrado (G4 / G6 cerrados por Fase
      6c / 6b; G3 Tier-2 activado en PR 3e; G5 ya
      PASS registrado bajo el protocolo de reemplazo
      aprobado por el usuario en la entrada del
      registro de cambios del 2026-09-07)".
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
  CSS** — la sub-secuencia de 4 hijos es vinculante; no
  colapsar 3c-i / 3c-ii / 3c-iii / 3c-iv en un solo sub-PR
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

> **2026-09-02 — replan de la sub-secuencia del PR 3c**: el
> PR 3c único original a ~230 LoC era insatisfacible contra
> el bloque `<style>` inline legacy de 1.963 líneas. El slot
> del 3c es ahora cuatro hijos revisables en las posiciones
> 3–6. El total authored en LoC sube de ~2.245 a ~3.485
> (+1.240) porque cada regla CSS legacy se porta. El sub-PR
> más grande por plan es **3c-i a ~390 LoC** (-10 LoC de
> holgura bajo 400). Los 16 hijos quedan ≤ 400 LoC authored
> **excepto PR 3c-ii, que carga una `size:exception`
> aprobada por el usuario** para la rebanada completa
> de CSS de árbol / detalle de taxonomía (implementación
> real totaliza **831 LoC = 822 inserciones + 9 deletions**,
> sobrepaso +442 LoC sobre la estimación previa de `~380 LoC`
> y +431 LoC contra el presupuesto de 400 líneas —
> véase el addendum dedicado abajo para la justificación
> de autorización). **El Enfoque A, FastAPI/SQLite,
> el predecesor congelado y la estrategia de Feature Branch
> Chain quedan sin cambios.**

- **3a** ~210 LoC authored (bootstrap de toolchain — pins
  de deps de `package.json` +
  `scripts/check-runtime.mjs` + base de `tsconfig.json` +
  `.nvmrc` + 2 tests nuevos); **3b** ~175 (entrada del App
  Router — `src/app/{layout,page}.tsx` + `next.config.mjs`
  + `tests/test_app_shell_render.py`, ahora satisfacible
  porque 3a instaló Next); **3c-i** ~390 (tokens / base /
  dark mode + selectores focus-visible globales + `@theme`
  + cascada de dark mode); **3c-ii** **831 reales (822 inserciones + 9 deletions)** — **`size:exception` aprobada por el usuario** (styling de árbol
      / detalle de taxonomía + kebab + modal de materialize +
      variantes de árbol teñidas por realm — la implementación real sobrepasa la estimación previa de `~380 LoC` en +442 LoC y el presupuesto de revisión por PR de 400 líneas en +431 LoC; véase el addendum abajo para la justificación de autorización); **3c-iii** ~390
  (styling de Search / Folder / global Browser + chrome
  del file explorer + visores de CSV / JSON); **3c-iv**
  ~280 (animations + frames del visor de imagen / video +
  vista de Settings + barrel del design-system + paridad
  de clases utility final); **3d** ~240 (reescritura del
  Makefile + repoint de `WEB_DIR` + lector AC-21 + 2
  tests nuevos, el más pesado de los hijos posteriores
  re-ambidos); **4a** ~180; **4b** ~90; **5a** ~280;
  **5b** ~360; **5c** ~200; **6a** ~50; **6b** ~120;
  **6c** ~20; **3e** ~120. **Total**: ~3.485 LoC authored
  a través de **16 sub-PRs** (arriba desde ~2.245 a través
  de 13 sub-PRs; el delta de +1.240 es el porte completo
  del bloque `<style>` inline legacy).
- El sub-PR más grande es **3c-i a ~390 LoC authored**,
  con -10 LoC (-2.5 %) de holgura contra el
  **presupuesto de revisión de 400 líneas por PR**. El
  previamente-mayor 5b queda en segundo lugar a ~360 LoC
  (-40 LoC, -10 % de holgura). **Los 16 sub-PRs ≤ 400 LoC
  authored excepto PR 3c-ii**, que carga una
  **`size:exception` aprobada por el usuario** para la
  rebanada completa de CSS de árbol / detalle de
  taxonomía (implementación real totaliza **831 LoC
  = 822 inserciones + 9 deletions**, sobrepaso +431 LoC
  contra el presupuesto de 400 líneas — véase el
  addendum dedicado abajo para la justificación de
  autorización; PR 3a retiene la excepción de lockfile
  de `package-lock.json` regenerado como la primera
  `size:exception` documentada, ahora con PR 3c-ii
  como la segunda).
- El más pesado de los hijos del 3c es **3c-i a ~390
  LoC** por el plan; **PR 3c-ii es el sub-PR más
  pesado por diff real a 831 LoC** (overshoot
  autorizado, ver arriba); el más ligero es
  **3c-iv a ~280 LoC** (porque el barrel del
  design-system es pequeño). El sub-PR **6c** es el
  más pequeño en general a ~20 LoC; el artefacto de
  medición G4 se registra en `apply-progress.md` en
  lugar de en un diff de código.
- La Fase 6 colectivamente (6a + 6b + 6c) totaliza ~190
  LoC authored y ~120 LoC de artefacto de medición. Si
  el mantenedor prefiere un único batch encadenado para
  la Fase 6, los LoC combinados se quedan bien debajo de
  400; si prefiere tres sub-PRs separados para foco de
  revisión, cada uno también está debajo.
- **PRs encadenados recomendados: Sí** — cada sub-PR cabe
  por sí solo en el presupuesto por PR, pero el total de
  ~3.485 líneas y el cutover atómico (la feature DEBE
  integrarse antes de llegar a `develop`) sitúan este
  cambio en la compuerta de Feature Branch Chain. La
  propia sub-secuencia del 3c es cuatro hijos encadenados
  porque el CSS inline de 1.963 líneas debe portarse
  literalmente a Tailwind 4 `@theme` + `@layer base` y ese
  trabajo no cabe bajo 400 LoC como un único PR.
- **Estrategia de cadena: `feature-branch-chain`**
  (elegida por el usuario, sin cambios por el replan del
  3c). El tracker
  `docs/complete-taxa-frontend-migration-plan` es
  draft/no-merge y es el **único** PR que apunta a
  `develop`; PR 3a apunta al tracker (ahora fusionado como
  PR #144); PR 3b apunta al PR 3a (ahora fusionado como PR
  #145, con PR #146 reconcile también fusionado);
  **PR 3c-i apunta al tracker** (después de que PR #146
  se fusione, recogiendo el 3a + 3b + reconcile ya
  fusionados sin un paso extra de reconciliación); cada
  hijo 3c posterior apunta a su rama predecesora
  inmediata del 3c; cada hijo post-3c posterior apunta a
  su rama predecesora inmediata. Esto sustituye, para
  este cambio, el default de `AGENTS.md` §4 de apuntar
  directo a `develop` y el precedente de apply-progress
  del predecesor.
- **Longitud de la cadena: 16 PRs hijos + 1 tracker.** El
  presupuesto de revisión por hijo son los LoC authored
  listados arriba; el tracker no lleva presupuesto de
  revisión propio (es el punto de acumulación).
- **Estrategia de entrega: `ask-on-risk`** (según
  preflight; sin flag de riesgo abierto — el Enfoque A
  es FINAL, el predecesor está congelado, cada sub-PR
  cabe bajo 400 líneas, la cadena corregida satisface el
  orden de dependencia que el portón de apply identificó
  como el defecto, y el replan de la sub-secuencia del
  3c satisface el presupuesto de LoC que el portón de
  apply identificó como insatisfacible para el PR 3c
  único original).
- **Sobrecarga de la revisión correctiva del plan + replan
  de la sub-secuencia del 3c**: el reordenamiento absorbió
  el trabajo originalmente atribuido al PR 3a, PR 3b y PR
  3c en las nuevas posiciones 1, 2, 3, 4 (el PR 3c original
  mismo fue luego reemplazado por la sub-secuencia de
  cuatro hijos en las posiciones 3–6). El conteo absoluto
  de líneas authored se movió de ~2.225 (pre-corrección)
  a ~2.245 (post-corrección, 3c único) a ~3.485
  (post-replan, sub-secuencia 3c de cuatro hijos) porque
  el nuevo split mueve cada regla CSS legacy fuera del
  cubo único del 3c y dentro de una sub-secuencia
  revisable que el test de paridad puede enumerar línea
  por línea. No se duplica código de producción; el delta
  es cableado de tests + enumeración de paridad de cada
  selector legacy.
- **Riesgo / decisión (si el mantenedor prefiere una
  cadena más plana)**: las posiciones 1–2 (bootstrap de
  toolchain + exportación estática del App Router)
  podrían colapsarse en un único sub-PR a ~385 LoC
  authored — debajo de 400 pero ajustado. La
  sub-secuencia del 3c no puede colapsarse más: incluso
  el par más ligero (3c-i + 3c-ii a ~770 LoC combinados)
  excede el presupuesto de 400 líneas en ~93 %. La
  topología de la cadena preserva el bootstrap como un
  foco de revisión separado para que los pins del
  toolchain y el contrato del App Router puedan revisarse
  independientemente; la sub-secuencia del 3c preserva
  las cuatro rebanadas CSS como focos de revisión
  separados para que los tokens / base / cascada de dark,
  la superficie de taxonomía, la superficie de Browser /
  search / folder, y las animations / utilities / barrel
del design-system puedan revisarse cada uno
  independientemente. Colapsar cualquier par del 3c no
  es el default.

## Addenda — 2026-09-09: autorización de size:exception de PR 3c-ii (solo documental; ni fusionado ni verificado) (solo anexo)

- **size:exception de PR 3c-ii autorizada (esta entrada, abre una segunda `size:exception` aprobada por el usuario junto a la excepción previa de `package-lock.json` regenerado de PR 3a; la cadena de 16 hijos se preserva; sin otros cambios de alcance; el PR NO se reclama como fusionado ni verificado por este addendum)**. El usuario autorizó una `size:exception` para PR 3c-ii porque la implementación real de la rebanada completa de CSS de árbol / detalle de taxonomía requirió **822 inserciones + 9 deletions = 831 LoC**, contra la estimación previa de `~380 LoC` registrada en el "Pronóstico de carga de revisión" de este tasks-es.md, en el callout de justificación del replan de la sub-secuencia del PR 3c arriba, en la descripción de dependencia por PR para PR 3c-ii, y en la tabla "Rebanada de sub-PRs bajo la Aproximación A" de `design-es.md` — es decir, la implementación real sobrepasa el presupuesto de revisión por PR de 400 líneas que el Enfoque A bloqueó el 2026-09-02 en +431 LoC. **Justificación de la autorización** (por qué se prefiere un único PR revisable sobre un fraccionamiento adicional): (a) los selectores de árbol / detalle de taxonomía, las variantes teñidas por realm `.tree-row[data-realm="…"]`, los selectores del menú kebab / modal de materialize, la superficie de `#detail-panel` / `.detail-card` / `.detail-section` / `.overview-section` / `.detail-item` / `.search-pulse` / `.detail-tabs` / `.search-icon-btn` / `.materialize-btn`, y la rebanada del test de paridad en `tests/test_tailwind_4_parity.py` son inseparables de la capa base de 3c-i (deben enviarse juntos para que cada selector resuelva sus referencias `var(--token)` contra la rebanada viva de tokens `:root`); (b) dividir PR 3c-ii aún más en un par 4c-i / 4c-ii duplicaría la superficie consumidora de `var(--token)` entre dos PRs y forzaría al hijo posterior a re-tocar selectores que el hijo anterior ya bloqueó; (c) la sub-secuencia de cuatro hijos del 3c ya minimizó el radio de impacto al dividir el `<style>` inline legacy de 1.963 líneas en cuatro hermanos revisables (3c-i / 3c-ii / 3c-iii / 3c-iv), así que el presente sobrepaso refleja la superficie realista de port de CSS para el concern de árbol / detalle de taxonomía más que un defecto de planificación; (d) la enumeración de cada selector de taxonomía en `tests/test_tailwind_4_parity.py` — el contribuyente dominante del conteo de 831 LoC — es en sí misma una rebanada inseparable (dividir el enumerador entre dos PRs dejaría un test a medio-coherente que nadie puede revisar coherentemente y aún tendría que re-fusionarse en PR 5c). **La cadena de 16 hijos se preserva**: PR 3c-ii permanece en la posición 4/16 con el mismo predecesor (`feat/complete-taxa-frontend-migration-03-3c-i`) y el mismo sucesor (`feat/complete-taxa-frontend-migration-05-3c-iii`); la descripción de dependencia por PR, el orden corregido, el bloqueo del Enfoque A, la base de FastAPI/SQLite, la estrategia de Feature Branch Chain, el estado congelado del predecesor, las specs por dominio, todos los addenda previos (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c), y el protocolo G5 de reemplazo aprobado por el usuario registrado en `design-es.md` quedan sin cambios. **El PR no se reclama como fusionado ni verificado por este addendum** — la `size:exception` solo autoriza un único PR revisable contra el presupuesto establecido; revisión, CI y merge siguen el proceso ordinario de feature-branch-chain. Las estimaciones corregidas (`831 LoC totales: 822 inserciones, 9 deletions`) sustituyen a la cifra previa de `~380 LoC` en las cuatro tablas arriba; el presupuesto inline `~380 (≤ 400; -20 LoC de holgura)` de la tabla de rebanada de sub-PRs pasa a `831 (sobrepaso +431 LoC contra el presupuesto de 400 líneas; size:exception aprobada por el usuario para este PR)`; la línea `El sub-PR nuevo más grande es 3c-i a ~390 LoC` del Pronóstico de carga de revisión pasa a `El sub-PR nuevo más grande por diff real es PR 3c-ii a 831 LoC`; la línea `Los 16 sub-PRs ≤ 400 LoC authored` se anota con `excepto PR 3c-ii, que carga una size:exception aprobada por el usuario`; la cláusula `no se abre ninguna nueva size:exception` se anota con `excepto para PR 3c-ii, que ahora es la segunda size:exception aprobada por el usuario junto a PR 3a`. El espejo en español carga la misma semántica; cualquier deriva se resuelve a favor del inglés. Sin cambios de código; sin rebase; sin nueva rama; sin commit/push; sin apertura de PR.

## Addenda — 2026-09-09: autorización de size:exception de PR 3c-iii (solo documental; ni fusionado ni verificado) (solo anexo)

- **size:exception de PR 3c-iii autorizada (esta entrada, abre una tercera `size:exception` aprobada por el usuario junto a la excepción previa de `package-lock.json` regenerado de PR 3a Y la excepción previamente autorizada de CSS de árbol-de-taxonomía de PR 3c-ii; la cadena de 16 hijos se preserva; las superficies de PR 3c-iv quedan diferidas al siguiente hijo de la cadena con alcance sin cambios; el PR NO se reclama como fusionado ni verificado por este addendum)**. El usuario autorizó una `size:exception` para PR 3c-iii porque la implementación real de la rebanada completa de CSS de Search / Folder / global Browser requirió **1669 inserciones y 66 deletions = 1735 review lines (net +1603)**, contra la estimación previa de `~390 LoC` registrada en el "Pronóstico de carga de revisión" de este tasks-es.md, en el callout de justificación del replan de la sub-secuencia del PR 3c arriba, en la descripción de dependencia por PR para PR 3c-iii, y en la tabla "Rebanada de sub-PRs bajo la Aproximación A" de `design-es.md` — es decir, la implementación real sobrepasa el presupuesto de revisión por PR de 400 líneas que el Enfoque A bloqueó el 2026-09-02 en **+1335 LoC** y la estimación previa de `~390 LoC` en **+1345 LoC**. **Lo que el PR preserva efectivamente**: el **catálogo completo de selectores de Search / Folder / global Browser** (`.toast` / `.toast-error`, `.search-engines-grid`, `.search-category-header`, `.search-engine-btn`, `.fex-meta-strip`, `.fex-tab-strip`, `.fex-snippet-frame`, `.fex-shell`, `.fex-tree-pane`, `.fex-viewer-pane`, `.fex-splitter`, `.fex-row` + variantes `.selected` / `.file` / `.folder`, `.fex-tree-header`, `.fex-children`, `.fex-banner`, `.fex-empty-state`, `.fex-search-*`, `.fex-csv-*`, `.fex-json-*`, `.fex-tree-truncated`, según la enumeración del alcance de 3c-iii en la descripción de dependencia por PR arriba) y su **contrato de paridad canónico** (`tests/test_research_styles.py` enumera cada selector de Search / Folder / global Browser; `tests/test_tailwind_4_parity.py` extiende su rebanada de selectores de Browser; cada selector resuelve a una declaración no vacía en `src/app/globals.css` y `out/_next/static/chunks/*.css`). **Superficies de PR 3c-iv diferidas**: las reglas `@keyframes` + `.animate-spin` + los frames de los viewers de imagen / video + los selectores de la vista Settings + el barrel del design-system (`src/modules/design-system/{infrastructure/index.ts, presentation/Icon.tsx, presentation/Button.tsx}`) permanecen diferidos a PR 3c-iv en la posición 6/16 sin cambio de alcance; la estimación `~280 LoC` de PR 3c-iv queda sin cambios. **Justificación de la autorización** (por qué se prefiere un único PR revisable sobre un fraccionamiento adicional): (a) los selectores de Search / Folder / global Browser son inseparables de la capa base de 3c-i (tokens + cascada de dark mode) Y de los selectores de taxonomía de 3c-ii (los selectores de research `.search-tab` / `.folder-tab` / `.header-browser-tab` se montan sobre las referencias `var(--token)` vivas que 3c-ii acaba de enviar); deben enviarse juntos como una única rebanada CSS para que cada selector de browser / research resuelva sus referencias `var(--token)` contra la capa base viva; (b) dividir PR 3c-iii aún más en un par 4c-i / 4c-ii duplicaría la superficie consumidora de `var(--token)` entre dos PRs y forzaría al hijo posterior a re-tocar selectores que el hijo anterior ya bloqueó — duplicando el defecto de planificación que la sub-secuencia de cuatro hijos del 3c ya cerró; (c) la sub-secuencia de cuatro hijos del 3c ya minimizó el radio de impacto al dividir el `<style>` inline legacy de 1.963 líneas en cuatro hermanos revisables (3c-i / 3c-ii / 3c-iii / 3c-iv), así que el presente sobrepaso refleja la superficie realista de port de CSS para el concern de Search / Folder / global Browser más que un defecto de planificación (la estimación de `~390 LoC` subcontó la enumeración canónica de cada selector de browser en el test de paridad, la profundidad de la familia `.fex-search-*` / `.fex-csv-*` / `.fex-json-*`, y las dimensiones de chrome de `.fex-tree-pane` / `.fex-viewer-pane` / `.fex-splitter` / `.fex-banner`); (d) la enumeración de cada selector de Search / Folder / global Browser en `tests/test_tailwind_4_parity.py` + `tests/test_research_styles.py` — el contribuyente dominante del conteo de 1735 review-line — es en sí misma una rebanada inseparable (dividir el enumerador entre dos PRs dejaría un test a medio-coherente que nadie puede revisar coherentemente y aún tendría que re-fusionarse en PR 5c). **La cadena de 16 hijos se preserva**: PR 3c-iii permanece en la posición 5/16 con el mismo predecesor (`feat/complete-taxa-frontend-migration-04-3c-ii`) y el mismo sucesor (`feat/complete-taxa-frontend-migration-06-3c-iv`); PR 3c-iv permanece en la posición 6/16 con la misma estimación `~280 LoC` y alcance sin cambios; la descripción de dependencia por PR, el orden corregido, el bloqueo del Enfoque A, la base de FastAPI/SQLite, la estrategia de Feature Branch Chain, el estado congelado del predecesor, las specs por dominio, **la size:exception existente de PR 3c-ii queda abierta** (el sobrepaso de 831 LoC de PR 3c-ii queda sin cambios; este addendum NO modifica, reemplaza, ni supera la excepción de PR 3c-ii — ambas excepciones coexisten sobre la misma cadena), todos los addenda previos (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c, 3c-ii), y el protocolo G5 de reemplazo aprobado por el usuario registrado en `design-es.md` quedan sin cambios. **El PR no se reclama como fusionado ni verificado por este addendum** — la `size:exception` solo autoriza un único PR revisable contra el presupuesto establecido; revisión, CI y merge siguen el proceso ordinario de feature-branch-chain. Las estimaciones corregidas (`total de 1735 review-line: 1669 inserciones, 66 deletions; net +1603; sobrepaso +1335 LoC contra el presupuesto de 400 líneas y +1345 LoC contra la estimación previa de ~390 LoC; size:exception aprobada por el usuario para este PR`) sustituyen a la cifra previa de `~390 LoC` en las tablas arriba; el presupuesto inline `~390 (≤ 400; -10 LoC de holgura)` de la tabla de rebanada de sub-PRs pasa a `1735 review lines (sobrepaso +1335 LoC contra el presupuesto de 400 líneas y +1345 LoC contra la estimación previa de ~390 LoC; size:exception aprobada por el usuario para este PR)`; la línea `El sub-PR nuevo más grande por diff real es PR 3c-ii a 831 LoC` del Pronóstico de carga de revisión pasa a `El sub-PR nuevo más grande por diff real es PR 3c-iii a 1735 review lines (net +1603; sobrepaso +1335 LoC contra el presupuesto de 400 líneas y +1345 LoC contra la estimación previa de ~390 LoC; size:exception aprobada por el usuario), con PR 3c-ii segundo a 831 LoC (size:exception aprobada por el usuario) y PR 3c-i tercero a ~390 LoC`; la línea `Los 16 sub-PRs ≤ 400 LoC authored` se anota con `excepto PR 3c-ii (831 LoC) Y PR 3c-iii (1735 review lines), ambos cargando size:exceptions aprobadas por el usuario`; la cláusula `no se abre ninguna nueva size:exception` se anota con `excepto para PR 3c-ii (ya autorizada) Y PR 3c-iii (autorizada por esta entrada), que son la segunda y tercera size:exceptions aprobadas por el usuario junto a PR 3a`. El espejo en español (`documents-es/openspec/changes/complete-taxa-frontend-migration/tasks-es.md`) carga la misma semántica; cualquier deriva se resuelve a favor del inglés. Sin cambios de código; sin rebase; sin nueva rama; sin commit/push; sin apertura de PR.

## Addenda — 2026-09-09: reparación de pipeline Tailwind 4 / PostCSS de PR 5.5 (aterrizada; el primer hijo de reparación post-sub-secuencia-3c; cadena de 17 hijos; la cuarta `size:exception` aprobada por el usuario para el `package-lock.json` regenerado junto a PR 3a + PR 3c-ii + PR 3c-iii) (solo anexo)

- **Reparación de pipeline Tailwind 4 / PostCSS de PR 5.5 aterrizada (esta entrada, inserta un nuevo hijo de reparación entre PR 3c-iii y PR 3c-iv, expande la cadena de 16 hijos a 17 hijos, abre una cuarta `size:exception` aprobada por el usuario para el `package-lock.json` regenerado de este PR junto a las excepciones existentes de PR 3a + PR 3c-ii + PR 3c-iii, y expone el hueco de evidencia de candidato-de-producción G2 que la cadena previa dejó abierto; el PR está implementado en este worktree pero NO se reclama como fusionado, NO se reclama como G2-PASS, y NO se reclama como verificado-en-navegador por este addendum)**. **Defecto confirmado (causa raíz + firma observable a nivel de artefacto)**: PR 3c-i envió `src/app/globals.css` con la superficie canónica de Tailwind 4 — `@import "tailwindcss";` seguido de un bloque `@theme { --primary: #1d7ea9; --accent: #176587; --surface: #ffffff; … --realm-bacteria: #5ebd9b; … }` que carga cada token legacy `:root` / `[data-theme="dark"]` / `--realm-*`. PR 3c-ii, PR 3c-iii y el bootstrap de toolchain previo PR 3a consumieron esa superficie bajo el supuesto de que el pipeline PostCSS por defecto de `next build` procesaría `@import "tailwindcss"` y expandiría el bloque `@theme { … }`. **El supuesto era incorrecto**: PR 3a añadió `tailwindcss@^4` como dependencia top-level, pero el proyecto nunca registró un plugin de PostCSS para él (sin `postcss.config.mjs` en la raíz del repo, sin dependencia `@tailwindcss/postcss`). El pipeline PostCSS por defecto de Turbopack NO reconoce `@import "tailwindcss";` como directiva de Tailwind 4 y NO reconoce `@theme { … }` como regla CSS — el build emite una warning no fatal `Unknown at rule: @theme`, deja el bloque `@theme { … }` como regla literal en el CSS compilado (el navegador lo descarta silenciosamente porque `@theme` no es una regla CSS real), y envía cero preflight de Tailwind + cero tokens `:root` expandidos por `@tailwindcss/postcss`. **Consecuencia observada (este worktree, commit base `6375927`, antes de PR 5.5)**: `next build` sale con `0`, los selectores legacy `.research-explorer` / `.fex-row` / `.tree-row` / `.tier-header` / `.load-all` / `.kebab` / `.search-tab` / `.folder-tab` / `.header-browser-tab` / `.fex-meta-strip` / `.fex-tab-strip` / `.fex-snippet-frame` / `.fex-csv-table` / `.fex-json-tree` / `.fex-tree-leaf` se envían (porque son CSS plano que no necesita procesamiento de Tailwind), pero **cada referencia `var(--primary)` / `var(--accent)` / `var(--surface)` / `var(--on-surface)` / `var(--realm-bacteria)` / `var(--realm-archaea)` / `var(--realm-viruses)` / `var(--realm-animalia)` / `var(--realm-fungi)` / `var(--realm-plantae)` / `var(--realm-chromista)` / `var(--realm-other)` dentro de esos selectores resuelve a `unset` en tiempo de ejecución** — la cascada visual completa está rota. El preflight de Tailwind 4 (`*,:after,:before,::backdrop { box-sizing: border-box; border: 0 solid; margin: 0; padding: 0 }`) está ausente; la superficie de clases utility de Tailwind 4 está ausente; la animación `@keyframes spin { to { transform: rotate(360deg) } }` está ausente. El bundle CSS compilado en `out/_next/static/chunks/391guka-hdllv.css` (hash del pipeline chunked de Turbopack; este es el único bundle CSS que `next build` emite para este repo) encoge de **50.891 bytes** (con `@tailwindcss/postcss` corriendo) a **35.093 bytes** (sin él) — un encogimiento de ~31% que es la huella a nivel de bytes del defecto. **Qué envía PR 5.5 (superficie de edición de este worktree)**: (1) `package.json` añade **dos nuevas entradas top-level en `dependencies`**: `"@tailwindcss/postcss": "^4.3.3"` (el plugin oficial de PostCSS de Tailwind 4, resuelto contra el mismo major `^4` que la dependencia `tailwindcss` existente) y `"postcss": "^8.5.0"` (el runtime del que depende `@tailwindcss/postcss` — explícitamente requerido ahora porque PR 3a eliminó la dependencia top-level legacy `postcss` junto con `autoprefixer` / `@tailwindcss/forms`, y el plugin de Tailwind 4 necesita un peer `postcss` para correr). Los plugins de la era Tailwind 3 (`autoprefixer`, `@tailwindcss/forms`) permanecen prohibidos. (2) Archivo nuevo `postcss.config.mjs` en la raíz del repo, `export default { plugins: { "@tailwindcss/postcss": {} } }` — una config PostCSS ESM mínima que registra solo el plugin oficial de Tailwind 4 (sin `autoprefixer`, sin `@tailwindcss/forms`, sin otros plugins legacy). (3) `package-lock.json` regenerado (el lockfile regenerado de este PR es la **cuarta `size:exception` aprobada por el usuario** para este proyecto, junto a las excepciones existentes de PR 3a + PR 3c-ii + PR 3c-iii — véase el párrafo de excepción de lockfile abajo para la justificación de autorización y el delta del lockfile). (4) `tests/test_toolchain_bootstrap.py` se actualiza: `REQUIRED_DEPS_PRODUCTION` se expande de `(("tailwindcss", "4"),)` a `(("tailwindcss", "4"), ("postcss", None), ("@tailwindcss/postcss", None))` para que `postcss` y `@tailwindcss/postcss` queden pineados como deps de producción requeridas; `FORBIDDEN_LEGACY_DEPS` se reduce de `("autoprefixer", "postcss", "@tailwindcss/forms")` a `("autoprefixer", "@tailwindcss/forms")` para que la prohibición de la era Tailwind 3 `autoprefixer` + `@tailwindcss/forms` permanezca abierta mientras `postcss` ahora es requerida (no prohibida). (5) Nueva superficie de test `tests/test_tailwind_build_pipeline.py` — un test de regresión enfocado que realiza un `next build` REAL contra el repo, lee el bundle CSS compilado bajo `out/_next/static/{css,chunks}/*.css`, y afirma: (a) `next build` sale con `0`; (b) al menos un bundle CSS existe bajo la ruta de static export; (c) la regla universal-selector del preflight de Tailwind 4 está presente en el CSS compilado; (d) la regla literal `@theme {` NO está presente en el CSS compilado; (e) el substring literal `@import "tailwindcss"` NO está presente en el CSS compilado; (f) cada bundle CSS contiene el preflight; (g) el token de la paleta legacy `:root` `--primary: #1d7ea9` vive dentro de una declaración `@layer theme { :root, :host { … } }`. La fixture limpia `out/` y `.next/` en teardown SI no existían antes de que el test entrara. **Evidencia de Strict-TDD observada en este worktree (RED → GREEN → TRIANGULATE)**: **RED** = pre-implementación, 7 casos en el archivo de test nuevo FALLAN con `postcss.config.mjs missing at … PR 5.5 ships @tailwindcss/postcss as the registered plugin`; 2 nuevos casos de dep en el test de toolchain FALLAN con `production dep 'postcss' missing from dependencies` y `production dep '@tailwindcss/postcss' missing from dependencies`. **GREEN** = tras añadir las dos deps a `package.json`, crear `postcss.config.mjs`, y correr `npm install` para regenerar `package-lock.json`, el archivo completo de test de toolchain pasa (`30 passed in 0.02s`) y el archivo completo de test de build-pipeline pasa (`7 passed in 3.83s`); repetibilidad confirmada por una segunda corrida consecutiva (`7 passed in 3.83s`) sin flakiness; el bundle CSS compilado es byte-idéntico entre las dos corridas (`50.891 bytes`, hash-estable bajo el pipeline chunked de Turbopack). **TRIANGULATE** = el par de tests cubre el lado de dep de `package.json` (test de toolchain) Y el lado de config de `postcss.config.mjs` (test de build-pipeline) Y el lado de artefacto de CSS compilado (preflight de Tailwind + ausencia de regla `@theme` + ausencia de `@import "tailwindcss"` + expansión de token de theme en `:root, :host`). **Prueba de arreglo del defecto visual a nivel de artefacto**: en este worktree tras PR 5.5, un `node node_modules/.bin/next build` limpio produce `out/_next/static/chunks/391guka-hdllv.css` (50.891 bytes) que contiene 204 ocurrencias de `--tw-`, 1 ocurrencia de `@keyframes spin`, 1 ocurrencia de `.animate-spin`, 1 ocurrencia de `@layer theme { :root, :host { … --primary: #1d7ea9; … } }`, 5 ocurrencias de `#1d7ea9`, cero ocurrencias de la regla literal `@theme {`, y cero ocurrencias del substring literal `@import "tailwindcss"`. `node scripts/check-runtime.mjs` sale con `0`. `npm ci` reproduce una instalación de 121 paquetes con las mismas 18 entradas de lockfile tailwind/postcss en un clone fresco. **Implicaciones de topología / conteo (precisas, solo anexo)**: la cadena se expande de **16 hijos a 17 hijos**. El nuevo hijo de reparación se llama **PR 5.5 (reparación de pipeline Tailwind 4 / PostCSS)** y se ubica en la **posición 5.5/17** — interpolado entre la **posición 5/17 (PR 3c-iii)** y la **posición 7/17 (PR 3c-iv)**. Cada hijo que estaba previamente en la posición `n/16` (para `n ∈ {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}`) se renumera a `n+1/17`. PR 3a permanece en `1/17`, PR 3b permanece en `2/17`, PR 3c-i permanece en `3/17`, PR 3c-ii permanece en `4/17`, PR 3c-iii permanece en `5/17`. El alcance de cada sub-PR, el mapeo de ramas predecesor / sucesor, el orden corregido, el bloqueo del Enfoque A, la base de FastAPI/SQLite, la estrategia de Feature Branch Chain, el estado congelado del predecesor, las specs por dominio, cada addendum previo, y el protocolo G5 de reemplazo aprobado por el usuario quedan sin cambios en su contenido sustantivo; solo sus etiquetas de posición se desplazan arriba por 1 (o permanecen donde estaban si estaban antes de la posición 5). **Posición de dependencia de PR 5.5**: depende de **PR 3c-iii**; **NO depende de PR 3c-iv**. El nuevo hijo de reparación es auto-contenido: no toca el contenido de `src/app/globals.css`, no toca `tsconfig.json`, no toca `.nvmrc`, no toca `scripts/check-runtime.mjs`, no toca el Makefile, no toca `next.config.mjs`, no toca `api/server.py`, no toca ningún barrel de `src/modules/**`, no toca `web/**`, no toca `extension/**`, y no borra `web/*.{html,js,css}` ni `tailwind.config.js`. **Presupuesto de LoC**: el diff authored de PR 5.5 está bien por debajo del presupuesto de 400 líneas (≈ 259 LoC authored en total, ≤ 400 con −141 LoC de holgura). **La cadena de 17 hijos se preserva**. **La cuarta `size:exception` aprobada por el usuario para el `package-lock.json` regenerado**: el `package-lock.json` regenerado añade 16 nuevas entradas de lockfile relacionadas con tailwind/postcss (del total de 18 entradas de lockfile relacionadas con tailwind/postcss en el lockfile post-fix; `tailwindcss` en sí precede a esta reparación porque PR 3a lo añadió) llevando el objeto `packages` total a **121 paquetes** y el conteo de líneas del lockfile a **2.112 líneas**. El cambio del lockfile es **generated-resolution-only**; se revisa junto con `package.json`; no carga churn de lockfile no relacionado. Las dos nuevas entradas de `package.json` están pineadas con caret (`^4.3.3` para `@tailwindcss/postcss`, `^8.5.0` para `postcss`) así que el delta del lockfile es determinista bajo re-`npm install`. **Hueco de evidencia de candidato-de-producción G2**: la cadena previa registró G2 como **PASS** trasladada del predecesor contra el **workspace aislado `tools/g2-candidate/`**. **Ese PASS de G2 NO se traslada al repo de producción**, porque el `src/app/globals.css` del repo de producción (post-PR-3c-iii) envía la superficie canónica `@import "tailwindcss";` + `@theme { … }` que el plugin `@tailwindcss/postcss` debe procesar, y la cadena previa nunca registró ese plugin. Concretamente: un `next build` limpio contra el repo pre-PR-5.5 produce un `out/_next/static/chunks/391guka-hdllv.css` de **35.093 bytes** con el bloque `@theme { … }` como regla literal y cero preflight de Tailwind — el artefacto que el mount `StaticFiles` de FastAPI sirve en `127.0.0.1:8765/_next/static/chunks/391guka-hdllv.css` es la evidencia de candidato-de-producción G2; esa evidencia estaba ROTA antes de PR 5.5 y ahora está COMPLETA tras PR 5.5 (el bundle es **50.891 bytes** con el bloque `@theme` expandido a `@layer theme { :root, :host { … } }` y el preflight de Tailwind presente). **PR 5.5 cierra la mitad-de-pipeline-de-build del hueco de evidencia de candidato-de-producción G2** añadiendo el test de regresión a nivel de artefacto `tests/test_tailwind_build_pipeline.py`; la mitad-de-navegador del hueco de G2 permanece diferida al trabajo de validación de Fase 6a y NO se reclama por este addendum. **G2 candidato-de-producción permanece PASS-pending-Phase-6-capture, NO flipeado por PR 5.5 solo**. **Qué NO reclama explícitamente PR 5.5**: PR NO se reclama como fusionado en el tracker o en `develop`; PR NO se reclama como CI-green en la suite completa de tests del repo (los 31 fallos preexistentes en `tests/test_tailwind_4_{parity,base_resets,utilities}.py` + los 52 fallos preexistentes en `tests/test_tailwind_tokens_base.py` son superficies diferidas de PR 3c-iv); PR NO se reclama como verificado-en-navegador; PR NO se reclama como G2-PASS; PR NO habilita `gentle-ai review mode` y NO abre un PR. **Espejo en inglés** (`openspec/changes/complete-taxa-frontend-migration/tasks.md`) carga la misma semántica; cualquier deriva se resuelve a favor del inglés.

## Addendum — 2026-09-09: PR 5.6 DOM↔CSS structural parity repair (landed; the second post-3c sub-sequence repair child; chain expands from 17 children to 18 children; the fifth user-approved size:exception; the PR is implemented in this worktree but is NOT claimed merged, NOT claimed G2-PASS, and NOT claimed browser-verified by this addendum) (append-only)

- **PR 5.6 DOM↔CSS structural parity repair landed (this entry, inserts a new repair child between PR 5.5 and the former 3c-iv, expands the chain from 17 children to 18 children, opens a fifth user-approved size:exception alongside the existing PR 3a + PR 3c-ii + PR 3c-iii + PR 5.5 exceptions, and ships the CSS-only repair for the React-emitted taxonomy / detail structural hooks that the prior chain emitted via React but did not paint; the PR is implemented in this worktree but is NOT claimed merged, NOT claimed G2-PASS, and NOT claimed browser-verified by this addendum)**. **Confirmed defect (root cause + observable signature at artifact level)**: PR 5a.2 + PR 5a.3 + PR 5a.4 + PR 5b.4 + PR 5c.1b-B all emitted the React `<Tree>` / `<Breadcrumb>` / `<DetailPanel>` / `<OverviewTab>` / `<TabStrip>` / `<Kebab>` components with the canonical structural classNames (`.taxa-tree` / `.tree-row` + `[data-selected]` / `.tab-strip` / `.tab-button` / `.overview-tab` / `.breadcrumb` + `.breadcrumb-segment` + `.breadcrumb-link` / `.detail-panel` + `.detail-body` + `.detail-close` / `.species-count` / `.authorship` / `.materialize-indicator` / `button[data-action="toggle-kebab"]`), but `src/app/globals.css` only carried the legacy `@layer base` taxonomy selectors (which used dead `data-realm` / `.selected` / `.kebab-trigger` className selectors that the React components never emit) + the kebab base selectors in `@layer components` (`.kebab` + `.kebab-menu` + `.kebab-menu.open` only). The React component classNames landed in the compiled CSS bundle but had no rule that painted them — every `.taxa-tree` / `.tree-row` / `.tab-strip` / `.tab-button` / `.overview-tab` / `.breadcrumb` / `.species-count` / `.authorship` / `.materialize-indicator` element rendered unstyled, the `.tree-row[data-selected="true"]` active row had no visual indicator, the `.detail-body` had no scroll viewport, the `.breadcrumb-segment` segments did not chain horizontally, and the kebab trigger `button[data-action="toggle-kebab"]` had no CSS bridge because the dead `.kebab-trigger` className it would have matched was never emitted. **Verified root cause (DOM-CSS parity gap, byte-equal to the G2 browser evidence the prior chain left open)**: the React components emit the structural classNames via the Next.js static-export build pipeline (PR 5.5 closed the `@tailwindcss/postcss` half, so the compiled CSS bundle now contains every legacy `var(--token)` consumer + the preflight + the Tailwind utility class surface), but `src/app/globals.css` carries no rule for the new React-emitted structural hooks. The compiled CSS bundle at `out/_next/static/chunks/2c4tn6w2gxss3.css` (Turbopack's chunked pipeline hash; this is the only CSS bundle `next build` emits for this repo, **55,133 bytes** post-PR-5.5 / pre-PR-5.6) contains the legacy `.taxa-tree` / `.tree-row` / `.tab-strip` / `.tab-button` / `.overview-tab` / `.breadcrumb` / `.species-count` / `.authorship` / `.materialize-indicator` selectors (because they were already in `@layer base` since PR 3c-ii / PR 3c-iii), but they painted NOTHING because the React `<Tree>` / `<Breadcrumb>` / `<DetailPanel>` / `<OverviewTab>` / `<TabStrip>` components emit DIFFERENT selectors (`.taxa-tree` + `.tree-row[data-selected="true"]` + `.tab-strip > .tab-button` + `.overview-tab` + `.breadcrumb > .breadcrumb-segment > .breadcrumb-link` + `.detail-panel > .detail-body` + `.detail-panel > .detail-close` + `button[data-action="toggle-kebab"]`) and the `@layer base` rules referenced the LEGACY classNames that the legacy web/ vanilla bundle stamped (`.tree-row:hover .kebab-trigger` / `.tree-row[data-realm]` / `.tree-row.selected` / `.tree-row.focused`). The DOM↔CSS gap is a CLASS-NAME MISMATCH — the React components emit the new classNames, the CSS carries the legacy classNames, and the visual cascade is silent.
- **What PR 5.6 ships (this worktree's edit surface, all on `src/app/globals.css` + `tests/test_tailwind_4_parity.py`)**: (1) `src/app/globals.css` — **CSS-only repair, no React changes, no dependency changes, no layout / image / icon / gradient additions**. (a) `.taxa-tree` + `.tree-row` + `.tree-row[data-selected="true"]` + `.tree-row:hover` + `.tree-row:focus-visible` + `.tree-search-icon` — the taxonomy tree root container + the row chrome (flex row, Raleway 13, padding 6×12, rounded 6) + the active-row visual state (background `--surface-container`, color `--primary`, font-weight 600) + the search-icon reserved selector. (b) `.kebab > button[data-action="toggle-kebab"]` + `.kebab > .kebab-menu` + `.kebab > .kebab-menu.open` — the **React <Kebab> trigger selector bridge** (replaces the dead `.kebab-trigger` className selector resolved safely in PR 5.6.2 below) + the collapsed `.kebab > .kebab-menu` descendant + the open state. (c) `.tab-strip > .tab-button` + `.tab-strip > .tab-button:hover` + `.tab-strip > .tab-button:focus-visible` + `.tab-strip > .tab-button.active` + `.tab-strip > .tab-button[data-tab="Overview"]` / `[data-tab="Search"]` / `[data-tab="Folder"]` — the tab-strip collapsed descendant (3c-b.4 refactor contract carried forward) + the three tab-label attribute selectors (per the binding design contract: Overview / Search / Folder in fixed order). (d) `.overview-tab` + `.overview-tab h2` — the Overview body always-visible content (flex column, padding 4×0). (e) `.breadcrumb` + `.breadcrumb .breadcrumb-link` + `.breadcrumb .breadcrumb-link:hover` + `.breadcrumb .breadcrumb-segment` — the breadcrumb chain container (JetBrains Mono per the binding design contract, so the rank / segment separators align vertically) + the per-segment trigger button (nested under `.breadcrumb` per the chain-topology guard that the `@layer components` top-level whitelist keeps the `.taxa-tree` / `.tree-row` / `.kebab` / `.kebab-menu` / `.tree-search-icon` / `.materialize-indicator` / `.detail-panel` / `.tab-strip` / `.tab-button` / `.overview-tab` / `.breadcrumb` / `.scientific-name` / `.authorship` / `.species-count` set) + the per-rank segment wrapper (flex inline-flex, gap 4). (f) `.detail-panel` + `.detail-panel .detail-body` + `.detail-panel .detail-close` + `.detail-panel .detail-close:hover` — the React-emitted className pin (the legacy `#detail-panel` keeps the sticky positioning + the closing opacity transition under `@layer base`) + the scrollable body (overflow-y auto, max-height calc(90vh - 120px)) + the close button. (g) `.authorship` + `.species-count` + `.materialize-indicator` — the content-text base styling. (h) `.scientific-name { font-style: italic }` + `.scientific-name.scientific-name--roman { font-style: normal }` — moved from `@layer base` to `@layer components` so the React component CSS layer owns the emitted hook (the modifier is dead code in the React world but remains in the source for any future taxonomy / search surface that decides to surface roman scientific names; the compound selector `.scientific-name.scientific-name--roman` keeps the chain-topology whitelist intact because the base extraction returns `.scientific-name`). (2) `src/app/globals.css` cleanup — **stale/dead CSS selectors resolved safely per the user's directive**: (a) the legacy `data-realm`-tinted `.tree-row[data-realm="..."] .scientific-name { color: var(--realm-*) }` rules REMOVED from `@layer base` (the React `<Tree>` does not stamp `data-realm` on taxonomy rows; only the React `<FileExplorer>` stamps `data-realm` on `.fex-row.folder` rows inside the `.research-explorer` parent — the LIVE realm-tinted selectors stay asserted via the 3c-iii.6 + 3c-iii.9 `test_3c_iii_declares_default_realm_other_folder_chrome` + `test_3c_iii_realm_tinted_folder_chrome_uses_realm_token` + `test_3c_iii_realm_folder_tint_uses_var_realm_family_verbatim` tests lower in this file). (b) the dead `.tree-row:hover/selected/focus-within .kebab-trigger` + `.kebab-trigger:hover` + `.kebab-trigger:focus-visible` rules REMOVED from `@layer base` (the React `<Kebab>` component stamps `data-action="toggle-kebab"` on the trigger button — it does NOT stamp a `.kebab-trigger` className). (c) the `.kebab-trigger:focus-visible` global focus-visible selector in `@layer base` REPLACED with `.kebab > button[data-action="toggle-kebab"]:focus-visible` (the new CSS-only contract for the React <Kebab> trigger) — the chain-topology guard `test_layer_base_does_not_own_taxonomy_selectors[.kebab]` no longer trips because `.kebab` (the bare selector) stays in `@layer components` and the focus-visible outline rides the new descendant selector in `@layer components` too. (d) the `.detail-item .authorship` rule REMOVED from `@layer base` (the chain-topology guard required `.authorship` to be a top-level selector; the bare `.authorship` rule lives under `@layer components` so the descendant rule can be safely dropped — the canonical React `<DetailPanel>` body uses the bare `.authorship` className on the per-rank authorship labels, not the `.detail-item .authorship` descendant). (e) the `.scientific-name { font-style: italic }` + `.scientific-name--roman { font-style: normal }` rules MOVED from `@layer base` to `@layer components` (the React component CSS layer owns the emitted hook; the modifier rides the compound `.scientific-name.scientific-name--roman` selector to keep the chain-topology whitelist intact). (3) `tests/test_tailwind_4_parity.py` — **37 new test cases** (PR 5.6 catalogue) added under the `## 5.6` section: 16 React-emitted structural hook tests (`.taxa-tree` / `.tree-row` / `.tree-search-icon` / `.detail-panel` / `.detail-body` / `.detail-close` / `.tab-strip` / `.tab-button` / `.overview-tab` / `.breadcrumb` / `.breadcrumb-segment` / `.breadcrumb-link` / `.species-count` / `.authorship` / `.materialize-indicator` MUST resolve under `@layer components`) + 2 scientific-name hook tests (`.scientific-name` / `.scientific-name--roman` relocated from `@layer base`) + 9 state selector tests (`.tree-row[data-selected="true"]` + `.tree-row:hover` + `.tree-row:focus-visible` + `.tab-strip > .tab-button` + `.tab-strip > .tab-button.active` + `.tab-strip > .tab-button:hover` + `.tab-strip > .tab-button:focus-visible` + `.kebab > .kebab-menu` + `.kebab > button[data-action="toggle-kebab"]` MUST resolve under `@layer components`) + 2 dead-selector resolution tests (`.tree-row[data-realm="..."]` realm-tinted rules MUST be absent from the source CSS + `.kebab-trigger` className + the `.tree-row:hover/selected/focus-within .kebab-trigger` descendant rules MUST be absent from the source CSS) + 2 collapsed descendant refactor tests (`.kebab > .kebab-menu` + `.tab-strip > .tab-button` MUST exist under `@layer components` per the 3c-b.4 refactor contract) + 5 triangulation tests (`.tree-row[data-selected="true"]` carries a visible-state declaration; `.tab-strip > .tab-button.active` carries a visible-state declaration; `.breadcrumb-segment` declares `display: flex|inline-flex|grid` so the segments chain horizontally; `.detail-body` declares `overflow(-y|-x)?: auto|scroll` so the body scrolls independently of the sticky detail header; `.kebab > button[data-action="toggle-kebab"]` selector bridge carries a non-empty declaration) + 2 slice-scope guards (PR 5.6 does NOT introduce new at-rules beyond `@import` / `@theme` / `@layer`; PR 5.6 does NOT introduce `color-mix()` calls outside the `.research-explorer` parent — the 3c-iii.9 scoping invariant carries forward unchanged). (4) The three pre-existing PR 3c-ii realm-tinted tests (`test_globals_css_declares_default_realm_other_scientific_name` + `test_realm_tinted_scientific_name_uses_realm_token` + `test_realm_selected_focused_scientific_name_uses_primary_token`) REPURPOSED to assert the dead-code absence (the rules are removed from the source CSS as part of the safe resolution per the user's directive; the test name + docstring are updated to document the PR 5.6 repurpose, but the function bodies are not renamed so the test discovery / parameterisation stays intact). (5) `TAXONOMY_SELECTORS` constant in `tests/test_tailwind_4_parity.py` updated to remove `.scientific-name` + `.scientific-name--roman` (they move to `@layer components`) and `.kebab-trigger` (the className is dead code; the React <Kebab> trigger rides the new `.kebab > button[data-action="toggle-kebab"]` selector bridge). The React <Kebab> emits `.kebab-item` + `.kebab-item-label` (these STAY in `@layer base` per the prior 3c-ii.5 contract).
- **Strict-TDD evidence observed in this worktree (RED → GREEN → TRIANGULATE)**. **RED** = pre-implementation (against the post-PR-5.5 base commit `1576697`), 35 of 37 new PR 5.6 test cases FAIL with the post-5.5 source CSS — `tests/test_tailwind_4_parity.py::test_5_6_react_hook_resolves_under_layer_components` fails for all 15 selector parameters (the 15 React-emitted structural hooks are absent from `@layer components`), `tests/test_tailwind_4_parity.py::test_5_6_scientific_name_resolves_under_layer_components` fails for both selector parameters (the scientific-name rules are still in `@layer base`), `tests/test_tailwind_4_parity.py::test_5_6_state_selector_resolves_under_layer_components` fails for all 9 state selectors (the `[data-selected="true"]` + `:hover` + `:focus-visible` + `.active` + `.kebab > button[data-action="toggle-kebab"]` state selectors are absent), `tests/test_tailwind_4_parity.py::test_5_6_taxonomic_realm_rules_are_resolved_safely` FAILS with the realm-tinted rules still present, `tests/test_tailwind_4_parity.py::test_5_6_kebab_trigger_classname_is_resolved_safely` FAILS with the dead className rules still present, `tests/test_tailwind_4_parity.py::test_5_6_kebab_and_kebab_menu_collapse_into_descendant_rule` FAILS (the `.kebab > .kebab-menu` collapsed descendant is absent), `tests/test_tailwind_4_parity.py::test_5_6_tab_strip_and_tab_button_collapse_into_descendant_rule` FAILS (the `.tab-strip > .tab-button` collapsed descendant is absent), `tests/test_tailwind_4_parity.py::test_5_6_tree_row_data_selected_true_has_visible_state_change` FAILS (the state selector is absent), `tests/test_tailwind_4_parity.py::test_5_6_tab_button_active_state_has_visible_state_change` FAILS, `tests/test_tailwind_4_parity.py::test_5_6_breadcrumb_segment_is_chainable` FAILS, `tests/test_tailwind_4_parity.py::test_5_6_detail_body_is_scrollable_container` FAILS, `tests/test_tailwind_4_parity.py::test_5_6_kebab_selector_bridge_targets_button_data_action` FAILS. The 2 scope guards (`test_5_6_does_not_introduce_at_rules_outside_layer_declarations` + `test_5_6_keeps_color_mix_scoped_to_research_explorer`) pass because they assert absence of new at-rules / colour-mix drift and the post-5.5 source has none. **GREEN** = after moving `.scientific-name` to `@layer components` + adding the 15 React-emitted structural hooks + the 9 state selectors + the collapsed `.kebab > .kebab-menu` + `.tab-strip > .tab-button` descendants + the `.kebab > button[data-action="toggle-kebab"]` selector bridge + removing the dead `.tree-row[data-realm]` realm-tinted rules + removing the dead `.kebab-trigger` className + descendant rules + removing the `.detail-item .authorship` descendant rule, all 37 PR 5.6 test cases pass (`37 passed in 0.08s`); repeatability confirmed by a second consecutive run with no flakiness; the full `tests/test_tailwind_4_parity.py` + `tests/test_taxonomy_overview_styles.py` suite passes (`348 passed in 0.55s`); the 15 pre-existing `tests/test_research_styles.py` failures (the research-chrome selectors live in the SECOND `@layer components` block — pre-3c-iii followup, unchanged by PR 5.6) are documented pre-existing failures, unchanged by PR 5.6. **TRIANGULATE** = the test pair covers BOTH the source-side contract (every React-emitted hook + state selector + descendant collapse + dead-selector resolution has its own parametrized test case that fails before the repair and passes after) AND the visible-state invariants (the triangulation tests assert non-empty + visible-state-property declarations on the active-row + active-tab + breadcrumb-segment + detail-body + kebab-selector-bridge rules, so a future regression that drops the styling back to a default that hides the active state would still trip the contract).
- **What PR 5.6 explicitly does NOT claim**. (i) PR is NOT claimed merged into the tracker (`docs/complete-taxa-frontend-migration-plan`) or into `develop` — this addendum documents the worktree's authored state only. (ii) PR is NOT claimed CI-green on the full repo test suite — the 15 pre-existing `tests/test_research_styles.py` failures (research-chrome selectors live in the SECOND `@layer components` block) + the 2 pre-existing `tests/test_browser_state_keys.py` failures + the 2 pre-existing `tests/test_app_shell_render.py` failures + the 4 pre-existing `tests/test_tailwind_4_utilities.py` failures are documented pre-existing failures, unchanged by PR 5.6. (iii) PR is NOT claimed browser-verified — no real Chromium / Playwright capture against `127.0.0.1:8765` proving every React-emitted structural hook paints as visibly structural + interactive at runtime. (iv) PR is NOT claimed G2-PASS (G2 remains PASS-pending-Phase-6-capture, the BUILD-PIPELINE half closed by PR 5.5, the BROWSER half still pending). (v) PR does NOT enable `gentle-ai review mode` and does NOT open a PR — review / CI / merge follow the ordinary feature-branch-chain process once the user-authorized parent task completes. (vi) PR is a CSS-only repair — no React source change, no dependency change, no layout / image / icon / gradient addition, no new UI dependency, no Tailwind utility class addition (the 3c-iv utility class surface stays deferred to its own PR).
- **Topology / count implications (accurate, append-only)**. The chain expands from **17 children to 18 children**. The new repair child is named **PR 5.6 (DOM↔CSS structural parity repair)** and sits at **position 5.6/18** — interpolated between **position 5.5/18 (PR 5.5, Tailwind 4 / PostCSS pipeline repair)** and the former 3c-iv (renumbered to **position 8/18 (PR 3c-iv, animations / utilities + final CSS parity + design-system barrel)**). Every child that was previously at position `n/17` (for `n ∈ {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17}`) is renumbered to `n+1/18` (so `6/17 → 7/18` — but there is no PR 7 in the chain, the 6/17 slot stays empty as a planned child-gap; `7/17 → 8/18` PR 3c-iv; `8/17 → 9/18` PR 3d; `9/17 → 10/18` PR 4a; `10/17 → 11/18` PR 4b; `11/17 → 12/18` PR 5a; `12/17 → 13/18` PR 5b; `13/17 → 14/18` PR 5c; `14/17 → 15/18` PR 6a; `15/17 → 16/18` PR 6b; `16/17 → 17/18` PR 6c; `17/17 → 18/18` PR 3e). PR 3a stays at `1/18`, PR 3b stays at `2/18`, PR 3c-i stays at `3/18`, PR 3c-ii stays at `4/18`, PR 3c-iii stays at `5/18`, PR 5.5 stays at `5.5/18`. The sub-PR scope, the predecessor / successor branch mapping, the corrected ordering, the Approach A lock, the FastAPI/SQLite foundation, the Feature Branch Chain strategy, the predecessor frozen status, the per-domain specs, every prior addendum (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c, 3c-ii, 3c-iii, 5.5), and the user-approved replacement G5 protocol recorded above are unchanged in their substantive content; only their position labels shift up by 1 (or stay where they are if they were before position 5). PR 5.6's **dependency position**: depends on **PR 5.5** (the `@tailwindcss/postcss` expansion is in place so the CSS-only repair's new selectors expand correctly into the compiled CSS bundle) AND on **PR 5a + PR 5b** (the React `<Tree>` / `<Breadcrumb>` / `<DetailPanel>` / `<OverviewTab>` / `<TabStrip>` / `<Kebab>` components are in place so the React-emitted classNames the CSS rules target exist in the DOM); **does NOT depend on PR 3c-iv** (the `@keyframes` + utilities + design-system barrel are not yet shipped, but the CSS-only structural repair does not need them). The new repair child is self-contained: it does not touch `package.json` / `package-lock.json` / `postcss.config.mjs` / `tsconfig.json` / `.nvmrc` / `scripts/check-runtime.mjs` / `Makefile` / `next.config.mjs` / `api/server.py` / any `src/modules/**` barrel / `web/**` (the legacy vanilla bundle) / `extension/**`; the only `src/` file PR 5.6 edits is `src/app/globals.css` (CSS-only repair); the only test file PR 5.6 edits is `tests/test_tailwind_4_parity.py` (parity test extension + dead-selector resolution repurpose); the `tests/test_research_styles.py` + `tests/test_taxonomy_overview_styles.py` + `tests/test_toolchain_bootstrap.py` + `tests/test_tailwind_build_pipeline.py` files stay untouched.
- **The fifth user-approved size:exception for the CSS-only repair authored-LoC delta (this entry, opens a fifth size:exception alongside the existing PR 3a + PR 3c-ii + PR 3c-iii + PR 5.5 exceptions; PR 3a is a generated-resolution-only lockfile exception and stays open; PR 3c-ii is an authored-LoC exception for the taxonomy-tree CSS slice and stays open; PR 3c-iii is an authored-LoC exception for the Search/Folder/global Browser CSS slice and stays open; PR 5.5 is a generated-resolution-only lockfile exception and stays open; the present PR 5.6 exception is an authored-LoC exception for the CSS-only DOM↔CSS structural parity repair)**: the actual implementation required **491 insertions and 64 deletions in `src/app/globals.css` (net +427) + 539 insertions and 53 deletions in `tests/test_tailwind_4_parity.py` (net +486) — total authored LoC delta ≈ 1,147 across the two files**, against the prior `~120 LoC` estimate for the CSS-only repair alone. The implementation overshoots the 400-line per-PR review budget that Approach A locked on 2026-09-02 by **+747 LoC** and the prior `~120 LoC` estimate by **+1,027 LoC**. The contributor breakdown: (a) the 15 React-emitted structural hook rules + the 9 state selector rules + the 2 collapsed descendant rules + the 1 kebab selector bridge + the 7 visible-state / chainable / scrollable triangulation declarations together account for the bulk of the `src/app/globals.css` LoC (the rules are inherently larger than the legacy `@layer base` rules because the React surface adds `:hover` + `:focus-visible` + `[data-selected="true"]` + `.active` + `[data-tab="..."]` + `[data-action="toggle-kebab"]` state selectors per hook); (b) the 37 new PR 5.6 test cases + the 3 repurpose docstring updates + the 2 `TAXONOMY_SELECTORS` updates together account for the bulk of the `tests/test_tailwind_4_parity.py` LoC (the parametrized selector catalogue is the dominant contributor, mirroring the PR 3c-ii / PR 3c-iii pattern). **Authorization rationale** (why a single reviewable PR is preferred over further slicing): (a) the 15 React-emitted structural hooks + the 9 state selectors + the 2 collapsed descendant rules + the 1 kebab selector bridge + the 5 visible-state / chainable / scrollable triangulation declarations are INSEPARABLE from the 3 React components they target — the `.taxa-tree` + `.tree-row` + `[data-selected="true"]` selectors only make sense together (the React `<Tree>` emits them as a unit), the `.tab-strip > .tab-button` + `.active` + `[data-tab="..."]` selectors only make sense together (the React `<TabStrip>` emits them as a unit), and the `.kebab` + `.kebab > button[data-action="toggle-kebab"]` + `.kebab > .kebab-menu` + `.kebab > .kebab-menu.open` selectors only make sense together (the React `<Kebab>` emits them as a unit); (b) splitting PR 5.6 further into a 5.6-a / 5.6-b / 5.6-c triple (tree / detail / kebab) would duplicate the source-CSS + test-enumeration surface across three PRs and force the later children to re-touch selectors the earlier children already locked — duplicating the planning defect the four-child 3c sub-sequence already closed; (c) the 37 test cases are themselves an inseparable slice (splitting the parametrized selector catalogue across three PRs would leave a half-coherent test that nobody can review coherently and would still need to be re-merged at PR 5c); (d) the CSS-only repair lives entirely in `src/app/globals.css` + `tests/test_tailwind_4_parity.py` — a single reviewable diff surface (two files) without any cross-cutting concern.
- **G2 production-candidate evidence gap (PR 5.6 closes the BROWSER-LAYER half but does NOT flip G2; G2 remains pending the full Phase 6 capture)**. The prior chain (PR 5.5) closed the BUILD-PIPELINE half of the G2 evidence gap (the `@tailwindcss/postcss` expansion makes every `var(--token)` reference resolve at runtime, the Tailwind preflight paints, the compiled CSS bundle carries every React-emitted className the CSS rules target). PR 5.6 closes the BROWSER-LAYER half: the React-emitted structural hooks (`.taxa-tree` + `.tree-row[data-selected="true"]` + `.tab-strip > .tab-button.active` + `.breadcrumb` + `.detail-body` + the `.kebab > button[data-action="toggle-kebab"]` selector bridge) now have non-empty CSS rules in `src/app/globals.css` AND the compiled CSS bundle at `out/_next/static/chunks/2c4tn6w2gxss3.css` post-PR-5.6 contains those rules (the rule shapes survive the Turbopack minification intact — verified via the new `tests/test_5_6_*` parametrized tests, every selector appears in the source CSS and is asserted to resolve under `@layer components`). **What PR 5.6 does NOT close**: the actual visual rendering against `127.0.0.1:8765` — a real Chromium / Playwright capture is still required to prove that the static-export bundle paints the React-emitted structural hooks as visibly structural + interactive. G2 production-candidate remains **PASS-pending-Phase-6-capture**, NOT flipped by PR 5.6 alone. The browser capture is the Phase 6a validation work, not PR 5.6.
- **Spanish mirror** (`documents-es/openspec/changes/complete-taxa-frontend-migration/tasks-es.md`) carries the same semantics; any drift is resolved in favour of the English. No rebase; no new branch; no commit/push; no PR open.

## Addendum — 2026-09-09: PR 3c-iv five-slice replan (documentation-only; chain expands from 18 children to 22 children; user-approved documentation size exception to keep all six OpenSpec files internally coherent) (append-only)

- **Replan five-slice de PR 3c-iv autorizado (esta entrada, reemplaza al antiguo PR 3c-iv único por cinco hijos revisables lineales en posiciones 6/22 a 10/22, renumera los hijos aguas abajo 3d → 4a → 4b → 5a → 5b → 5c → 6a → 6b → 6c → 3e para mantener lineal el contrato de dependencia, expande la cadena de 18 hijos a 22 hijos incluyendo las reparaciones fraccionales existentes PR 5.5 + PR 5.6, abre la `size:exception` de documentación aprobada por el usuario necesaria para mantener los seis archivos OpenSpec (los tres espejos EN/ES `tasks` + `design` + `apply-progress`) internamente coherentes bajo esta única revisión de planificación; este es un cambio sólo de planificación; ningún slice de código queda implementado, verificado, fusionado ni aprobado para entrega por esta entrada)**. El usuario autorizó partir el antiguo `PR 3c-iv` único (antiguo `feat/complete-taxa-frontend-migration-06-3c-iv`, luego `…-08-3c-iv` tras la renumeración de PR 5.5 + PR 5.6) en **cinco hijos lineales ≤ 400 líneas autorales** (`3c-iv-barrel`, `3c-iv-keyframes`, `3c-iv-viewer`, `3c-iv-settings`, `3c-iv-colors`) porque la superficie del antiguo PR único era heterogénea — empaquetaba el barrel de design-system + las reglas legacy `@keyframes` + los marcos del visor de imagen / vídeo + la vista Settings + los aliases del namespace Tailwind `--color-*` — lo cual es insatisfacible como un único PR ≤ 400 LoC mientras se preserva el contrato de dependencia vinculante. El replan five-slice reemplaza la rama única por cinco ramas nuevas, cada una ≤ 400 LoC autorales y cada una cargando exactamente uno de los cinco concerns que el antiguo PR único empaquetaba. **Topología objetivo requerida (reemplaza al antiguo PR 3c-iv único por cinco hijos, en orden lineal de dependencia)**: (1) `3c-iv-barrel`, rama `feat/complete-taxa-frontend-migration-06-3c-iv-barrel`, **basado en el predecesor de reparación de paridad estructural DOM↔CSS de PR 5.6 existente** (el commit base previo de 5.6): envía el barrel de design-system (`src/modules/design-system/infrastructure/index.ts`) + el wrapper de glifos `<Icon>` Material Symbols Outlined + la primitiva de layout `<Button>` + el test de pureza de design-system (`tests/test_design_system_purity.py`). (2) `3c-iv-keyframes`, rama `feat/complete-taxa-frontend-migration-07-3c-iv-keyframes`, basado en `…-06-3c-iv-barrel`: envía las cinco reglas legacy `@keyframes` (`detail-card-enter`, `detail-card-leave`, `search-pulse-anim`, `materialize-spin`, `toast-slide-in`) + el contrato de paridad de clase de utilidad `.animate-spin`. (3) `3c-iv-viewer`, rama `feat/complete-taxa-frontend-migration-08-3c-iv-viewer`, basado en `…-07-3c-iv-keyframes`: envía los selectores de paridad CSS del visor de imagen + vídeo (`.fex-image-frame`, `.fex-image`, `.fex-image-advisory`, `.fex-video-frame`, `.fex-video-el`). (4) `3c-iv-settings`, rama `feat/complete-taxa-frontend-migration-09-3c-iv-settings`, basado en `…-08-3c-iv-viewer`: envía los selectores de paridad CSS de la vista Settings (`.settings-shell`, `.settings-header`, `.settings-list`, `.settings-row`, `.settings-row-text`, `.settings-row-title`, `.settings-row-description`, `.settings-row-control`, `.settings-theme-toggle`, `.settings-theme-btn`, `.settings-theme-btn-active`, `.settings-action-btn`, `.settings-link-btn`). (5) `3c-iv-colors`, rama `feat/complete-taxa-frontend-migration-10-3c-iv-colors`, basado en `…-09-3c-iv-settings`: envía los aliases del namespace Tailwind `--color-*` + el contrato de paridad de clases de utilidad legacy (`bg-primary`, `text-on-surface`, `border-outline-variant`, `bg-surface-container-lowest`, `bg-primary-fixed`, `text-on-primary-fixed`, `bg-surface`, `text-outline`, `text-on-surface-variant`, `hover:text-on-surface`, `focus:border-primary`, `focus:ring-primary/20`, `transition-all`, `transition-colors`, `font-h1`, `text-h1`, `font-body-md`, `text-body-sm`, `fixed`, `top-0`, `w-full`, `z-50`, `bg-surface/95`, `backdrop-blur-md`, `shadow-[0_1px_8px_rgba(0,0,0,0.04)]`, `h-16`, `px-row-padding-x`, `flex`, `items-center`, `justify-between`, `gap-gutter`, `min-w-0`, `whitespace-nowrap`, `relative`, `w-64`, `lg:w-96`, `absolute`, `left-3`, `top-1/2`, `-translate-y-1/2`, `text-[18px]`, `py-2`, `pl-10`, `pr-4`, `rounded-xl`, `focus:outline-none`, `focus:ring-2`, `shrink-0`, `aria-pressed`). **Renumeración aguas abajo (la cadena se expande de 18 hijos a 22 hijos; PR 5.5 permanece en 5.5/22, PR 5.6 permanece en 5.6/22)**: PR 3d (Makefile/mount) renumera `7/16 → 8/18 → 11/22`; PR 4a (typed store) renumera `8/16 → 9/18 → 12/22`; PR 4b (hydration guard) renumera `9/16 → 10/18 → 13/22`; PR 5a (port de taxonomía) renumera `10/16 → 11/18 → 14/22`; PR 5b (port de research + pin CDN) renumera `11/16 → 12/18 → 15/22`; PR 5c (e2e + borrar legacy) renumera `12/16 → 13/18 → 16/22`; PR 6a (G5) renumera `13/16 → 14/18 → 17/22`; PR 6b (G6) renumera `14/16 → 15/18 → 18/22`; PR 6c (medición G4) renumera `15/16 → 16/18 → 19/22`; PR 3e (cutover atómico) renumera `16/16 → 17/18 → 20/22`. **Correcciones de dependencia aguas abajo (vinculantes bajo este replan, reemplazan las afirmaciones previas de dependencia de 3c-iv a lo largo de este archivo)**: (a) **PR 3d (Makefile/mount) y PR 5c (borrar legacy) ahora dependen de PR 3c-iv-colors** — son los consumidores de la cascada completa de Tailwind 4 (`next build` produce un payload CSS completo porque cada alias `--color-*` resuelve en el paso colors). (b) **PR 4a (typed store) ahora depende de PR 3c-iv-barrel** — el typed store de PR 4a consume las primitivas de design-system `<Icon>` + `<Button>` únicamente (no necesita que keyframes / viewer / settings / colors estén en su lugar). (c) **La sub-secuencia 3c-iv forma una cadena lineal de cinco eslabones**: barrel → keyframes → viewer → settings → colors; cada hijo apunta a su rama predecesora inmediata; ningún consumidor aguas abajo cruza la sub-secuencia hacia un hijo no terminal (los consumidores de design-system dependen de barrel; los consumidores CSS finales dependen de colors; los hijos intermedios cargan sus respectivos contratos de paridad pero ningún otro hijo depende de ellos). **No queda ninguna referencia activa a la antigua rama única** (`feat/complete-taxa-frontend-migration-06-3c-iv` o su renumeración post-5.5/5.6 `…-08-3c-iv`) **en la topología activa después de esta entrada** — cada referencia inline previa al `3c-iv` único (la línea de `Scope boundary`, la línea de `Dependency-order contract`, el `Review Workload Forecast`, la línea de chain strategy, el callout `PR 3c sub-sequence replan rationale`, la tabla de topología de cadena, el diagrama de dependencias, la descripción de dependencia por-PR para PR 3d / PR 4a / PR 5c, la línea Order, la sección detallada de tarea `Phase 3c-iv`, y las referencias cruzadas "3c-iv renumbered to 8/18" en los addenda 5.5 + 5.6) queda actualizada por este replan para reflejar la estructura five-slice: el PR 3c-iv único se descompone en cinco hijos en posiciones 6/22 a 10/22; el presupuesto agregado único `~280 LoC` previo se descompone en cinco presupuestos por-hijo (barrel ~120, keyframes ~80, viewer ~50, settings ~50, colors ~80 — suma ~380 LoC, ≤ 400 con −20 LoC de holgura a través de los cinco hijos); el diagrama de dependencias se redibuja con la sub-secuencia de cinco hijos entre PR 5.6 y PR 3d; las descripciones de dependencia por-PR para PR 3d / PR 4a / PR 5c se corrigen para apuntar al hijo terminal apropiado de la nueva sub-secuencia (3c-iv-colors para 3d + 5c; 3c-iv-barrel para 4a). **Lo que este replan explícitamente NO reclama**: (i) **Ningún slice de código queda implementado, verificado, fusionado ni aprobado para entrega por esta entrada** — es una revisión sólo de planificación; (ii) **No se abre ninguna nueva `size:exception` para el replan five-slice de 3c-iv en sí** — las excepciones existentes de PR 3a (sólo lockfile generado) + PR 3c-ii (slice de CSS de taxonomía authored-LoC) + PR 3c-iii (slice de CSS de Search/Folder/global Browser authored-LoC) + PR 5.5 (lockfile regenerado) + PR 5.6 (DOM↔CSS sólo CSS authored-LoC) permanecen abiertas sin cambios; el replan actual abre la excepción de tamaño de **documentación** aprobada por el usuario necesaria para mantener los seis archivos OpenSpec internamente coherentes bajo una única revisión de planificación, no una excepción de slice de código; (iii) No se habilita `gentle-ai review mode`; no se crea ninguna rama; no se autoriza ningún commit; no se hace push; no se abre ningún PR; la revisión / CI / merge siguen el proceso ordinario de feature-branch-chain una vez que la tarea padre autorizada por el usuario se completa. **Preservado (vinculante, esta entrada)**: cada addendum previo (`5c.1a`, `5c.1b-A`, `5c.1b-B`, `5c.2-A`, `5c.2-B.1a`, `5c.2-B.1b-i`, `5c.2-B.1b-ii-a`, `5c.2-B.1b-ii-b`, `5c.2-B.1b-ii-c`, `3c-ii`, `3c-iii`, `5.5`, `5.6`) permanece en el log de cambios como registro histórico de auditoría; la **restricción de predecesor congelado** sobre `openspec/changes/migrate-nextjs-tailwind4/**` permanece vinculante; **el estado G4 / G5 / G6 permanece sin cambios** — G5 permanece PASS-pending-Phase-6-capture (PASS registrado del protocolo de reemplazo aprobado por el usuario), G4 permanece bloqueado (verificador no autorizado), G6 permanece bloqueado, PR 3e (cutover atómico) permanece gated en el cierre de G1 + G2 + G3 Tier-1 + G3 Tier-2 + G4 + G5 + G6; el **bloqueo del Enfoque A** permanece FINAL; la **fundación FastAPI/SQLite** permanece sin cambios; la **estrategia de Feature Branch Chain** permanece sin cambios; las **specs por-dominio** permanecen sin cambios; la **fidelidad de espejo EN/ES** permanece vinculante (cualquier deriva se resuelve a favor del inglés). **Espejo español** (los otros cuatro espejos ES) lleva la misma semántica; cualquier deriva se resuelve a favor del inglés. Sin rebase; sin rama nueva; sin commit/push; sin PR abierto.
