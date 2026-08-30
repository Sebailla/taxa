# Propuesta: migrate-nextjs-tailwind4

## Intención

El frontend actual de `taxa` es una aplicación vanilla-JS de pantalla
única con 6.345 líneas servida por FastAPI en un único puerto local
(8765). Combina CSS ad hoc, estado del lado del cliente y mejora
progresiva sin bundler, sin React y sin router. Este cambio reemplaza
dicho frontend por un stack Next.js (App Router) + React + Tailwind 4
en una sola entrega, manteniendo FastAPI como único origen local y el
contrato de `/api/*` byte-idéntico cuando sea posible. La migración
elimina deuda técnica acumulada (sin tipado, JS monolítico, diff
manual del DOM mediante reescritura por `render()`) y habilita el
trabajo de paridad para la extensión de Chrome y futuras rutas
(Settings, About, Help).

## Alcance

### Incluido

- Aplicación Next.js 16 (App Router) bajo `src/app/` que
  renderiza toda la UI de pantalla única: pestañas del header,
  árbol, breadcrumb, panel de detalle, explorador de archivos,
  visor de archivos, diálogos, banners, ajustes y ayuda.
- Componentes funcionales de React 19 que reemplazan los módulos
  de `web/*.js` uno a uno cuando sea posible.
- Configuración CSS-first de Tailwind 4 en
  `src/app/globals.css` con `@theme { … }`, conteniendo todos
  los design tokens presentes hoy en `tailwind.config.js` y en
  el bloque `:root` inline.
- FastAPI sigue sirviendo la salida estática construida en
  `http://127.0.0.1:8765/`; se preserva el contrato de origen
  único.
- Estado y preferencias locales del navegador (tema, fuente del
  árbol, último taxón seleccionado, estado del menú kebab)
  migrados desde el singleton `state` a estado/contexto de
  React, con un pequeño adaptador que hidrata desde
  `localStorage` en el primer render.
- Accesibilidad: cada elemento interactivo actualmente
  desplegado mantiene su semántica ARIA y su paridad de teclado
  (sin regresión frente al suite actual de Playwright).
- Paridad funcional: cada flujo visible de usuario (navegar,
  buscar, materializar, previsualizar, abrir carpeta, guardar
  URL, ver archivos en PDF/HTML/MD/TXT/DOCX/XLSX/EPUB/JSON/imagen/video)
  se comporta de forma idéntica al build legacy; regresión de
  rendimiento ≤ 0%.
- Conjunto mínimo de dependencias: `next@^16`, `react@^19`,
  `react-dom@^19`, `tailwindcss`, `@tailwindcss/cli` (solo para
  la transición del build CSS legacy), toolchain de TypeScript
  `>=5.1.0`. Cada adición debe estar justificada.
- Compatibilidad de runtime: el build y las herramientas de
  desarrollo DEBEN ejecutarse sobre Node.js `>=20.9.0`
  (requisito duro de Next.js 16) y DEBEN escribirse contra
  TypeScript `>=5.1.0`. Las versiones exactas pineadas para
  Next.js 16 y Tailwind 4 se registran en
  `openspec/changes/migrate-nextjs-tailwind4/design.md` (espejo en
  español bajo
  `documents-es/openspec/changes/migrate-nextjs-tailwind4/design-es.md`),
  §§"Contrato del motor de runtime", "Superficie de dependencias",
  "§1 Decisión de frontera de responsabilidad del servidor".
- Plan de rollback: `git revert` del PR único de migración
  restaura el build vanilla; `web/dist/tailwind.css` se
  regenera a partir de la fuente revertida.

### Frontera de Responsabilidad del Servidor (Next.js ↔ FastAPI)

La frontera entre el runtime de Next.js y el servidor FastAPI se
**evalúa y decide** durante esta migración. La exploración enumeró
tres aproximaciones viables:

| Aproximación | Rol de Next.js | Rol de FastAPI | Contrato de puerto único |
|--------------|----------------|----------------|--------------------------|
| **A — Exportación estática bajo FastAPI** | `next build` → `out/`; el montaje `StaticFiles` de FastAPI lo sirve. Sin SSR / route handlers / server components. | Único origen HTTP en `127.0.0.1:8765`; sirve frontend + `/api/*`. El montaje `StaticFiles` en `api/server.py:1815` se reorienta a `out/` una vez registrada. | **Preservado.** |
| **B — Servidor de dev Next.js completo, dos puertos** | `next dev` en puerto 3000; `rewrites()` redirige `/api/*` hacia FastAPI. SSR real, server components, `next/font`. | FastAPI en 8765 solo para `/api/*`; la allowlist CORS se amplía para incluir `localhost:3000`. El montaje `StaticFiles` queda como código muerto en dev. | **Roto.** El `host_permissions` de la extensión debe ampliarse. |
| **C — Híbrido por fases** | Fase 1: solo Tailwind 4 sobre vanilla JS. Fase 2: pre-renderizado de Next.js hacia `web/dist/`. Fase 3: hidratación incremental de React tras un feature flag. Fase 4: retirada de vanilla. | Único origen durante todo el proceso; el montaje `web/dist/*` se mantiene compatible. | **Preservado durante todo el proceso.** |

**Restricciones que CUALQUIER aproximación elegida DEBE respetar:**

- Origen local único / puerto único (`127.0.0.1:8765`) — no se
  introduce un segundo puerto de servidor de desarrollo en este
  cambio.
- Equivalencia funcional: cada forma, payload y comportamiento de
  endpoint `/api/*` se mantiene idéntico (sin cambios incompatibles
  de ruta o payload).
- Continuidad de la extensión:
  `extension/manifest.json::host_permissions` permanece como
  `["http://localhost:8765/*"]` en este cambio.
- La lógica de backend (`api/server.py`, SQLite/WAL, flujo de
  materialización, defensa SSRF en `save-url`) **no se reescribe**,
  pero el montaje de activos estáticos (`api/server.py:1815`) y
  cualquier middleware de FastAPI estrictamente necesario para
  cablear la aproximación elegida SÍ está dentro del alcance.

**Resultado**: esta propuesta **no prejuzga** la aproximación A, B
ni C. La aproximación seleccionada se registra como decisión
finalizada en `design.md` §1 una vez que las fases spec/design
produzcan evidencia concreta (tamaño de bundle, perfil de
hidratación, paridad Playwright). Las restricciones duras
anteriores son innegociables. **Decisión de frontera G1** (FastAPI
único origen en `127.0.0.1:8765`; `/api/*` y
`extension/manifest.json::host_permissions` sin cambios) registrada
en `design.md::§1`; vincula cada Aproximación.

### Fuera de Alcance

- Reescritura del backend: handlers de ruta de `api/server.py`,
  lógica SQLite/WAL, flujo de materialización, defensa SSRF en
  `save-url`, pipeline ETL. El código de la aplicación FastAPI
  que respalda `/api/*` no se toca; el único cambio permitido del
  lado del servidor es el mínimo necesario para montar la nueva
  salida del frontend (p. ej. reorientar `WEB_DIR`, añadir un paso
  de build a `make api`). Las formas de los endpoints permanecen
  idénticas (equivalencia funcional, sin cambios incompatibles de
  ruta o payload).
- Pipeline ETL: `etl/parse_textree`, `load_coldp`,
  `load_worms`, `load_freshwater`, migraciones.
- Paridad de la extensión de Chrome
  (`extension/manifest.json`, `background.js`, `content.js`).
  El `host_permissions` de la extensión se mantiene en
  `http://localhost:8765/*`. Un cambio aparte documenta el
  plan de adaptación a React.
- SEO (sin trabajo de metadatos, sitemap o robots en este
  cambio).
- Nuevas rutas (Settings, About, Help) más allá de lo que la UI
  legacy expone hoy.
- Rediseño visual a nivel de píxel (revisión impeccable/Stitch),
  queda como seguimiento, no como bloqueante.
- Cobertura (`coverage.available: false` es el estado actual;
  fuera de alcance).

### Sonda de Exportación Estática Desechable (Solo Evidencia)

Una rebanada de sonda de exportación estática acotada y
**desechable** se permite **solo como ejercicio de recolección
de evidencia** mientras la decisión de responsabilidad de
servidor Next.js ↔ FastAPI siga abierta. La sonda se rige por
estos innegociables:

- **Inalcanzable desde producción**: la salida de la sonda no la
  sirve FastAPI, no se vincula a `127.0.0.1:8765` y no es
  alcanzable desde ningún artefacto desplegado (sin cambios en
  `host_permissions` de la extensión, sin integración con
  `make api`, sin artefacto de release).
- **Sin cambios en consumidores**: el montaje `StaticFiles` en
  `api/server.py:1815`, los consumidores del contrato AC-21 de
  motores de búsqueda y las rutas de activación de UI
  (singleton `state`, claves de `localStorage`) quedan intactos.
  La sonda no produce ninguna superficie visible para los
  consumidores.
- **Solo evidencia**: registra tamaño de `next build`, perfil de
  hidratación y muestras opcionales de paridad con Playwright.
  No modifica `design.md` §1 ni pre-selecciona la Aproximación A.
- **Descarte / rollback explícito**: la sonda vive en una rama
  de corta vida; `git branch -D` más la eliminación del worktree
  restablece el estado previo a la sonda sin residuos en
  fuente, tests o configuración.
- **No puede seleccionar exportación estática por sí sola**: la
  evidencia de la sonda es necesaria pero no suficiente.
  Seleccionar la Aproximación A requiere una modificación de
  seguimiento a esta propuesta (o un cambio sucesor), revisada
  contra la evidencia registrada; esta propuesta no es el punto
  de selección.

La sonda **no** modifica "Fuera de Alcance", "Approach" ni
"Criterios de Éxito", y no introduce cambios en fuente, tests
o configuración en este PR. Su único propósito es convertir la
decisión abierta de responsabilidad de servidor en evidencia
antes de finalizarla.

## Capabilities

### Nuevas

- `frontend-runtime`: aplicación Next.js App Router de pantalla
  única, SSR cuando sea compatible (payload inicial de la
  ruta), hidratación en cliente de los componentes
  interactivos de árbol / detalle / explorador de archivos,
  todo bajo el montaje estático de FastAPI.
- `design-tokens`: bloque `@theme` de Tailwind 4 + variables
  CSS (`--primary`, `--realm-*`, etc.) preservadas
  literalmente, de modo que tanto las clases utilitarias como
  las reglas CSS planas resuelvan.
- `browser-state-hydration`: migración consciente de React del
  singleton legacy `state` (`web/state.js`) a un store tipado
  con claves explícitas de rehidratación desde `localStorage`:
  `theme`, `tree-source`, `last-taxon-id`, `kebab-open-id`.

### Modificadas

- `research`: los consumidores API migran a llamadas `fetch`
  desde componentes React / server components. Sin cambios en
  la forma de request/response; el test de contrato AC-21
  sigue leyendo `web/search_urls.js` salvo que la fase
  sdd-spec revise explícitamente AC-21.
- `frontend-bootstrap`: `web/index.html` deja de ser el entry;
  el entry es la salida de `next build` (`out/` o `.next/static`)
  servida por el montaje `StaticFiles` existente de FastAPI.

## Approach

La Aproximación (A / B / C) queda **bloqueada por evidencia** según
`design.md::§1` (G2–G6); el default esperado es `next build` → `out/`
servido por FastAPI en `127.0.0.1:8765`. Tailwind 4
se entrega en la misma release mediante su configuración
CSS-first (`@theme { … }`) que reemplaza a `tailwind.config.js`
y al bloque `<style>` inline; los tokens `:root` ad hoc migran
a `src/app/globals.css` dentro de `@layer base` para que el
orden en cascada coincida con el actual. Los 18 módulos ES
vanilla se convierten en ~18 componentes funcionales React en
`src/components/`, con server components para los primitivos de
solo lectura (header / footer / breadcrumb / detail-card) y
client components para el árbol, el explorador de archivos, el
visor y cualquier superficie con estado. El singleton `state`
se convierte en un store tipado con rehidratación desde
`localStorage`. La forma del contrato AC-21 (literal en
`web/search_urls.js`) se mantiene durante esta primera
entrega; si la fase spec decide reubicarlo, AC-21 se modifica
antes de cualquier movimiento de fuente. Las claves de estado
local del navegador se documentan y migran de forma
determinista (una clave, un sitio de lectura, un sitio de
escritura).

## Áreas Afectadas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `web/index.html` | Eliminado | Reemplazado por `src/app/layout.tsx` + `src/app/page.tsx`. |
| `web/*.js` (18 módulos, 6.345 LoC) | Eliminado | Reescrito como componentes React bajo `src/components/` y `src/lib/`. |
| `web/index.css` | Modificado | Pasa a ser `src/app/globals.css`; el bloque `@theme` reemplaza a `tailwind.config.js`. |
| `tailwind.config.js` | Eliminado | Configuración CSS-first de Tailwind 4 en `globals.css`. |
| `package.json` | Modificado | Sube a `next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss ^4.x`; elimina `autoprefixer`, `postcss`; añade `@tailwindcss/cli`, TypeScript `>=5.1.0`, `@types/*`. Añade `engines.node: ">=20.9.0"` y la versión de Node pineada en tiempo de desarrollo. |
| `api/server.py:1815` (`app.mount("/", StaticFiles(...))`) | Modificado | La constante `WEB_DIR` se reorienta a la salida de Next.js elegida (`out/`, `web/dist/next-static/`, o equivalente) según la Aproximación decidida en `design.md` §1. Cualquier middleware nuevo estrictamente necesario para servir la salida elegida se añade aquí; los handlers de ruta no se reescriben. |
| `Makefile` | Modificado | `make api` primero construye Next.js (alias `make web`) y luego ejecuta uvicorn; `make smoke` mantiene la misma superficie. No se introduce un segundo puerto de servidor de desarrollo. |
| `tests/test_smoke.py::test_search_engine_contract` | Modificado | Lee `src/data/search-engines.ts` solo si sdd-spec modifica AC-21; en caso contrario, el archivo mantiene la forma de `web/search_urls.js` bajo `src/data/`. |
| `tests/test_e2e_file_explorer.py`, `tests/test_web_toggle.py` | Modificado | Selectores DOM actualizados al nuevo árbol de componentes; contrato de atributos `data-*` preservado. |
| `extension/manifest.json` | Sin cambios | `host_permissions: ["http://localhost:8765/*"]` se mantiene (diferido). |
| `openspec/changes/migrate-nextjs-tailwind4/design.md` | Migrar (PR 2a) | Versiones fijadas, justificación de dependencias, decisión finalizada de responsabilidad de servidor Next.js ↔ FastAPI (Aproximación A / B / C), decisiones de layout acotadas a PR 2a y el contrato de alias de ruta de `tsconfig.json`. Destino canónico de toda referencia previamente apuntada al artefacto ahora reemplazado `scope-decisions.md`. |
| `documents-es/openspec/changes/migrate-nextjs-tailwind4/design-es.md` | Migrar (PR 2a) | Espejo fiel en español neutro/profesional de `design.md` según AGENTS.md. |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| El cambio de namespace de tokens en Tailwind 4 (`--color-primary` vs `--primary`) rompe las referencias `var(--primary)` del CSS plano. | Media | Alias de nombres en `@theme` para que los tokens `--primary`, `--bg-surface`, `--realm-*` resuelvan sin cambios; test de paridad enumera cada referencia `var(--token)` y exige una declaración no vacía. |
| Reordenamiento en cascada de `color-mix()` en el bloque `<style>` inline de 80 KB provoca deriva visual. | Media | Migrar las reglas ad hoc a `globals.css` dentro de `@layer base` para preservar el orden de fuente; regresión visual con Playwright sobre el fixture existente de `tests/test_web_toggle.py`. |
| El test de contrato AC-21 de motores de búsqueda falla porque `web/search_urls.js` deja de ser byte-idéntico. | Media | Mantener el literal JS bajo `src/data/search-engines.js` con la misma forma; el test lee `open()` desde la ruta nueva. La fase spec decide si se modifica AC-21. |
| Desajuste de hidratación por lecturas de `localStorage` en servidor vs cliente. | Media | El render inicial usa una bandera `mounted`; las lecturas suceden dentro de `useEffect`; la estructura del árbol asume estado vacío en el primer pintado. |
| La exportación estática pierde rutas dinámicas / image optimization que pueda requerir trabajo futuro. | Baja | Aceptable para v1; documentar el trade-off en `design.md` §1; migrar al servidor de dev completo de Next.js (Approach B) es el coste del siguiente cambio si se necesita. |
| El bundle de Next.js + React introduce regresión en el pintado inicial (presupuesto de rendimiento). | Baja | Perfil de `next build` capturado antes/después; muestra de Playwright + Lighthouse sobre el fixture chromium existente; ≤ 0% de regresión como criterio de éxito. |
| El contrato de puerto único se rompe si cambian accidentalmente los `host_permissions` de la extensión. | Baja | Regla dura en `Makefile` y verificación CI de humo: `make api` solo escucha 8765; sin segundo origen añadido; `manifest.json` sin cambios en este PR. |

## Plan de Rollback

1. **Reversión a nivel de PR**: `git revert <migration-sha>`
   restaura el `web/` vanilla + `tailwind.config.js` + pipeline
   de Tailwind 3.4. `package-lock.json` conserva el estado
   previo de dependencias Node; `npm ci` reproduce el lock.
   `make api` regenera `web/dist/tailwind.css` desde la fuente
   revertida.
2. **Efectos colaterales**: el test de contrato AC-21 vuelve a su
   lectura previa `open("web/search_urls.js")`; los tests de
   backend quedan intactos.
3. **Rollback de producción** (si la migración llega a `main`):
   `git checkout <last-good-sha> -- web/ package.json
   package-lock.json Makefile src/ tests/`, reinstalar con
   `npm ci && make css`, redesplegar mediante el proceso de
   release existente. Este cambio no introduce cambios de
   esquema de BD, por lo que la reversión no requiere migración
   de datos.
4. **Continuidad de la extensión**: la extensión habla con
   `http://localhost:8765` antes, durante y después del
   rollback — no se requiere actualización del manifest.
5. **Verificación tras el rollback**: `make smoke` vuelve a la
   línea base previa a la migración (63 passed, 8 skipped sobre
   el mismo conjunto de fixtures, más las ejecuciones existentes
   de Playwright).

## Dependencias

- `next@^16` (App Router; Next.js 16 es la línea objetivo y
  admite React `^19.0.0`).
- `react@^19`, `react-dom@^19` (coinciden con el major de React
  pineado por Next.js 16).
- `tailwindcss` ^4.x.
- `@tailwindcss/cli` (solo transitorio, si se requiere una ruta
  de build no-Next durante la migración).
- `typescript` `>=5.1.0`, `@types/react@^19`,
  `@types/react-dom@^19`, `@types/node` (toolchain TS,
  justificado para estado React tipado y tipos del cliente API;
  TypeScript `>=5.1.0` es el suelo de Next.js 16).
- `next/font` para Raleway, JetBrains Mono y Material Symbols
  Outlined (justificación: se mantienen las fuentes existentes,
  sin nuevo set de iconos según el AGENTS.md del proyecto).
- Motor de runtime: Node.js `>=20.9.0` (requisito duro de
  Next.js 16). Registrado en `package.json::engines.node` cuando
  la reescritura aterriza con la tarea 3.4 de PR 3, y en
  `design.md` §"Contrato del motor de runtime".
- Ninguna otra dependencia runtime sin justificación explícita
  por capability en `design.md` §"Superficie de dependencias".

## Criterios de Éxito

- [ ] Paridad funcional: cada flujo de usuario (navegar,
      buscar, materializar, previsualizar, abrir carpeta,
      guardar URL, ver archivos en todos los formatos
      soportados) se comporta de forma idéntica al build
      legacy.
- [ ] Rendimiento: sin regresión en pintado inicial ni en
      latencia de interacción sobre la muestra existente de
      Playwright + Lighthouse (Δ ≤ 0%).
- [ ] Origen local único: `make api` solo escucha 8765; sin
      segundo servidor de dev; `host_permissions` de la
      extensión sin cambios.
- [ ] Todos los tests pytest de backend siguen verdes (línea
      base 63 passed, 8 skipped preservada).
- [ ] El suite de Playwright queda actualizado y verde sobre
      el nuevo árbol de componentes; contrato de atributos
      `data-*` preservado.
- [ ] Test de contrato AC-21 de motores de búsqueda pasa (la
      ubicación del archivo puede moverse, la forma byte a
      byte se mantiene salvo revisión por sdd-spec).
- [ ] El estado y las preferencias locales del navegador
      migran de forma determinista (`theme`, `tree-source`,
      `last-taxon-id`, `kebab-open-id`) con un sitio de
      lectura y un sitio de escritura por clave.
- [ ] Accesibilidad: cada rol ARIA, etiqueta y handler de
      teclado del build legacy se preserva; el escaneo axe
      no muestra nuevas violaciones.
- [ ] Paridad Tailwind 4: cada clase utilitaria presente en
      el build legacy resuelve a una declaración no vacía en
      el nuevo build; cada token `:root` (`--primary`,
      `--realm-*`, etc.) resuelve.
- [ ] Rollback: `git revert` del PR único de migración
      restaura el build legacy con humo + Playwright verdes.
