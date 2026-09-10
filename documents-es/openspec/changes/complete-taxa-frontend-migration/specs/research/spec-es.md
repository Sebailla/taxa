# Delta para Research

> Spec delta contra el canónico
> `openspec/specs/research/spec.md` (que captura el file
> explorer + visor multi-formato). El spec canónico se
> **preserva sin cambios** — cada requisito y cada escenario
> permanece vinculante. Este delta captura **solo el contrato
> de migración**: los componentes React consumen las mismas
> formas `/api/*`, el test de contrato AC-21 de motores de
> búsqueda mantiene la misma forma byte a byte y la ubicación
> del literal PUEDE moverse bajo `src/data/`.

## Requisitos AÑADIDOS

### Requisito: Contrato de migración — mismas formas `/api/*` desde React

El sistema DEBE consumir cada endpoint `/api/*` que el spec
canónico de research enumera desde componentes React (server o
client components) sin cambiar la forma de la petición, la forma
de la respuesta, el código de estado ni las cabeceras.

#### Escenario: Forma de `/api/taxon/{id}/files` sin cambios desde React

- DADO que el spec canónico de research enumera la forma de
  respuesta de `GET /api/taxon/{id}/files`
- CUANDO el componente file-explorer de React dispara la petición
  vía `fetch('/api/taxon/{id}/files')`
- ENTONCES la respuesta es 200 con la misma forma del cuerpo JSON
  (`{ exists, taxon_id, taxon_name, taxon_path, filesystem_path,
  root: { … } | null }`)
- Y se devuelve 404 con `detail: "taxon {id} not found"` cuando
  el taxón es desconocido
- Y se devuelve 200 con `exists: false, root: null` cuando el
  taxón existe pero la carpeta de research no está materializada
- Y se reutiliza el recorrido por la cadena de padres para
  sinónimos (`_build_segments()` desde `api/server.py`)

#### Escenario: Forma de `/api/taxon/{id}/files/serve` sin cambios desde React

- DADO que el spec canónico de research enumera la forma de
  respuesta de `GET /api/taxon/{id}/files/serve?path=<rel>`
- CUANDO el visor de ficheros de React dispara la petición vía
  `fetch('/api/taxon/{id}/files/serve?path=<rel>')`
- ENTONCES la respuesta es 200 con el cuerpo del fichero, el
  `Content-Type` correspondiente y
  `Content-Disposition: inline`
- Y el path traversal (`..`), las rutas absolutas y las escapes
  por symlink se rechazan con 400 `detail: "Path escapes research
  root"`
- Y las rutas de fichero desconocidas devuelven 404
  `detail: "File not found"`
- Y los taxones no materializados devuelven 404
  `detail: "Research folder not materialized"`
- Y los ficheros mayores que el cap de 100 MB devuelven 413
- Y `Content-Type` coincide con la tabla de extensiones canónica

### Requisito: Test de contrato AC-21 de motores de búsqueda preservado

El sistema DEBE preservar la forma byte a byte del test de
contrato AC-21 de motores de búsqueda. Si el literal de
search-engines se reubica, la ruta `open()` del test se
actualiza en la misma release; la forma byte a byte del literal
(key, label, with_authorship, ordering) queda sin cambios.

#### Escenario: Paridad byte a byte de AC-21

- DADO que `tests/test_smoke.py::test_search_engine_contract`
  (AC-21) parsea el literal de search-engines como texto y
  afirma que cada triple `{ key, label, with_authorship }`
  coincide byte a byte con `api/server.py::_SEARCH_ENGINES` en
  el mismo orden
- CUANDO el worker de apply envía el cutover
- ENTONCES AC-21 sigue pasando
- Y si el literal se movió de `web/search_urls.js` a
  `src/data/search-engines.js`, la ruta `open()` de AC-21 se
  actualiza en la misma release
- Y la forma byte a byte del literal queda sin cambios (sin
  reformatear, sin reordenar entradas, sin renombrar campos)
- Y `api/server.py::_SEARCH_ENGINES` queda sin cambios
- Y la pestaña Search en el panel de detalle sigue agrupando los
  motores bajo los encabezados legacy de `CATEGORIES` (`general`,
  `taxonomic`, `academic`, `multimedia`, `documents`)

#### Escenario: Mirror del lado servidor sin cambios

- DADO que `api/server.py::_SEARCH_ENGINES` es la fuente de
  verdad del lado servidor para `/api/taxon/{id}/searches`
- CUANDO el worker de apply envía el cutover
- ENTONCES la respuesta del servidor (plantillas de URL, flag
  `with_authorship`, orden) es byte-idéntica a la respuesta
  legacy
- Y el frontend nunca construye URLs localmente; las URLs
  siempre vienen del servidor (`urllib.parse.quote_plus`)

### Requisito: Las superficies UI de research son componentes React

El sistema DEBE renderizar cada superficie UI de research (file
explorer, visor de ficheros, búsqueda en el árbol, tira de
pestañas Raw / Table / Tree, lazy loader de librerías CDN, meta
strip, breadcrumb, banners de error) como componentes React
bajo la capability `research` de la modular-architecture. Los
componentes React DEBEN preservar cada comportamiento visible,
cada rol / etiqueta ARIA, cada handler de teclado y cada
atributo `data-*` que el spec canónico de research enumera.

#### Escenario: Comportamiento del árbol del file explorer desde React

- DADO que el spec canónico de research enumera la semántica de
  clic simple / doble clic, la semántica de expand / collapse de
  carpetas, el debounce de búsqueda en el árbol (200 ms), los
  modos filter / highlight, el comportamiento
  switching-taxon-clears-state y los mensajes de estado vacío
- CUANDO el file explorer de React se renderiza
- ENTONCES cada comportamiento coincide con el escenario del spec
  canónico
- Y cada atributo `data-*` en las filas del árbol se preserva
  (`data-file-path`, `data-folder-path`)

#### Escenario: Despacho de formato del visor desde React

- DADO que el spec canónico de research enumera el dispatcher de
  formato (PDF, EPUB, HTML, TXT, MD, DOC, DOCX, XLS, XLSX,
  fallback de formato no soportado, fallback de DOC legacy,
  fallback por fallo de CDN)
- CUANDO el visor de ficheros de React despacha el formato del
  fichero abierto
- ENTONCES cada renderer coincide con el escenario del spec
  canónico
- Y las URLs CDN (`mammoth@1.8.0`, `xlsx@0.18.5`,
  `epubjs@0.3.93`) las carga el lazy loader de React (o
  pineadas inline en `out/index.html`) y las URLs están
  pineadas

#### Escenario: Flujo Save URL sin cambios desde React

- DADO que la extensión de Chrome hace POST de `{url,
  suggested_filename}` a `/api/taxon/{id}/save-url`
- CUANDO la capa de rendering de React refresca después del save
- ENTONCES el indicador de materialización por fila se actualiza
  sin recarga de página
- Y la defensa SSRF en `api/server.py` (rechazo de private nets,
  allowlist, cap de bytes, timeouts) queda sin cambios

## Notas

- El `openspec/specs/research/spec.md` canónico es el contrato
  autoritativo para comportamiento, escenarios y tests. Este
  delta no modifica ninguno de sus requisitos; añade el contrato
  de migración al que se ata la capa de rendering consciente de
  React.
- El literal de search-engines PUEDE moverse de
  `web/search_urls.js` a `src/data/search-engines.js` bajo la
  capa `research/infrastructure/` (según la regla 3 de
  modular-architecture) — si lo hace, la ruta `open()` de AC-21
  se actualiza en la misma release.
- `web/search_urls.js` se enumera como una arista de propiedad
  separada en `design.md::§3.1.2` del predecesor. Se nombran
  cinco consumidores: `web/detail.js:24`, `:325`, `:332`,
  `tests/test_smoke.py:77–100` (AC-21) y
  `tests/test_search_categories.py:141`. El cutover actualiza
  los cinco atómicamente.
- La sección "G3 canonical PASS record" del
  `apply-progress.md` del predecesor registra los 26 consumidores
  §3.1 (21 web mount + 5 search URLs) en verde contra el
  fixture controlado; el cutover de React preserva esa
  cobertura.