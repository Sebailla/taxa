# Fixture Legado G3 (solo diagnóstico)

Fixture legado G3 mínimo, autocontenido y desechable, usado para
verificación controlada del estado HTTP. **No es parte del producto.**
Inalcanzable desde producción por diseño.

## Contenido

| Ruta | Propósito |
|---|---|
| `taxa.db` | SQLite pre-sembrado: 10 filas `taxon` + 8 `vernacular`. El esquema refleja producción v1+v2. |
| `web/index.html` | HTML mínimo que referencia `dist/tailwind.css` + `app.js`. Contiene los marcadores `data-testid` de disponibilidad de hidratación G5 (`g5-shell-ready`, `g5-tree-ready`, `g5-search-ready`, `g5-keymap-ready`). |
| `web/dist/tailwind.css` | Recurso CSS requerido (consumidor `mount-runtime-link-tag-css-003` del manifiesto). |
| `web/app.js` | Entrada mínima que importa 10 stubs de módulos hermanos. Tras importar, activa `document.body.dataset.state = "g5-keymap-ready"` (señal de disponibilidad G5). |
| `web/tree.js` | Stub de módulo que activa `#tree-view[data-state="ready"]` cuando el DOM está disponible (señal de disponibilidad G5). |
| `web/{state,api,breadcrumb,…}.js` | Stubs de módulo (`export {};`). |
| `scripts/seed_db.py` | Reconstruye `taxa.db`. Idempotente. |
| `scripts/check_http_status.py` | Verificador controlado: parsea la salida de `curl -w '%{http_code}'` y la valida contra `expect`. Cierre-fallido ante cualquier desajuste. |

## Porción 1 — Disponibilidad pre-corte legada G3 (PASS vía PR #116)

La porción G3 verifica cada `verification.command` contra la fixture
controlada (`web/` servido por `python -m http.server` en un puerto
libre aislado mediante `--fixture-web-root`) con enrutamiento
cierre-fallido de forma HTTP a través de
`scripts/check_http_status.py`. Véanse PR #109 + #111 + #115 + #116
para el registro canónico PASS de los 26 / 26 consumidores.

## Porción 2 — Marcadores de disponibilidad de hidratación G5 (PR 1 de la cadena)

La porción G5 añade marcadores deterministas de disponibilidad de
hidratación al HTML/JS de la fixture para que el PR 2 de la cadena
pueda registrar una línea base con Playwright sin depender de los bytes
de `web/` de producción. Los marcadores son el contrato público; el
lanzador FastAPI controlado que monta la fixture se restaura a partir
de un parche externo preservado en el PR 2 de la cadena.

### Marcadores

| Marcador | Dónde | Lo activa |
|---|---|---|
| `data-testid="g5-shell-ready"` | `<body>` (estático) | `web/index.html` |
| `data-testid="g5-tree-ready"` | `<div id="tree-view">` (estático) | `web/index.html` |
| `data-testid="g5-search-ready"` | `<input id="search">` (estático) | `web/index.html` |
| `data-testid="g5-keymap-ready"` | `<span hidden>` cerca del inicio de `<body>` (estático; elemento propio — `<body>` ya lleva `g5-shell-ready` y el parser HTML5 descarta atributos duplicados posteriores, por lo que un segundo `data-testid` en `<body>` se perdería silenciosamente) | `web/index.html` |
| `data-state="ready"` en `#tree-view` | dinámico | `web/tree.js` (DOMContentLoaded o ahora) |
| `data-state="g5-keymap-ready"` en `<body>` | dinámico | `web/app.js` (ahora o DOMContentLoaded) |

Los marcadores son deterministas (sin sellos de tiempo, sin
identificadores aleatorios) de modo que los diffs línea-base-vs-candidato
del PR 2 de la cadena queden limpios.

### Fuera del alcance (el PR 2 de la cadena es responsable)

- El productor real `scripts/measure_hydration.py`.
- El bucle de captura con Playwright + Lighthouse.
- El esquema + escritor de `parity-reports/<date>/hydration.json`.
- La unión candidato-vs-línea-base + aserción del umbral ±10%.

## Porción 3 — Lanzador FastAPI controlado (PR 2 de la cadena)

El lanzador G5 (`scripts/g5_legacy_asgi.py`) es una aplicación ASGI
controlada que monta la fixture delante de `api.server.app` para que
el bucle de captura Playwright + Lighthouse del PR 2 de la cadena
pueda ejercitar un entorno determinista sin depender de los bytes de
`web/` de producción. Ejecútalo con
`.venv/bin/uvicorn tools.g3-legacy-fixture.scripts.g5_legacy_asgi:app`.
Tres pasos, todos al tiempo de importación del módulo:

| Paso | Qué | Por qué |
|---|---|---|
| 1. Verificación cierre-fallido | `_require_nonempty_file(FIXTURE_DB, ...)` + `_require_nonempty_dir(FIXTURE_WEB, ...)` lanzan `RuntimeError("fail-closed")` antes de cualquier trabajo de rutas | Una aplicación a medio cablear nunca debe llegar a uvicorn ni al bucle de captura |
| 2. Recableado de la BD | `api.server.DB_PATH = FIXTURE_DB` (solo) — `api.server.WEB_DIR` se deja intencionalmente intacto | Cada endpoint respaldado por BD (`/api/health`) lee filas de la fixture; el guardia de regresión verifica que `WEB_DIR` nunca se mutó |
| 3. Montaje de la fixture | Inserta un `Mount("/", StaticFiles(...))` **justo antes** del montaje raíz de producción | Starlette empareja en orden de registro; colocar el montaje de la fixture antes de la `/` de producción hace que los bytes de la fixture ganen para rutas estáticas manteniendo cada ruta `/api/*` alcanzable |

### Modos de fallo (verificados por `tests/test_g3_legacy_fixture.py`)

| Entrada | Resultado |
|---|---|
| `taxa.db` ausente o vacío | `RuntimeError("fail-closed: fixture DB ...")` en tiempo de importación |
| `web/` ausente o vacío | `RuntimeError("fail-closed: fixture web dir ...")` en tiempo de importación |
| `web/<ruta>` no presente en la fixture | 404 (responde el montaje `/` de producción) |
| `/api/health` | Lee `taxa.db` (10 filas `taxon` + 8 `vernacular`) |

### Por qué insertar antes del montaje de producción (no en el índice 0)

Insertar en el índice 0 pondría el `Mount("/")` de la fixture delante
de cada `APIRoute` en `api.server.app`. Starlette despacha por orden
de registro, así que el catch-all `/` ganaría antes de que
`/api/health` alcanzase su `APIRoute` — el lanzador devolvería
silenciosamente 404 para cada llamada a la API. Insertar **justo
antes** del montaje raíz de producción (la última ruta en
`api.server.app`) preserva cada ruta `/api/*` de FastAPI a la vez
que permite que la fixture gane para cualquier ruta estática que
sirva.

## Frontera de la cadena

| PR | Responsable de |
|---|---|
| PR 1 de la cadena | Marcadores de disponibilidad de hidratación en `web/index.html` + `web/app.js` + `web/tree.js` + sus pruebas de regresión |
| 📍 PR 2 de la cadena (este) | Lanzador `scripts/g5_legacy_asgi.py` + pruebas de contrato del lanzador + esta actualización del README |
| PR 3 de la cadena (posterior) | Productor `scripts/measure_hydration.py`, bucle de captura Playwright + Lighthouse, escritor `parity-reports/<date>/hydration.json`, aserción candidato-vs-línea-base ±10% |

## Frontera de alcance

- **Dentro (G3)**: base de datos mínima + `web/` mínimo + el helper
  verificador controlado.
- **Dentro (G5 / PR 1 de la cadena)**: marcadores de disponibilidad de
  hidratación en el HTML/JS de la fixture + pruebas de regresión para
  los mismos.
- **Dentro (G5 / PR 2 de la cadena)**: lanzador FastAPI controlado +
  pruebas de contrato del lanzador (`test_g5_launcher_contract`,
  `test_g5_launcher_fails_*`).
- **Fuera**: `web/` raíz, `Makefile` raíz, `extension/manifest.json`,
  código fuente de producto, corte atómico, selección de Aproximación
  A / B / C, captura Lighthouse / Playwright.

## Reconstrucción y prueba

```sh
python tools/g3-legacy-fixture/scripts/seed_db.py
.venv/bin/python -m pytest tests/test_g3_legacy_fixture.py -v
```
