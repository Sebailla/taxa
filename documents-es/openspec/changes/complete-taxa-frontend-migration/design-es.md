# Diseño: complete-taxa-frontend-migration

> Sucesor de `migrate-nextjs-tailwind4` (congelado como historial de
> planificación bajo `openspec/changes/migrate-nextjs-tailwind4/**`).
> Este diseño registra la arquitectura **final** para el cutover a
> React y el cierre planificado de G4 / G5 / G6. La fase spec ya
> bloqueó la Aproximación A el **2026-09-02**; este diseño es la
> referencia arquitectónica para la fase de apply.

## TL;DR

| Pregunta | Respuesta |
| --- | --- |
| Aproximación | **A — FINAL.** `next build` → `out/` servido por el montaje `StaticFiles` de FastAPI en `127.0.0.1:8765`. |
| Origen | FastAPI origen único; **sin** segundo puerto de dev-server. |
| Unidad de cutover | **Atómica.** `WEB_DIR` + 26 consumidores §3.1 + `Makefile::api` + `out/` cambian en un solo release. No se permite revertir un subconjunto. |
| Unidad de rollback | **`git revert <cutover-sha>`**. Restaura el build vanilla legacy atómicamente. No se requiere migración de BD. |
| Puertas de evidencia | **G1, G2, G3 Tier-1 PASS** (trasladadas del predecesor). **G4, G5, G6** se cierran en la fase de apply; este diseño planifica su cierre. |
| Predecesor | **Congelado.** `openspec/changes/migrate-nextjs-tailwind4/**` es byte-idéntico antes y después de la fase de apply. |

---

## §1 Decisión de Aproximación — FINAL

**La Aproximación A es la arquitectura elegida.** Registrada el
**2026-09-02** (bloqueada por el usuario). La Aproximación B
(dev-server completo de Next.js en un segundo puerto) y la
Aproximación C (híbrido por fases) están rechazadas. La autoridad
arquitectónica es `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
regla 7 (requisito de cita de retorno).

| Invariante | Implementación bajo A | Fuente |
| --- | --- | --- |
| Origen único | `127.0.0.1:8765`; FastAPI enlaza vía `uvicorn.run(app, host="127.0.0.1", port=8765, …)` | Final de `api/server.py` |
| Único dueño de HTML | El `app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")` de FastAPI sirve `out/index.html` y el fallback SPA | `api/server.py:1815` |
| Único dueño de assets estáticos | El mismo montaje `StaticFiles` sirve `out/_next/static/**` | `api/server.py:1815` |
| `WEB_DIR` | `WEB_DIR = Path(__file__).parent.parent / "out"` (antes `…/"web"`) | `api/server.py:54` |
| `host_permissions` de la extensión | `["http://localhost:8765/*"]` — **sin cambios** | `extension/manifest.json:13–15` |
| `content_scripts.matches` de la extensión | `["http://localhost:8765/*"]` — **sin cambios** | `extension/manifest.json:21` |
| Formas de `/api/*` | Byte-idénticas al FastAPI actual | Regla de equivalencia funcional |
| Artefacto de build | `out/` producido por `next build`; contrato G2 verificado en limpio (Next 16.3.3 / Turbopack) | Predecesor `design.md::§3.3.2.1` |

### Por qué A (y no B o C)

A honra G1 (origen único) trivialmente; B rompe G1 al abrir un
segundo puerto; C preserva G1 mediante despliegue por fases pero
añade superficie de revisión y un estado de doble-build en dos
ventanas que el spec rechaza explícitamente. El cambio de edición
única a `WEB_DIR` es la ruta de radio de explosión mínimo; la firma
del montaje permanece byte-idéntica; el bind de uvicorn permanece
byte-idéntico; ningún cambio al manifest de la extensión.

### Lo que A sacrifica (aceptable)

- Rutas dinámicas / optimización de imágenes (aceptable para v1;
  cambiar al dev-server completo de Next.js es un cambio separado
  si se necesita).
- Route handlers del lado del servidor / server components (no se
  requieren; la UI de Taxa es una app cliente de pantalla única).

---

## Fronteras de módulos

El monolito modular (5 módulos × 4 capas) fue establecido por el
predecesor PR 2a (origin/develop #78). Este cambio **no re-andamia**
el layout; puebla las capas que los PRs 3 / 4 / 5 del predecesor
dejaron como placeholders `.gitkeep`. El spec modular-architecture
(reglas 1–7) aplica sin cambios; el spec del predecesor está
congelado.

### Propiedad de módulos bajo A

| Módulo | Domain | Application | Infrastructure | Presentation |
| --- | --- | --- | --- | --- |
| `taxonomy` | Tipos `Taxon` + invariantes | `useTaxonTree()`, `useTaxonDetail()`, walker de cadena de padres | `fetchTaxon`, `fetchChildren`, `fetchDomains` | `Tree`, `DetailPanel`, `Breadcrumb`, `DomainList` |
| `research` | Tipos `ResearchFile`, `Engine`, `FileNode` | `useFileExplorer()`, `useFileViewer()`, despachador de formatos | `fetchFiles`, `fetchServe`, `loadScriptOnce` (cargador perezoso CDN), `search-engines.js` | `FileExplorer`, `FileViewer`, `RawTableTreeTabs`, `MetaStrip`, `BreadcrumbPanel`, `Banners` |
| `design-system` | Tokens de tema (tipados) | — | `globals.css` (bloque `@theme` + `@layer base`), wire-up de `next/font` | `<Icon>`, `<Button>`, primitivas de layout |
| `browser-state` | Tipos `LocalStorageKey`, defaults tipados, tipo de subscriber | — | `store.ts` (4 claves × {read, write}), adaptador `useSyncExternalStore` | — |
| `app-shell` | — | Composición host `AppShell`, estado del shell de ruta | `src/app/page.tsx`, `src/app/layout.tsx`, `next.config.mjs` | `AppShell`, `<Header>`, `<Tabs>`, `<HelpShell>`, `<SettingsView>`, `<BannerHost>` |

### Contrato de importación entre módulos (vinculante)

- El barrel público (`src/modules/<capability>/index.ts`) es el único
  punto de acceso entre módulos legal. El predecesor PR 2b + 2c
  envió los patrones `no-restricted-imports` de ESLint + la
  triangulación de 40 fixtures a `origin/develop` (PR #80 + #82).
- La capa `domain` compila sin React, Next, FastAPI ni ningún
  subsistema de I/O (la guarda domain-purity del predecesor PR 2e se
  envía a `origin/develop`).
- `browser-state::domain` son tipos TS planos; `browser-state::infrastructure`
  posee las llamadas a `localStorage`.

### Archivos NO en el alcance de las ediciones de módulos de este cambio

- Handlers de ruta de `api/server.py` (la reescritura del backend
  está fuera de alcance).
- `etl/**` (el pipeline ETL está fuera de alcance).
- `extension/**` (la paridad de la extensión de Chrome es un cambio
  separado).
- `tests/test_module_layers.py` (el predecesor PR 2a lo envía; este
  cambio no lo edita).

---

## Ciclo de vida de build estático / start

### Pipeline de build (ejecutado por `Makefile::api`)

```
make api
  ├── scripts/check-runtime.mjs      # Node ≥ 20.9.0; sale no-cero en caso contrario
  ├── npm run build:web               # next build → out/
  │     ├── out/index.html
  │     ├── out/_next/static/chunks/*.js
  │     ├── out/_next/static/chunks/*.css
  │     ├── out/_next/static/media/*  (next/font)
  │     └── out/.next/build-manifest.json  (staged atómicamente por Next 16)
  └── uvicorn api.server:app          # enlaza 127.0.0.1:8765
```

| Knob | Valor | Autoridad |
| --- | --- | --- |
| `package.json::engines.node` | `">=20.9.0"` (requisito duro de Next 16) | Predecesor `design.md::§3.3.2.1` |
| `next.config.mjs::output` | `"export"` | Predecesor `design.md::§3.3.2.1` |
| `next.config.mjs::images.unoptimized` | `true` (requisito de exportación estática) | Predecesor `design.md::§3.3.2.1` |
| `next.config.mjs::trailingSlash` | `false` | Predecesor `design.md::§3.3.2.1` |
| Script de verificación de runtime | `scripts/check-runtime.mjs` | Tarea 3.4 del predecesor |
| Target de Makefile | `make api` ejecuta `npm install && npm run build:web && uvicorn …` | Tarea 3.4 del predecesor |

### Contrato de start (semántica de fallo)

| Condición | Comportamiento | Fuente |
| --- | --- | --- |
| Node `< 20.9.0` | `scripts/check-runtime.mjs` sale no-cero; `make api` sale no-cero **antes** de que uvicorn se enlace | Predecesor `design.md::§3.3.2.1` |
| `next build` sale no-cero | `make api` sale no-cero **antes** de que uvicorn se enlace; `web/` legacy **no** es un fallback | Predecesor `design.md::§3.3.2.1` |
| Falta `out/index.html` | `make api` sale no-cero; uvicorn no se enlaza | Predecesor `design.md::§3.3.2.1` |
| `out/_next/static/chunks/` vacío | El build no emitió nada útil; uvicorn no se enlaza | Predecesor `design.md::§3.3.2.1` |

No hay **ningún** fallback silencioso a archivos legacy. El build
vanilla legacy es alcanzable solo vía un `git revert <cutover-sha>`
explícito, nunca vía un modo degradado silencioso.

### Contrato de montaje (`api/server.py:1815` — firma sin cambios)

```python
# La firma del montaje permanece byte-idéntica al build legacy.
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
```

Solo la declaración de la constante **`WEB_DIR`** en `api/server.py:54`
se reorienta (cambio de una línea). Sin middleware, sin segundo
montaje, sin mecanismo de fallback SPA — el `html=True` de
`StaticFiles` de FastAPI es el único fallback para navegación directa
a rutas profundas (`/taxon/123`, `/help`, `/settings`); el router
del lado del cliente dentro del SPA decide la ruta final.

---

## Unidad de cutover atómica

La unidad de cutover (PR3e-equivalente, re-rebanada bajo A) cambia
**exactamente lo siguiente** en un solo release:

1. **Constante `WEB_DIR`** en `api/server.py:54` (reorientada a `out/`).
2. **Cada actualización de consumidor activo** enumerada en el
   `design.md::§3.1` del predecesor (imports, la ruta del lector
   AC-21, cada consumidor de test). Los 21 consumidores del mount
   web y los 5 consumidores de `web/search_urls.js` están nombrados
   literalmente en el `cutover-manifest.json` del predecesor.
3. **Los targets `Makefile::api` y `Makefile::web`** — el target
   `api` ejecuta `next build` antes de uvicorn; el paso legacy
   `make css` de Tailwind-3.4 se retira.
4. **El artefacto de build** — el directorio `out/` mismo
   (`out/index.html`, `out/_next/static/chunks/**`,
   `out/.next/build-manifest.json`, la clasificación de página de
   error si `404.html` / `500.html` se emite).

**No se soporta revertir un subconjunto.** Las reversiones parciales
dejan consumidores referenciando rutas borradas y rompen el shell SPA
o el test de contrato AC-21.

### Activación del manifiesto de cutover (durante apply)

`openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
invierte `activation_status` y `replacement.status` de `selected`
(legacy pre-cut, Tier-1) al **registro de activación post-cut**
(Tier-2) para cada uno de los 26 consumidores §3.1. La inversión es
un artefacto de planificación autorizado por el apply worker en el
mismo release que el código; el verificador G3 Tier-2 (ya
autorizado, PR #109 + #111) se vuelve a ejecutar contra la selección
de cut atómico y emite un nuevo `CONSUMER-READINESS.json`.

### Compuerta previa al vuelo (el cutover no puede enviarse hasta que todo esté verde)

- [ ] **G1 PASS** — registrado (`design.md::§1` del predecesor).
- [ ] **G2 PASS** — registrado contra el build limpio verificado de
      Next 16.3.3 / Turbopack (entrada del 2026-08-30 de
      `apply-progress.md` del predecesor).
- [ ] **G3 Tier-1 PASS** — registrado: los 26 consumidores §3.1 en
      verde contra el runtime legacy pre-cut vía el fixture
      controlado y `scripts/verify_consumers.py` (PR #109 + #111 +
      #115 + #116).
- [ ] **G4 PASS** — el arnés de paridad Playwright + Lighthouse se
      cierra en la fase de apply (cierre de G4 planificado abajo).
- [ ] **G5 reproducible** — la línea base legacy se reconstruye o
      reemplaza en la fase de apply (cierre de G5 planificado abajo).
- [ ] **G6 PASS** — `scripts/rehearse_cutover.py` sale 0 contra el
      manifiesto activado (cierre de G6 planificado abajo).

Evidencia ausente, fallida, obsoleta (> 7 días) o incomparable es
**bloqueada**, nunca éxito.

---

## Unidad de rollback

La unidad de rollback es **`git revert <cutover-sha>`**. Restaura
**los cuatro conjuntos** juntos:

- `web/index.html`, `web/app.js`, los 18 módulos `web/*.js`,
  `web/dist/tailwind.css`, `tailwind.config.js`.
- El `package.json` + `package-lock.json` legacy; `npm ci`
  reproduce el lock.
- `api/server.py:54` revierte a
  `WEB_DIR = Path(__file__).parent.parent / "web"`.
- El `Makefile::api` revierte a invocar `make css` antes de
  uvicorn.

### Estado post-revert

| Verificación | Expectativa |
| --- | --- |
| `make api` | Regenera `web/dist/tailwind.css` desde el `tailwind.config.js` revertido |
| `make smoke` | 63 pasados, 8 saltados (línea base pre-migración) |
| `make test` | Todos los tests del backend en verde |
| `curl http://127.0.0.1:8765/index.html` | Devuelve el shell vanilla |
| `extension/manifest.json` | Sin cambios a través del cutover y el rollback |
| `data/db/taxa.db` | Sin cambios (ningún esquema de BD se envía en este cambio) |
| `openspec/changes/migrate-nextjs-tailwind4/**` | Byte-idéntico (predecesor congelado) |

No se requiere migración de datos para revertir. Ningún camino de
regresión de AC-21 queda abierto. No se requiere actualización del
manifest de la extensión.

---

## Plan de paridad / evidencia

### Evidencia trasladada (importada, no re-derivada)

| Puerta | Estado | Fuente |
| --- | --- | --- |
| G1 (origen único) | **PASS registrado** | Predecesor `design.md::§1` |
| G2 (build fundacional) | **PASS registrado** contra el build limpio verificado de Next 16.3.3 / Turbopack | Predecesor `apply-progress.md` (captura de evidencia del 2026-08-30) |
| G3 Tier-1 (consumer readiness, legacy pre-cut) | **PASS registrado** — los 26 consumidores §3.1 en verde vía el fixture controlado, `scripts/verify_consumers.py` | Predecesor `apply-progress.md` (PR #109 + #111 + #115 + #116) |
| G3 Tier-2 (selección de cut atómico) | **NO PASSED** — requiere cierre de G4 + G5 + G6 | Fase de apply de este cambio |
| G4 (paridad Playwright + Lighthouse) | **bloqueado — verificador no autorizado** | Fase de apply de este cambio (planificado abajo) |
| G5 (línea base de hidratación) | **no reproducible — la línea base legacy no está en disco** | Fase de apply de este cambio (planificado abajo) |
| G6 (ensayo de cutover) | **bloqueado — verificador no autorizado** | Fase de apply de este cambio (planificado abajo) |

### Artefactos de planificación trasladados (entradas congeladas)

- `openspec/changes/migrate-nextjs-tailwind4/proposal.md`
- `openspec/changes/migrate-nextjs-tailwind4/design.md` (incl.
  decisión de frontera `§1`, inventario de consumidores activos
  `§3.1`, contrato G2 `§3.3.2.1`, contrato G3 `§3.3.3` /
  `§3.3.3.1`, disposición G5 `§3.3.5`)
- `openspec/changes/migrate-nextjs-tailwind4/apply-progress.md`
  (incl. el change log registrando G2 PASS, G3 Tier-1 PASS,
  G5 no reproducible)
- `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
- `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md`
- `openspec/specs/research/spec.md` (canónico; preservado sin cambios)

### Lista de verificación de paridad (la fase de apply debe satisfacer cada fila)

- [ ] **Paridad funcional** — cada flujo de usuario (navegar,
      buscar, materializar, previsualizar, abrir carpeta, guardar
      URL, ver archivos en todos los formatos soportados) se
      comporta idénticamente al build legacy.
- [ ] **Rendimiento** — ≤ 0 % de regresión en paint inicial o
      latencia de interacción sobre el fixture chromium capturado
      por el predecesor.
- [ ] **Origen local único** — `make api` enlaza solo 8765; sin
      segundo puerto de dev-server; `host_permissions` de la
      extensión sin cambios.
- [ ] **pytest del backend** — línea base 63 pasados, 8 saltados
      preservada.
- [ ] **Suite de Playwright** — selectores DOM actualizados;
      contrato de atributos `data-*` preservado; sigue en verde.
- [ ] **Contrato AC-21** —
      `tests/test_smoke.py::test_search_engine_contract` pasa; el
      literal puede moverse bajo `src/data/search-engines.js`;
      forma de bytes sin cambios.
- [ ] **Estado local del navegador** — `theme`, `tree-source`,
      `last-taxon-id`, `kebab-open-id` tienen cada uno un sitio de
      lectura + un sitio de escritura dentro de
      `src/modules/browser-state/`; sin warning de hidratación.
- [ ] **Paridad de Tailwind 4** — cada token `:root` resuelve;
      cada referencia `var(--token)` resuelve; cada clase de utility
      resuelve.
- [ ] **Accesibilidad** — cada rol ARIA, label, manejador de
      teclado preservado; escaneo axe sin nuevas violaciones
      serias/críticas.
- [ ] **Predecesor congelado** — `openspec/changes/migrate-nextjs-tailwind4/**`
      byte-idéntico antes y después del apply.
- [ ] **Rollback** — `git revert` restaura el legacy con humo +
      Playwright en verde.

---

## Costuras de test

La superficie de test está estratificada para que el apply worker
pueda conducir RED → GREEN → TRIANGULATE sin re-derivar evidencia
que el predecesor ya produjo.

### Preservados (el predecesor entrega; este cambio no los edita)

| Test | Propietario | Propósito |
| --- | --- | --- |
| `tests/test_module_layers.py` | Predecesor PR 2a (#78) | 40 aserciones de layout; fija `CAPABILITIES`, `LAYERS`, `BARREL_NAME` |
| `tests/test_no_restricted_imports.py` | Predecesor PR 2b + 2c (#80, #82) | 102 aserciones de imports solo por barrel + triangulación de 40 fixtures |
| `tests/test_taxonomy_domain.py` | Predecesor PR 2d (#84) | Tipos de domain + invariantes compilan sin framework |
| `tests/test_domain_purity.py` | Predecesor PR 2e (#86) | Guarda de grep de tokens de framework sobre la capa domain |
| `tests/test_verify_consumers.py` | Predecesor PR #109 + #111 + #115 + #116 | Triangulación del verificador G3; runtime controlado / servir-fixture / forma-HTTP / preservación de symlinks |
| `tests/test_g3_legacy_fixture.py` | Predecesor PR #113 + #114 + #115 + #116 | Cobertura de fixture DB + assets de fixture servidos |
| `tests/test_verify_build.py` | Evidencia G2 del predecesor | 14 aserciones del contrato G2 |
| `tests/test_g2_candidate.py` | Evidencia G2 del predecesor | 34 aserciones del build candidato G2 |
| `tests/test_smoke.py` | Línea base del repo | 63 pasados, 8 saltados (contrato AC-21 preservado) |
| `tests/test_search_categories.py` | Línea base del repo | Test de agrupación de `CATEGORIES` (general / taxonomic / academic / multimedia / documents) |
| `tests/test_evidence_baseline.py` | Predecesor PR 1b.1 + 1b.2 | Pin de Chromium + línea base de evidencia legacy |
| `tests/test_build_profile.py` | Predecesor PR 1a.1 + 1a.2 | Emisor de build-profile + esquema |
| `tests/test_hydration_timing.py` | Predecesor PR 1b.3a + 1b.3b | Medición de hidratación + esquema |

### Nuevos (este cambio los envía)

| Test | Rebanada | Propósito |
| --- | --- | --- |
| `tests/test_tailwind_4_parity.py` | Bootstrap | Cada token `:root` legacy + referencia `var(--name)` resuelve a declaración no vacía |
| `tests/test_make_api_build.py` | Bootstrap | `Makefile::api` ejecuta build de Next antes de uvicorn; falla rápido en Node < 20.9.0 |
| `tests/test_static_mount.py` | Bootstrap | `GET /` devuelve HTML de Next; `GET /_next/static/<h>.js` devuelve 200; sin segundo listener en 8765 |
| `tests/test_browser_state_keys.py` | Browser-state | Greps en `src/`; afirma exactamente 4 sitios de llamada `localStorage.getItem` + 4 `localStorage.setItem` |
| `tests/test_hydration_console.py` | Browser-state | Playwright: cero warnings de hidratación de React tras paint inicial + ciclo de rehydration |
| `tests/test_taxonomy_infra.py` | Capability ports | Mocks de `fetchTaxon` / `fetchChildren`; aserciones de forma |
| `tests/test_research_infra.py` | Capability ports | Mocks de `/api/taxon/{id}/files{,/serve}`; aserciones de forma |
| `tests/test_e2e_file_explorer.py` | Capability ports | Playwright; selectores DOM actualizados; contrato `data-*` preservado |
| `tests/test_web_toggle.py` | Capability ports | Playwright; toggle de tema persiste vía store tipado; estampado de `data-theme` |

### Compuertas de respaldo (la fase de apply las cierra)

| Puerta | Verificador | Artefacto | Umbral |
| --- | --- | --- | --- |
| G4 (paridad Playwright + Lighthouse) | Autorizado en apply | `tests/test_e2e_file_explorer.py` + traza Playwright + JSON de Lighthouse | Δ ≤ 0 % en paint inicial + latencia de interacción vs. fixture chromium legacy |
| G5 (línea base de hidratación) | `scripts/measure_hydration.py` (ya autorizado) re-ejecutado contra línea base reconstruida | JSON de línea base de hidratación | Δ ≤ 0 % vs. línea base legacy reconstruida |
| G6 (ensayo de cutover) | `scripts/rehearse_cutover.py` (a autorizar) | `cutover-rehearsal.json` | Sale 0; sin rutas de fallback silencioso; unidad de cutover atómico + unidad de rollback consistentes |

---

## Cierre planificado de G4 / G5 / G6

La fase de apply posee los tres bloqueadores. El diseño planifica el
cierre; la implementación ocurre durante apply.

### G4 — Arnés de paridad Playwright + Lighthouse

| Paso | Propietario | Salida |
| --- | --- | --- |
| Actualizar selectores de `tests/test_e2e_file_explorer.py` para el árbol de componentes React (atributos `data-*` preservados según el spec research canónico) | Apply | `tests/test_e2e_file_explorer.py` |
| Actualizar selectores de `tests/test_web_toggle.py`; afirmar que el toggle de tema persiste vía `localStorage.taxa.settings.theme` y estampa `data-theme` en `<html>` | Apply | `tests/test_web_toggle.py` |
| Re-ejecutar el fixture chromium del predecesor contra el nuevo build; capturar paint inicial + latencia de interacción bajo Playwright + Lighthouse | Apply | Traza Playwright + JSON de Lighthouse |
| Comparar contra `web/dist/evidence-baseline.json` del predecesor | Apply | Reporte de Δ |
| Δ ≤ 0 % en paint inicial + latencia de interacción sin exención documentada → **G4 PASS** | Apply | Inversión de estado |

### G5 — Línea base de hidratación

| Paso | Propietario | Salida |
| --- | --- | --- |
| Auditar `web/dist/evidence-baseline.json` para confirmar si la línea base legacy está en disco (la auditoría §3.3.5 del predecesor la lista como **no reproducible**) | Apply | Reporte de auditoría |
| Si es reproducible: capturar la línea base legacy vía `scripts/measure_hydration.py` contra el fixture chromium legacy | Apply | JSON de hidratación legacy |
| Si no es reproducible: reconstruir desde paint inicial de `web/index.html` + `delta_server_to_tree_first_paint_ms` legacy documentado en `design.md::§"Migration Evidence Baseline"` | Apply | JSON de línea base reconstruida |
| Re-ejecutar `scripts/measure_hydration.py` contra el nuevo build | Apply | JSON de hidratación nueva |
| Δ ≤ 0 % vs. línea base reconstruida → **G5 reproducible** | Apply | Inversión de estado |

### G6 — Ensayo de cutover

| Paso | Propietario | Salida |
| --- | --- | --- |
| Autorizar `scripts/rehearse_cutover.py` que ejecuta en dry-run la unidad de cutover atómico: reorientación de WEB_DIR + actualizaciones de 26 consumidores + reescritura de Makefile + artefacto de build `out/`, luego ejecuta el verificador G3 (PR #109 + #111) contra el manifiesto activado | Apply | `scripts/rehearse_cutover.py` |
| Autorizar `tests/test_rehearse_cutover.py` (parametrizado sobre los 4 subconjuntos de la unidad de cutover, afirmando la invariante fail-closed) | Apply | `tests/test_rehearse_cutover.py` |
| Ejecutar el ensayo de extremo a extremo; capturar `cutover-rehearsal.json` | Apply | `cutover-rehearsal.json` |
| Ensayo sale 0; sin rutas de fallback silencioso; unidades de cutover atómico + rollback consistentes → **G6 PASS** | Apply | Inversión de estado |

### Secuencia de activación del cutover (cuando las seis puertas estén verdes)

1. Autorizar el **registro de activación post-cut** en el
   `cutover-manifest.json` del predecesor (invertir
   `activation_status` + `replacement.status` a Tier-2 para los 26
   consumidores §3.1).
2. Aplicar la **unidad de cutover atómico** — el cambio de los
   cuatro conjuntos en un solo release (ver §"Unidad de cutover
   atómica" arriba).
3. Ejecutar el verificador G3 Tier-2 contra la selección activada;
   `CONSUMER-READINESS.json` sale 0 con `activation_complete = true`,
   `unselected_count = 0`.
4. Ejecutar `make smoke` + Playwright + Lighthouse; verificar la
   lista de verificación de paridad.
5. Marcar el PR de cutover listo para revisión.

---

## Rebanada de sub-PRs bajo la Aproximación A

El `tasks.md` del predecesor enumera 35 tareas a través de 14+
sub-PRs. Este cambio las re-rebana bajo la Aproximación A dentro
del presupuesto de revisión de 400 líneas por sub-PR. Las listas
de archivos por tarea completas viven en `tasks.md`; la tabla
siguiente es la vista ejecutiva.

| Sub-PR | Tarea del predecesor | Alcance | Nuevo / preservado | Presupuesto LoC |
| --- | --- | --- | --- | --- |
| PR 3a | tarea 3.1 | `src/app/{layout,page}.tsx` + `next.config.mjs` + config de plugins TS / Next en `tsconfig.json` | Nuevo | ≤ 400 |
| PR 3b | tarea 3.2 | `src/modules/design-system/infrastructure/globals.css` (`@import "tailwindcss"` + `@theme` + `@layer base`) | Nuevo | ≤ 400 |
| PR 3c | tarea 3.4 | Reescritura de `Makefile::api` + `scripts/check-runtime.mjs` + reescritura de `package.json` (deps + `engines.node`) | Nuevo | ≤ 400 |
| PR 3d | tarea 3.6 + 3.7 | Reorientación de `api/server.py:54` WEB_DIR + `web/search_urls.js` → `src/data/search-engines.js` + actualización de `open()` de AC-21 | Nuevo | ≤ 400 |
| PR 4a | tarea 4.1 + 4.2 | `src/modules/browser-state/{store,keys,defaults}.ts` + 4 sitios de lectura + 4 de escritura dentro de `useEffect` | Nuevo | ≤ 400 |
| PR 4b | tarea 4.3 + 4.4 | `useSyncExternalStore` detrás de flag `mounted` + aserción Playwright de cero warnings de hidratación | Nuevo | ≤ 400 |
| PR 5a | tarea 5.1 + 5.2 + 5.3 | `src/modules/taxonomy/{domain,application,infrastructure,presentation}` + port de `web/{tree,detail,breadcrumb}.js` | Nuevo | ≤ 400 |
| PR 5b | tarea 5.4 + 5.5 + 5.6 | `src/modules/research/{domain,application,infrastructure,presentation}` + port de `web/{file_explorer,file_viewer,format,keymap}.js` + pin CDN | Nuevo | ≤ 400 |
| PR 5c | tarea 5.7 + 5.8 + 5.9 | Actualizaciones de selectores Playwright + e2e + preservación del contrato `data-*` + borrar `web/*.{html,js,css}` + `tailwind.config.js` | Nuevo | ≤ 400 |
| PR 3e (cutover) | unidad de cutover atómico | El release de los cuatro conjuntos + inversión del cutover-manifest a Tier-2 + reejecución del verificador G3 Tier-2 + inversiones del status-footer para el cierre de G4 / G5 / G6 | Atómico | ≤ 400 |

El sub-PR de cutover PR 3e se envía **solo cuando** las seis
puertas estén verdes; el apply worker está bloqueado por los
sub-PRs de cierre de G4 / G5 / G6 (3e mismo aterriza después de las
verificaciones de cierre).

---

## Archivos afectados (vista ejecutiva)

| Área | Acción | Archivos |
| --- | --- | --- |
| `web/index.html` | Borrado en la activación (PR 5c) | `web/index.html` |
| `web/*.js` (18 módulos) | Borrados en la activación (PR 5c) | `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,help,keymap,settings,search,file_explorer,file_viewer,format,search_urls}.js` |
| `web/index.css` | Borrado en la activación (PR 5c) | `web/index.css` |
| `web/dist/tailwind.css` | Regenerado por el `make css` revertido tras el rollback; no parte del nuevo build | `web/dist/tailwind.css` |
| `tailwind.config.js` | Borrado en la activación (PR 5c) | `tailwind.config.js` |
| `src/app/{layout,page}.tsx` | Creados (PR 3a) | nuevos |
| `src/modules/**` | Poblados (PR 3b + 4a/4b + 5a/5b) | nuevos |
| `src/data/search-engines.js` | Creado (PR 3d) — reemplaza a `web/search_urls.js` | nuevo |
| `src/app/globals.css` | Creado (PR 3b) — Tailwind 4 `@theme` + `@layer base` | nuevo |
| `package.json` | Modificado (PR 3c) — `next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss@^4`, toolchain TS, `engines.node ">=20.9.0"`; quita `autoprefixer`, `postcss`, `@tailwindcss/forms` | `package.json` |
| `api/server.py` | Modificado (PR 3d) — reorientación de `WEB_DIR` en línea 54 únicamente; firma de montaje sin cambios | `api/server.py` |
| `Makefile` | Modificado (PR 3c) — el target `api` ejecuta `npm run build:web` antes de uvicorn; `make css` legacy retirado | `Makefile` |
| `tests/test_tailwind_4_parity.py` | Creado (PR 3b) | nuevo |
| `tests/test_make_api_build.py` | Creado (PR 3c) | nuevo |
| `tests/test_static_mount.py` | Creado (PR 3d) | nuevo |
| `tests/test_browser_state_keys.py` | Creado (PR 4a) | nuevo |
| `tests/test_hydration_console.py` | Creado (PR 4b) | nuevo |
| `tests/test_taxonomy_infra.py` | Creado (PR 5a) | nuevo |
| `tests/test_research_infra.py` | Creado (PR 5b) | nuevo |
| `tests/test_e2e_file_explorer.py` | Modificado (PR 5c) — selectores DOM actualizados; contrato `data-*` preservado | `tests/test_e2e_file_explorer.py` |
| `tests/test_web_toggle.py` | Modificado (PR 5c) — toggle de tema persiste vía store tipado | `tests/test_web_toggle.py` |
| `tests/test_smoke.py::test_search_engine_contract` | Modificado (PR 3d) — ruta de `open()` actualizada si el literal se movió; forma de bytes preservada | `tests/test_smoke.py` |
| `scripts/check-runtime.mjs` | Creado (PR 3c) — aplicación de Node ≥ 20.9.0 | nuevo |
| `scripts/rehearse_cutover.py` | Creado (PR 3e) — dry-run G6 | nuevo |
| `tests/test_rehearse_cutover.py` | Creado (PR 3e) — invariante fail-closed parametrizada | nuevo |
| `extension/manifest.json` | **Sin cambios** | `extension/manifest.json` |
| `openspec/changes/migrate-nextjs-tailwind4/**` | **Sin cambios (congelado)** | (congelado) |
| `documents-es/openspec/changes/complete-taxa-frontend-migration/**` | Espejo en español (este cambio) | `documents-es/openspec/changes/complete-taxa-frontend-migration/design-es.md` |

---

## Fuera de alcance (vinculante, preservado del spec)

- Reescritura del backend: handlers de ruta de `api/server.py`,
  lógica SQLite/WAL, flujo de materialización, defensa SSRF en
  `save-url`.
- Pipeline ETL: `etl/parse_textree`, `etl/load_coldp`,
  `etl/load_worms`, `etl/load_freshwater`, migraciones.
- Trabajo de paridad de la extensión de Chrome — un cambio separado
  rastrea cualquier adaptación de la extensión consciente de React.
- Trabajo de SEO / metadata / sitemap / robots.
- Rutas nuevas (Settings, About, Help) más allá de lo que la UI
  legacy expone hoy.
- Tooling de cobertura (`coverage.available: false` es el estado
  actual).
- Rediseño visual (impeccable / Stitch follow-up, no es un
  bloqueador).
- Editar o "completar" el directorio del cambio del predecesor. El
  predecesor está **congelado**, no finalizado.
- Re-ejecutar las sondas G2 / G3 / G4 / G5 / G6 del predecesor —
  sus salidas se importan tal cual.

---

## Riesgos (preservados de propuesta + spec, con mitigación en fase de apply)

| Riesgo | Probabilidad | Mitigación |
| --- | --- | --- |
| El default de Aproximación A es anulado por spec/design sin evidencia fresca | Baja (A es FINAL) | El spec ya bloqueó A el 2026-09-02; este diseño registra el bloqueo en §1 |
| El desplazamiento del namespace de tokens de Tailwind 4 (`--color-primary` vs `--primary`) rompe referencias `var(--token)` en CSS plano | Media | Alias de nombres en `@theme` para que los tokens legacy `--primary`, `--bg-surface`, `--realm-*` resuelvan sin cambios; el test de paridad enumera cada referencia `var(--token)` y afirma una declaración no vacía |
| Reordenamiento de la cascada `color-mix()` en el bloque `<style>` inline de 80 KB causa deriva visual | Media | Migrar reglas bespoke a `globals.css` dentro de `@layer base` para que el orden de fuentes coincida; regresión visual de Playwright sobre el fixture chromium existente |
| El test de contrato AC-21 falla porque la ubicación de `web/search_urls.js` cambió | Media | Mantener el literal bajo `src/data/search-engines.js` con la misma forma; la ruta de `open()` del test se actualiza en el mismo release |
| Mismatch de hidratación por lecturas de `localStorage` en servidor vs cliente | Media | Render inicial usa una flag `mounted`; lecturas de storage ocurren dentro de `useEffect`; la estructura del árbol defaultea al estado vacío en el primer paint |
| La exportación estática sacrifica rutas dinámicas / optimización de imágenes usadas por trabajo futuro | Baja | Aceptable para v1; cambiar al dev-server completo de Next.js (Aproximación B) es el costo del próximo cambio si se necesita |
| El tamaño del bundle de dependencias de Next.js + React regresiona el paint inicial | Baja | Perfil de `next build` capturado antes/después; muestra de Playwright + Lighthouse sobre el fixture chromium existente; ≤ 0 % de regresión es el criterio de éxito |
| El contrato de puerto único se rompe si `host_permissions` de la extensión cambia accidentalmente | Baja | Regla dura en Makefile + check de humo en CI: `make api` solo enlaza 8765; ningún segundo origen añadido; `manifest.json` sin cambios en este cambio |
| Los artefactos del predecesor derivan durante la fase de apply | Baja | Regla de CI / protección de rama: los PRs de este cambio NO DEBEN modificar `openspec/changes/migrate-nextjs-tailwind4/**`; hook de lint rechaza |

---

## Estado

**La Aproximación A es FINAL** (bloqueada el 2026-09-02; registrada
en §1 de este diseño). G1 PASS registrado; G2 PASS registrado
contra el build limpio verificado de Next 16.3.3 / Turbopack;
G3 Tier-1 PASS registrado (los 26 consumidores §3.1 en verde contra
el runtime legacy pre-cut vía el fixture controlado,
`scripts/verify_consumers.py`, PR #109 + #111 + #115 + #116).
G3 Tier-2 (selección de cut atómico) NO PASSED — bloqueada por el
cierre de G4 + G5 + G6. G4 (paridad Playwright + Lighthouse)
**bloqueada — verificador no autorizado**; debe cerrarse en la
fase de apply. G5 (línea base de hidratación) **no reproducible —
la línea base legacy no está en disco**; debe reconstruirse o
reemplazarse durante la fase de apply. G6 (ensayo de cutover)
**bloqueada — verificador no autorizado**; debe cerrarse en la fase
de apply. Predecesor `openspec/changes/migrate-nextjs-tailwind4/**`
congelado. Ninguna activación de FastAPI en esta pasada de diseño;
el PR3e de cutover atómico se envía solo cuando las seis puertas
estén verdes.

---

## Próximo paso

La **fase de tasks** (sdd-tasks) lee este diseño más el `tasks.md`,
`apply-progress.md` y `cutover-manifest.json` del predecesor, luego
autoriza las listas de archivos por sub-PR para los 10 sub-PRs de
arriba bajo la Aproximación A dentro del presupuesto de revisión de
400 líneas por sub-PR. La **fase de apply** posee los sub-PRs de
cierre de G4 / G5 / G6 y el PR3e de cutover atómico. La **fase de
archive** copia cada spec por dominio literalmente a
`openspec/specs/{frontend-runtime,design-tokens,browser-state-hydration,frontend-bootstrap,research}/spec.md`
y promueve el spec modular-architecture al árbol de specs canónico.