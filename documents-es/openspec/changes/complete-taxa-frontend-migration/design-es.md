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
| `taxonomy` | Tipos `Taxon` + invariantes | `useTaxonTree()`, `useTaxonDetail()`, walker de cadena de padres | `fetchTaxon`, `fetchChildren`, `fetchDomains` | `Tree`, `DetailPanel`, `OverviewTab`, `SearchTab`, `FolderTab`, `Breadcrumb`, `DomainList`, `Kebab` |
| `research` | Tipos `ResearchFile`, `Engine`, `FileNode` | `useFileExplorer()`, `useFileViewer()`, despachador de formatos | `fetchFiles`, `fetchServe`, `loadScriptOnce` (cargador perezoso CDN), `search-engines.js` | `FileExplorer`, `FileViewer`, `RawTableTreeTabs`, `MetaStrip`, `BreadcrumbPanel`, `Banners`, `SearchLinkList` |
| `design-system` | Tokens de tema (tipados) | — | `globals.css` (bloque `@theme` + `@layer base`), wire-up de `next/font` | `<Icon>`, `<Button>`, primitivas de layout |
| `browser-state` | Tipos `LocalStorageKey`, defaults tipados, tipo de subscriber | — | `store.ts` (4 claves × {read, write}), adaptador `useSyncExternalStore` | — |
| `app-shell` | — | Composición host `AppShell`, estado del shell de ruta | `src/app/page.tsx`, `src/app/layout.tsx`, `next.config.mjs` | `AppShell`, `<Header>`, `<Tabs>` (Browser / Classification / Settings — Browser es el **Research global / file explorer**, NO scoped por taxón), `<HelpShell>`, `<SettingsView>`, `<BannerHost>` |

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

### Superficie de UI y estructura de pestañas (comportamiento actual verificado)

La UI de pantalla única se entrega con dos superficies de nivel
superior (las `<Tabs>` del header y el árbol taxonómico más su
panel de detalle) y el comportamiento verificado de cada una,
capturado contra `http://127.0.0.1:8765/`:

| Superficie | Ubicación | Comportamiento (vinculante) |
| --- | --- | --- |
| **Árbol taxonómico** | columna izquierda de `<main>` | Las filas del árbol renderizan `rank / name / source / species-count` más un menú kebab por fila. La selección de cualquier nodo — incluidos los dominios de nivel superior — abre el panel de detalle inline. |
| **Panel de detalle** (por taxón seleccionado) | columna derecha de `<main>` | Panel contextual inline con un encabezado inline (rank + nombre científico) y un strip de pestañas. **Tres pestañas en este orden fijo: `Overview`, `Search`, `Folder`.** Las tres pestañas son alcanzables desde cualquier selección; **`Overview` siempre está disponible y siempre es visible** según la política seleccionada por el usuario (ningún estado futuro puede condicionar `Overview` a un feature flag, un permiso, o una verificación de forma del taxón). |
| Pestaña `Overview` | cuerpo del panel de detalle | Renderiza los metadatos del taxón — nombre científico, estado de aceptación, autoría, conteo de especies. La pestaña por defecto en una selección fresca. |
| Pestaña `Search` | cuerpo del panel de detalle | Una lista categorizada de enlaces salientes. Las categorías se renderizan en este orden fijo: `General`, `Taxonomic`, `Academic`, `Multimedia`, `Documents`. Cada entrada es un anchor (`<a>`) con `target="_blank"`, `rel="noopener noreferrer"`, y la plantilla de URL resuelta desde `SEARCH_ENGINES`. **`Search` es una pestaña primaria**, no una lista de tarjetas secundaria anidada bajo `Overview`. |
| Pestaña `Folder` | cuerpo del panel de detalle | Indicador de carpeta / materialización por taxón; **separado de `Search`**. |
| Pestaña `Browser` (header) | `<Tabs>` de `<Header>` | **Research global / file explorer** — abre el par carpeta recursiva / visor de archivos **sin** filtro `taxonId`; es la superficie de Research, no una superficie scoped por taxón. Seleccionar un taxón mientras se está en `Browser` **no** acota el file explorer a ese taxón; el explorer continúa mostrando el corpus de investigación activo. |
| Acciones de kebab (por fila de árbol) | popover flotante anclado al glifo kebab | Incluye (a) "Search online", (b) affordance de materialize / open-folder, (c) otras affordances de fila de árbol preservadas del legacy. |

#### Contrato vinculante del comportamiento de pestañas (aplica durante la fase de apply)

- El strip de pestañas del panel de detalle renderiza **las tres
  pestañas** para cada selección. `Overview` nunca se oculta
  condicionalmente; la política seleccionada por el usuario de que
  `Overview` siempre esté disponible / visible es vinculante y
  anula cualquier cortocircuito por fuente (`col` / `worms` /
  `freshwater`).
- `Search` es una **pestaña primaria** (hermana de `Overview` y
  `Folder`), no una lista de tarjetas secundaria anidada bajo
  `Overview`. La categorización de las entradas de enlace
  saliente (`General` / `Taxonomic` / `Academic` / `Multimedia`
  / `Documents`) vive dentro del cuerpo de la pestaña `Search`.
- La acción kebab "Search online" **fuerza la pestaña `Search`
  activa** sobre el taxón seleccionado (NO debe defaultear a
  `Overview`, ni siquiera para taxones de nivel superior). El
  comportamiento actual en vivo aterriza en `Overview` para
  taxones de nivel superior — esta es una regresión conocida que
  la fase de apply DEBE cerrar; la interacción corregida es
  "Search online" → pestaña `Search` para **cada** selección.
- `Browser` (la pestaña del header) es el **Research global /
  file explorer** y **no** es una tercera pestaña del panel de
  detalle. Es la superficie de Research, independiente del taxón;
  seleccionar un taxón mientras `Browser` está activo NO DEBE
  acotar el explorer a ese taxón.
- La topología de cadena de 16 hijos (tras la re-división del
  CSS) se preserva; la estructura de pestañas y el
  comportamiento de forzar `Search` aterrizan dentro de los
  sub-PRs PR 5a (port de taxonomy) y PR 5b (port
  de research) existentes sin cambiar posiciones, dependencias,
  o sobres de LoC que empujarían la cadena por encima del
  presupuesto de 400 líneas por PR.

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
- `tsconfig.json` revierte al scaffold de strict-mode + aliases
  de ruta `@taxa/<capability>` del predecesor (el archivo ya
  existía en la raíz del repo antes del PR 3a; la config
  completa de Next.js / JSX / plugins se elimina en el rollback).
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
| `tests/test_tailwind_4_tokens.py` | CSS (PR 3c-a) | Cada token `:root` / `[data-theme="dark"]` / `--realm-*` legacy resuelve a declaración no vacía en `globals.css::@theme` |
| `tests/test_taxonomy_styles.py` | CSS (PR 3c-b) | Cada selector `@layer components` de taxonomía (`.taxa-tree`, `.tree-row`, `.kebab`, `.detail-panel`, `.tab-strip`, `.overview-tab`, `.breadcrumb`, …) resuelve a declaración no vacía |
| `tests/test_research_styles.py` | CSS (PR 3c-c) | Cada selector `@layer components` de research / chrome (`.search-tab`, `.search-category-section`, `.search-link-list`, `.search-link`, `.folder-tab`, `.header-browser-tab`, `.research-explorer`, …) resuelve a declaración no vacía |
| `tests/test_tailwind_4_parity.py` | CSS (PR 3c-d) | Test de paridad final consolidado parametrizado — cada token `:root` legacy, cada referencia `var(--token)`, cada clase de utilidad legacy, cada selector `@keyframes` / `color-mix()` resuelve a declaración no vacía; cubre el CSS inline legacy de 1.963 líneas de extremo a extremo |
| `tests/test_design_system_purity.py` | CSS (PR 3c-a) | Guardia de grep sobre `src/modules/design-system/`; sin literales hex fuera del módulo design-system |
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

> **2026-09-02 — revisión correctiva del plan**: la tabla
> de rebanada de abajo reemplaza el orden original
> después de que el portón de apply identificara un
> defecto de orden de dependencia (el PR 3a original
> requería `next build`/`out/index.html` antes de que
> existieran el toolchain de Next/React/Tailwind/TypeScript
> y el contrato de runtime de Node; esos aterrizaban en el
> PR 3c original). El orden corregido instala el
> toolchain primero (posición 1), degrada la exportación
> estática del App Router a la posición 2 (ahora
> satisfacible), mantiene Tailwind/tokens en la posición
> 3, fusiona la reescritura del Makefile con el repoint
> de `WEB_DIR` + AC-21 en un único sub-PR en la posición
> 4, y sigue con state, ports, e2e, validación y cutover
> atómico. El conteo de 13 hijos se preserva. Las listas
> de archivos por tarea completas y la justificación de
> corrección de dependencias viven en `tasks.md`; esta
> tabla es la vista ejecutiva.

> **2026-09-02 — corrección del defecto de dependencia
> (esta revisión)**. La re-auditoría de pre-flight del
> portón de apply identificó un segundo defecto de
> dependencia dentro de la topología corregida: el PR 3b
> en la posición 2 importaba `@taxa/app-shell` (un módulo
> que el PR 4b envía en la posición 9/16 — *más tarde* en
> la cadena) y `./globals.css` (un archivo que el PR 3c-a
> envía en la posición 3/16 — *más tarde* en la cadena).
> En su testigo de `next build`, ninguno de los dos
> archivos objetivo existía todavía. La misma auditoría
> marcó la aserción de triangulación de PR 3b.5 que dice
> que la salida de build referencia la ruta del barrel del
> typed store `@taxa/browser-state` — ese archivo de barrel
> no existe hasta que el PR 4a aterriza. **El PR 3b se
> re-ambia a un bootstrap autocontenido de exportación
> estática del App Router**: marcadores semánticos mínimos
> que no importan ni `@taxa/app-shell` ni `./globals.css`;
> la línea `import "./globals.css";` se mueve al PR 3c-a;
> la integración de `<AppShell>` en
> `src/app/{layout,page}.tsx` se mueve al PR 4b. La
> referencia insatisfacible a `@taxa/browser-state` de
> PR 3b.5 se elimina. **La topología y el orden de la
> cadena se preservan**; los presupuestos LoC por sub-PR
> se quedan muy por debajo de 400; **solo permanece la
> excepción previa de `package-lock.json` regenerado de

> **2026-09-02 — re-división del CSS (esta revisión)**. La
> re-auditoría de pre-flight del portón de apply identificó
> que el PR 3c, según su ámbito en la revisión correctiva
> del defecto de dependencia anterior, era
> **insatisfacible**: se le había encargado migrar el
> bloque `<style>` inline de **1.963 líneas** del
> `web/index.html` legacy en un único sub-PR mientras se
> mantenía bajo el presupuesto de revisión por PR de 400
> líneas — la migración no cabe. Por tanto la porción de
> CSS de la migración se **re-divide en cuatro hijos
> encadenados**, cada uno ≤ 400 líneas authored:
> PR 3c-a (tokens / base / modo oscuro, posición 3/16);
> PR 3c-b (estilos de árbol + Overview inline, posición
> 4/16); PR 3c-c (estilos de Search / Folder / Browser
> global, posición 5/16); PR 3c-d (animaciones /
> utilidades + paridad final, posición 6/16). El **PR
> #146** tracker es el punto de partida fusionado para el
> primer nuevo hijo CSS (PR 3c-a). Cada PR hijo
> posterior cambia de posición por +3 para acomodar los
> cuatro hijos CSS (3d 4→7; 4a 5→8; 4b 6→9; 5a 7→10;
> 5b 8→11; 5c 9→12; 6a 10→13; 6b 11→14; 6c 12→15;
> 3e 13→16). Las etiquetas semánticas (3a, 3b, 3c-a,
> 3c-b, 3c-c, 3c-d, 3d, 4a, 4b, 5a, 5b, 5c, 6a, 6b, 6c,
> 3e) se preservan; solo cambian el contador de posición
> (NN en `feat/complete-taxa-frontend-migration-NN-XXX`)
> y las referencias a las ramas base. Los cuatro hijos
> CSS migran colectivamente las 1.963 líneas legacy del
> CSS inline a `src/app/globals.css` (≤ 1.500 líneas
> authored más el reset base de Tailwind 4, bien dentro
> del presupuesto del predecesor para
> `out/_next/static/chunks/*.css`); el bloque
> `<style>` legacy se retira en PR 5c. El **conteo de
> 16 hijos** reemplaza al conteo previo de 13 hijos.
> Los presupuestos LoC por sub-PR se quedan muy por
> debajo del presupuesto de revisión de 400 líneas;
> **solo permanece la excepción previa de
> `package-lock.json` regenerado de PR 3a**. El Enfoque
> A, FastAPI/SQLite, el predecesor congelado y los
> specs por dominio quedan sin cambios.
> PR 3a**. El Enfoque A, FastAPI/SQLite, el predecesor
> congelado y los specs por dominio quedan sin cambios.

El `tasks.md` del predecesor enumeraba 35 tareas a través
de 14+ sub-PRs. La cadena corregida las re-rebana bajo la
Aproximación A dentro del presupuesto de revisión de 400
líneas por sub-PR.

| Posición | Sub-PR | Mapeo de tarea del predecesor | Alcance | Nuevo / preservado | Presupuesto LoC |
| --- | --- | --- | --- | --- | --- |
| 1 / 13 | PR 3a (bootstrap de toolchain) | NUEVO (absorbe parte de la tarea 3.4 original — reescritura de `package.json` + `scripts/check-runtime.mjs`) | Pines de deps de `package.json` (`next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss@^4`, toolchain TS, `engines.node ">=20.9.0"`; elimina `autoprefixer` / `postcss` / `@tailwindcss/forms` legacy; scripts `check-runtime` y `build:web`) + `package-lock.json` regenerado (la única excepción de tamaño aprobada por el usuario; generado-only-resolution — contiene únicamente los cambios de resolución requeridos por este manifiesto; revisado junto con `package.json`; sin churn de lockfile no relacionado) + `scripts/check-runtime.mjs` (nuevo, Node ≥ 20.9.0) + `tsconfig.json` (modificado en su lugar; el predecesor ya creó el archivo en la raíz del repo en el PR 2a — PR 3a lo extiende con la config completa de Next.js / JSX / plugins y los aliases de ruta `@taxa/<capability>`; restaurado a su estado del predecesor en el rollback) + `.nvmrc` (nuevo, pin `20`) + `tests/test_toolchain_bootstrap.py` (nuevo) + `tests/test_check_runtime.py` (nuevo) | Nuevo | ~210 authored (≤ 400; la única `size:exception` es el `package-lock.json` regenerado; el trabajo authored de fuente/tests/config permanece ≤400) |
| 2 / 13 | PR 3b (bootstrap autocontenido de exportación estática del App Router) | tarea 3.1 (re-ambido) | `src/app/{layout,page}.tsx` (marcador semántico mínimo; **sin AppShell, sin import de `globals.css`**) + `next.config.mjs` + `tests/test_app_shell_render.py` (el testigo de `out/index.html` / viewport / preload Raleway es satisfacible aquí porque el toolchain está en vivo **y** el PR 3b no importa nada que el 3c o el 4b produzcan) | Nuevo (re-ambido) | ~150 (≤ 400) |
| 3 / 16 | PR 3c-a (tokens / base / modo oscuro) | tarea 3.2 + integración de 1 línea | `src/app/globals.css` (andamio inicial: `@import "tailwindcss"` + `@theme` reflejando cada token legacy `:root` / `[data-theme="dark"]` / `--realm-*` + placeholder vacío de `@layer base` para hijos posteriores) + `import "./globals.css";` añadido a `src/app/layout.tsx` (la corrección del defecto de dependencia — el 3c-a posee el archivo que importa) + `src/modules/design-system/{infrastructure/index.ts,presentation/Icon.tsx,presentation/Button.tsx}` + `tests/test_tailwind_4_tokens.py` + `tests/test_design_system_purity.py` | Nuevo | ~400 (≤ 400) |
| 4 / 16 | PR 3c-b (estilos de árbol + Overview inline) | tarea 3.2 (partición de selectores de taxonomía) | `src/app/globals.css` extendido con reglas de `@layer components` para el módulo taxonomy: `.taxa-tree`, `.tree-row`, `.kebab`, `.kebab-menu`, `.tree-search-icon`, `.materialize-indicator`, `.detail-panel`, `.tab-strip`, `.tab-button`, `.overview-tab`, `.breadcrumb` (kebab por fila, icono de búsqueda por fila, indicador de materialize por fila, familia monoespaciada del breadcrumb, styling del strip de 3 pestañas) + `tests/test_taxonomy_styles.py` | Nuevo | ~400 (≤ 400) |
| 5 / 16 | PR 3c-c (estilos de Search / Folder / Browser global) | tarea 3.2 (partición de selectores de research / chrome) | `src/app/globals.css` extendido con reglas de `@layer components` para el módulo research y el shell de chrome: `.search-tab`, `.search-category-section`, `.search-link-list`, `.search-link` (anchor `target="_blank"` / `rel="noopener noreferrer"`), `.folder-tab`, `.header-browser-tab` (Research / file explorer global, NO scoped por taxón), `.research-explorer`, `.file-explorer-pane`, `.file-viewer-pane` + `tests/test_research_styles.py` | Nuevo | ~400 (≤ 400) |
| 6 / 16 | PR 3c-d (animaciones / utilidades + paridad final) | tarea 3.2 (partición de animaciones / utilidades / paridad final) | `src/app/globals.css` extendido con `@keyframes` (`spin`), selectores de `color-mix()`, superficie de clases de utilidad (`bg-primary`, `text-on-surface`, `border-outline-variant`, `bg-surface-container-lowest`, `shadow-sm`, `rounded-r-md`, `bg-primary-fixed`, `text-on-primary-fixed`, …), regla `body { overscroll-behavior: none; … }`, reset `main > :first-child { margin-top: 0 !important; }` — todo bajo `@layer base` en orden de fuente + `tests/test_tailwind_4_parity.py` (test de paridad final consolidado parametrizado) | Nuevo | ~300 (≤ 400) |
| 7 / 16 | PR 3d (Makefile/mount) | tarea 3.4 (porción Makefile) + tarea 3.6 + 3.7 (repoint WEB_DIR + AC-21) | Reescritura de `Makefile::api` (corre `check-runtime.mjs` → `npm run build:web` → `uvicorn … --port 8765`; el `make css` legacy se vuelve shim no-op) + repoint de `api/server.py:54` WEB_DIR + `web/search_urls.js` → `src/data/search-engines.js` + actualización de `open()` de AC-21 + `tests/test_make_api_build.py` + `tests/test_static_mount.py` | Nuevo (fusionado) | ~240 (≤ 400) |
| 8 / 16 | PR 4a | tarea 4.1 + 4.2 | `src/modules/browser-state/{domain/keys.ts, infrastructure/store.ts, index.ts}` + 4 sitios de lectura + 4 de escritura dentro de `useEffect` | Nuevo | ~180 (≤ 400) |
| 9 / 16 | PR 4b (guardia de hidratación + integración de AppShell) | tarea 4.3 + 4.4 + costura de integración de AppShell | `useSyncExternalStore` detrás de flag `mounted` + aserción Playwright de cero warnings de hidratación + `src/app/{layout,page}.tsx` modificado para integrar `<AppShell>` desde `@taxa/app-shell` (la corrección del defecto de dependencia — el 4b posee tanto el módulo AppShell **como** la integración del host del App Router) | Nuevo | ~120 (≤ 400) |
| 10 / 16 | PR 5a | tarea 5.1 + 5.2 + 5.3 | `src/modules/taxonomy/{domain,application,infrastructure,presentation}` + port de `web/{tree,detail,breadcrumb}.js` + **strip de pestañas de `DetailPanel`** (`Overview` / `Search` / `Folder`, las tres siempre alcanzables; `Overview` siempre disponible según la política de usuario) + **`OverviewTab`** (nombre científico, estado de aceptación, autoría, conteo de especies) + **`Kebab`** con la acción `Search online` que **fuerza la pestaña `Search`** (cierra la regresión actual en vivo donde `Search online` aterriza en `Overview` para taxones de nivel superior); la capa de presentation de taxonomía se monta sobre los selectores de `@layer components` de PR 3c-b | Nuevo | ~310 (≤ 400) |
| 11 / 16 | PR 5b | tarea 5.4 + 5.5 + 5.6 | `src/modules/research/{domain,application,infrastructure,presentation}` + port de `web/{file_explorer,file_viewer,format,keymap}.js` + pin CDN + **`SearchTab`** con lista categorizada de enlaces salientes (`General` / `Taxonomic` / `Academic` / `Multimedia` / `Documents`, orden fijo) + **`FolderTab`** (indicador de materialize por taxón; **separado** de `SearchTab`) + presentador **`SearchLinkList`** que mapea cada `Engine` a un anchor con `target="_blank"`, `rel="noopener noreferrer"` + **pestaña `Browser` del header re-anclada como Research global / file explorer** (NO scoped por taxón; seleccionar un taxón mientras `Browser` está activo NO DEBE acotar el explorer); la capa de presentation de research se monta sobre los selectores de `@layer components` de PR 3c-c | Nuevo | ~395 (≤ 400, holgura ajustada; mantenibilidad rastreada) |
| 12 / 16 | PR 5c | tarea 5.7 + 5.8 + 5.9 | Actualizaciones de selectores Playwright + e2e + preservación del contrato `data-*` + borrar `web/*.{html,js,css}` (el borrado del `web/index.html` legacy retira el CSS inline legacy de 1.963 líneas que los cuatro hijos CSS migraron a `src/app/globals.css`) + `tailwind.config.js` | Nuevo | ~200 (≤ 400) |
| 13–15 / 16 | Fase 6a / 6b / 6c (validación) | NUEVO | Reconstrucción de baseline G5 / ensayo de cutover G6 / medición de paridad G4 Playwright + Lighthouse (trabajo de validación; sin código nuevo en `web/**`, handlers de ruta de `api/server.py`, ni `extension/**`) | Nuevo (medición) | ~190 + ~120 medición (≤ 400 cada uno) |
| 16 / 16 | PR 3e (cutover) | unidad de cutover atómico | El release de los cuatro conjuntos + inversión del cutover-manifest a Tier-2 + reejecución del verificador G3 Tier-2 + inversiones del status-footer para el cierre de G4 / G5 / G6 | Atómico | ~120 (≤ 400) |

### Orden de dependencia (contrato de la revisión correctiva del plan + corrección del defecto de dependencia + re-división del CSS)

- **PR 3a — bootstrap de toolchain**. Autocontenido.
- **PR 3b — bootstrap autocontenido de exportación estática
  del App Router** depende de 3a (deps instaladas + contrato
  Node ≥ 20.9.0). No importa nada que el 3c-a o el 4b
  produzcan.
- **PR 3c-a — tokens / base / modo oscuro** depende de 3a
  (`tailwindcss@^4` instalado) y de **3b** (el
  `src/app/layout.tsx` marcador en el que el PR 3c-a importa
  `./globals.css` — la corrección del defecto de dependencia
  mueve el import al sub-PR que posee el archivo). Crea
  `src/app/globals.css` (andamio inicial con `@theme` +
  placeholder vacío de `@layer base`) y envía el barrel de
  design-system.
- **PR 3c-b — estilos de árbol + Overview inline** depende
  de 3c-a (el andamio de `globals.css` + el placeholder de
  `@layer base` existen). Extiende `globals.css` con las
  reglas de `@layer components` para el módulo taxonomy.
- **PR 3c-c — estilos de Search / Folder / Browser global**
  depende de 3c-b (el bloque `@layer components` de taxonomía
  está en su lugar). Extiende `globals.css` con las reglas
  de `@layer components` para el módulo research y el shell
  de chrome.
- **PR 3c-d — animaciones / utilidades + paridad final**
  depende de 3c-c (el bloque `@layer components` de research
  / chrome está en su lugar). Finaliza `globals.css` con los
  `@keyframes`, `color-mix()`, clases de utilidad, reset de
  body y reset de primer hijo bajo `@layer base`; envía el
  test de paridad final consolidado
  `tests/test_tailwind_4_parity.py`.
- **PR 3d — Makefile/mount** depende de 3b
  (`next build` produce `out/index.html`) y de 3c-d
  (los tokens de Tailwind 4 + `@layer base` + `@layer
  components` fluyen a través de `next build`; el test de
  paridad final de Tailwind 4 está en disco).
- **PR 4a — typed store** depende de 3c-a (barrel de
  design-system cargado).
- **PR 4b — guardia de hidratación + integración de AppShell**
  depende de 4a (store disponible), **3b** (los marcadores
  `src/app/{layout,page}.tsx` en los que el PR 4b integra
  `<AppShell>` — la corrección del defecto de dependencia
  mueve la integración del AppShell al sub-PR que posee el
  módulo `app-shell`), y 3c-a (los tokens `@theme` de
  Tailwind 4 + barrel de design-system cargados para
  `next build`).
- **PR 5a — port de taxonomy** depende de 4b (lectura
  de estado segura de hidratación) y de 3c-b (el bloque
  `@layer components` de taxonomía está en su lugar — la
  capa de presentation de taxonomía se monta sobre el CSS
  de PR 3c-b).
- **PR 5b — port de research + pin CDN** depende de 5a
  (lectura de estado de taxonomía compartida), de 3d
  (`src/data/search-engines.js` para el export nombrado
  `Engine`), y de 3c-c (el bloque `@layer components` de
  research / chrome está en su lugar — la capa de
  presentation de research se monta sobre el CSS de PR
  3c-c).
- **PR 5c — e2e + borrar legacy** depende de 5b (todos los
  componentes UI en vivo) y de 3c-d (el test de paridad
  final de Tailwind 4 está en disco; el CSS inline legacy
  de 1.963 líneas ha sido migrado a `src/app/globals.css`
  de extremo a extremo y está listo para retirarse en PR
  5c).
- **PR 6a / 6b / 6c — validación** depende de 5c.
- **PR 3e — cutover atómico** depende de que las seis
  puertas estén verdes.

El sub-PR de cutover PR 3e se envía **solo cuando** las
seis puertas estén verdes; el apply worker está
bloqueado por los sub-PRs de cierre de G4 / G5 / G6 (3e
mismo aterriza después de las verificaciones de cierre).

---

## Archivos afectados (vista ejecutiva)

> **Revisión correctiva del plan del 2026-09-02**: las
> etiquetas de PR en esta tabla reflejan la cadena
> reordenada (bootstrap de toolchain en la posición 1,
> exportación estática del App Router en la posición 2,
> Tailwind/tokens en la posición 3, Makefile/mount
> fusionado en la posición 4).

| Área | Acción | Archivos |
| --- | --- | --- |
| `web/index.html` | Borrado en la activación (PR 5c) | `web/index.html` |
| `web/*.js` (18 módulos) | Borrados en la activación (PR 5c) | `web/{app,state,api,tree,breadcrumb,detail,nav,dom,banner,help,keymap,settings,search,file_explorer,file_viewer,format,search_urls}.js` |
| `web/index.css` | Borrado en la activación (PR 5c) | `web/index.css` |
| `web/dist/tailwind.css` | Regenerado por el `make css` revertido tras el rollback; no parte del nuevo build | `web/dist/tailwind.css` |
| `tailwind.config.js` | Borrado en la activación (PR 5c) | `tailwind.config.js` |
| `package.json` | Modificado (PR 3a, bootstrap de toolchain) — `next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss@^4`, toolchain TS, `engines.node ">=20.9.0"`; quita `autoprefixer`, `postcss`, `@tailwindcss/forms`; añade `scripts.check-runtime` y `scripts.build:web` | `package.json` |
| `package-lock.json` | Regenerado (PR 3a, bootstrap de toolchain) — única excepción de tamaño aprobada por el usuario; generado-only-resolution (sin contenido authored a mano); contiene únicamente los cambios de resolución requeridos por este manifiesto; revisado junto con `package.json`; sin churn de lockfile no relacionado | `package-lock.json` |
| `tsconfig.json` | Modificado en su lugar (PR 3a, bootstrap de toolchain) — config completa de Next.js / JSX / plugins superpuesta sobre el scaffold de strict-mode + aliases de ruta `@taxa/<capability>` del predecesor (el predecesor ya creó el archivo en la raíz del repo en el PR 2a; restaurado a su estado del predecesor en el rollback) | `tsconfig.json` |
| `.nvmrc` | Creado (PR 3a, bootstrap de toolchain) — pin `20` | `.nvmrc` |
| `scripts/check-runtime.mjs` | Creado (PR 3a, bootstrap de toolchain) — aplicación de Node ≥ 20.9.0 | nuevo |
| `tests/test_toolchain_bootstrap.py` | Creado (PR 3a, bootstrap de toolchain) — verifica deps, engines.node, scripts, aliases de ruta, .nvmrc | nuevo |
| `tests/test_check_runtime.py` | Creado (PR 3a, bootstrap de toolchain) — verifica los códigos de salida del piso Node ≥ 20.9.0 | nuevo |
| `src/app/{layout,page}.tsx` | Creados (PR 3b, bootstrap autocontenido de exportación estática del App Router) — **cuerpo marcador semántico mínimo**; **NO monta `<AppShell>`** (aterriza en PR 4b) **y NO importa `./globals.css`** (aterriza en PR 3c-a). PR 4b luego los modifica para integrar `<AppShell>` desde `@taxa/app-shell` | nuevos (3b) + modificados (4b) |
| `next.config.mjs` | Creado (PR 3b, exportación estática del App Router) — `output: "export"`, `images.unoptimized: true`, `trailingSlash: false`, `reactStrictMode: true` | nuevo |
| `tests/test_app_shell_render.py` | Creado (PR 3b, exportación estática del App Router) — lee `out/index.html` después de `next build`; verifica meta de viewport + preload Raleway + archivo Raleway `.woff2` en `out/_next/static/media/` | nuevo |
| `src/app/globals.css` | Creado (PR 3c-a, tokens / base / modo oscuro) — Tailwind 4 `@import "tailwindcss"` + `@theme` reflejando cada token legacy `:root` / `[data-theme="dark"]` / `--realm-*` + placeholder vacío de `@layer base`. PR 3c-a **también** añade `import "./globals.css";` a `src/app/layout.tsx` (la corrección del defecto de dependencia — el import vive con el archivo que importa). PR 3c-b extiende el archivo con reglas de `@layer components` de taxonomía; PR 3c-c extiende con reglas de `@layer components` de research / chrome; PR 3c-d finaliza con `@layer base` de `@keyframes` / `color-mix()` / utilidad / reset de body / reset de primer hijo | nuevo (3c-a) + extendido (3c-b / 3c-c / 3c-d) |
| `src/modules/design-system/{infrastructure/index.ts, presentation/Icon.tsx, presentation/Button.tsx}` | Creados (PR 3c-a, tokens / base / modo oscuro) — barrel de design-system | nuevos |
| `tests/test_tailwind_4_tokens.py` | Creado (PR 3c-a, tokens / base / modo oscuro) — enumera tokens legacy `:root` / `[data-theme="dark"]` / `--realm-*` contra `globals.css::@theme` | nuevo |
| `tests/test_design_system_purity.py` | Creado (PR 3c-a, tokens / base / modo oscuro) | nuevo |
| `tests/test_taxonomy_styles.py` | Creado (PR 3c-b, estilos de árbol + Overview inline) — enumera selectores de `@layer components` de taxonomía contra `globals.css` | nuevo |
| `tests/test_research_styles.py` | Creado (PR 3c-c, estilos de Search / Folder / Browser global) — enumera selectores de `@layer components` de research / chrome contra `globals.css` | nuevo |
| `tests/test_tailwind_4_parity.py` | Creado (PR 3c-d, animaciones / utilidades + paridad final) — test de paridad final consolidado parametrizado (cada token `:root` legacy, cada referencia `var(--token)`, cada clase de utilidad legacy, cada selector `@keyframes` / `color-mix()`) | nuevo |
| `Makefile` | Modificado (PR 3d, Makefile/mount) — el target `api` ejecuta `check-runtime.mjs` → `npm run build:web` → uvicorn; el `make css` legacy retirado a shim no-op | `Makefile` |
| `api/server.py` | Modificado (PR 3d, Makefile/mount) — reorientación de `WEB_DIR` en línea 54 únicamente; firma de montaje sin cambios | `api/server.py` |
| `src/data/search-engines.js` | Creado (PR 3d, Makefile/mount) — reemplaza a `web/search_urls.js` con export nombrado `SEARCH_ENGINES` | nuevo |
| `tests/test_make_api_build.py` | Creado (PR 3d, Makefile/mount) — verifica el orden de ejecución del Makefile y el piso de Node | nuevo |
| `tests/test_static_mount.py` | Creado (PR 3d, Makefile/mount) — verifica el repoint de `WEB_DIR` y el contrato de origen único | nuevo |
| `tests/test_smoke.py::test_search_engine_contract` | Modificado (PR 3d, Makefile/mount) — ruta de `open()` actualizada si el literal se movió; forma de bytes preservada | `tests/test_smoke.py` |
| `src/modules/browser-state/**` | Creado (PR 4a) — typed store + 4 sitios de lectura + 4 de escritura | nuevos |
| `tests/test_browser_state_keys.py` | Creado (PR 4a) | nuevo |
| `src/modules/app-shell/**` | Creado (PR 4b) — AppShell + page-chrome + guardia de hidratación. PR 4b **también** integra `<AppShell>` desde este módulo en `src/app/{layout,page}.tsx` (la corrección del defecto de dependencia — el PR 4b posee tanto el módulo AppShell **como** la integración del host del App Router; el layout/page marcador del PR 3b se reemplaza por la composición del AppShell integrada en 4b) | nuevos |
| `tests/test_hydration_console.py` | Creado (PR 4b) | nuevo |
| `src/modules/taxonomy/**` | Porteado (PR 5a) — port de `web/{tree,detail,breadcrumb}.js` a React + strip de pestañas de `DetailPanel` (`Overview` / `Search` / `Folder`, las tres siempre alcanzables; `Overview` siempre disponible según la política de usuario) + `OverviewTab` + menú `Kebab` con la acción `Search online` que fuerza la pestaña `Search` | nuevos |
| `tests/test_taxonomy_infra.py` | Creado (PR 5a) — más aserciones para el strip de tres pestañas, el contrato `Overview`-siempre-visible, y la fuerza kebab `Search online` → pestaña `Search` (cierra la regresión actual en vivo donde taxones de nivel superior aterrizan en `Overview`) | nuevo |
| `src/modules/research/**` | Porteado (PR 5b) — port de `web/{file_explorer,file_viewer,format,keymap}.js` + pin CDN + `SearchTab` con lista categorizada de enlaces salientes (`General` / `Taxonomic` / `Academic` / `Multimedia` / `Documents`) + `FolderTab` (separado) + presentador `SearchLinkList` + pestaña `Browser` del header re-anclada como Research global / file explorer (NO scoped por taxón) | nuevos |
| `tests/test_research_infra.py` | Creado (PR 5b) | nuevo |
| `tests/test_e2e_file_explorer.py` | Modificado (PR 5c) — selectores DOM actualizados; contrato `data-*` preservado | `tests/test_e2e_file_explorer.py` |
| `tests/test_web_toggle.py` | Modificado (PR 5c) — toggle de tema persiste vía store tipado | `tests/test_web_toggle.py` |
| `tests/test_evidence_baseline.py` | Modificado (PR 5c) — la aserción del roster legacy `web/*.js` volta a "ausente" | `tests/test_evidence_baseline.py` |
| `scripts/reconstruct_hydration_baseline.py` + `scripts/g5_close.sh` | Creados (Fase 6a) — cierre de baseline G5 | nuevos |
| `scripts/rehearse_cutover.py` + `tests/test_rehearse_cutover.py` | Creados (Fase 6b) — ensayo de cutover G6 + invariante fail-closed parametrizada | nuevos |
| `scripts/g4_measure.sh` + `out/g4-parity-report.json` | Creados (Fase 6c) — medición de paridad G4 Playwright + Lighthouse | nuevos |
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
| **Regresión de la estructura de pestañas del panel de detalle** (comportamiento actual en vivo): la acción kebab `Search online` aterriza en `Overview` en lugar de forzar `Search`, y `Browser` queda scoped al taxón seleccionado. | Media | El §"Superficie de UI y estructura de pestañas" del diseño ancla el contrato (Overview siempre disponible/visible; Search es una pestaña primaria; Search online → Search; Browser es Research global). Las tareas de PR 5a / PR 5b aseguran el comportamiento; el testigo Playwright en PR 5c cubre regresión. La interacción corregida cierra la regresión actual en la misma fase de apply que aterriza el cutover a React. |
| `Search` se degrada de pestaña primaria a lista de tarjetas secundaria. | Media | El diseño ancla `Search` como hermana de `Overview` / `Folder` dentro del strip de pestañas del panel de detalle; la narrativa del spec por dominio se actualiza a través de esta revisión de diseño (solo a nivel alto — los specs por dominio están fuera del alcance de esta revisión). El testigo Playwright del strip de pestañas en PR 5c asegura tres hermanas en el orden legacy. |

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

La **fase de tasks** (sdd-tasks) lee este diseño más el
`tasks.md`, `apply-progress.md` y `cutover-manifest.json`
del predecesor, luego autoriza las listas de archivos por
sub-PR para los 13 sub-PRs de arriba bajo la Aproximación
A dentro del presupuesto de revisión de 400 líneas por
sub-PR (la revisión correctiva del plan del 2026-09-02
reordenó la rebanada y re-ambó los PRs 3a–3d para que el
bootstrap de toolchain aterrice primero). La **fase de
apply** posee los sub-PRs de cierre de G4 / G5 / G6 y el
PR3e de cutover atómico. La **fase de archive** copia cada
spec por dominio literalmente a
`openspec/specs/{frontend-runtime,design-tokens,browser-state-hydration,frontend-bootstrap,research}/spec.md`
y promueve el spec modular-architecture al árbol de specs
canónico.