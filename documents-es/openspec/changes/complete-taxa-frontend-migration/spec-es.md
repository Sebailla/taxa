# Spec: complete-taxa-frontend-migration

> Sucesor de `migrate-nextjs-tailwind4` (congelado como historial
> de planificación). La propuesta, los artefactos del predecesor
> (`proposal.md`, `design.md`, `apply-progress.md`,
> `cutover-manifest.json`, `specs/modular-architecture/spec.md`)
> y el `openspec/specs/research/spec.md` canónico son el
> contexto aguas arriba. Este spec **no** rederiva la evidencia
> que el predecesor ya produjo.

## TL;DR

- **La Aproximación A es FINAL** (decisión del usuario,
  2026-09-02). Exportación estática de Next.js 16 + React 19 +
  Tailwind 4 (`out/`) servida por el montaje `StaticFiles`
  existente de FastAPI en `127.0.0.1:8765`. Origen único, puerto
  único. Sin SSR, sin route handlers, sin server components. Sin
  segundo puerto de servidor de desarrollo. `host_permissions` de
  la extensión sin cambios.
- **Unidad de cutover atómica** (PR3e en el vocabulario del
  predecesor, re-rebanado bajo la Aproximación A): una sola
  unidad de release cambia la constante `WEB_DIR`, cada
  consumidor activo en `design.md::§3.1` del predecesor, el
  pipeline de build `make api` y el artefacto de build `out/`
  juntos. **No se soporta revertir un subconjunto.**
- **Unidad de rollback**: `git revert <cutover-sha>` restaura el
  build vanilla legacy atómicamente con humo + Playwright en
  verde. No se envía ningún cambio de esquema de BD en este
  cambio, por lo que no se requiere ninguna migración de datos.
- **El backend es innegociable**: FastAPI + SQLite (WAL);
  `/api/*` byte-idéntico; defensa SSRF en `save-url`; pipeline
  ETL; `extension/manifest.json::host_permissions` permanece en
  `["http://localhost:8765/*"]`.
- **Puertas de evidencia trasladadas literalmente**:
  - G1 (origen único) — **PASS registrado**.
  - G2 (build fundacional) — **PASS registrado** contra el build
    limpio verificado de Next.js 16.3.3 / Turbopack.
  - G3 Tier-1 (consumer readiness, legacy pre-cut) — **PASS
    registrado** (los 26 consumidores §3.1 en verde vía el
    fixture controlado, `scripts/verify_consumers.py`).
  - G3 Tier-2 (selección de cut atómico) — **NO PASSED**;
    requiere cierre de G2 + G4 + G5 + G6.
  - G4 (paridad Playwright + Lighthouse) — **bloqueado —
    verificador no autorizado**; debe cerrarse en la fase de
    apply.
  - G5 (línea base de hidratación) — **no reproducible — la
    línea base legacy no está en disco**; debe reconstruirse o
    reemplazarse durante la fase de apply.
  - G6 (ensayo de cutover) — **bloqueado — verificador no
    autorizado**; debe cerrarse en la fase de apply.
- **Predecesor congelado**: `openspec/changes/migrate-nextjs-tailwind4/**`
  es byte-idéntico antes y después de la fase de apply de este
  cambio. CI / branch-protection rechaza cualquier PR que lo
  modifique.

## Aproximación A — final

La propuesta documentó la Aproximación A como el default
bloqueado por evidencia con una ruta explícita de anulación
(citar los números G2 + G5 desde el `apply-progress.md` del
predecesor, registrar la anulación en `design.md::§1`). El
**2026-09-02** el usuario bloqueó la Aproximación A como
selección final. B y C no están bajo consideración. La evidencia
que apoya el bloqueo es la misma evidencia que el predecesor ya
produjo:

| Puerta | Estado | Por qué A se apoya |
| --- | --- | --- |
| G1 (origen único) | PASS registrado | A cumple G1 trivialmente; sin segundo puerto, sin segundo contenedor. |
| G2 (build fundacional) | PASS registrado | El build limpio de Next 16.3.3 / Turbopack produjo `BUILD-INVENTORY.json` con todas las clases de rutas de aplicación requeridas (único `out/index.html`, JS + CSS bajo `out/_next/static/chunks/**`, `build-manifest.json` copiado, `app-build-manifest.json` opcional registrado como `not_emitted`) más la clasificación de `out/404.html` como página de error. |
| G3 Tier-1 (consumer readiness, legacy pre-cut) | PASS registrado | Los 26 consumidores §3.1 en verde contra el runtime legacy pre-cut vía el fixture controlado y `scripts/verify_consumers.py` (PR #109 + PR #111 + PR #115 + PR #116). |
| G4 (paridad Playwright + Lighthouse) | Bloqueado — verificador no autorizado | Debe cerrarse en la fase de apply. |
| G5 (línea base de hidratación) | No reproducible — línea base legacy no en disco | Debe reconstruirse o reemplazarse por un equivalente durante la fase de apply. |
| G6 (ensayo de cutover) | Bloqueado — verificador no autorizado | Debe cerrarse en la fase de apply. |

El cutover está bloqueado por **G1 PASS + G2 PASS + G3 Tier-1
PASS** más **cierre de G4 + G5 + G6** antes de que la release
atómica se envíe. La fase de apply posee G4 / G5 / G6; la fase
de design registra la decisión final (A, sin anulación) en
`design.md::§1` (final, no diferida).

## Alcance

### Dentro del alcance

- Migración total del frontend a Next.js 16 + React 19 + Tailwind
  4, reemplazando la app vanilla-JS en disco de `web/` bajo la
  Aproximación A.
- Un único frontend en producción. El build legacy de pre-corte
  paralelo se retira al activar — sin estado de doble build en la
  fase de apply de este cambio.
- Origen FastAPI preservado en `127.0.0.1:8765`. Se permiten
  ediciones mínimas de `api/server.py` solo para el repoint de
  `WEB_DIR` y cualquier middleware estrictamente necesario para
  montar la nueva salida del frontend. Los handlers de ruta no
  se reescriben.
- Test de contrato AC-21 de motores de búsqueda preservado
  (`web/search_urls.js` puede moverse bajo `src/data/`; forma
  byte a byte preservada salvo revisión explícita de esta fase
  spec — no la revisa).
- Estado local del navegador (`theme`, `tree-source`,
  `last-taxon-id`, `kebab-open-id`) migrado de forma
  determinista a un store tipado con un sitio de lectura + un
  sitio de escritura por clave.
- Restricciones de arquitectura modular desde
  `specs/modular-architecture/spec.md` del predecesor se aplican
  sin cambios.

### Fuera del alcance

- Reescritura del backend: handlers de ruta de `api/server.py`,
  lógica SQLite/WAL, flujo de materialización, defensa SSRF en
  `save-url`.
- Pipeline ETL: `etl/parse_textree`, `etl/load_coldp`,
  `etl/load_worms`, `etl/load_freshwater`, migraciones.
- Trabajo de paridad de la extensión de Chrome — un cambio
  aparte rastrea cualquier adaptación de la extensión consciente
  de React.
- Trabajo de SEO / metadata / sitemap / robots.
- Nuevas rutas (Settings, About, Help) más allá de lo que la UI
  legacy expone hoy.
- Herramientas de cobertura (`coverage.available: false` es el
  estado actual).
- Rediseño visual (impeccable / seguimiento de Stitch, no es
  bloqueante).
- Editar o "completar" el directorio de cambios del predecesor.
  El predecesor está **congelado**, no finalizado.
- Reejecutar las sondas G2 / G4 / G5 / G6 del predecesor — sus
  salidas se importan tal cual.

## Contrato del backend (innegociable)

Cualquier cambio que viole una fila de esta tabla queda fuera
del alcance y debe plantearse en un cambio aparte.

| Superficie | Restricción | Fuente |
| --- | --- | --- |
| Origen | Solo `http://127.0.0.1:8765` | G1 (origen único) |
| Puerto | Solo 8765; sin segundo puerto de servidor de desarrollo | G1 |
| Formas de `/api/*` | Byte-idénticas al FastAPI actual | Regla de equivalencia funcional |
| `host_permissions` de la extensión | `["http://localhost:8765/*"]` sin cambios | Regla de continuidad |
| Modo SQLite | WAL; conexiones API de solo lectura | Convención del repo (`openspec/sdd-init.md`) |
| Pipeline ETL | Sin cambios en este cambio | Fuera del alcance del predecesor |
| Flujo de materialización, defensa SSRF en `save-url` | Sin cambios en este cambio | Fuera del alcance del predecesor |

## Specs por dominio

Los specs por dominio son el contrato canónico; este `spec.md`
es la vista ejecutiva sintetizada.

- `specs/frontend-runtime/spec.md` — App de pantalla única
  exportada estáticamente por Next.js bajo el montaje
  `StaticFiles` de FastAPI; superficie UI completa + paridad +
  rendimiento + accesibilidad.
- `specs/design-tokens/spec.md` — Bloque `@theme` de Tailwind 4 +
  variables CSS preservados desde el `<style>` inline legacy y
  `tailwind.config.js`; test de paridad de tokens.
- `specs/browser-state-hydration/spec.md` — Store tipado con
  cuatro claves `localStorage`, un sitio de lectura + un sitio
  de escritura por clave, guardia de hidratación.
- `specs/frontend-bootstrap/spec.md` — Repoint de `WEB_DIR`,
  contrato de montaje único, pipeline de build `make api`,
  verificación de versión de runtime, unidad de cutover atómico
  + rollback.
- `specs/research/spec.md` — **delta** contra el canónico
  `openspec/specs/research/spec.md`. Captura el contrato de
  migración sin cambiar las formas de request/response ni la
  paridad byte a byte de AC-21.
- **No se autoriza spec** para `modular-architecture`. El spec
  canónico vive bajo
  `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
  (congelado). El sucesor hereda las reglas 1–7 sin cambios
  según la propuesta §Capacidades §"Capacidades sin cambios
  (importadas del predecesor)".

## Criterios de éxito

Los specs por dominio enumeran los escenarios testeables. La
lista de abajo es el resumen ejecutivo; los specs por dominio
son autoritativos.

### Paridad funcional

- [ ] **Flujo de navegación** — dominio → sub-árbol → fila de
  especie; el breadcrumb se actualiza; el panel de detalle
  carga; la URL refleja `<root>/<taxon>` según la forma legacy.
- [ ] **Flujo de búsqueda** — el modal de búsqueda del header
  dispara `GET /api/search?q=<q>`; los resultados de las tres
  fuentes (`col`, `worms`, `freshwater`) aparecen en la
  agrupación legacy de resultados.
- [ ] **Flujo de materialización** —
  `POST /api/taxon/{id}/materialize`; el callback del modal
  incorpora los ids devueltos en `state.materialized`; el
  indicador por fila se vuelve verde saturado para los nuevos
  ids y sus descendientes visibles.
- [ ] **Flujo Save URL** — la extensión hace POST a
  `/api/taxon/{id}/save-url`; la defensa SSRF queda sin
  cambios; la capa de rendering de React refresca sin cambios
  de código en la extensión.
- [ ] **Visor de ficheros** — cada formato soportado despacha al
  renderer legacy correspondiente (PDF, HTML, TXT, MD, DOCX,
  XLS, XLSX, EPUB) con el meta strip
  `FORMAT | SIZE | ENCODING`. DOC legacy y formatos no
  soportados muestran el fallback de descarga.
- [ ] **Fallo de CDN** — el visor renderiza el banner
  `"Viewer offline — raw download unavailable"` y mantiene el
  árbol interactivo.
- [ ] **Búsqueda en el árbol** — debounce de 200 ms, modos
  filter / highlight, `state.explorer.search.{query, mode,
  hideEmpty}` persistido.
- [ ] **Cambiar de taxón limpia el estado del explorer** —
  `state.explorer.{rootTaxonId, tree, openFilePath,
  openFileFormat, viewerTab}` se resetea; al reabrir Browser se
  vuelve a disparar `GET /api/taxon/{B}/files`.

### Rendimiento

- [ ] **≤ 0 % de regresión** en initial paint sobre el fixture
  chromium que capturó el predecesor.
- [ ] **≤ 0 % de regresión** en latencia de interacción.
- [ ] **≤ 0 % de regresión** en `out/BUILD-INVENTORY.json`
  (`chunks`, `total_bytes`, `per_route_bytes`) frente a la
  línea base de evidencia legacy, sin exención documentada.

### Origen único

- [ ] **`make api` solo enlaza el 8765**; sin segundo listener.
- [ ] **`extension/manifest.json::host_permissions`** permanece
  en `["http://localhost:8765/*"]`.
- [ ] **`content_scripts.matches`** permanece en
  `["http://localhost:8765/*"]`.

### Backend

- [ ] **Línea base 63 passed, 8 skipped** preservada
  (`make test` contra el `.venv`).
- [ ] **`make smoke`** pasa (API en vivo en
  `127.0.0.1:8765`).

### Contrato AC-21

- [ ] **`tests/test_smoke.py::test_search_engine_contract`**
  pasa. Si el literal se movió a `src/data/search-engines.js`,
  la ruta `open()` del test se actualiza en la misma release;
  la forma byte a byte (key, label, with_authorship, ordering)
  queda sin cambios; `api/server.py::_SEARCH_ENGINES` queda sin
  cambios.

### Hidratación del estado del navegador

- [ ] **`theme`, `tree-source`, `last-taxon-id`, `kebab-open-id`**
  tienen exactamente un sitio de lectura + un sitio de
  escritura dentro de `src/modules/browser-state/`.
- [ ] **Sin advertencia de hidratación** en la consola del
  navegador tras el ciclo de primer pintado + rehidratación.
- [ ] **Excepciones de `localStorage`** (modo privado, cuota
  excedida) se tragan; se devuelve el default tipado.

### Paridad de Tailwind 4

- [ ] **Cada token `:root`** resuelve a una declaración no
  vacía en `globals.css`.
- [ ] **Cada referencia `var(--name)`** en el CSS ad hoc legacy
  resuelve.
- [ ] **Cada clase utility** que el build legacy emite resuelve
  a una declaración CSS no vacía en el nuevo build.

### Accesibilidad

- [ ] **Cada rol ARIA, etiqueta y handler de teclado** del
  build legacy se preserva.
- [ ] **El escaneo de axe** no reporta nuevas violaciones
  `serious` / `critical` frente a la línea base legacy.

### Predecesor congelado

- [ ] **`openspec/changes/migrate-nextjs-tailwind4/**`** es
  byte-idéntico antes y después de la fase de apply de este
  cambio.
- [ ] **CI / branch-protection** rechaza cualquier PR que
  modifique el directorio del predecesor.

### Rollback

- [ ] **`git revert <cutover-sha>`** restaura el build vanilla
  legacy atómicamente.
- [ ] **`make smoke`** vuelve a la línea base previa a la
  migración (63 passed, 8 skipped).
- [ ] **No se requiere migración de datos** para revertir.

## Puertas de validación

Cada puerta tiene un productor nombrado, un comando de
invocación, una ruta de artefacto y un umbral de aceptación. La
fase de apply posee el cierre de G4 / G5 / G6; la fase de spec
registra el estado trasladado literalmente.

| Puerta | Productor | Comando | Artefacto | Umbral | Estado (trasladado) |
| --- | --- | --- | --- | --- | --- |
| G1 (origen único) | predecesor `design.md::§1` | n/a (decisión de frontera) | bloque `design.md::§1` | Invariantes de origen único FastAPI registrados; `/api/*` + manifest de la extensión sin cambios. | **PASS registrado** |
| G2 (build fundacional) | `scripts/verify_build.py` | `python scripts/verify_build.py --out <build-root> --node-min 20.9.0` | `<build-root>/BUILD-INVENTORY.json` | Build sale 0; el inventario lista cada clase de activo requerida; Node ≥ 20.9.0; sin clases ausentes; `build-manifest.json` requerido copiado atómicamente; `app-build-manifest.json` opcional registrado como `staged` o `not_emitted`; exenciones de página de error clasificadas por separado. | **PASS registrado** |
| G3 Tier-1 (consumer readiness, legacy pre-cut) | `scripts/verify_consumers.py` | `python scripts/verify_consumers.py --manifest … --out <build-root> --serve --venv <repo-root>/.venv/bin/python --fixture-web-root <repo-root>/tools/g3-legacy-fixture/web --repo-root <repo-root>` | `<build-root>/CONSUMER-READINESS.json` | El verificador sale 0; cada consumidor §3.1 PASS; `manifest_sha256` estable; `activation_complete = true`; `unselected_count = 0`; expectativas de forma HTTP enrutadas vía `tools/g3-legacy-fixture/scripts/check_http_status.py` (PR #115); symlinks del venv preservados (PR #116). | **PASS registrado** |
| G3 Tier-2 (selección de cut atómico) | mismo verificador, pasada de cut atómico | mismo | mismo | Igual que Tier-1 más el volteo de los consumidores §3.1 de `selected` (legacy pre-cut) al registro de activación post-cut. | **NO PASSED** — bloqueado por G4 + G5 + G6 |
| G4 (paridad Playwright + Lighthouse) | `tests/test_e2e_file_explorer.py`, `tests/test_web_toggle.py`, harness Playwright + Lighthouse | `.venv/bin/python3 -m pytest tests/ -v` + ejecución de Playwright + Lighthouse | `tests/test_web_toggle.py`, trace de Playwright, JSON de Lighthouse | Cada escenario legacy pasa contra el nuevo árbol de componentes; Δ ≤ 0 % en initial paint y latencia de interacción. | **bloqueado — verificador no autorizado** |
| G5 (línea base de hidratación) | `scripts/measure_hydration.py` | `python scripts/measure_hydration.py --baseline <path>` | JSON de línea base de hidratación | Δ ≤ 0 % frente a la línea base legacy; línea base legacy reproducible. | **no reproducible — línea base legacy no en disco** |
| G6 (ensayo de cutover) | `scripts/rehearse_cutover.py` | `python scripts/rehearse_cutover.py --manifest …` | `cutover-rehearsal.json` | El ensayo sale 0; sin rutas de fallback silencioso; unidad de cutover atómico + unidad de rollback consistentes. | **bloqueado — verificador no autorizado** |

La unidad de cutover se envía **solo** cuando G1 + G2 + G3
Tier-1 PASS más cierre de G4 + G5 + G6 estén todos en disco. La
evidencia ausente, fallida, obsoleta (> 7 días) o incomparable
está **bloqueada**, nunca es éxito.

## Unidad de cutover atómico

La unidad de cutover atómico (equivalente a PR3e, re-rebanada
bajo la Aproximación A) cambia **exactamente lo siguiente** en
una sola release:

1. **Constante `WEB_DIR`** en `api/server.py:54` (repoint a
   `out/`).
2. **Cada actualización de consumidor activo** enumerada en
   `design.md::§3.1` del predecesor (imports, la ruta lectora de
   AC-21, cada consumidor de test). Los 21 consumidores del web
   mount y los 5 consumidores de `web/search_urls.js` están
   nombrados literalmente en el `cutover-manifest.json` del
   predecesor.
3. **Los targets `Makefile::api` y `Makefile::web`.**
4. **El artefacto de build** — el propio directorio `out/`
   (`out/index.html`, `out/_next/static/chunks/**`,
   `out/.next/build-manifest.json`, la clasificación de página
   de error si se emiten `404.html` / `500.html`).

**No se soporta revertir un subconjunto.** Las reversiones
parciales dejan a los consumidores referenciando rutas borradas
y rompen el shell de la SPA o el test de contrato AC-21.

## Unidad de rollback

La unidad de rollback es **`git revert <cutover-sha>`**. Restaura
**los cuatro conjuntos** juntos:

- `web/index.html`, `web/app.js`, los 18 módulos `web/*.js`,
  `web/dist/tailwind.css`, `tailwind.config.js`.
- El `package.json` + `package-lock.json` legacy; `npm ci`
  reproduce el lock.
- `api/server.py:54` revierte a
  `WEB_DIR = Path(__file__).parent.parent / "web"`.
- `Makefile::api` revierte a invocar `make css` antes de
  uvicorn.

Tras la reversión:

- `make api` regenera `web/dist/tailwind.css` desde la fuente
  revertida.
- `make smoke` vuelve a la línea base previa a la migración
  (63 passed, 8 skipped).
- `curl http://127.0.0.1:8765/index.html` devuelve el shell
  vanilla.
- `extension/manifest.json` queda sin cambios durante el
  cutover y el rollback (no se requiere actualizar el manifest
  para revertir).
- No se envía ningún cambio de esquema de BD, por lo que no se
  requiere ninguna migración de datos para revertir.
- `openspec/changes/migrate-nextjs-tailwind4/**` queda byte-
  idéntico durante el cutover y el rollback — el predecesor
  está congelado.

## Reutilización de evidencia

Este spec **no** rederiva la evidencia del predecesor. Los
siguientes artefactos se importan como historial de planificación:

- `openspec/changes/migrate-nextjs-tailwind4/proposal.md`
- `openspec/changes/migrate-nextjs-tailwind4/design.md` (incl.
  `§1` decisión de frontera, `§3.1` inventario de consumidores
  activos, `§3.3.2.1` contrato G2, `§3.3.3` / `§3.3.3.1`
  contrato G3, `§3.3.5` disposición G5)
- `openspec/changes/migrate-nextjs-tailwind4/apply-progress.md`
  (incl. el change log que registra G2 PASS, G3 Tier-1 PASS,
  G5 no reproducible)
- `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
- `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
- `openspec/specs/research/spec.md` (canónico; preservado sin
  cambios; el delta vive en `specs/research/spec.md` de este
  cambio)

## Siguiente paso

La **fase de design** registra la decisión final del enfoque
(ya bloqueada en A, sin anulación) en
`openspec/changes/complete-taxa-frontend-migration/design.md::§1`
(final, no diferida), rebana las 35 tareas del predecesor bajo
la Aproximación A dentro del presupuesto de revisión de 400
líneas por sub-PR y produce las listas de ficheros por tarea que
el worker de apply sigue en `tasks.md`. La **fase de apply**
posee el cierre de G4 / G5 / G6 antes de que el cutover atómico
aterrice. La **fase de archive** copia cada spec por dominio
literalmente a
`openspec/specs/{frontend-runtime,design-tokens,browser-state-hydration,frontend-bootstrap,research}/spec.md`
y promueve el spec modular-architecture al árbol de specs
canónicos.