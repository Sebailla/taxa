# Especificación del Frontend Runtime

> Dominio: `frontend-runtime`. Dominio nuevo. Autorizado bajo
> `complete-taxa-frontend-migration`. La sede canónica es la
> carpeta del cambio; el archivo copia este fichero literalmente
> en `openspec/specs/frontend-runtime/spec.md` al activarse.

## Propósito

La UI de Taxa, de pantalla única, se renderiza como una
aplicación Next.js 16 (App Router) + React 19 **exportada
estáticamente** a `out/` y servida por el montaje `StaticFiles`
existente de FastAPI en el origen único `127.0.0.1:8765`. No hay
SSR, ni route handlers de Next.js, ni server components, ni un
segundo puerto de servidor de desarrollo. El contrato preservado
contra el build vanilla legacy es **paridad funcional total de
toda la app** a través de cada flujo de usuario, cada superficie
ARIA / teclado, cada clave de estado y cada atributo `data-*`.

El runtime DEBE preservar todas las superficies UI legacy
(pestañas del header, árbol, breadcrumb, panel de detalle,
explorador de archivos, visor de archivos, diálogos, banners,
ajustes, ayuda) sin regresión visible contra el fixture chromium
de Playwright que capturó el predecesor.

## Requisitos

### Requisito: Origen único servido por FastAPI

El sistema DEBE servir el frontend de producción desde el proceso
FastAPI en `127.0.0.1:8765`, sin segundo origen, sin segundo
puerto de servidor de desarrollo y sin cambio en el manifest de
la extensión.

#### Escenario: `make api` arranca FastAPI y sirve la exportación estática

- DADO que `out/index.html` existe y es un fichero no vacío
  producido por `next build`
- CUANDO el usuario ejecuta `make api`
- ENTONCES uvicorn se enlaza a `127.0.0.1:8765`
- Y `GET /` devuelve `200` con el contenido de `out/index.html`
- Y `GET /index.html` devuelve `200` con el mismo contenido
- Y no se abre ningún listener en otro puerto

#### Escenario: Las peticiones de activos estáticos succeeden

- DADO que la exportación estática produjo chunks JS, chunks CSS,
  fuentes y assets de imagen bajo `out/_next/static/**`
- CUANDO el navegador sigue las referencias relativas desde
  `out/index.html`
- ENTONCES cada URL referenciada `_next/static/**` devuelve `200`
- Y el `Content-Type` de la respuesta coincide con la extensión
  del fichero

#### Escenario: Fallback SPA para enlaces profundos

- DADO que el `StaticFiles(directory=str(WEB_DIR), html=True)` de
  FastAPI es el único montaje
- CUANDO el usuario navega directamente a una ruta profunda (p.
  ej. `/taxon/123`)
- ENTONCES el fallback `html=True` de FastAPI devuelve
  `out/index.html`
- Y el router del lado cliente dentro de la SPA decide la ruta
  final
- Y no se introduce un segundo mecanismo de fallback

### Requisito: Exportación estática bajo FastAPI

El sistema DEBE producir el frontend de producción mediante
`next build` al directorio `out/`; FastAPI DEBE servir ese
directorio mediante su montaje `StaticFiles` existente.

#### Escenario: `next build` produce `out/`

- DADO que `package.json` fija `next@^16`, `react@^19`,
  `react-dom@^19` y `engines.node >= 20.9.0`
- Y `next.config.mjs` declara `output: "export"` más
  `images: { unoptimized: true }` y `trailingSlash: false`
- CUANDO el worker de apply ejecuta `next build`
- ENTONCES `next build` sale con `0`
- Y el directorio `out/` existe
- Y `out/index.html` es no vacío
- Y `<candidate>/out/.next/build-manifest.json` se copia (de forma
  atómica) desde `<candidate>/.next/build-manifest.json`
- Y `<candidate>/out/.next/app-build-manifest.json`, si está
  presente, se copia atómicamente; su ausencia se registra como
  `not_emitted` y **nunca** es un fallo por clase ausente

#### Escenario: Clases de activos presentes

- DADO que `next build` terminó con éxito
- CUANDO `scripts/verify_build.py` clasifica `out/`
- ENTONCES `application_route_html` tiene exactamente una entrada
  — `out/index.html`
- Y `js_class` tiene al menos un fichero `*.js` no vacío en
  cualquier punto bajo `out/_next/static/chunks/**`
- Y `css_class` tiene al menos un fichero `*.css` no vacío en
  cualquier punto bajo `out/_next/static/chunks/**` (CSS
  co-localizado con los chunks JS; no se requiere directorio
  `_next/static/css/`)
- Y `staged_manifest` lista el `build-manifest.json` copiado
- Y `404.html` / `500.html`, si están presentes, se reportan bajo
  la clase de activos separada `error_pages`; su ausencia
  **nunca** es un fallo por clase ausente para el contrato de
  rutas de aplicación
- Y `missing_classes` está vacío

#### Escenario: Un fallo de build nunca degrada silenciosamente

- DADO que `next build` sale con código distinto de cero (versión
  de Node por debajo de `20.9.0`, dependencia ausente, entry
  ausente, etc.)
- CUANDO se invoca `make api`
- ENTONCES el target del Makefile sale con código distinto de cero
  **antes** de que uvicorn enlace el puerto
- Y `out/BUILD-INVENTORY.json` **no** se emite
- Y los ficheros vanilla legacy solo son alcanzables mediante un
  `git revert <cutover-sha>` explícito, nunca mediante un modo
  degradado silencioso

### Requisito: Todas las superficies UI legacy se renderizan

El sistema DEBE renderizar cada superficie UI legacy que el build
vanilla envía hoy, con las mismas affordances visuales, la misma
semántica ARIA, los mismos handlers de teclado y el mismo
contrato de atributos `data-*`.

#### Escenario: Pestañas del header

- DADO que el usuario aterriza en `/`
- CUANDO el header se renderiza
- ENTONCES las tres pestañas con nombre — **Browser**,
  **Classification**, **Settings** — se renderizan en el mismo
  orden que el build legacy
- Y cada pestaña lleva los atributos legacy
  `data-action="nav-tab"` y `data-path="<tab>"`
- Y la pestaña activa usa el estilo legacy de pestaña activa
  (`bg-surface-container-lowest shadow-sm`)

#### Escenario: Renderizado del árbol

- DADO que un dominio de primer nivel se carga vía
  `GET /api/domains`
- CUANDO el usuario hace clic en una fila de dominio
- ENTONCES se dispara `GET /api/taxon/{id}/children?source=col`
  (por defecto)
- Y el árbol recursivo se renderiza con el layout legacy de filas
  (kebab por fila, icono de búsqueda por fila, indicador de
  materialización por fila)
- Y el toggle `tree-source` (`col` ↔ `worms`) re-renderiza el
  árbol con la fuente correspondiente

#### Escenario: Renderizado del breadcrumb

- DADO que hay un taxón seleccionado (`state.selected !== null`)
- CUANDO se renderiza el breadcrumb
- ENTONCES el breadcrumb recorre la cadena de padres vía
  `GET /api/taxon/{id}` para cada ancestro
- Y los enlaces del breadcrumb navegan la posición enfocada
- Y el breadcrumb usa la familia monoespaciada legacy para los
  segmentos del nombre científico

#### Escenario: Tira de pestañas del panel de detalle

- DADO que hay un taxón seleccionado
- CUANDO el usuario abre el panel de detalle
- ENTONCES la tira de pestañas se renderiza en el orden legacy —
  **Búsquedas**, **Carpeta**, **Vernáculares**, **Sinónimos**,
  **Distribución**
- Y **Búsquedas** es la pestaña por defecto en una selección
  nueva
- Y los clics explícitos en pestañas persisten vía
  `state.activeTab[taxonId]`
- Y la pestaña activa usa el estilo legacy de pestaña activa
- Y la pestaña Search agrupa los motores bajo los encabezados
  legacy de `CATEGORIES` (`general`, `taxonomic`, `academic`,
  `multimedia`, `documents`) según el literal de search-engines

#### Escenario: Iconos de búsqueda e indicadores de materialización por fila

- DADO que el usuario expande un tier group
- CUANDO cada fila hija se renderiza
- ENTONCES el icono de búsqueda por fila selecciona el taxón y
  abre la pestaña **Búsquedas**
- Y el indicador de materialización por fila está saturado en
  verde cuando `state.materialized` contiene el id de la fila
- Y el indicador se atenúa / desatura en caso contrario

#### Escenario: Vista de Settings

- DADO que el usuario hace clic en la pestaña **Settings**
- CUANDO la vista de ajustes se monta
- ENTONCES el toggle de tema (light / dark) persiste en
  `localStorage.taxa.settings.theme` mediante el nuevo store
  tipado
- Y el toggle estampa `data-theme` en `<html>` para que las
  variables CSS se re-resuelvan
- Y la media query `prefers-color-scheme` del SO se respeta como
  por defecto cuando no existe preferencia almacenada
- Y el control **Reset tree pane width** limpia
  `localStorage.taxa.fex.treeWidth` y pide al file explorer que
  re-renderice con el default CSS (30 %)

#### Escenario: Vista de Help

- DADO que el usuario hace clic en la pestaña `?` del header
- CUANDO la vista de ayuda se monta
- ENTONCES el shell de ayuda renderiza la tabla legacy de
  atajos de teclado
- Y al hacer clic en una pestaña de nav (`Classification`,
  `Settings`, `Browser`) se saca el shell de ayuda de `<main>`

#### Escenario: Banners

- DADO que se dispara cualquier condición de banner del build
  legacy (offline, 5xx del servidor, fallo de materialización,
  fallo de save-url)
- CUANDO el banner se renderiza
- ENTONCES el texto del banner y el control de descarte coinciden
  línea por línea con el build legacy
- Y los atributos `data-*` del banner (`data-banner`,
  `data-banner-kind`) se preservan

### Requisito: Paridad del file explorer

El sistema DEBE renderizar el file explorer dentro de la pestaña
**Browser** con el mismo layout de dos paneles, la misma semántica
de clic simple vs doble clic, la misma tira de pestañas Raw /
Table / Tree y la misma carga diferida de librerías CDN que el
build legacy.

#### Escenario: La pestaña Browser monta el file explorer

- DADO que hay un taxón seleccionado
- CUANDO el usuario hace clic en la pestaña **Browser**
- ENTONCES se dispara `GET /api/taxon/{selected}/files`
- Y el panel izquierdo (`w-72`) renderiza el árbol recursivo de
  carpetas
- Y el panel derecho renderiza el placeholder del visor vacío
- Y el meta strip muestra el estado vacío hasta que se abre un
  fichero

#### Escenario: Clic simple vs doble clic sobre un fichero

- DADO que hay una fila de fichero en el árbol izquierdo
- CUANDO el usuario hace un clic simple
- ENTONCES la fila se resalta con `bg-primary-fixed` +
  `text-on-primary-fixed` + `rounded-r-md`
- Y no se dispara ninguna petición de red
- Y el estado del visor derecho no cambia
- CUANDO el usuario hace doble clic sobre la misma fila
- ENTONCES el visor obtiene el fichero vía
  `GET /api/taxon/{id}/files/serve?path=<rel>`
- Y el visor renderiza el fichero en el formato correspondiente
- Y la fila del fichero permanece resaltada

#### Escenario: Clic simple sobre una carpeta

- DADO que hay una fila de carpeta en el árbol izquierdo
- CUANDO el usuario hace un clic simple
- ENTONCES la fila de la carpeta se resalta con `bg-primary/5` +
  `border-l-2 border-primary` + el icono `folder_open`
- Y la carpeta alterna la visibilidad de sus hijos
- Y una guía vertical de 1 px outline-variant/20 conecta
  visualmente los hijos de la carpeta

#### Escenario: Tira de pestañas Raw / Table / Tree

- DADO que el usuario ha hecho doble clic en `data.csv`
- CUANDO hace clic en la pestaña **Table**
- ENTONCES el visor derecho re-renderiza el fichero vía Papa
  Parse con un `<thead>` sticky y un body scrollable
- Y la pestaña **Table** es la pestaña activa en la tira
- Y la pestaña **Tree** **no** se autoactiva
- Y el meta strip muestra `FORMAT=CSV | SIZE=<bytes>`

#### Escenario: Pestaña Tree para JSON

- DADO que el usuario ha hecho doble clic en `spec.json`
- CUANDO hace clic en la pestaña **Tree**
- ENTONCES el objeto raíz aparece como un nodo caret clickable
- Y al hacer clic en el caret se expanden los hijos con 16 px de
  indent por nivel
- Y los valores hoja se colorean por tipo usando los tokens del
  Tailwind config (sin hex hardcodeado)

#### Escenario: Renderizado multi-formato de ficheros

- DADO un fichero `.pdf`, `.html`, `.txt`, `.md`, `.docx`, `.xls`,
  `.xlsx` o `.epub` en el árbol
- CUANDO el usuario hace doble clic sobre él
- ENTONCES se dispara el renderer legacy correspondiente — PDF →
  iframe, HTML → iframe sandboxed (`sandbox=""`, sin
  `allow-same-origin`), TXT / MD → `<pre>` con fence (MD vía
  `marked.min.js`), DOCX → mammoth (`mammoth.js@1.8.0`),
  XLS/XLSX → SheetJS (`xlsx@0.18.5`) con un selector de hoja
  para libros multi-hoja, EPUB → epubjs (`epubjs@0.3.93`) con
  controles de página prev/next
- Y el meta strip muestra el `FORMAT=<EXT> | SIZE=<bytes> |
  ENCODING=UTF-8` correspondiente
- Y las librerías CDN se cargan de forma diferida vía
  `loadScriptOnce(name, src)` para que el usuario nunca pague el
  coste de ~600 KB de descarga para formatos no usados

#### Escenario: Fallback DOC legacy

- DADO un fichero `.doc`
- CUANDO el usuario hace doble clic sobre él
- ENTONCES el visor muestra `"Legacy .doc cannot be rendered
  inline. <Download file>"` con un enlace
  `<a href="<serve-url>" download>`
- Y el meta strip muestra `FORMAT=DOC`

#### Escenario: Fallback para formato no soportado

- DADO un fichero con extensión fuera de los nueve formatos
  soportados
- CUANDO el usuario hace doble clic sobre él
- ENTONCES el visor muestra `"Format not supported in viewer."`
  con un enlace de descarga
- Y el `GET /files/serve` subyacente devuelve
  `Content-Type: application/octet-stream` con
  `Content-Disposition: inline; filename="<basename>"`

#### Escenario: Fallback por fallo de CDN

- DADO que alguna de las librerías CDN pineadas falla al cargar
- CUANDO el usuario hace doble clic sobre un fichero que requiere
  esa librería
- ENTONCES el visor renderiza el banner
  `"Viewer offline — raw download unavailable"` y mantiene el
  árbol interactivo
- Y no se lanza ninguna excepción no capturada

#### Escenario: Búsqueda en el árbol

- DADO que el árbol está montado
- CUANDO el usuario teclea en el input de búsqueda del árbol
  izquierdo
- ENTONCES el input tiene debounce de 200 ms
- Y el modo filter oculta las filas no coincidentes
- Y cualquier carpeta cuyo subárbol contiene una coincidencia se
  expande automáticamente
- Y el modo highlight preserva el estado expand/collapse y pinta
  las filas coincidentes con `.fex-row.search-match`
- Y `state.explorer.search.{query, mode, hideEmpty}` se actualiza

#### Escenario: Cambiar de taxón limpia el estado del explorer

- DADO que el explorer está montado mostrando ficheros del taxón A
- CUANDO el usuario selecciona el taxón B en el árbol taxonómico
- ENTONCES `state.explorer` se limpia: `rootTaxonId = null`,
  `tree = null`, `openFilePath = null`, `openFileFormat = null`,
  `viewerTab = "Raw"`
- Y al reabrir la pestaña **Browser** se dispara una petición
  nueva `GET /api/taxon/{B}/files`

### Requisito: Paridad funcional total de la app

El sistema DEBE preservar cada flujo de usuario que el build
legacy soporta sin regresión visible.

#### Escenario: Flujo de navegación

- DADO que el usuario abre la aplicación en `/`
- CUANDO el usuario expande un dominio → un sub-árbol → una fila
  de especie
- ENTONCES el breadcrumb se actualiza, el panel de detalle carga
  y se renderizan los metadatos del taxón seleccionado
- Y la URL se actualiza a `<root>/<taxon>` coincidiendo con la
  forma de URL del build legacy

#### Escenario: Flujo de búsqueda

- DADO que el usuario abre el modal de búsqueda (icono de búsqueda
  del header)
- CUANDO teclea una consulta
- ENTONCES `GET /api/search?q=<q>` se dispara con debounce
- Y los resultados de las tres fuentes (`col`, `worms`,
  `freshwater`) aparecen en la agrupación legacy de resultados

#### Escenario: Flujo de materialización

- DADO que un taxón no tiene carpeta materializada en disco
- CUANDO el usuario confirma el modal de materialización
- ENTONCES se dispara `POST /api/taxon/{id}/materialize`
- Y el callback del modal incorpora los ids devueltos en
  `state.materialized`
- Y el indicador de materialización por fila se vuelve verde
  saturado para los nuevos ids y sus descendientes visibles

#### Escenario: Flujo Save URL

- DADO que la extensión de Chrome hace POST de `{url,
  suggested_filename}` a `/api/taxon/{id}/save-url`
- CUANDO se procesa la petición
- ENTONCES el cuerpo de la respuesta se escribe en la carpeta de
  research materializada
- Y la defensa SSRF (`_PRIVATE_NETS`, allowlist de
  `_SAVE_URL_ALLOWED_TYPES`, cap de 50 MB, timeouts de 30 s de
  conexión / 60 s de lectura) queda sin cambios
- Y la extensión recibe una respuesta 2xx que la capa de
  rendering consciente de React puede re-renderizar sin cambios
  de código

### Requisito: Paridad de accesibilidad

El sistema DEBE preservar cada rol ARIA, etiqueta y handler de
teclado del build legacy, sin nuevas violaciones de axe.

#### Escenario: Handlers de teclado

- DADO que el usuario usa los atajos de teclado legacy (p. ej. `/`
  para abrir la búsqueda, `Esc` para cerrar modales, flechas en
  el árbol, `Enter` para abrir el fichero enfocado)
- CUANDO dispara el atajo
- ENTONCES se dispara el comportamiento legacy correspondiente
- Y la gestión del foco coincide con el build legacy (focus trap
  dentro de modales, restore del foco al cerrar, skip-link para
  el árbol)

#### Escenario: Semántica ARIA

- DADO cualquier elemento interactivo del build legacy
- CUANDO el lector de pantalla o axe lo inspecciona
- ENTONCES el elemento lleva los mismos atributos `role`,
  `aria-label`, `aria-controls`, `aria-expanded`,
  `aria-selected`, `aria-current` que el build legacy

#### Escenario: Escaneo de axe

- DADO que el nuevo frontend está completamente montado
- CUANDO el escaneo de axe se ejecuta contra el fixture chromium
- ENTONCES el conteo de violaciones `serious` / `critical` **no
  es mayor** que la línea base legacy
- Y cada violación reportada previamente o se resuelve a
  `resolved` o lleva una exención documentada

### Requisito: Paridad de rendimiento

El sistema NO DEBE regresar el presupuesto de initial-paint o de
latencia de interacción en el fixture chromium que capturó el
predecesor.

#### Escenario: Initial paint

- DADO que el fixture chromium es el mismo usado por la harness
  G4 de Playwright + Lighthouse
- CUANDO el worker de apply mide el initial paint contra la
  round-trip de `/api/health`
- ENTONCES el delta frente a la línea base legacy es `≤ 0 %`
  según los criterios de éxito del predecesor

#### Escenario: Latencia de interacción

- DADO que el usuario interactúa con el árbol, el panel de detalle
  y el visor de ficheros
- CUANDO el worker de apply mide la latencia de interacción
- ENTONCES el delta frente a la línea base legacy es `≤ 0 %`

#### Escenario: Regresión del perfil de build

- DADO que `next build` ha corrido
- CUANDO el worker de apply compara `out/BUILD-INVENTORY.json`
  (`chunks`, `total_bytes`, `per_route_bytes`) contra la línea
  base de evidencia legacy
- ENTONCES ninguna métrica regresa más de `0 %` sin una exención
  documentada firmada en `design.md`

### Requisito: Hidratación del estado del navegador sin mismatch

El sistema DEBE hidratar el estado local del navegador sin
levantar advertencias de hydration mismatch.

#### Escenario: Primer paint bajo la guardia de hidratación

- DADO que el árbol React se monta por primera vez
- CUANDO se dispara el render inicial
- ENTONCES la bandera `mounted` es `false`
- Y las lecturas de `localStorage` se difieren a `useEffect`
- Y la estructura del árbol toma como default el estado vacío en
  el primer pintado
- Y no se dispara ninguna advertencia de hidratación de React en
  la consola del navegador

#### Escenario: Hidratación tras el primer paint

- DADO que el primer paint completó con el estado vacío
- CUANDO corre el `useEffect`
- ENTONCES el store tipado rehidrata cada una de las cuatro
  claves (`theme`, `tree-source`, `last-taxon-id`,
  `kebab-open-id`) mediante un sitio de lectura por clave
- Y un render posterior aplica el estado rehidratado
- Y no se dispara ninguna advertencia de hidratación

## Notas

- La exportación estática pierde las rutas dinámicas y la
  optimización de imágenes (aceptable para v1; migrar al
  servidor de dev completo de Next.js es un cambio aparte).
- `next build` DEBE correr antes de que uvicorn enlace el puerto;
  la verificación de runtime `scripts/check-runtime.mjs` (Node
  `>= 20.9.0`) DEBE salir con código distinto de cero antes de
  que uvicorn arranque si Node es demasiado antiguo.
- Las URLs CDN legacy pineadas (`mammoth@1.8.0`, `xlsx@0.18.5`,
  `epubjs@0.3.93`) las carga el lazy loader del file viewer y
  viajan como parte de la exportación estática (ya sea vía tags
  `<script>` inline en `out/index.html` o vía el árbol de
  componentes React); la ruta que se elija, las URLs DEBEN
  permanecer pineadas.