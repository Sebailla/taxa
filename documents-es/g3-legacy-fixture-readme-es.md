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

- El lanzador FastAPI controlado (`scripts/g5_legacy_asgi.py`).
- El productor real `scripts/measure_hydration.py`.
- El bucle de captura con Playwright + Lighthouse.
- El esquema + escritor de `parity-reports/<date>/hydration.json`.
- La unión candidato-vs-línea-base + aserción del umbral ±10%.

## Frontera de alcance

- **Dentro (G3)**: base de datos mínima + `web/` mínimo + el helper
  verificador controlado.
- **Dentro (G5 / PR 1 de la cadena)**: marcadores de disponibilidad de
  hidratación en el HTML/JS de la fixture + pruebas de regresión para
  los mismos.
- **Fuera**: `web/` raíz, `Makefile` raíz, `extension/manifest.json`,
  código fuente de producto, corte atómico, selección de Aproximación
  A / B / C, lanzador FastAPI controlado, captura Lighthouse / Playwright.

## Reconstrucción y prueba

```sh
python tools/g3-legacy-fixture/scripts/seed_db.py
.venv/bin/python -m pytest tests/test_g3_legacy_fixture.py -v
```
