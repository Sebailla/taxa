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
| Puertas de evidencia | **G1, G2, G3 Tier-1, G5 PASS** (G1/G2/G3 Tier-1 trasladadas del predecesor; G5 PASS registrado bajo el protocolo de reemplazo aprobado por el usuario — DOMContentLoaded; ambos lados servidos por HTTP controlado; 1 warm-up + 9 corridas medidas por lado; agregación por mediana con muestras crudas y procedencia; tolerancia absoluta candidato − línea base ≤ 10 ms; captura fresca con mediana baseline `3.3 ms`, mediana candidato `3.2 ms`, delta `−0.1 ms`, umbral `10 ms`). **G3 Tier-2, G4 y G6 aún no son PASS**; la semántica de fallo del protocolo de reemplazo aprobado por el usuario (el fallo se mantiene bloqueado, sin PASS automático, sin PASS previo trasladado a través de un fallo) continúa atando cada reintento futuro de G5. |
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
- La topología de cadena de 16 hijos (tras el replan de la
  sub-secuencia del PR 3c que sustituyó al PR 3c original
  único por `3c-i` / `3c-ii` / `3c-iii` / `3c-iv`) se
  preserva; la estructura de pestañas y el comportamiento de
  forzar `Search` aterrizan dentro de los sub-PRs PR 5a (port
  de taxonomy) y PR 5b (port de research) existentes sin
  cambiar posiciones, dependencias, o sobres de LoC que
  empujarían la cadena por encima del
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
      reemplaza en la fase de apply bajo el **protocolo de reemplazo
      aprobado por el usuario** registrado en §"G5 — Línea base de
      hidratación" abajo (métrica observable `DOMContentLoaded`; ambos
      lados servidos por HTTP controlado; 1 warm-up + 9 corridas
      medidas por lado; agregación por mediana con muestras crudas y
      procedencia; tolerancia absoluta candidato − línea base ≤ 10 ms;
      el fallo se mantiene bloqueado y requiere una nueva solicitud).
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
| G5 (línea base de hidratación) | **PASS registrado — captura fresca bajo el protocolo de reemplazo aprobado por el usuario** (`scripts/g5_close.sh` exit 0; tanto el baseline como el candidato servidos por HTTP controlado — `http://127.0.0.1:64809/` y `http://127.0.0.1:64824/`; métrica observable `DOMContentLoaded`; 1 warm-up + 9 muestras medidas retenidas por lado; agregación por mediana por lado con muestras crudas y procedencia preservadas; tolerancia absoluta (candidato − línea base) ≤ 10 ms satisfecha — mediana baseline `3.3 ms`, mediana candidato `3.2 ms`, delta `−0.1 ms`, umbral `10 ms`; `baseline_source: "captured"` en `evidence/g5/status.json` y `source: "captured"` en `out/hydration-candidate.json`; `evidence/g5/status.json` registra `status: "ready"`, `regression: false`, sin `blocker`; `evidence/g5/regression-report.json` registra `pass: true` con el contrato completo de muestras/warmup/origen/mediana por lado y el delta absoluto). La regla previa de porcentaje/mediana 5+2 (baseline 0.0 / 3.0 ms vs candidato 1.0 / 4.0 ms; `initial_paint_delta_pct: Infinity`, `interaction_latency_delta_pct: 33.33%`; exit de comparación 4) está **superada** por este protocolo fresco y se retiene en el registro de cambios de `apply-progress.md` como historial de auditoría únicamente. **G5 está cerrada** bajo el protocolo de reemplazo aprobado por el usuario. | Fase 6a — `scripts/reconstruct_hydration_baseline.py` (captura HTTP del fixture legacy), `scripts/capture_hydration_candidate.py` (captura HTTP del candidato `out/`) y `scripts/g5_close.sh` (el arnés de runtime) produjeron juntos la evidencia del protocolo fresco registrada en `evidence/g5/{status,regression-report}.json`. El protocolo de reemplazo aprobado por el usuario registrado en §"G5 — Línea base de hidratación" abajo ata cada reintento futuro: el fallo se mantiene bloqueado, sin PASS automático, sin PASS previo trasladado a través de un fallo. |
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
| `tests/test_tailwind_4_parity.py` | CSS (PR 3c-i, rebanada de tokens `:root`) | Cada token `:root` / `[data-theme="dark"]` / `--realm-*` legacy resuelve a declaración no vacía en `globals.css::@theme`; extendido en PR 3c-ii / 3c-iii / 3c-iv para cubrir las superficies de taxonomía / browser / Search / Folder / `fex-*` / `@keyframes` / clases de utilidad |
| `tests/test_tailwind_4_tokens.py` | CSS (PR 3c-i) | Misma superficie que `test_tailwind_4_parity.py` rebanada de tokens `:root` — guardia de paridad co-localizada |
| `tests/test_taxonomy_styles.py` | CSS (PR 3c-ii) | Cada selector de taxonomía (`.taxa-tree`, `.tree-row`, `.kebab`, `.detail-panel`, `.tab-strip`, `.overview-tab`, `.breadcrumb`, …) resuelve a declaración no vacía |
| `tests/test_research_styles.py` | CSS (PR 3c-iii) | Cada selector de Search / Folder / global Browser (`.search-tab`, `.search-category-section`, `.search-link-list`, `.search-link`, `.folder-tab`, `.header-browser-tab`, `.research-explorer`, …) resuelve a declaración no vacía |
| `tests/test_design_system_purity.py` | CSS (PR 3c-iv) | Guardia de grep sobre `src/modules/design-system/`; sin literales hex fuera del módulo design-system |
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
| G5 (línea base de hidratación) | `scripts/measure_hydration.py` (ya autorizado) re-ejecutado bajo el **protocolo de reemplazo aprobado por el usuario** | JSON de línea base de hidratación + muestras crudas/procedencia | Métrica observable = `DOMContentLoaded`; tanto la línea base como el candidato servidos por HTTP controlado (sin `file://`); 1 warm-up + 9 corridas medidas por lado; agregación = mediana por lado con muestras crudas + procedencia preservadas; **absoluta (candidato − línea base) ≤ 10 ms**; el fallo se mantiene bloqueado, sin PASS automático |
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

    #### Slice 6c.0 — sub-slice solo de navegación (aterrizado, no cierra)

    El primer sub-slice de G4 entrega el productor solo de navegación.
    **No** es un G4 PASS — captura solo uno de los cinco reportes que
    espera el agregador `scripts/verify_parity.py`, y la compuerta
    permanece bloqueada hasta que aterricen los cuatro reportes restantes.

    - **Productor**: `tools/g4-capture/scripts/parity_navigation.mjs`
      (driver Playwright; dynamic-imported; `playwright@1.49.1` pinned
      aislado junto al `lighthouse@12.2.1` + `chrome-launcher@1.2.1`
      existente; sin cambios en dependencias raíz).
    - **CLI**: `--legacy-origin`, `--candidate-origin`, `--paths`
      (separados por coma), `--output-root`, `--manifest` opcional.
      Los puertos de producción NO están horneados.
    - **Disposición de salida**: `<outputRoot>/<UTC-timestamp>/{legacy,
      candidate}/{navigation.json,manifest.snapshot.json,run.json}`.
      El timestamp del run es `YYYY-MM-DDTHH-MM-SSZ` (filename-safe;
      los dos puntos se reemplazan con guión porque Windows los
      rechaza en componentes de path). El valor JSON `captured_at`
      usa la forma con precisión de segundos `YYYY-MM-DDTHH:MM:SSZ`
      según `scripts/verify_parity.py::ISO_FMT`.
    - **Esquema**: `navigation.json` coincide con la cabecera común
      versionada (`schema_version: "1.0.0"`, `captured_at`) más la
      lista de registros de navegación (`paths: [{path: str,
      status: int}, ...]`) que el agregador ya valida. El campo
      `schema` del lado del productor nombra el contrato específico
      del slice (`taxa.g4-parity.navigation/1`).
    - **Transporte**: ambos lados conducidos a través de HTTP
      controlado (solo `http(s)://`; `file://` y cualquier otro
      esquema explícitamente rechazados). Legacy y candidate DEBEN
      diferir — lados iguales se rechazan para que un candidato
      roto nunca pueda "pasar" silenciosamente contra sí mismo.
    - **Guardas fail-closed**: orígenes faltantes/inválidos, origen
      con componente de path, lados iguales, `paths` vacío, desajuste
      de path del manifest, 5xx o status `0` (error de red, timeout
      de navegación) en cualquier lado, drift de outcome por path
      entre lados, y un directorio `<outputRoot>/<UTC-timestamp>/`
      preexistente (guarda de colisión de salida). Cada guarda la
      ejercita un test hermético en `tests/test_capture_parity.py`.
    - **Tests herméticos**: 25 tests inyectan un `runFn` sintético
      (resultados `(path, status)` enlatados, throws, o casos de
      drift) y un `now()` fijo para que el productor corra sin
      navegador real ni red en vivo. El runner de Playwright se
      dynamic-importa dentro de `defaultRunNavigation` para que
      el arnés de tests permanezca libre de dependencias de
      navegador hasta que se ejercite el camino real.
    - **Reversión**: `git revert <6c-sha>` elimina el productor,
      los tests, el delta del Makefile, y el delta del lockfile.
      El slice 6c.1–6c.4 queda intacto. Sin flip G4 / G3 Tier-2 /
      cutover status.

### G5 — Línea base de hidratación

| Paso | Propietario | Salida |
| --- | --- | --- |
| Auditar `web/dist/evidence-baseline.json` para confirmar si la línea base legacy está en disco; bajo la regla previa de porcentaje/mediana, capturas reales comparables dieron veredictos `ready` / `blocked` / `blocked` con varianza de ±1 ms a 0–4 ms (la auditoría §3.3.5 del predecesor la lista como **no reproducible**). | Apply | Reporte de auditoría |
| Capturar la línea base legacy vía `scripts/measure_hydration.py` contra el fixture chromium legacy bajo el **protocolo de reemplazo aprobado por el usuario** | Apply | JSON de hidratación legacy |
| Si no es reproducible bajo el nuevo protocolo: reconstruir desde paint inicial de `web/index.html` + `delta_server_to_tree_first_paint_ms` legacy documentado en `design.md::§"Migration Evidence Baseline"`, sirviendo por HTTP controlado | Apply | JSON de línea base reconstruida |
| Re-ejecutar `scripts/measure_hydration.py` contra el nuevo build bajo el protocolo aprobado | Apply | JSON de hidratación nueva |
| Bajo el protocolo aprobado: `mediana(candidato) − mediana(línea base) ≤ 10 ms`; el fallo se mantiene bloqueado y requiere una nueva solicitud (sin PASS automático, sin cierre, sin activación de cutover). | Apply | Inversión/actualización de estado |

**Protocolo de reemplazo de G5 aprobado por el usuario (registrado aquí como registro canónico del diseño; aprobado tras la inestabilidad de G5 bajo la regla previa, pero no es una captura de G5 ni una autorización de PASS).** Capturas reales comparables bajo la regla previa de porcentaje empírico + mediana dieron veredictos `ready`, `blocked` y `blocked`: a 0–4 ms, las mediciones de cada corrida pueden moverse ±1 ms, por lo que la regla previa no es reproducible. El protocolo de reemplazo aprobado por el usuario que sigue **supera** esa regla y ata cada reintento de G5.

- **Transporte — ambos lados servidos por HTTP controlado.** El fixture de línea base legacy y el build candidato se sirven a través de un servidor HTTP estático local en proceso (sin URIs `file://`). El servicio HTTP es el mismo transporte HTTP controlado para ambos lados; la única diferencia es el directorio servido (fixture legacy vs. `out/` del candidato). Esto elimina la deriva de origen de reloj por `file://` de la comparación.
- **Métrica observable — `DOMContentLoaded`.** El evento observable nombrado es la marca de tiempo `DOMContentLoaded` del navegador, capturada vía la API PerformanceNavigationTiming sobre el servicio HTTP controlado. `DOMContentLoaded` reemplaza al par previo de paint-inicial + latencia-de-interacción, que estaba dominado por ruido sub-milisegundo a la escala de 0–4 ms.
- **Muestreo — 1 warm-up + 9 corridas medidas por lado.** Cada lado (línea base legacy, candidato) ejecuta exactamente **1 corrida de warm-up** seguida de **9 corridas medidas**. El warm-up prepara la caché del navegador y el JIT; solo las 9 corridas medidas contribuyen a la agregación. Total por lado: 10 navegaciones (1 warm-up + 9 medidas). Los conteos de muestra están pineados en el script de medición y afirmados en el validador.
- **Agregación — mediana por lado, muestras crudas + procedencia preservadas.** Para cada lado, el valor de `DOMContentLoaded` por corrida a lo largo de las 9 corridas medidas se agrega como la **mediana** (no la media), porque la mediana es robusta a un único outlier y coincide con la intención declarada de la regla previa. El artefacto debe persistir **cada muestra cruda** más la **procedencia por corrida** (versión del navegador, SHA del build, ruta, marca de tiempo de captura, entorno de captura) junto a la mediana calculada. Sin submuestreo, sin resumen sin muestras crudas.
- **Tolerancia — absoluta (candidato − línea base) ≤ 10 ms.** La regla de PASS/fallo es una única tolerancia absoluta en milisegundos: `mediana(candidato) − mediana(línea base) ≤ 10 ms`. No hay umbral porcentual ni holgura en dirección negativa: cualquier regresión positiva de la mediana mayor a 10 ms es un fallo. El tope de 10 ms es el límite absoluto; las deltas absolutas menores pasan.
- **Semántica de fallo — se mantiene bloqueada, nunca un PASS automático.** Una corrida fallida bajo este protocolo **no** invierte G5 a PASS, **no** concede cierre, **no** levanta la tolerancia, y **no** autoriza activación de cutover. El status-footer permanece `blocked`. Un reintento posterior requiere una **nueva solicitud del usuario** (una nueva captura se inicia solo bajo solicitud explícita); el protocolo aprobado no se re-ejecuta automáticamente, y un PASS previo nunca se traslada a través de un fallo.
- **Predecesor congelado.** Este protocolo supera a la **solicitud** previa de excepción metodológica; **no** modifica `openspec/changes/migrate-nextjs-tailwind4/**`. Los scripts bajo `scripts/` (ya autorizados: `scripts/reconstruct_hydration_baseline.py`, `scripts/capture_hydration_candidate.py`, `scripts/measure_hydration.py`, `scripts/g5_close.sh`) y `tests/test_hydration_timing.py` se extienden en la fase de apply para atar el protocolo de arriba; este diseño registra el protocolo, el apply worker extiende el arnés.
- **Cierre de G5 bajo este protocolo.** El protocolo de arriba fue atado por una captura fresca (capturada el `2026-09-07T15:41:38Z`; ver la entrada del registro de cambios del 2026-09-07 en `apply-progress.md`): `scripts/g5_close.sh` exit `0`; tanto el baseline como el candidato servidos por HTTP controlado (`baseline_origin: "http://127.0.0.1:64809/"`, `candidate_origin: "http://127.0.0.1:64824/"`); 1 warm-up + 9 muestras medidas retenidas por lado; agregación por mediana por lado con muestras crudas y procedencia preservadas; tolerancia absoluta (candidato − línea base) ≤ 10 ms satisfecha — mediana baseline `3.3 ms`, mediana candidato `3.2 ms`, delta `−0.1 ms`, umbral `10 ms`. `evidence/g5/status.json` registra `status: "ready"`, `regression: false`, sin `blocker`; `evidence/g5/regression-report.json` registra `pass: true` con el contrato completo de muestras/warmup/origen/mediana por lado y el delta absoluto. **G5 está cerrada** bajo este protocolo. La regla previa de porcentaje/mediana 5+2 (la comparación porcentual `initial_paint_delta_pct` / `interaction_latency_delta_pct`; medianas baseline 0.0 / 3.0 ms vs candidato 1.0 / 4.0 ms; exit de comparación 4) está **superada** por este protocolo y la evidencia del protocolo fresco; se retiene en el registro de cambios de `apply-progress.md` como historial de auditoría únicamente. La semántica de fallo-bloqueado / nueva-solicitud / sin-PASS-trasladado-a-través-de-un-fallo de arriba continúa atando cada **reintento futuro** de G5 — una corrida fallida subsiguiente se mantiene bloqueada, requiere una nueva solicitud del usuario, y nunca traslada el PASS previo a través de un fallo.

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
> PR 3c original). El orden corregido instaló el toolchain
> primero (posición 1), degradó la exportación estática
> del App Router a la posición 2 (ahora satisfacible),
> mantuvo Tailwind/tokens en la posición 3, fusionó la
> reescritura del Makefile con el repoint de `WEB_DIR` +
> AC-21 en un único sub-PR en la posición 4, y siguió con
> state, ports, e2e, validación y cutover atómico. El
> conteo de 13 hijos se preservó en esa revisión. Las
> listas de archivos por tarea completas y la justificación
> de corrección de dependencias viven en `tasks.md`; esta
> tabla es la vista ejecutiva.

> **2026-09-02 — replan de la sub-secuencia del PR 3c (esta
> entrada)**. Después de que PR #144 (3a), PR #145 (3b) y
> PR #146 (reconciliación de 3b) aterrizaran en el tracker,
> el PR 3c único original en la posición 3 fue diagnosticado
> como insatisfacible: reclamaba ~230 LoC mientras el bloque
> `<style>` inline legacy en `web/index.html` (líneas 14–1972
> = **1.963 líneas**) tenía que portarse literalmente a
> Tailwind 4 (`@theme` para tokens, `@layer base` para la
> cascada, más el barrel de design-system). El usuario
> autorizó una sub-secuencia encadenada que reemplaza el
> PR 3c único con **cuatro hijos revisables en las
> posiciones 3–6** (`3c-i` tokens / base / dark mode,
> `3c-ii` styling de árbol / detalle de taxonomía,
> `3c-iii` styling de Search / Folder / global Browser,
> `3c-iv` animations / utilities + paridad CSS final +
> barrel de design-system), cada uno ≤ 400 líneas
> authored incluyendo tests. Los hijos restantes se
> **renumeran** (`3d → 7`, `4a → 8`, `4b → 9`,
> `5a → 10`, `5b → 11`, `5c → 12`, `6a → 13`,
> `6b → 14`, `6c → 15`, `3e → 16`) para mantener el
> contrato de dependencia lineal. **PR 3c-i apunta al
> tracker** (la rama
> `docs/complete-taxa-frontend-migration-plan`
> **después** de que la reconciliación del PR #146 se
> fusione, recogiendo el 3a + 3b + reconcile ya fusionados
> sin un paso extra de reconciliación); cada hijo
> posterior apunta a su rama predecesora inmediata. El
> total authored en LoC sube de ~2.245 a ~3.485 porque
> cada regla CSS legacy se porta; el sub-PR nuevo más
> grande es **3c-i a ~390 LoC** (-10 LoC de holgura bajo
> 400). PR 3a retiene la `size:exception` de
> `package-lock.json` regenerado (generated-resolution-only)
> como la `size:exception` documentada previa;
> **PR 3c-ii abre subsecuentemente una segunda
> `size:exception` aprobada por el usuario** para
> la rebanada completa de CSS de árbol / detalle de
> taxonomía (la implementación real totaliza **822
> insertions + 9 deletions = 831 LoC**, sobrepasando
> la estimación previa de `~380 LoC` en +442 LoC y
> el presupuesto de revisión por PR de 400
> líneas en +431 LoC — véase el addendum append-only dedicado
> abajo para la justificación de autorización y la
> estimación corregida; la cadena de 16 hijos se
> preserva). **El Enfoque A, FastAPI/SQLite, el
> predecesor congelado y la estrategia de Feature
> Branch Chain quedan sin cambios.**

El `tasks.md` del predecesor enumeraba 35 tareas a través
de 14+ sub-PRs. La cadena corregida las re-rebana bajo la
Aproximación A dentro del presupuesto de revisión de 400
líneas por sub-PR.

| Posición | Sub-PR | Mapeo de tarea del predecesor | Alcance | Nuevo / preservado | Presupuesto LoC |
| --- | --- | --- | --- | --- | --- |
| 1 / 16 | PR 3a (bootstrap de toolchain) | NUEVO (absorbe parte de la tarea 3.4 original — reescritura de `package.json` + `scripts/check-runtime.mjs`) | Pines de deps de `package.json` (`next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss@^4`, toolchain TS, `engines.node ">=20.9.0"`; elimina `autoprefixer` / `postcss` / `@tailwindcss/forms` legacy; scripts `check-runtime` y `build:web`) + `package-lock.json` regenerado (la única excepción de tamaño aprobada por el usuario **para el lockfile regenerado de este PR**; generado-only-resolution — contiene únicamente los cambios de resolución requeridos por este manifiesto; revisado junto con `package.json`; sin churn de lockfile no relacionado; **PR 3c-ii es la segunda `size:exception` aprobada por el usuario** para el sobrepaso de LoC authored — véase el addendum append-only dedicado abajo) + `scripts/check-runtime.mjs` (nuevo, Node ≥ 20.9.0) + `tsconfig.json` (modificado en su lugar; el predecesor ya creó el archivo en la raíz del repo en el PR 2a — PR 3a lo extiende con la config completa de Next.js / JSX / plugins y los aliases de ruta `@taxa/<capability>`; restaurado a su estado del predecesor en el rollback) + `.nvmrc` (nuevo, pin `20`) + `tests/test_toolchain_bootstrap.py` (nuevo) + `tests/test_check_runtime.py` (nuevo) | Nuevo | ~210 authored (≤ 400; la única `size:exception` **para el lockfile regenerado de este PR** es el `package-lock.json` regenerado; el trabajo authored de fuente/tests/config permanece ≤400 — **PR 3c-ii es la segunda `size:exception` aprobada por el usuario** para el sobrepaso de LoC authored, véase el addendum abajo). **Fusionado como PR #144 en el tracker.** |
| 2 / 16 | PR 3b (exportación estática del App Router) | tarea 3.1 (re-ambido) | `src/app/{layout,page}.tsx` + `next.config.mjs` + `tests/test_app_shell_render.py` (el testigo de `out/index.html` es satisfacible aquí porque el toolchain está en vivo) | Nuevo (re-ambido) | ~175 (≤ 400). **Fusionado como PR #145 en el tracker, con la reconciliación PR #146 también fusionada.** |
| 3 / 16 | PR 3c-i (tokens / base / dark mode) | tarea 3.2 (rebanada 1) | `src/app/globals.css` (nuevo, `@import "tailwindcss"` + bloque `@theme` con cada token `:root` legacy + cascada `[data-theme="dark"]` + familia `--realm-*`) + `@layer base` (resets de body / html / `main > :first-child` + selectores focus-visible globales) + `tests/test_tailwind_4_parity.py` (rebanada de tokens `:root`) | Nuevo | ~390 (≤ 400; -10 LoC de holgura) |
| 4 / 16 | PR 3c-ii (styling de árbol / detalle de taxonomía) | tarea 3.2 (rebanada 2) | `src/app/globals.css` (extendido, selectores de taxonomía: `.tier-header`, `.tree-row`, `.rank-badge`, `.scientific-name`, `.tree-source-toggle`, `#detail-panel`, `.detail-card`, `.detail-section`, `.overview-section`, `.detail-item`, `.search-pulse`, `.detail-tabs`, `.search-icon-btn`, `.materialize-btn`, kebab, modal de materialize, variantes `.tree-row[data-realm="…"]` teñidas por realm) + `tests/test_tailwind_4_parity.py` (rebanada de selectores de taxonomía) | Nuevo | **831 reales (822 inserciones + 9 deletions)** — **`size:exception` aprobada por el usuario** (sobrepaso +431 LoC contra el presupuesto de 400 líneas); la estimación previa de `~380 LoC` subestimó las variantes teñidas por realm + los selectores kebab/modal + la enumeración del test de paridad. Véase el addendum abajo para la justificación de autorización; la cadena de 16 hijos se preserva. |
| 5 / 16 | PR 3c-iii (styling de Search / Folder / global Browser) | tarea 3.2 (rebanada 3) | `src/app/globals.css` (extendido, selectores de Browser / search / folder: `.toast`, `.search-engines-grid`, `.search-category-header`, `.search-engine-btn`, `.fex-meta-strip`, `.fex-tab-strip`, `.fex-snippet-frame`, `.fex-shell`, `.fex-tree-pane`, `.fex-viewer-pane`, `.fex-splitter`, `.fex-row`, `.fex-tree-header`, `.fex-children`, `.fex-banner`, `.fex-empty-state`, `.fex-search-*`, `.fex-csv-*`, `.fex-json-*`, `.fex-tree-truncated`) + `tests/test_tailwind_4_parity.py` (rebanada de selectores de Browser) | Nuevo | ~390 (≤ 400; -10 LoC de holgura) |
| 6 / 16 | PR 3c-iv (animations / utilities + paridad CSS final + barrel del design-system) | tarea 3.2 (rebanada 4) + tarea 3.3 barrel del design-system del predecesor | `src/app/globals.css` (extendido, reglas `@keyframes`, `.animate-spin`, frames del visor de imagen / video, selectores de la vista de Settings) + `src/modules/design-system/{infrastructure/index.ts,presentation/Icon.tsx,presentation/Button.tsx}` + `tests/test_tailwind_4_parity.py` (enumeración de `@keyframes` + clases utility) + `tests/test_design_system_purity.py` | Nuevo | ~280 (≤ 400; -120 LoC de holgura) |
| 7 / 16 | PR 3d (Makefile/mount) | tarea 3.4 (porción Makefile) + tarea 3.6 + 3.7 (repoint WEB_DIR + AC-21) | Reescritura de `Makefile::api` (corre `check-runtime.mjs` → `npm run build:web` → `uvicorn … --port 8765`; el `make css` legacy se vuelve shim no-op) + repoint de `api/server.py:54` WEB_DIR + `web/search_urls.js` → `src/data/search-engines.js` + actualización de `open()` de AC-21 + `tests/test_make_api_build.py` + `tests/test_static_mount.py` | Nuevo (fusionado) | ~240 (≤ 400) |
| 8 / 16 | PR 4a | tarea 4.1 + 4.2 | `src/modules/browser-state/{domain/keys.ts, infrastructure/store.ts, index.ts}` + 4 sitios de lectura + 4 de escritura dentro de `useEffect` | Nuevo | ~180 (≤ 400) |
| 9 / 16 | PR 4b | tarea 4.3 + 4.4 | `useSyncExternalStore` detrás de flag `mounted` + aserción Playwright de cero warnings de hidratación | Nuevo | ~90 (≤ 400) |
| 10 / 16 | PR 5a | tarea 5.1 + 5.2 + 5.3 | `src/modules/taxonomy/{domain,application,infrastructure,presentation}` + port de `web/{tree,detail,breadcrumb}.js` | Nuevo | ~280 (≤ 400) |
| 11 / 16 | PR 5b | tarea 5.4 + 5.5 + 5.6 | `src/modules/research/{domain,application,infrastructure,presentation}` + port de `web/{file_explorer,file_viewer,format,keymap}.js` + pin CDN | Nuevo | ~360 (≤ 400) |
| 12 / 16 | PR 5c | tarea 5.7 + 5.8 + 5.9 | Actualizaciones de selectores Playwright + e2e + preservación del contrato `data-*` + borrar `web/*.{html,js,css}` + `tailwind.config.js` | Nuevo | ~200 (≤ 400) |
| 13–15 / 16 | Fase 6a / 6b / 6c (validación) | NUEVO | Reconstrucción de baseline G5 / ensayo de cutover G6 / medición de paridad G4 Playwright + Lighthouse (trabajo de validación; sin código nuevo en `web/**`, handlers de ruta de `api/server.py`, ni `extension/**`) | Nuevo (medición) | ~190 + ~120 medición (≤ 400 cada uno) |
| 16 / 16 | PR 3e (cutover) | unidad de cutover atómico | El release de los cuatro conjuntos + inversión del cutover-manifest a Tier-2 + reejecución del verificador G3 Tier-2 + inversiones del status-footer para el cierre de G4 / G5 / G6 | Atómico | ~120 (≤ 400) |

### Orden de dependencia (contrato de la revisión correctiva del plan + replan de la sub-secuencia del PR 3c)

- **PR 3a — bootstrap de toolchain**. Autocontenido.
- **PR 3b — exportación estática del App Router** depende
  de 3a (deps instaladas + contrato Node ≥ 20.9.0).
- **PR 3c-i — tokens / base / dark mode** depende de 3a
  (`tailwindcss@^4` instalado). **Apunta al tracker
  después de que PR #146 se fusione**, recogiendo el
  3a + 3b + reconcile ya fusionados.
- **PR 3c-ii — styling de árbol / detalle de taxonomía**
  depende de 3c-i (capa de token + base en vivo, de modo
  que cada selector en esta rebanada resuelve las
  referencias `var(--token)`).
- **PR 3c-iii — styling de Search / Folder / global Browser**
  depende de 3c-ii (selectores de taxonomía en vivo;
  selectores de Browser resuelven).
- **PR 3c-iv — animations / utilities + paridad CSS final**
  depende de 3c-iii (cascada CSS legacy completa portada
  excepto `@keyframes` + utilities + barrel del
  design-system).
- **PR 3d — Makefile/mount** depende de 3c-iv (cascada
  completa de Tailwind 4 portada de modo que `next build`
  produce un payload CSS completo) y de 3b (el App Router
  produce `out/index.html` cuando `next build` corre).
- **PR 4a — typed store** depende de 3c-iv (módulo
  design-system cargado).
  cargado).
- **PR 4b — guardia de hidratación** depende de 4a
  (store disponible) y de 3b (host AppShell + slot de
  flag `mounted`).
- **PR 5a — port de taxonomy** depende de 4b (lectura
  de estado segura de hidratación) y de 3c-ii (los
  selectores de taxonomía están en su lugar — la capa de
  presentation de taxonomía se monta sobre el CSS de
  PR 3c-ii).
- **PR 5b — port de research + pin CDN** depende de 5a
  (lectura de estado de taxonomía compartida), de 3d
  (`src/data/search-engines.js` para el export nombrado
  `Engine`), y de 3c-iii (los selectores de Search /
  Folder / global Browser están en su lugar — la capa de
  presentation de research se monta sobre el CSS de
  PR 3c-iii).
- **PR 5c — e2e + borrar legacy** depende de 5b (todos los
  componentes UI en vivo) y de 3c-iv (el test de paridad
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
| `package-lock.json` | Regenerado (PR 3a, bootstrap de toolchain) — única excepción de tamaño aprobada por el usuario **para el lockfile regenerado**; generado-only-resolution (sin contenido authored a mano); contiene únicamente los cambios de resolución requeridos por este manifiesto; revisado junto con `package.json`; sin churn de lockfile no relacionado. **El cambio carga una segunda `size:exception` aprobada por el usuario en PR 3c-ii** (831 reales vs. estimación de ~380 LoC; sobrepaso +431 contra el presupuesto de 400 líneas; véase el addendum append-only dedicado abajo para la justificación de autorización) | `package-lock.json` |
| `tsconfig.json` | Modificado en su lugar (PR 3a, bootstrap de toolchain) — config completa de Next.js / JSX / plugins superpuesta sobre el scaffold de strict-mode + aliases de ruta `@taxa/<capability>` del predecesor (el predecesor ya creó el archivo en la raíz del repo en el PR 2a; restaurado a su estado del predecesor en el rollback) | `tsconfig.json` |
| `.nvmrc` | Creado (PR 3a, bootstrap de toolchain) — pin `20` | `.nvmrc` |
| `scripts/check-runtime.mjs` | Creado (PR 3a, bootstrap de toolchain) — aplicación de Node ≥ 20.9.0 | nuevo |
| `tests/test_toolchain_bootstrap.py` | Creado (PR 3a, bootstrap de toolchain) — verifica deps, engines.node, scripts, aliases de ruta, .nvmrc | nuevo |
| `tests/test_check_runtime.py` | Creado (PR 3a, bootstrap de toolchain) — verifica los códigos de salida del piso Node ≥ 20.9.0 | nuevo |
| `src/app/{layout,page}.tsx` | Creados (PR 3b, bootstrap autocontenido de exportación estática del App Router) — **cuerpo marcador semántico mínimo**; **NO monta `<AppShell>`** (aterriza en PR 4b) **y NO importa `./globals.css`** (aterriza en PR 3c-i). PR 4b luego los modifica para integrar `<AppShell>` desde `@taxa/app-shell` | nuevos (3b) + modificados (4b) |
| `next.config.mjs` | Creado (PR 3b, exportación estática del App Router) — `output: "export"`, `images.unoptimized: true`, `trailingSlash: false`, `reactStrictMode: true` | nuevo |
| `tests/test_app_shell_render.py` | Creado (PR 3b, exportación estática del App Router) — lee `out/index.html` después de `next build`; verifica meta de viewport + preload Raleway + archivo Raleway `.woff2` en `out/_next/static/media/` | nuevo |
| `src/app/globals.css` | Creado (PR 3c-i, tokens / base / dark mode) — Tailwind 4 `@import "tailwindcss"` + `@theme` reflejando cada token legacy `:root` / `[data-theme="dark"]` / `--realm-*` + bloque inicial de `@layer base` con resets body / html / `main > :first-child` + selectores `:focus-visible` globales. PR 3c-i **también** añade `import "./globals.css";` a `src/app/layout.tsx` (la corrección del defecto de dependencia — el import vive con el archivo que importa). PR 3c-ii extiende el archivo con selectores de taxonomía; PR 3c-iii extiende con selectores de Search / Folder / global Browser; PR 3c-iv finaliza con `@keyframes` / `color-mix()` / utilidad / frames de viewer / Settings / `body { overscroll-behavior: none; }` / `main > :first-child { margin-top: 0 !important; }` | nuevo (3c-i) + extendido (3c-ii / 3c-iii / 3c-iv) |
| `src/modules/design-system/{infrastructure/index.ts, presentation/Icon.tsx, presentation/Button.tsx}` | Creados (PR 3c-iv, animations / utilities + paridad CSS final + barrel del design-system) — barrel de design-system `<Icon>` (envoltorio de glyphs Material Symbols Outlined) + primitiva de layout `<Button>` | nuevos |
| `tests/test_tailwind_4_parity.py` | Creado (PR 3c-i) + extendido en PR 3c-ii / 3c-iii / 3c-iv. Enumera cada token legacy `:root`, cada referencia `var(--name)`, cada selector `--realm-*`, cada regla `@keyframes`, cada clase de utilidad legacy, cada selector de taxonomía / browser / search / folder / viewer, y cada selector de Settings / viewer frame, verificando declaraciones no vacías en `src/app/globals.css` y `out/_next/static/chunks/*.css` | nuevo (archivo), extendido (3c-ii / 3c-iii / 3c-iv) |
| `tests/test_design_system_purity.py` | Creado (PR 3c-iv, animations / utilities + paridad CSS final + barrel del design-system) — guardia de grep sobre literales hex en `src/` | nuevo |
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
| El protocolo previo de G5 (porcentaje/mediana) es inestable a 0–4 ms; capturas reales comparables dieron veredictos **`ready` / `blocked` / `blocked`** con movimiento de ±1 ms. | **Retirada / superada** | La disposición de riesgo de Fase 6a fue una **solicitud** de excepción metodológica que ha sido **superada por el protocolo de reemplazo de G5 aprobado por el usuario** registrado en §"G5 — Línea base de hidratación" abajo Y atada por la captura fresca bajo ese protocolo. La evidencia del protocolo fresco (métrica observable `DOMContentLoaded`; ambos lados servidos por HTTP controlado — `http://127.0.0.1:64809/` y `http://127.0.0.1:64824/`; 1 warm-up + 9 muestras medidas retenidas por lado; agregación por mediana por lado con muestras crudas y procedencia preservadas; tolerancia absoluta (candidato − línea base) ≤ 10 ms satisfecha; mediana baseline `3.3 ms`, mediana candidato `3.2 ms`, delta `−0.1 ms`, umbral `10 ms`) está registrada en `openspec/changes/complete-taxa-frontend-migration/evidence/g5/{status,regression-report}.json`. G5 está **PASS registrada / cerrada** bajo el protocolo de reemplazo aprobado por el usuario; la regla previa de porcentaje/mediana 5+2 se retiene en el registro de cambios de `apply-progress.md` como historial de auditoría únicamente. |
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
fase de apply. G5 (línea base de hidratación) **PASS
registrado / cerrada — captura fresca bajo el protocolo de
reemplazo aprobado por el usuario** (`scripts/g5_close.sh` exit
0; tanto el baseline como el candidato servidos por HTTP
controlado — `http://127.0.0.1:64809/` y `http://127.0.0.1:64824/`;
métrica observable `DOMContentLoaded`; 1 warm-up + 9 muestras
medidas retenidas por lado; agregación por mediana por lado con
muestras crudas y procedencia preservadas; tolerancia absoluta
(candidato − línea base) ≤ 10 ms satisfecha — mediana baseline
`3.3 ms`, mediana candidato `3.2 ms`, delta `−0.1 ms`, umbral
`10 ms`; `baseline_source: "captured"` en `evidence/g5/status.json`
y `source: "captured"` en `out/hydration-candidate.json`;
`evidence/g5/status.json`
registra `status: "ready"`, `regression: false`, sin `blocker`;
`evidence/g5/regression-report.json` registra `pass: true` con
el contrato completo de muestras/warmup/origen/mediana por lado
y el delta absoluto). La regla previa de porcentaje/mediana
5+2 (el baseline previo 0.0 / 3.0 ms vs candidato 1.0 / 4.0 ms;
regresión en ambos ejes; exit de comparación 4) está
**superada** por este protocolo fresco y se retiene en el
registro de cambios de `apply-progress.md` como historial de
auditoría únicamente. La **solicitud** de excepción metodológica
registrada en entradas previas del registro de cambios está
superada por el protocolo de reemplazo aprobado por el usuario
y la evidencia del protocolo fresco. G5 permanece sujeta al
protocolo de reemplazo aprobado por el usuario: el fallo se
mantiene bloqueado, sin PASS automático, sin PASS previo
trasladado a través de un fallo. G6 (ensayo de cutover)
**bloqueada — verificador no autorizado**; debe cerrarse en la
fase de apply. Predecesor
`openspec/changes/migrate-nextjs-tailwind4/**` congelado. Ninguna
activación de FastAPI en esta pasada de diseño; el PR3e de cutover
atómico se envía solo cuando las seis puertas estén verdes.

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
  cabalga sobre los selectores de taxonomía de PR 3c-ii. Sin
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
  selectores de Search / Folder / global Browser de PR 3c-iii. Sin `SearchTab` /
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

---

## Addenda — 2026-09-07: PR 5c.1a fundación tipada de browser-state (aterrizada); 5c.1b + 5c.2 diferidas (solo anexo)

- **PR 5c.1a aterrizada (esta entrada, supersede la enumeración previa de sub-PRs de Fase 5c para el próximo worktree de código)**. La enumeración de siete PRs de Fase 5c (`5c.1 R / 5c.2 R / 5c.3 G / 5c.4 G / 5c.5 T / 5c.6 G / 5c.7 Refactor`) colapsa en una única rebanada **`5c.1b` (diferida)** de UI y la rebanada de fundación tipada `5c.1a` (registrada como **aterrizada**). `5c.1a` añade la llave booleana `versionBannerDismissed: "taxa.settings.versionBannerDismissed"` + `TreeSource` `col | worms | freshwater` a `domain/keys.ts` y restaura el contrato de llamadas de almacenamiento **5 + 5** de `getItem(` / `setItem(` en `infrastructure/store.ts`. La evidencia completa vive en `apply-progress-es.md` §registro de cambios entrada "2026-09-07 — PR 5c.1a: fundación tipada de browser-state aterrizada"; `5c.1b` y `5c.2` están diferidas. **G4 permanece bloqueada.** El espejo en español carga la misma semántica; cualquier deriva se resuelve a favor del inglés. Sin React, sin tests E2E, sin selectores de fuente, sin features de research, sin salidas de build, sin commit/push.

## Addenda — 2026-09-07: PR 5c.1b-A UI de fuente de árbol + ids de nav/breadcrumb (aterrizada); 5c.1b-B + 5c.2 diferidas (solo anexo)

- **PR 5c.1b-A aterrizada (esta entrada, divide la `5c.1b` diferida previa en A aterrizada + B diferida)**. La rebanada de UI `5c.1b` se divide en **`5c.1b-A` (aterrizada)** + **`5c.1b-B` (diferida)** + **`5c.2` (diferida)**. `5c.1b-A` aterriza la UI de fuente de árbol en `page-chrome.tsx` (`#tree-source-toggle` con tres botones `data-tree-source="col|worms|freshwater"`, `aria-pressed` por botón, `setTreeSource` en click), los ids de React en los botones de nav existentes (`nav-browser` / `nav-classification` / `nav-settings`) y Breadcrumb (`id="breadcrumb"`), y el cableado de contexto de store único (`useBrowserStateStore` exportado desde `@taxa/app-shell`; `page.tsx` se suscribe vía `useSyncExternalStore`; `source: "col"` ya no está hard-coded). Sin cambios en `domain/keys.ts` / `infrastructure/store.ts`. `5c.1b-B` (render de VersionBanner + trabajo de cierre/sticky de panel + pulido de hidratación de fuente de árbol) y `5c.2` (cableado de research / search / folder) están diferidas. **G4 / G3 Tier-2 / cutover permanecen bloqueadas.** El espejo en español carga la misma semántica; cualquier deriva se resuelve a favor del inglés. Sin render de VersionBanner, sin trabajo de cierre/sticky de panel, sin cambio de comportamiento de Folder/Search research, sin tests G4, sin captura de browser, sin commit/push.

## Addenda — 2026-09-07: PR 5c.1b-B render de VersionBanner + contrato de cierre/sticky de panel (aterrizada); 5c.2 diferida (solo anexo)

- **PR 5c.1b-B aterrizada (esta entrada, divide la `5c.1b-B` diferida previa en una rebanada aterrizada, `5c.2` sigue diferida)**. `5c.1b-B` aterriza (a) el `VersionBanner` con gate de mount en `src/modules/app-shell/presentation/VersionBanner.tsx` — lee `/api/health` solo DESPUÉS de que `useMounted()` se voltea, falla cerrado ante datos de salud no disponibles / malformados (guardas `typeof X !== "number"`), preserva los ids DOM legacy `version-banner` / `version-banner-actual` / `version-banner-expected`, persiste los descartes vía `store.setVersionBannerDismissed(true)`, y reusa el slot existente `data-slot="banner-host"` sin duplicar `createBrowserStateStore()`; (b) el contrato de cierre/sticky de `DetailPanel` en `src/modules/taxonomy/presentation/DetailPanel.tsx` — `id="detail-panel"` en el aside raíz, el botón de cierre `data-action="close-detail"` cableado a un nuevo estado `detailOpen` que el siguiente bump de `forceOpenSearch` resetea a `true` (cierra la regresión legacy del no-op silencioso), y los hooks estructurales `.detail-header` / `.detail-tabs`; (c) el contrato mínimo de sticky-CSS en `src/app/globals.css` — `position: sticky` + `top:` + `z-index` tanto en `.detail-header` como en `.detail-tabs` dentro del viewport de scroll existente de `.detail-panel`, más una regla mínima de `#version-banner` (todos los colores enrutados vía tokens `var(--…)`; sin literales hex crudos). `page-chrome.tsx` monta `<VersionBanner />` en lugar del host banner estático previo (consumido vía un import de módulo hermano, no una reexportación de barrel — el barrel público de `app-shell` se queda intacto en esta rebanada). Sin cambios en `domain/keys.ts` / `infrastructure/store.ts`. `5c.2` (cableado de research / search / folder) está diferida. **G4 / G3 Tier-2 / cutover permanecen bloqueadas.** El espejo en español carga la misma semántica; cualquier deriva se resuelve a favor del inglés. Sin cambio de comportamiento de Folder/Search research, sin tests G4, sin captura de browser, sin salidas de build, sin commit/push.

## Addenda — 2026-09-07: PR 5c.2-A alineación del contrato de motores de búsqueda (aterrizada); montaje global de FileExplorer + actualizaciones de selectores/arnés + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos (solo anexo)

- **PR 5c.2-A aterrizada (esta entrada, divide la `5c.2` diferida previa en A aterrizada + resto diferido)**. `5c.2-A` alinea `api/server.py::_SEARCH_ENGINES` y `src/data/search-engines.js::SEARCH_ENGINES` al roster canónico de 14 motores (google, imagen, documentos, pdf, wikipedia, bhl, researchgate, plos, academia, scielo, scholar, youtube, zootaxa, scribd) en los mismos campos ordenados; las tres entradas retiradas de `general` social/share (`threads_acipenser`, `facebook_acipenser_baerii`, `threads_shared_post`) se eliminan de ambos espejos. `tests/test_smoke.py::test_search_engine_contract` se extiende (TDD estricto) para fijar el conteo exacto (14) y la lista ordenada de llaves además de la verificación de paridad key/label/with_authorship existente; `tests/test_smoke.py::test_fixed_search_destinations_are_returned_unchanged` se retira (sus tres afirmaciones apuntan a motores que ya no están en el roster). `5c.2` (montaje global de FileExplorer, actualizaciones de selectores/arnés e2e, borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`) sigue diferida. **G4 / G3 Tier-2 / cutover permanecen bloqueadas.** El espejo en español carga la misma semántica; cualquier deriva se resuelve a favor del inglés. Sin cambio de comportamiento de Folder/Search research, sin cambios en `domain/keys.ts` / `infrastructure/store.ts`, sin actualizaciones de selectores e2e, sin borrado legacy, sin tests G4, sin captura de browser, sin salidas de build, sin commit/push.

## Addenda — 2026-09-07: PR 5c.2-B.1a andamio del arnés React E2E (aterrizada, solo workspace aislado); driver de captura + servidores de fixture/export + tests herméticos del arnés + modernización de selectores + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos (solo anexo)

- **PR 5c.2-B.1a aterrizada (esta entrada, divide la `5c.2` diferida previa en A aterrizada + B.1a aterrizada + resto diferido)**. `5c.2-B.1a` aterriza un **workspace privado aislado** en `tools/react-e2e-harness/` (sin superficie de edición en `src/`, sin cambios de API, sin cambios de FastAPI/SQLite/extension, sin cambios en `domain/keys.ts` / `infrastructure/store.ts`, sin cambio en `next.config.mjs` / `package.json` de producción, sin captura G4, sin borrado legacy). El workspace fija Next 16.3.3, React 19.2.8, ReactDOM 19.2.8, `@playwright/test` 1.56.0 y Node ≥ 20.9.0; `npm install` genera `tools/react-e2e-harness/package-lock.json` (la excepción de tamaño de lockfile generado aprobada por el usuario solo para este workspace aislado — el fuente/docs authored se queda ≤ 400 líneas de diff; total authored = 245 LoC entre `package.json` + `next.config.mjs` + `tsconfig.json` + `app/layout.tsx` + `app/page.tsx`). `next.config.mjs` refleja los flags de exportación estática G2 (`output: "export"`, `images.unoptimized: true`, `trailingSlash: false`, `reactStrictMode: true`); `app/layout.tsx` es un título semántico mínimo del arnés (sin réplica de AppShell / chrome; sin `import "./globals.css"`; sin preload de Raleway); `app/page.tsx` monta `FileExplorer` directamente desde `@taxa/research` contra un id de taxon sintético determinista no nulo (`1`) y un `baseUrl` leído solo desde la variable de entorno pública del arnés `NEXT_PUBLIC_HARNESS_BASE_URL` (default `http://127.0.0.1:8765`). `tsconfig.json` declara aliases de path `@taxa/*` seguros que resuelven a `../../src/modules/*/index.ts` para que el barrel vivo de research compile contra el arnés sin una reexportación de barrel. **Sin superficie de test** en esta sub-rebanada — el contrato strict-TDD para `5c.2-B.1a` se satisface con (a) una verificación negativa de contrato de fuente pre-build RED que prueba que la app del arnés aún no existe, luego (b) un GREEN `npm ci` (exit `0`, 32 paquetes) + `npm run build` (exit `0`, `out/index.html` renderizado con `<title>Taxa React E2E Harness — FileExplorer mount</title>`, `data-harness-surface="file-explorer"`, `data-harness-taxon-id="1"`, y el montaje vivo de `FileExplorer` renderizando su estado inicial `data-explorer="loading"` con `aria-busy="true"`). El resto de `5c.2-B` (driver de captura, servidores de fixture/export, tests herméticos del arnés, modernización de selectores e2e sobre el nuevo árbol de componentes, borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`) sigue diferido. **G4 / G3 Tier-2 / cutover permanecen bloqueadas; G4 NO se voltea con el aterrizaje de este andamio** (sin verificador Playwright + Lighthouse autordado; solo el workspace aislado + el green-path de exportación estática aterrizaron). El espejo en español carga la misma semántica; cualquier deriva se resuelve a favor del inglés.

## Addenda — 2026-09-08: PR 5c.2-B.1b-i CLI de captura + runner Chromium para exportación React (aterrizada, solo workspace aislado); servidor fixture + servidor de exportación + tests herméticos + modernización de selectores + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos (solo anexo)

- **PR 5c.2-B.1b-i aterrizada (esta entrada, divide el resto diferido previo de `5c.2-B` en B.1b-i aterrizada + resto diferido más estrecho)**. `5c.2-B.1b-i` aterriza la **CLI de captura + runner Chromium** en el workspace aislado `tools/react-e2e-harness/` solo (sin superficie de edición en `src/`, sin cambios de API/FastAPI/SQLite/extension, sin cambios en `domain/keys.ts` / `infrastructure/store.ts`, sin cambio en `next.config.mjs` / `package.json` de producción, sin captura G4, sin borrado legacy). Archivos: `tools/react-e2e-harness/scripts/run.mjs` (CLI; requiere `--origin` + `--output-root`; rechaza `file://` / no-http(s) / rutas en el origen / flags faltantes / colisiones de salida; inyecta dinámicamente el `runFn` desde `./chromium-driver.mjs`; escribe `evidence.json` atómico con timestamp solo tras una captura exitosa — fail-closed) + `tools/react-e2e-harness/scripts/chromium-driver.mjs` (navegación Chromium; importa dinámicamente `playwright` desde el `node_modules/` local; valida los contratos de datos de React `data-harness-root` + `data-harness-surface` + `data-harness-taxon-id` no nulo + `[data-explorer="ready"]` + ambos slots `[data-pane]` + `input[data-search-input]` + ≥1 `[data-file-path]`; captura trazas concisas `pageerror` / `console.error` / navegación / aserciones; cierra el navegador de forma fiable vía `finally`) + `tools/react-e2e-harness/package.json` (+3 líneas; `scripts.capture = "node scripts/run.mjs"`) + `tools/react-e2e-harness/README.md` (uso conciso del origen provisto por el caller + lista fail-closed + lista de diferimientos). **Sin puerto por defecto hard-coded** horneado en la CLI; el caller provee ambos flags. **Sin superficie de test** en esta sub-rebanada — el contrato strict-TDD se satisface con (a) RED de verificación de contrato de fuente pre-implementación (`scripts/run.mjs` + `scripts/chromium-driver.mjs` + directorio `scripts/` ausentes), luego (b) GREEN de `node --check` sobre ambos módulos + rechazo CLI de `missing --origin` / `missing --output-root` / `file://` / ruta en origen con exit `1`. La inyección dinámica de `runFn` + `now()` sobre `capture()` mantiene la superficie adecuada para una futura rebanada de tests herméticos; **no se reclama éxito de runtime del navegador** (los servidores fixture/de exportación están diferidos). El resto de `5c.2-B` (servidor fixture de API + orquestación del servidor HTTP de exportación + target de Makefile + tests herméticos del driver + modernización de selectores e2e sobre el nuevo árbol de componentes + borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`) sigue diferido. **G4 / G3 Tier-2 / cutover permanecen bloqueadas; G4 NO se voltea con el aterrizaje de la CLI de captura** (solo se envió la CLI + runner Chromium; sin agregación G4; sin flip end-to-end de `scripts/verify_parity.py`). El espejo en español carga la misma semántica; cualquier deriva se resuelve a favor del inglés.

## Addenda — 2026-09-09: PR 5c.2-B.1b-ii-a API fixture React FileExplorer hermética (aterrizada, solo workspace aislado); servidor HTTP de exportación estático + rebanada de composición + tests herméticos del driver + modernización de selectores + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos (solo anexo)

- **PR 5c.2-B.1b-ii-a aterrizada (esta entrada, divide el resto diferido previo de `5c.2-B` en B.1b-i aterrizada + B.1b-ii-a aterrizada + resto diferido más estrecho)**. `5c.2-B.1b-ii-a` aterriza la **API fixture Node en-proceso hermética** en el workspace aislado `tools/react-e2e-harness/` solo (sin superficie de edición en `src/`, sin cambios de API/FastAPI/SQLite/extension, sin cambios en `domain/keys.ts` / `infrastructure/store.ts`, sin cambio en `next.config.mjs` / `package.json` de producción, sin captura G4, sin borrado legacy). Archivo: `tools/react-e2e-harness/scripts/fixture-server.mjs` (Node puro built-ins `node:http` + `node:buffer`; cero deps npm; cero delta en `package.json` del arnés; CLI `--port N` / `--host H` OR `--port 0` asignado por el OS; nunca hard-coded 8765). Refleja la forma FastAPI de producción: `GET /api/taxon/1/files` devuelve el `FilesEnvelope` tipado (`exists`, `taxon_id`, `taxon_name`, `taxon_path`, `filesystem_path`, `subpath`, `root: WireFileNode`); `GET /api/taxon/1/files/serve?path=<encoded>` devuelve el cuerpo del archivo + `Content-Type` correspondiente (refleja `api/server.py::_CONTENT_TYPE_BY_EXT`) + `Content-Disposition: inline; filename="<basename>"`. Corpus fixture determinista en memoria: `index.html`, `notes.md`, `readme.txt`, `paper.pdf` (cada formato con el Content-Type de producción correspondiente), y un `Papers/lynx.pdf` recursivo para ejercitar la recursión de `_walk_tree`. `safeResolve()` refleja `api/server.py::_safe_resolve()` paso a paso: rechaza vacío / NUL / percent malformado / absoluto / `..` / `.`; join explícito de segmentos para que separadores mixtos no escapen; verificación de padre estricto. Solo el id de taxon `1` se sirve; rutas desconocidas / taxon desconocido / método incorrecto / traversal codificado URL todos rechazados fail-closed (400 / 404 / 405). Importable vía `startServer({port, host}) → {schema, taxonId, host, port, baseUrl, server, close}` para que la rebanada de composición (5c.2-B.1b-ii-b) pueda spawn/teardown en-proceso. Superficie de test: `tests/test_5c_2_b_react_harness.py` (21 tests herméticos; `subprocess` Node + Python `urllib`; sin Playwright / Chromium / FastAPI / SQLite / red). Cubre contrato de fuente (archivo existe, exporta `startServer`, `node --check`, cero deps `npm:`); ciclo de vida start/stop (puerto elegido por caller honrado, puertos OS-asignados únicos, `SIGTERM` libera el listener); forma del envelope (cada campo de `FilesEnvelope`, orden carpetas antes de archivos, las cuatro extensiones del fixture, subfolder recursivo, wire-shape en cada archivo); tipos de contenido de cuatro formatos + `Content-Disposition` + magic `%PDF-`; fail-closed traversal (`..`, `../../etc/passwd`, `/etc/passwd`, URL-encoded `%2E%2E%2Fpasswd`); archivo desconocido 404 dentro de la raíz; taxon desconocido 404; ruta desconocida 404; no-GET 405. **TDD estricto**: **RED** = verificación de contrato de fuente pre-implementación (`fixture-server.mjs` ausente) FALLÓ sobre la fuente previa a `5c.2-B.1b-ii-a`. **GREEN** = `node --check` exit `0` + los 21 tests herméticos pasan. Sin cambios de fuente/API de producción; sin cambios en `domain/keys.ts` / `infrastructure/store.ts`; sin borrado legacy `web/*.{html,js,css}`; sin agregación G4; sin cambio en `tools/g4-capture/**`; sin cambio de FastAPI/SQLite/extension. El resto de `5c.2-B` (orquestación del servidor HTTP de exportación estático + rebanada de composición + target de Makefile + tests herméticos del driver de captura + modernización de selectores e2e sobre el nuevo árbol de componentes + borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`) sigue diferido. **G4 / G3 Tier-2 / cutover permanecen bloqueadas; G4 NO se voltea con el aterrizaje del fixture API** (sin flip end-to-end de `scripts/verify_parity.py`; sin artefacto de build de producción; sin éxito de runtime de navegador). El espejo en español carga la misma semántica; cualquier deriva se resuelve a favor del inglés.

## Addenda — 2026-09-09: PR 5c.2-B.1b-ii-b servidor HTTP de exportación estática hermético (aterrizada, solo workspace aislado); rebanada de composición + tests herméticos del driver + modernización de selectores + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos (solo anexo)

- **PR 5c.2-B.1b-ii-b aterrizada (esta entrada, divide el resto diferido previo de `5c.2-B` en B.1b-i aterrizada + B.1b-ii-a aterrizada + B.1b-ii-b aterrizada + resto diferido más estrecho)**. `5c.2-B.1b-ii-b` aterriza el **servidor HTTP de exportación estática Node en-proceso hermético** en el workspace aislado `tools/react-e2e-harness/` solo (sin superficie de edición en `src/`, sin cambios de API/FastAPI/SQLite/extension, sin cambios en `domain/keys.ts` / `infrastructure/store.ts`, sin cambio en `next.config.mjs` / `package.json` de producción, sin captura G4, sin borrado legacy). Archivo: `tools/react-e2e-harness/scripts/export-server.mjs` (Node puro built-ins `node:http` + `node:fs/promises` + `node:path` + `node:url`; cero deps npm; cero delta en `package.json` del arnés; CLI `--port N` / `--host H` OR `--port 0` asignado por el OS; nunca hard-coded 8765; default loopback `127.0.0.1`). **--root es obligatorio, absoluto, y debe apuntar a un directorio existente** — cualquier otra forma exit non-zero ANTES de bindear cualquier listener (fail-closed). `/` mapea a `index.html` dentro de la raíz; los archivos exactos bajo la raíz se sirven recursivamente con el Content-Type correspondiente (HTML / HTM / JS / MJS / CSS / JSON / MAP / XML / TXT / SVG / PNG / JPG / JPEG / GIF / WEBP / ICO / WOFF / WOFF2 / TTF / OTF — extensiones desconocidas caen a `application/octet-stream`). HEAD refleja el Content-Type + Content-Length de GET (sin cuerpo). `safeJoin()` refleja la misma postura defensiva que `fixture-server.mjs`: rechaza segmentos `..` / `.` ANTES de cualquier join; split explícito de segmentos para que separadores mixtos no escapen; verificación de padre estricto después del join. Traversal / leakage de directorio / rutas desconocidas / métodos no-GET todos fail-closed (404 / 405 con `Allow: GET, HEAD`). Importable vía `startServer({port, host, root}) → {schema, root, host, port, baseUrl, server, close}` para que la rebanada de composición pueda spawn/teardown en-proceso. La CLI parsea `--root` / `--port` / `--host` / `--help` y sale non-zero en flags desconocidas. **TDD estricto**: **RED** = verificación de contrato de fuente pre-implementación (`export-server.mjs` ausente) FALLÓ sobre la fuente previa a `5c.2-B.1b-ii-b`. **GREEN** = `node --check` exit `0` + los 39 tests herméticos pasan (21 fixture + 18 export-server); sonda de ciclo de vida confirma puerto elegido por el caller honrado, puertos OS-asignados únicos, `SIGTERM` libera el listener; sonda de gating CLI confirma `--root` faltante / relativo / inexistente cada uno exit non-zero; sonda de `/` → `index.html` confirma que el documento de entrada de React se sirve en el origen raíz; sonda de tipo de contenido confirma siete familias MIME (HTML / JS / MJS / CSS / JSON / PNG / WOFF2) + fallback `application/octet-stream` para `.bin`; sonda de archivo anidado confirma el servicio recursivo de archivos exactos; sonda de HEAD-mirror confirma Content-Type + Content-Length iguales a GET y sin cuerpo; sonda de traversal confirma `..` / `../../etc/passwd` / `%2Fetc%2Fpasswd` / `%2E%2E%2Fpasswd` todos 404; sonda de leakage de directorio confirma `/sub/` 404 (sin listado, sin auto-append de `index.html`); sonda de ruta desconocida confirma `/no-such-file.html` 404; sonda de no-GET confirma que POST devuelve exactamente 405 con `Allow: GET, HEAD`. Sin cambios de fuente/API de producción; sin cambios en `domain/keys.ts` / `infrastructure/store.ts`; sin borrado legacy `web/*.{html,js,css}`; sin agregación G4; sin cambio en `tools/g4-capture/**`; sin cambio de FastAPI/SQLite/extension. El resto más estrecho de `5c.2-B` (wiring de la rebanada de composición + target de Makefile + tests herméticos del driver de captura + modernización de selectores e2e sobre el nuevo árbol de componentes + borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`) sigue diferido. **G4 / G3 Tier-2 / cutover permanecen bloqueadas; G4 NO se voltea con el aterrizaje del servidor de exportación estática** (sin flip end-to-end de `scripts/verify_parity.py`; sin artefacto de build de producción; sin éxito de runtime de navegador; solo se envió el servidor HTTP de exportación). El espejo en español carga la misma semántica; cualquier deriva se resuelve a favor del inglés.

## Addenda — 2026-09-09: PR 5c.2-B.1b-ii-c orquestador de composición (aterrizada, solo workspace aislado); tests herméticos del driver de captura + modernización de selectores + borrado legacy + G4 / G3 Tier-2 / cutover siguen diferidos (solo anexo)

- **PR 5c.2-B.1b-ii-c aterrizada (esta entrada, divide el resto diferido previo de `5c.2-B` en B.1b-i + B.1b-ii-a + B.1b-ii-b + B.1b-ii-c aterrizadas + resto diferido más estrecho)**. `5c.2-B.1b-ii-c` aterriza el **orquestador de composición + driver CLI + target de Makefile + `capture:composed` package-script + rebanada de tests de composición hermética** en el workspace aislado `tools/react-e2e-harness/` solo (sin superficie de edición en `src/`, sin cambios de API/FastAPI/SQLite/extension, sin cambios en `domain/keys.ts` / `infrastructure/store.ts`, sin cambio en `next.config.mjs` / `package.json` de producción, sin captura G4, sin borrado legacy). Archivo: `tools/react-e2e-harness/scripts/composed-capture.mjs` (Node puro built-ins; cero deps npm; cero delta en `package.json` del arnés). Cablea `fixture-server.mjs` (5c.2-B.1b-ii-a) → `buildFn` inyectado (default `npm run build` con `NEXT_PUBLIC_HARNESS_BASE_URL` fijado al origen del fixture) → sonda de acceso `out/index.html` (fail-closed) → `export-server.mjs` (5c.2-B.1b-ii-b) → `captureFn` inyectado (default `run.mjs::capture`) en un único orquestador `composeCapture({harnessDir, outputRoot, taxonId, host, buildFn, captureFn, startFixtureFn, startExportFn, now})`. **La CLI requiere `--output-root`** (sin default, exit non-zero con `missing --output-root`); **rechaza host no-loopback** (`127.0.0.1` / `::1` / `localhost` son las únicas formas aceptables, alineado con los defaults de `fixture-server.mjs` / `export-server.mjs`); **rechaza cualquier `--taxon-id` distinto del `1` sintético** que sirven la app y el fixture del arnés (endurece el validador parcial previo que aceptaba cualquier entero positivo — observado RED: con el endurecimiento desactivado, `test_composed_capture_cli_rejects_other_taxon_id` y `test_composed_capture_validate_taxon_id_accepts_one_only` fallan con un fallo de aserción "taxon" claro y la CLI cayendo hasta una invocación real de `npm run build` que surfacea la validación faltante). **Sin puerto hard-coded** (`--port 0` para ambos servidores, asignado por el OS, distintos). **Limpieza en orden inverso bajo `finally` anidados** (export cerrado antes que fixture; verificado en-proceso vía espías `startFixtureFn` / `startExportFn` inyectados — observado `exportCloseSeq=1`, `fixtureCloseSeq=2` en fallo de `captureFn`). Ambas primitivas de validación (`validateTaxonId`, `validateHost`) están exportadas para la rebanada de tests hermética. **Sin éxito de runtime de navegador reclamado** — `chromium-driver.mjs` es alcanzable vía el `captureFn` por defecto, pero la rebanada de tests de composición nunca lo invoca (el fixture en-proceso usa un stub de captura inyectado que devuelve evidencia sintética). `Makefile::capture-react-e2e` requiere `OUTPUT_ROOT` (sin default; sin puertos de producción horneados; reenvía `HARNESS_DIR`); `tools/react-e2e-harness/package.json` añade `scripts.capture:composed = "node scripts/composed-capture.mjs"`. Superficie de test: `tests/test_5c_2_b_react_harness.py` gana un bloque de composición (11 casos herméticos; `subprocess` Node + Python `urllib`; sin Playwright / Chromium / FastAPI / SQLite / red; total del archivo ahora 65 casos herméticos incluyendo expansiones parametrizadas). Cubre contrato de fuente (archivo existe + `node --check` + cero-dep), gating de CLI (`--output-root` obligatorio; `--host 0.0.0.0` rechazado; `--taxon-id 2` rechazado), primitivas de validación (`validateTaxonId("1") → 1`; cualquier otro entero positivo / cero / negativo / no-numérico lanza; `validateHost` acepta `127.0.0.1` / `::1` / `localhost` y rechaza todo lo demás), orquestación en-proceso con `out/index.html` sintético + `buildFn` inyectado + `captureFn` inyectado (devuelve sobre estructurado `taxa.react-e2e-composed-capture/1` con baseUrls loopback asignados por el OS), bypass de build → fail-closed (`buildFn` reclama éxito pero no hay `out/index.html` → `composeCapture` lanza ANTES de iniciar el servidor de exportación o invocar `captureFn`), y limpieza en orden inverso en fallo de captura (secuencia `close()` rastreada por espías). **TDD estricto**: **RED** = verificación de contrato de fuente pre-`5c.2-B.1b-ii-c` (módulo de composición ausente) FALLÓ sobre la fuente previa a `5c.2-B.1b-ii-c`; el sub-ciclo de endurecimiento de validación corrió en vivo (desactivar la comprobación `n !== HARNESS_TAXON_ID` envió los tests relevantes a RED con fallos claros). **GREEN** = `node --check` exit `0` sobre `composed-capture.mjs` + los 65 tests herméticos pasan. El resto más estrecho de `5c.2-B` (tests herméticos del driver de captura que ejercitan `chromium-driver.mjs` end-to-end contra un fixture real + servidor de exportación; modernización de selectores e2e sobre el nuevo árbol de componentes; borrado legacy `web/*.{html,js,css}` + `tailwind.config.js`) sigue diferido. **G4 / G3 Tier-2 / cutover permanecen bloqueadas; G4 NO se voltea con el aterrizaje de la composición** (sin flip end-to-end de `scripts/verify_parity.py`; sin artefacto de build de producción; sin éxito de runtime de navegador; solo se enviaron orquestador + CLI + target de Makefile + package-script + rebanada de tests hermética). El espejo en español carga la misma semántica; cualquier deriva se resuelve a favor del inglés.

## Addenda — 2026-09-09: autorización de size:exception de PR 3c-ii (solo documental; ni fusionado ni verificado) (solo anexo)

- **size:exception de PR 3c-ii autorizada (esta entrada, abre una segunda `size:exception` aprobada por el usuario junto a la excepción previa de `package-lock.json` regenerado de PR 3a; la cadena de 16 hijos se preserva; sin otros cambios de alcance; el PR NO se reclama como fusionado ni verificado por este addendum)**. El usuario autorizó una `size:exception` para PR 3c-ii porque la implementación real de la rebanada completa de CSS de árbol / detalle de taxonomía requirió **822 inserciones + 9 deletions = 831 LoC**, contra la estimación previa de `~380 LoC` registrada en el callout "replan de la sub-secuencia del PR 3c" de este design, en el presupuesto inline `~380 (≤ 400; -20 LoC de holgura)` de la tabla "Rebanada de sub-PRs bajo la Aproximación A", en la cifra `~280 LoC para selectores de árbol / detalle / kebab / modal de materialize` de la entrada de "Archivos afectados" para `src/app/globals.css`, en la línea `El sub-PR nuevo más grande es 3c-i a ~390 LoC` del "Pronóstico de carga de revisión" de `tasks-es.md`, en la línea `los otros hijos del 3c son 3c-ii ~380, 3c-iii ~390, 3c-iv ~280` del mismo pronóstico, en la afirmación **Los 16 sub-PRs ≤ 400 LoC authored**, y en la cláusula `no se abre ninguna nueva size:exception para la sub-secuencia del 3c` — es decir, la implementación real sobrepasa el presupuesto de revisión por PR de 400 líneas que el Enfoque A bloqueó el 2026-09-02 en +431 LoC. **Justificación de la autorización** (por qué se prefiere un único PR revisable sobre un fraccionamiento adicional): (a) los selectores de árbol / detalle de taxonomía, las variantes teñidas por realm `.tree-row[data-realm="…"]`, los selectores del menú kebab / modal de materialize, la superficie de `#detail-panel` / `.detail-card` / `.detail-section` / `.overview-section` / `.detail-item` / `.search-pulse` / `.detail-tabs` / `.search-icon-btn` / `.materialize-btn`, y la rebanada del test de paridad en `tests/test_tailwind_4_parity.py` son inseparables de la capa base de 3c-i (deben enviarse juntos para que cada selector resuelva sus referencias `var(--token)` contra la rebanada viva de tokens `:root`); (b) dividir PR 3c-ii aún más en un par 4c-i / 4c-ii duplicaría la superficie consumidora de `var(--token)` entre dos PRs y forzaría al hijo posterior a re-tocar selectores que el hijo anterior ya bloqueó; (c) la sub-secuencia de cuatro hijos del 3c ya minimizó el radio de impacto al dividir el `<style>` inline legacy de 1.963 líneas en cuatro hermanos revisables (3c-i / 3c-ii / 3c-iii / 3c-iv), así que el presente sobrepaso refleja la superficie realista de port de CSS para el concern de árbol / detalle de taxonomía más que un defecto de planificación; (d) la enumeración de cada selector de taxonomía en `tests/test_tailwind_4_parity.py` — el contribuyente dominante del conteo de 831 LoC — es en sí misma una rebanada inseparable (dividir el enumerador entre dos PRs dejaría un test a medio-coherente que nadie puede revisar coherentemente y aún tendría que re-fusionarse en PR 5c). **La cadena de 16 hijos se preserva**: PR 3c-ii permanece en la posición 4/16 con el mismo predecesor (`feat/complete-taxa-frontend-migration-03-3c-i`) y el mismo sucesor (`feat/complete-taxa-frontend-migration-05-3c-iii`); la descripción de dependencia por PR, el orden corregido, el bloqueo del Enfoque A, la base de FastAPI/SQLite, la estrategia de Feature Branch Chain, el estado congelado del predecesor, las specs por dominio, todos los addenda previos (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c), y el protocolo G5 de reemplazo aprobado por el usuario registrado arriba quedan sin cambios. **El PR no se reclama como fusionado ni verificado por este addendum** — la `size:exception` solo autoriza un único PR revisable contra el presupuesto establecido; revisión, CI y merge siguen el proceso ordinario de feature-branch-chain. Las estimaciones corregidas (`831 LoC totales: 822 inserciones, 9 deletions`) sustituyen a la cifra previa de `~380 LoC` en las cuatro tablas arriba; el presupuesto inline `~380 (≤ 400; -20 LoC de holgura)` pasa a `831 (sobrepaso +431 LoC contra el presupuesto de 400 líneas; size:exception aprobada por el usuario para este PR)`; la cifra `~280 LoC para selectores de árbol / detalle / kebab / modal de materialize` de la entrada de archivos afectados se anota con la size:exception aprobada por el usuario; el total de archivos afectados sube de `~980 LoC` a `~1.510 LoC`; la línea `El sub-PR nuevo más grande es 3c-i a ~390 LoC` del Pronóstico de carga de revisión pasa a `El sub-PR nuevo más grande por diff real es PR 3c-ii a 831 LoC`; la línea `Los 16 sub-PRs ≤ 400 LoC authored` se anota con `excepto PR 3c-ii, que carga una size:exception aprobada por el usuario`; la cláusula `no se abre ninguna nueva size:exception` se anota con `excepto para PR 3c-ii, que ahora es la segunda size:exception aprobada por el usuario junto a PR 3a`. El espejo en español carga la misma semántica; cualquier deriva se resuelve a favor del inglés. Sin cambios de código; sin rebase; sin nueva rama; sin commit/push; sin apertura de PR.

## Addenda — 2026-09-09: autorización de size:exception de PR 3c-iii (solo documental; ni fusionado ni verificado) (solo anexo)

- **size:exception de PR 3c-iii autorizada (esta entrada, abre una tercera `size:exception` aprobada por el usuario junto a la excepción previa de `package-lock.json` regenerado de PR 3a Y la excepción previamente autorizada de CSS de árbol-de-taxonomía de PR 3c-ii; la cadena de 16 hijos se preserva; las superficies de PR 3c-iv quedan diferidas al siguiente hijo de la cadena con alcance sin cambios; el PR NO se reclama como fusionado ni verificado por este addendum)**. El usuario autorizó una `size:exception` para PR 3c-iii porque la implementación real de la rebanada completa de CSS de Search / Folder / global Browser requirió **1669 inserciones y 66 deletions = 1735 review lines (net +1603)**, contra la estimación previa de `~390 LoC` registrada en el callout "replan de la sub-secuencia del PR 3c" de este design, en el presupuesto inline `~390 (≤ 400; -10 LoC de holgura)` de la tabla "Rebanada de sub-PRs bajo la Aproximación A", en la cifra `~330 LoC para selectores de Search / Folder / global Browser / file explorer / CSV / JSON` de la entrada de "Archivos afectados" para `src/app/globals.css`, en la línea `El sub-PR nuevo más grande es 3c-i a ~390 LoC` del "Pronóstico de carga de revisión" de `tasks-es.md`, en la línea `los otros hijos del 3c son 3c-i ~390, 3c-iii ~390, 3c-iv ~280` del mismo pronóstico (post excepción de 3c-ii), en la afirmación **Los 16 sub-PRs ≤ 400 LoC authored**, y en la cláusula `no se abre ninguna nueva size:exception para la sub-secuencia del 3c` — es decir, la implementación real sobrepasa el presupuesto de revisión por PR de 400 líneas que el Enfoque A bloqueó el 2026-09-02 en **+1335 LoC** y la estimación previa de `~390 LoC` en **+1345 LoC**. **Lo que el PR preserva efectivamente**: el **catálogo completo de selectores de Search / Folder / global Browser** (`.toast` / `.toast-error`, `.search-engines-grid`, `.search-category-header`, `.search-engine-btn`, `.fex-meta-strip`, `.fex-tab-strip`, `.fex-snippet-frame`, `.fex-shell`, `.fex-tree-pane`, `.fex-viewer-pane`, `.fex-splitter`, `.fex-row` + variantes `.selected` / `.file` / `.folder`, `.fex-tree-header`, `.fex-children`, `.fex-banner`, `.fex-empty-state`, `.fex-search-*`, `.fex-csv-*`, `.fex-json-*`, `.fex-tree-truncated`, según la enumeración del alcance de 3c-iii en la tabla "Rebanada de sub-PRs bajo la Aproximación A") y su **contrato de paridad canónico** (`tests/test_research_styles.py` enumera cada selector de Search / Folder / global Browser; `tests/test_tailwind_4_parity.py` se extiende con la rebanada de selectores de Browser; cada selector resuelve a una declaración no vacía en `src/app/globals.css` y `out/_next/static/chunks/*.css`). **Superficies de PR 3c-iv diferidas**: las reglas `@keyframes` + `.animate-spin` + los frames de los viewers de imagen / video (`.fex-image-frame`, `.fex-image`, `.fex-image-advisory`, `.fex-video-frame`, `.fex-video-el`) + los selectores de la vista Settings (`.settings-shell`, `.settings-header`, `.settings-list`, `.settings-row`, `.settings-theme-toggle`, `.settings-action-btn`, `.settings-link-btn`) + el barrel del design-system (`src/modules/design-system/{infrastructure/index.ts, presentation/Icon.tsx, presentation/Button.tsx}`) permanecen diferidos a PR 3c-iv en la posición 6/16 sin cambio de alcance; la estimación `~280 LoC` de PR 3c-iv, la cifra `~120 LoC para @keyframes + viewer de imagen / video + vista Settings` de la entrada de archivos afectados, y el alcance de `tests/test_design_system_purity.py` quedan sin cambios. **Justificación de la autorización** (por qué se prefiere un único PR revisable sobre un fraccionamiento adicional): (a) los selectores de Search / Folder / global Browser son inseparables de la capa base de 3c-i (tokens + cascada de dark mode) Y de los selectores de taxonomía de 3c-ii (los selectores de research `.search-tab` / `.folder-tab` / `.header-browser-tab` se montan sobre las referencias `var(--token)` vivas que 3c-ii acaba de enviar); deben enviarse juntos como una única rebanada CSS para que cada selector de browser / research resuelva sus referencias `var(--token)` contra la capa base viva; (b) dividir PR 3c-iii aún más en un par 4c-i / 4c-ii duplicaría la superficie consumidora de `var(--token)` entre dos PRs y forzaría al hijo posterior a re-tocar selectores que el hijo anterior ya bloqueó — duplicando el defecto de planificación que la sub-secuencia de cuatro hijos del 3c ya cerró; (c) la sub-secuencia de cuatro hijos del 3c ya minimizó el radio de impacto al dividir el `<style>` inline legacy de 1.963 líneas en cuatro hermanos revisables (3c-i / 3c-ii / 3c-iii / 3c-iv), así que el presente sobrepaso refleja la superficie realista de port de CSS para el concern de Search / Folder / global Browser más que un defecto de planificación (la estimación de `~390 LoC` subcontó la enumeración canónica de cada selector de browser en el test de paridad, la profundidad de la familia `.fex-search-*` / `.fex-csv-*` / `.fex-json-*`, y las dimensiones de chrome de `.fex-tree-pane` / `.fex-viewer-pane` / `.fex-splitter` / `.fex-banner`); (d) la enumeración de cada selector de Search / Folder / global Browser en `tests/test_tailwind_4_parity.py` + `tests/test_research_styles.py` — el contribuyente dominante del conteo de 1735 review-line — es en sí misma una rebanada inseparable (dividir el enumerador entre dos PRs dejaría un test a medio-coherente que nadie puede revisar coherentemente y aún tendría que re-fusionarse en PR 5c). **La cadena de 16 hijos se preserva**: PR 3c-iii permanece en la posición 5/16 con el mismo predecesor (`feat/complete-taxa-frontend-migration-04-3c-ii`) y el mismo sucesor (`feat/complete-taxa-frontend-migration-06-3c-iv`); PR 3c-iv permanece en la posición 6/16 con la misma estimación `~280 LoC` y alcance sin cambios; la descripción de dependencia por PR, el orden corregido, el bloqueo del Enfoque A, la base de FastAPI/SQLite, la estrategia de Feature Branch Chain, el estado congelado del predecesor, las specs por dominio, **la size:exception existente de PR 3c-ii queda abierta** (el sobrepaso de 831 LoC de PR 3c-ii queda sin cambios; este addendum NO modifica, reemplaza, ni supera la excepción de PR 3c-ii — ambas excepciones coexisten sobre la misma cadena), todos los addenda previos (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c, 3c-ii), y el protocolo G5 de reemplazo aprobado por el usuario registrado arriba quedan sin cambios. **El PR no se reclama como fusionado ni verificado por este addendum** — la `size:exception` solo autoriza un único PR revisable contra el presupuesto establecido; revisión, CI y merge siguen el proceso ordinario de feature-branch-chain. Las estimaciones corregidas (`total de 1735 review-line: 1669 inserciones, 66 deletions; net +1603; sobrepaso +1335 LoC contra el presupuesto de 400 líneas y +1345 LoC contra la estimación previa de ~390 LoC; size:exception aprobada por el usuario para este PR`) sustituyen a la cifra previa de `~390 LoC`; el presupuesto inline `~390 (≤ 400; -10 LoC de holgura)` de la tabla de rebanada de sub-PRs pasa a `1735 review lines (sobrepaso +1335 LoC contra el presupuesto de 400 líneas y +1345 LoC contra la estimación previa de ~390 LoC; size:exception aprobada por el usuario para este PR)`; la cifra `~330 LoC para selectores de Search / Folder / global Browser / file explorer / CSV / JSON` de la entrada de archivos afectados se anota con la size:exception aprobada por el usuario; el total acumulativo de `src/app/globals.css` (3c-i `~250` + 3c-ii 831 + 3c-iii 1735 review lines + 3c-iv `~120`) sube del post-3c-ii `~1,510 LoC` (con la excepción 3c-ii solamente) a `~2,936 LoC` (con ambas excepciones); la línea `El sub-PR nuevo más grande por diff real es PR 3c-ii a 831 LoC` del Pronóstico de carga de revisión pasa a `El sub-PR nuevo más grande por diff real es PR 3c-iii a 1735 review lines (net +1603; sobrepaso +1335 LoC contra el presupuesto de 400 líneas y +1345 LoC contra la estimación previa de ~390 LoC; size:exception aprobada por el usuario), con PR 3c-ii segundo a 831 LoC (size:exception aprobada por el usuario) y PR 3c-i tercero a ~390 LoC`; la línea `Los 16 sub-PRs ≤ 400 LoC authored` se anota con `excepto PR 3c-ii (831 LoC) Y PR 3c-iii (1735 review lines), ambos cargando size:exceptions aprobadas por el usuario`; la cláusula `no se abre ninguna nueva size:exception` se anota con `excepto para PR 3c-ii (ya autorizada) Y PR 3c-iii (autorizada por esta entrada), que son la segunda y tercera size:exceptions aprobadas por el usuario junto a PR 3a`. El espejo en español (`documents-es/openspec/changes/complete-taxa-frontend-migration/design-es.md`) carga la misma semántica; cualquier deriva se resuelve a favor del inglés. Sin cambios de código; sin rebase; sin nueva rama; sin commit/push; sin apertura de PR.

## Addenda — 2026-09-09: reparación de pipeline Tailwind 4 / PostCSS de PR 5.5 (aterrizada; el primer hijo de reparación post-sub-secuencia-3c; cadena de 17 hijos; la cuarta `size:exception` aprobada por el usuario para el `package-lock.json` regenerado junto a PR 3a + PR 3c-ii + PR 3c-iii) (solo anexo)

- **Reparación de pipeline Tailwind 4 / PostCSS de PR 5.5 aterrizada (esta entrada, inserta un nuevo hijo de reparación entre PR 3c-iii y PR 3c-iv, expande la cadena de 16 hijos a 17 hijos, abre una cuarta `size:exception` aprobada por el usuario para el `package-lock.json` regenerado de este PR junto a las excepciones existentes de PR 3a + PR 3c-ii + PR 3c-iii, y expone el hueco de evidencia de candidato-de-producción G2 que la cadena previa dejó abierto; el PR está implementado en este worktree pero NO se reclama como fusionado, NO se reclama como G2-PASS, y NO se reclama como verificado-en-navegador por este addendum)**. **Defecto confirmado (causa raíz + firma observable a nivel de artefacto)**: PR 3c-i envió `src/app/globals.css` con la superficie canónica de Tailwind 4 — `@import "tailwindcss";` seguido de un bloque `@theme { --primary: #1d7ea9; --accent: #176587; --surface: #ffffff; … --realm-bacteria: #5ebd9b; … }` que carga cada token legacy `:root` / `[data-theme="dark"]` / `--realm-*`. PR 3c-ii, PR 3c-iii y el bootstrap de toolchain previo PR 3a consumieron esa superficie bajo el supuesto de que el pipeline PostCSS por defecto de `next build` procesaría `@import "tailwindcss"` y expandiría el bloque `@theme { … }`. **El supuesto era incorrecto**: PR 3a añadió `tailwindcss@^4` como dependencia top-level, pero el proyecto nunca registró un plugin de PostCSS para él (sin `postcss.config.mjs` en la raíz del repo, sin dependencia `@tailwindcss/postcss`). El pipeline PostCSS por defecto de Turbopack NO reconoce `@import "tailwindcss";` como directiva de Tailwind 4 y NO reconoce `@theme { … }` como regla CSS — el build emite una warning no fatal `Unknown at rule: @theme`, deja el bloque `@theme { … }` como regla literal en el CSS compilado (el navegador lo descarta silenciosamente porque `@theme` no es una regla CSS real), y envía cero preflight de Tailwind + cero tokens `:root` expandidos por `@tailwindcss/postcss`. **Consecuencia observada (este worktree, commit base `6375927`, antes de PR 5.5)**: `next build` sale con `0`, los selectores legacy `.research-explorer` / `.fex-row` / `.tree-row` / `.tier-header` / `.load-all` / `.kebab` / `.search-tab` / `.folder-tab` / `.header-browser-tab` / `.fex-meta-strip` / `.fex-tab-strip` / `.fex-snippet-frame` / `.fex-csv-table` / `.fex-json-tree` / `.fex-tree-leaf` se envían (porque son CSS plano que no necesita procesamiento de Tailwind), pero **cada referencia `var(--primary)` / `var(--accent)` / `var(--surface)` / `var(--on-surface)` / `var(--realm-bacteria)` / `var(--realm-archaea)` / `var(--realm-viruses)` / `var(--realm-animalia)` / `var(--realm-fungi)` / `var(--realm-plantae)` / `var(--realm-chromista)` / `var(--realm-other)` dentro de esos selectores resuelve a `unset` en tiempo de ejecución** — la cascada visual completa está rota. El preflight de Tailwind 4 (`*,:after,:before,::backdrop { box-sizing: border-box; border: 0 solid; margin: 0; padding: 0 }`) está ausente; la superficie de clases utility de Tailwind 4 está ausente; la animación `@keyframes spin { to { transform: rotate(360deg) } }` está ausente. El bundle CSS compilado en `out/_next/static/chunks/391guka-hdllv.css` (hash del pipeline chunked de Turbopack; este es el único bundle CSS que `next build` emite para este repo) encoge de **50.891 bytes** (con `@tailwindcss/postcss` corriendo) a **35.093 bytes** (sin él) — un encogimiento de ~31% que es la huella a nivel de bytes del defecto. **Qué envía PR 5.5 (superficie de edición de este worktree)**: (1) `package.json` añade **dos nuevas entradas top-level en `dependencies`**: `"@tailwindcss/postcss": "^4.3.3"` (el plugin oficial de PostCSS de Tailwind 4, resuelto contra el mismo major `^4` que la dependencia `tailwindcss` existente) y `"postcss": "^8.5.0"` (el runtime del que depende `@tailwindcss/postcss` — explícitamente requerido ahora porque PR 3a eliminó la dependencia top-level legacy `postcss` junto con `autoprefixer` / `@tailwindcss/forms`, y el plugin de Tailwind 4 necesita un peer `postcss` para correr). Los plugins de la era Tailwind 3 (`autoprefixer`, `@tailwindcss/forms`) permanecen prohibidos. (2) Archivo nuevo `postcss.config.mjs` en la raíz del repo, `export default { plugins: { "@tailwindcss/postcss": {} } }` — una config PostCSS ESM mínima que registra solo el plugin oficial de Tailwind 4 (sin `autoprefixer`, sin `@tailwindcss/forms`, sin otros plugins legacy). (3) `package-lock.json` regenerado (el lockfile regenerado de este PR es la **cuarta `size:exception` aprobada por el usuario** para este proyecto, junto a las excepciones existentes de PR 3a + PR 3c-ii + PR 3c-iii — véase el párrafo de excepción de lockfile abajo para la justificación de autorización y el delta del lockfile). (4) `tests/test_toolchain_bootstrap.py` se actualiza: `REQUIRED_DEPS_PRODUCTION` se expande de `(("tailwindcss", "4"),)` a `(("tailwindcss", "4"), ("postcss", None), ("@tailwindcss/postcss", None))` para que `postcss` y `@tailwindcss/postcss` queden pineados como deps de producción requeridas (major sin restricción porque Tailwind 4 las mantiene alineadas con su propio cadencia de releases); `FORBIDDEN_LEGACY_DEPS` se reduce de `("autoprefixer", "postcss", "@tailwindcss/forms")` a `("autoprefixer", "@tailwindcss/forms")` para que la prohibición de la era Tailwind 3 `autoprefixer` + `@tailwindcss/forms` permanezca abierta mientras `postcss` ahora es requerida (no prohibida). (5) Nueva superficie de test `tests/test_tailwind_build_pipeline.py` — un test de regresión enfocado que realiza un `next build` REAL contra el repo, lee el bundle CSS compilado bajo `out/_next/static/{css,chunks}/*.css`, y afirma: (a) `next build` sale con `0`; (b) al menos un bundle CSS existe bajo la ruta de static export; (c) la regla universal-selector del preflight de Tailwind 4 (`*,:after,:before,::backdrop { box-sizing: border-box; … }`) está presente en el CSS compilado — este es el testigo canónico de que `@tailwindcss/postcss` efectivamente corrió; (d) la regla literal `@theme {` NO está presente en el CSS compilado — un `@theme {` literal sobreviviente es la firma del defecto que prueba que el plugin nunca expandió el bloque `@theme` en la declaración `@layer theme { :root, :host { … } }` que el navegador realmente lee; (e) el substring literal `@import "tailwindcss"` NO está presente en el CSS compilado — un import literal sobreviviente es la firma de que el plugin nunca resolvió la directiva; (f) cada bundle CSS contiene el preflight (sin filtración de subset — el plugin corrió sobre todos los bundles, no solo uno); (g) el token de la paleta legacy `:root` `--primary: #1d7ea9` vive dentro de una declaración `@layer theme { :root, :host { … } }` (la forma canónica de expansión de Tailwind 4, NO dentro de un bloque `@theme` literal). La fixture limpia `out/` y `.next/` en teardown SI no existían antes de que el test entrara (así un desarrollador que ya tiene un `out/` de un build previo conserva el suyo; el test posee su propio ciclo de vida de artefacto). **Evidencia de Strict-TDD observada en este worktree (RED → GREEN → TRIANGULATE)**: **RED** = pre-implementación, tanto los 7 casos del archivo de test nuevo como los 2 casos de dep nuevos del test de toolchain FALLAN con la base post-3c-iii — `tests/test_tailwind_build_pipeline.py::test_next_build_emits_css_bundle_under_out_static` y 5 tests hermanos ERRORean con `postcss.config.mjs missing at … PR 5.5 ships @tailwindcss/postcss as the registered plugin`; `tests/test_tailwind_build_pipeline.py::test_triangulate_postcss_config_registers_tailwind_plugin_only` FALLA con `postcss.config.mjs missing at …`; `tests/test_toolchain_bootstrap.py::test_required_dep_present_in_dependencies[postcss-None]` y `[postcss-None]` y `[@tailwindcss/postcss-None]` FALLAN con `production dep 'postcss' missing from dependencies` y `production dep '@tailwindcss/postcss' missing from dependencies`. **GREEN** = tras añadir las dos deps a `package.json`, crear `postcss.config.mjs`, y correr `npm install` para regenerar `package-lock.json`, el archivo completo de test de toolchain pasa (`30 passed in 0.02s`) y el archivo completo de test de build-pipeline pasa (`7 passed in 3.83s`); repetibilidad confirmada por una segunda corrida consecutiva (`7 passed in 3.83s`) sin flakiness; el bundle CSS compilado es byte-idéntico entre las dos corridas (`50.891 bytes`, hash-estable bajo el pipeline chunked de Turbopack). **TRIANGULATE** = el par de tests cubre tanto el lado de dep de `package.json` (test de toolchain) Y el lado de config de `postcss.config.mjs` (test de build-pipeline) Y el lado de artefacto de CSS compilado (preflight de Tailwind + ausencia de regla `@theme` + ausencia de `@import "tailwindcss"` + expansión de token de theme en `:root, :host`); una regresión futura que elimine la dep, remueva la config, o deje la directiva sin procesar en el CSS compilado queda capturada a nivel de artefacto. **Prueba de arreglo del defecto visual a nivel de artefacto**: en este worktree tras PR 5.5, un `node node_modules/.bin/next build` limpio produce `out/_next/static/chunks/391guka-hdllv.css` (50.891 bytes) que contiene **204 ocurrencias de `--tw-`** (variables utility de Tailwind — prueba de que el plugin generó clases utility), **1 ocurrencia de `@keyframes spin`** (la animación de Tailwind), **1 ocurrencia de `.animate-spin`** (una clase utility de Tailwind generada para el fuente React), **1 ocurrencia de `@layer theme { :root, :host { … --primary: #1d7ea9; … } }`** (la expansión de Tailwind 4 del bloque `@theme` legacy), **5 ocurrencias de `#1d7ea9`** (el valor hex de la paleta legacy `:root`, ahora correctamente izado en la cascada `:root` compilada), **cero ocurrencias de la regla literal `@theme {`**, y **cero ocurrencias del substring literal `@import "tailwindcss"`**. `node scripts/check-runtime.mjs` sale con `0` con `[check-runtime] Node 26.8.1 >= 20.9.0 OK (engines.node = ">=20.9.0")` — el guard de runtime queda inalterado. `npm ci` reproduce una instalación de 121 paquetes con las mismas 18 entradas de lockfile tailwind/postcss (`node_modules/@tailwindcss/{node,oxide,oxide-*,postcss}` + `node_modules/postcss` + `node_modules/tailwindcss`) en un clone fresco. **Implicaciones de topología / conteo (precisas, solo anexo)**: la cadena se expande de **16 hijos a 17 hijos**. El nuevo hijo de reparación se llama **PR 5.5 (reparación de pipeline Tailwind 4 / PostCSS)** y se ubica en la **posición 5.5/17** — interpolado entre la **posición 5/17 (PR 3c-iii, styling de Search / Folder / global Browser)** y la **posición 7/17 (PR 3c-iv, animaciones / utilities + paridad CSS final + barrel del design-system)**. Cada hijo que estaba previamente en la posición `n/16` (para `n ∈ {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}`) se renumera a `n+1/17` (así `6/16 → 7/17`, `7/16 → 8/17`, `8/16 → 9/17`, `9/16 → 10/17`, `10/16 → 11/17`, `11/16 → 12/17`, `12/16 → 13/17`, `13–15/16 → 14–16/17`, `16/16 → 17/17`). PR 3a permanece en `1/17`, PR 3b permanece en `2/17`, PR 3c-i permanece en `3/17`, PR 3c-ii permanece en `4/17`, PR 3c-iii permanece en `5/17`. El alcance de cada sub-PR, el mapeo de ramas predecesor / sucesor, el orden corregido, el bloqueo del Enfoque A, la base de FastAPI/SQLite, la estrategia de Feature Branch Chain, el estado congelado del predecesor, las specs por dominio, cada addendum previo (5c.1a, 5c.1b-A, 5c.1b-B, 5c.2-A, 5c.2-B.1a, 5c.2-B.1b-i, 5c.2-B.1b-ii-a, 5c.2-B.1b-ii-b, 5c.2-B.1b-ii-c, 3c-ii, 3c-iii), y el protocolo G5 de reemplazo aprobado por el usuario registrado arriba quedan sin cambios en su contenido sustantivo; solo sus etiquetas de posición se desplazan arriba por 1 (o permanecen donde estaban si estaban antes de la posición 5). **Posición de dependencia de PR 5.5**: depende de **PR 3c-iii** (el bloque `@theme` + los consumidores legacy `var(--token)` están en su lugar para que una expansión de `@tailwindcss/postcss` funcional tenga tokens para expandir y selectores para servir); **NO depende de PR 3c-iv** (los `@keyframes` + utilities + barrel del design-system aún no se envían, pero la reparación del pipeline de build no los necesita — el preflight + expansión de `@theme` + generación de utilities `--tw-*` son todo lo que PR 5.5 necesita para ser auto-contenido). El nuevo hijo de reparación es auto-contenido: no toca el contenido de `src/app/globals.css` (3c-i / 3c-ii / 3c-iii son dueños de ese archivo), no toca `tsconfig.json`, no toca `.nvmrc`, no toca `scripts/check-runtime.mjs`, no toca el Makefile, no toca `next.config.mjs`, no toca `api/server.py`, no toca ningún barrel de `src/modules/**`, no toca `web/**` (el bundle vanilla legacy), no toca `extension/**`, y no borra `web/*.{html,js,css}` ni `tailwind.config.js` (esos borrados aterrizan con PR 5c). **Presupuesto de LoC**: el diff authored de PR 5.5 está bien por debajo del presupuesto de 400 líneas (1 nuevo archivo de config `postcss.config.mjs` ≈ 25 LoC, 1 nuevo archivo de test `tests/test_tailwind_build_pipeline.py` ≈ 220 LoC, 1 archivo de test modificado `tests/test_toolchain_bootstrap.py` ≈ +12 LoC de delta, 1 `package.json` modificado ≈ +2 LoC de delta — total **≈ 259 LoC authored**, ≤ 400 con **−141 LoC de holgura**). **La excepción de lockfile es la única `size:exception` que abre PR 5.5** — véase el párrafo de excepción de lockfile abajo. **La cadena de 17 hijos se preserva** (la cadena creció exactamente por un hijo, en el único punto seguro de inserción: entre la rebanada de `src/app/globals.css` de PR 3c-iii y la rebanada de `@keyframes` + utilities + barrel del design-system de PR 3c-iv — ambas，位于下游 de la expansión de `@tailwindcss/postcss` que PR 5.5 finalmente provee). **La cuarta `size:exception` aprobada por el usuario para el `package-lock.json` regenerado (esta entrada, abre una cuarta `size:exception` de lockfile junto a las excepciones existentes de PR 3a + PR 3c-ii + PR 3c-iii; PR 3a es generated-resolution-only y permanece abierta como la `size:exception` de lockfile documentada previa; PR 3c-ii es una excepción de LoC authored, no de lockfile, y permanece abierta sin cambios; PR 3c-iii es una excepción de LoC authored, no de lockfile, y permanece abierta sin cambios; la presente excepción de PR 5.5 es una excepción de lockfile generado para las adiciones de resolución de `@tailwindcss/postcss` + `postcss`)**: el `package-lock.json` regenerado añade **16 nuevas entradas de lockfile relacionadas con tailwind/postcss** (del total de **18 entradas de lockfile relacionadas con tailwind/postcss** en el lockfile post-fix; `tailwindcss` en sí precede a esta reparación porque PR 3a lo añadió) (`node_modules/@tailwindcss/{node, oxide, oxide-android-arm64, oxide-darwin-arm64, oxide-darwin-x64, oxide-freebsd-x64, oxide-linux-arm-gnueabihf, oxide-linux-arm64-gnu, oxide-linux-arm64-musl, oxide-linux-x64-gnu, oxide-linux-x64-musl, oxide-wasm32-wasi, oxide-win32-arm64-msvc, oxide-win32-x64-msvc, postcss}` + `node_modules/postcss` + `node_modules/tailwindcss`) llevando el objeto `packages` total desde la línea base pre-3c-iii a **121 paquetes** y el conteo de líneas del lockfile a **2.112 líneas**. El cambio del lockfile es **generated-resolution-only** (sin contenido authored a mano); contiene **únicamente los cambios de resolución requeridos por las dos nuevas deps top-level** en `package.json`; se revisa junto con `package.json`; no carga churn de lockfile no relacionado. Las dos nuevas entradas de `package.json` están pineadas con caret (`^4.3.3` para `@tailwindcss/postcss` contra el mismo major Tailwind 4 que `tailwindcss`, `^8.5.0` para `postcss` contra la línea estándar PostCSS 8) así que el delta del lockfile es determinista bajo re-`npm install`. **Justificación de autorización** (por qué se prefiere un único PR revisable sobre fraccionar `postcss.config.mjs` lejos del cambio de dep + lockfile): (a) el registro del plugin PostCSS, las dos nuevas deps top-level, y el lockfile regenerado son inseparables — sin `@tailwindcss/postcss` instalado, `postcss.config.mjs` no puede registrarlo; sin `postcss` como dep peer, `@tailwindcss/postcss` no puede correr; sin el lockfile regenerado, `npm ci` no reproducirá la instalación en un clone fresco; (b) el test de regresión de build-pipeline es inseparable del arreglo (lee la salida CSS compilada que el arreglo produce); (c) fraccionar PR 5.5 aún más en un par 5.5-a / 5.5-b dejaría un pipeline de build medio roto que nadie puede revisar coherentemente y aún tendría que re-fusionarse en PR 5c; (d) el diff authored de PR 5.5 es ~259 LoC (bien por debajo del presupuesto de 400 líneas) así que no se necesita ninguna excepción adicional de LoC authored. **Hueco de evidencia de candidato-de-producción G2 (esta entrada expone un hueco que la cadena previa dejó abierto; PR 5.5 cierra un testigo pero NO flipea G2; G2 permanece pendiente de la captura completa de Fase 6)**: la cadena previa registró G2 como **PASS** trasladada del predecesor (`migrate-nextjs-tailwind4/`) según `design.md::§TL;DR` y `tasks.md::Phase 1.1` (G2 = build de static export limpio en `out/`). El PASS predecesor de G2 se capturó contra el **workspace aislado `tools/g2-candidate/`** con `tools/g2-candidate/app/globals.css` conteniendo SOLO `:root { color-scheme: light; }` + un reset de body — es decir, un archivo CSS de 4 líneas sin `@import "tailwindcss"`, sin `@theme`, y sin dependencia de Tailwind. **Ese PASS de G2 NO se traslada al repo de producción**, porque el `src/app/globals.css` del repo de producción (post-PR-3c-iii) envía la superficie canónica `@import "tailwindcss";` + `@theme { … }` que el plugin `@tailwindcss/postcss` debe procesar, y la cadena previa nunca registró ese plugin. Concretamente: un `next build` limpio contra el repo pre-PR-5.5 produce un `out/_next/static/chunks/391guka-hdllv.css` de **35.093 bytes** con el bloque `@theme { … }` como regla literal y cero preflight de Tailwind — el artefacto que el mount `StaticFiles` de FastAPI sirve en `127.0.0.1:8765/_next/static/chunks/391guka-hdllv.css` es la evidencia de candidato-de-producción G2; esa evidencia estaba ROTA antes de PR 5.5 y ahora está COMPLETA tras PR 5.5 (el bundle es **50.891 bytes** con el bloque `@theme` expandido a `@layer theme { :root, :host { … } }` y el preflight de Tailwind presente). **PR 5.5 cierra la mitad-de-pipeline-de-build del hueco de evidencia de candidato-de-producción G2** añadiendo el test de regresión a nivel de artefacto `tests/test_tailwind_build_pipeline.py` (que realiza un `next build` real y afirma sobre el CSS compilado); la mitad-de-navegador del hueco de G2 (una captura real de Chromium / Playwright contra `127.0.0.1:8765` probando que cada referencia `var(--token)` resuelve y que el preflight de Tailwind toma efecto en tiempo de ejecución) **permanece diferida al trabajo de validación de Fase 6a** y NO se reclama por este addendum. **G2 candidato-de-producción permanece PASS-pending-Phase-6-capture, NO flipeado por PR 5.5 solo**. **Qué NO reclama explícitamente PR 5.5**: (i) PR NO se reclama como fusionado en el tracker (`docs/complete-taxa-frontend-migration-plan`) o en `develop` — este addendum documenta solo el estado authored del worktree; (ii) PR NO se reclama como CI-green en la suite completa de tests del repo — los 31 fallos preexistentes en `tests/test_tailwind_4_{parity,base_resets,utilities}.py` + los 52 fallos preexistentes en `tests/test_tailwind_tokens_base.py` (todos los cuales son superficies diferidas de PR 3c-iv — aliases de namespace utility `--color-*` de Tailwind 4, `@keyframes spin` + `.animate-spin` en `@layer base`, presupuesto de tamaño-de-bytes contra el PR 3c-iv aún-por-enviar) son fallos preexistentes documentados, sin cambios por PR 5.5, y el test de regresión para ellos aterriza con PR 3c-iv según el addendum previo; (iii) PR NO se reclama como verificado-en-navegador (sin captura real de Chromium / Playwright contra `127.0.0.1:8765`); (iv) PR NO se reclama como G2-PASS (G2 permanece PASS-pending-Phase-6-capture, véase arriba); (v) PR NO habilita `gentle-ai review mode` y NO abre un PR — revisión / CI / merge siguen el proceso ordinario de feature-branch-chain una vez que la tarea padre autorizada-por-el-usuario complete. **Espejo en español** (`documents-es/openspec/changes/complete-taxa-frontend-migration/design-es.md`, este mismo archivo) carga la misma semántica; cualquier deriva se resuelve a favor del inglés.
