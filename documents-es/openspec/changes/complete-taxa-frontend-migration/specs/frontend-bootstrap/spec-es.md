# Especificación del Bootstrap del Frontend

> Dominio: `frontend-bootstrap`. Modificado según la propuesta
> pero no existe aún ningún spec canónico, por lo que este
> fichero es un **spec de dominio nuevo completo** (según el
> paso 3 del flujo OpenSpec). Autorizado bajo
> `complete-taxa-frontend-migration`. La sede canónica es la
> carpeta del cambio; el archivo copia este fichero literalmente
> en `openspec/specs/frontend-bootstrap/spec.md` al activarse.

## Propósito

El bootstrap del frontend enlaza la nueva exportación estática
de Next.js al montaje `StaticFiles` existente de FastAPI,
conecta el pipeline de build `make api` para que el artefacto
de build exista antes de que uvicorn enlace el puerto y aplica
el contrato de versión del runtime / Node. El contrato
preservado contra el build legacy es **propiedad del origen
único `127.0.0.1:8765`** — `WEB_DIR` se reorienta, la firma
del montaje queda sin cambios, el bind de uvicorn queda sin
cambios y no hay fallback silencioso al build vanilla legacy
ante un fallo.

## Requisitos

### Requisito: `WEB_DIR` reorientado a la exportación estática de Next.js

El sistema DEBE reorientar la constante `WEB_DIR` en
`api/server.py:54` al directorio producido por `next build`, y el
resto del código fuente de FastAPI DEBE quedar sin cambios.

#### Escenario: `WEB_DIR` resuelve a la exportación estática

- DADO que `api/server.py:54` declara
  `WEB_DIR = Path(__file__).parent.parent / "web"`
- CUANDO el worker de apply envía el cutover
- ENTONCES `WEB_DIR` resuelve a `<repo-root>/out/` (la
  exportación estática de Next.js)
- Y el resto de `api/server.py` es byte-idéntico excepto por la
  declaración de la constante `WEB_DIR` y cualquier middleware
  estrictamente necesario para cablear la Aproximación A

#### Escenario: La firma del montaje queda sin cambios

- DADO que `api/server.py:1815` declara
  `app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")`
- CUANDO el worker de apply envía el cutover
- ENTONCES la firma del montaje queda byte-idéntica
- Y el fallback SPA `html=True` queda byte-idéntico
- Y no se introduce un segundo montaje

### Requisito: Sin segundo puerto de servidor de desarrollo

El sistema DEBE enlazar uvicorn a `127.0.0.1:8765` y NO DEBE
abrir ningún segundo puerto de servidor de desarrollo.

#### Escenario: `make api` solo enlaza el 8765

- DADO que `make api` invoca `next build` y luego uvicorn
- CUANDO el worker de apply inspecciona los listeners abiertos
- ENTONCES uvicorn está enlazado a `127.0.0.1:8765`
- Y ningún segundo uvicorn / servidor de dev de Next.js /
  proceso Node está enlazado a otro puerto TCP
- Y los `host_permissions` de la extensión de Chrome
  permanecen en `["http://localhost:8765/*"]`

#### Escenario: Sin segundo origen en el manifest de la extensión

- DADO que `extension/manifest.json::host_permissions` es
  `["http://localhost:8765/*"]` y `content_scripts.matches` es
  `["http://localhost:8765/*"]`
- CUANDO el worker de apply envía el cutover
- ENTONCES `host_permissions` queda sin cambios
- Y `content_scripts.matches` queda sin cambios
- Y no se añade ningún segundo origen, ni puerto nuevo, ni URL
  nueva al manifest de la extensión

### Requisito: El pipeline de build corre antes que uvicorn

El sistema DEBE asegurar que el artefacto de build de Next.js
exista antes de que uvicorn enlace el puerto, sin fallback
silencioso a legacy.

#### Escenario: `make api` corre `next build` primero

- DADO el target `Makefile::api`
- CUANDO el usuario ejecuta `make api`
- ENTONCES el target invoca el paso de build de Next.js primero
- Y solo después de que `next build` sale con `0` el target
  invoca uvicorn
- Y si `next build` sale con código distinto de cero, el target
  sale con código distinto de cero **antes** de que uvicorn
  enlace

#### Escenario: Artefacto de build ausente falla rápido

- DADO un clon limpio (no existe el directorio `out/`)
- CUANDO el usuario ejecuta `make api`
- ENTONCES el paso de build corre y produce `out/`
- Y uvicorn solo enlaza después de que `out/index.html` y
  `out/_next/static/chunks/**` existan con bytes no nulos
- Y no hay **ningún** fallback silencioso a los ficheros legacy
  de `web/`

#### Escenario: Verificación de versión del runtime de Node

- DADO que `package.json::engines.node` es `">=20.9.0"`
- CUANDO el usuario ejecuta `make api`
- ENTONCES `scripts/check-runtime.mjs` corre primero
- Y la verificación sale con código distinto de cero si
  `node --version` está por debajo de `20.9.0`
- Y el target del Makefile sale con código distinto de cero
  **antes** de que uvicorn enlace ante un mismatch de versión
  de Node

### Requisito: Atomicidad del manifiesto de consumidores activos

El sistema DEBE actualizar cada consumidor activo enumerado en
`design.md::§3.1` del predecesor en la misma release que el
repoint de `WEB_DIR`.

#### Escenario: Los 26 consumidores §3.1 se actualizan juntos

- DADO que `design.md::§3.1` del predecesor enumera 21
  consumidores activos del montaje web de FastAPI y 5
  consumidores activos de `web/search_urls.js`
- CUANDO el worker de apply envía el cutover
- ENTONCES cada consumidor activo se actualiza en la misma
  unidad de release
- Y ningún consumidor permanece "activo" contra una ruta que el
  cutover borra
- Y el `activation_status` del cutover-manifest.json se voltea a
  `selected` para cada consumidor que el cutover activa

#### Escenario: El test de contrato AC-21 sigue verde

- DADO que `tests/test_smoke.py::test_search_engine_contract`
  (AC-21) lee el literal de search-engines
- CUANDO el worker de apply envía el cutover
- ENTONCES el test sigue pasando
- Y si el literal se movió de `web/search_urls.js` a
  `src/data/search-engines.js`, la ruta `open()` del test se
  actualiza en la misma release
- Y la forma byte a byte (key, label, with_authorship,
  ordering) queda idéntica al literal legacy
- Y el mirror del lado servidor en
  `api/server.py::_SEARCH_ENGINES` queda byte-idéntico a los
  campos coincidentes del literal

### Requisito: La configuración CSS-first de Tailwind 4 reemplaza a `tailwind.config.js`

El sistema DEBE borrar `tailwind.config.js` y reemplazarlo con
el bloque `@theme` CSS-first de Tailwind 4 dentro de
`globals.css`.

#### Escenario: `tailwind.config.js` se borra en la activación

- DADO que `tailwind.config.js` se envía en el `package.json`
  legacy
- CUANDO el worker de apply envía el cutover
- ENTONCES `tailwind.config.js` se borra
- Y el bloque `@theme` de Tailwind 4 vive en `globals.css`
- Y el `package.json` elimina `autoprefixer`, `postcss`,
  `@tailwindcss/forms`
- Y el `package.json` añade `tailwindcss@^4`, `next@^16`,
  `react@^19`, `react-dom@^19`, el toolchain TS
  (`typescript@>=5.1.0`, `@types/react@^19`,
  `@types/react-dom@^19`, `@types/node`)

### Requisito: Unidad de cutover atómica

El sistema DEBE cambiar la unidad de cutover de forma atómica —
una sola unidad de release cambia la constante `WEB_DIR`, cada
consumidor activo, el pipeline de build y el artefacto de build
juntos.

#### Escenario: El cutover es una sola release

- DADO que `design.md::§1` del predecesor registra el cutover
  atómico como una sola unidad de release
- CUANDO el worker de apply envía el cutover
- ENTONCES lo siguiente cambia junto en una sola release:

  1. Constante `WEB_DIR` en `api/server.py:54`.
  2. Cada actualización de consumidor activo enumerada en
     `design.md::§3.1` del predecesor (imports, la ruta lectora
     de AC-21, cada consumidor de test).
  3. Los targets `Makefile::api` y `Makefile::web`.
  4. El artefacto de build (el propio `out/`).

- Y no se soporta ningún cutover parcial bajo este dominio

#### Escenario: No se soporta revertir un subconjunto

- DADO que el cutover aterrizó atómicamente
- CUANDO el maintainer revierte solo uno de los cuatro conjuntos
- ENTONCES el sistema queda roto (los consumidores referencian
  rutas borradas, falla el shell de la SPA o el test de contrato
  AC-21)
- Y `git revert <cutover-sha>` es la **única** ruta de rollback
  soportada

### Requisito: Unidad de rollback

El sistema DEBE soportar rollback mediante un único
`git revert` que restaure el build vanilla legacy atómicamente.

#### Escenario: `git revert <cutover-sha>` restaura el build legacy

- DADO que el cutover aterrizó
- CUANDO el maintainer ejecuta `git revert <cutover-sha>`
- ENTONCES `web/index.html`, `web/app.js`, los 18 módulos
  `web/*.js`, `web/dist/tailwind.css` y `tailwind.config.js` se
  restauran atómicamente
- Y el `package.json` revierte al estado de dependencias legacy
- Y `npm ci` reproduce el lock legacy
- Y `make api` regenera `web/dist/tailwind.css` desde la fuente
  revertida
- Y `make smoke` vuelve a la línea base previa a la migración
  (63 passed, 8 skipped sobre el mismo conjunto de fixtures)

#### Escenario: No se requiere migración de datos

- DADO que no se envía ningún cambio de esquema de BD en este
  cambio
- CUANDO el maintainer ejecuta `git revert <cutover-sha>`
- ENTONCES no se requiere ninguna migración de datos para
  revertir
- Y `data/db/taxa.db` queda sin cambios por el cutover y el
  rollback

#### Escenario: Continuidad de la extensión durante el rollback

- DADO que la extensión habla con `http://localhost:8765` antes,
  durante y después del cutover
- CUANDO el maintainer ejecuta `git revert <cutover-sha>`
- ENTONCES la extensión sigue funcionando sin una actualización
  del `manifest.json`
- Y `host_permissions` permanece en
  `["http://localhost:8765/*"]`

## Notas

- El `design.md::§1` del predecesor ("G1 boundary decision
  recorded") y `design.md::§3.1` ("Active-consumer inventory")
  se importan como historial de planificación — este spec de
  dominio los refleja, no los rederiva.
- El `cutover-manifest.json` en
  `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
  es la fuente de verdad legible por máquina para los 26
  consumidores activos. La activación voltea `activation_status`
  de `selected` (legacy pre-cut) a un registro de activación
  post-cut; la fase de apply posee ese volteo.
- La lista "Fuera del alcance" de la propuesta (reescritura del
  backend, pipeline ETL, SEO, rutas nuevas, herramientas de
  cobertura, rediseño visual) aplica a este dominio sin
  cambios.