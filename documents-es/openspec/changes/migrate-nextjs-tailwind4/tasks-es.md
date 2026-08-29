# Tareas: migrate-nextjs-tailwind4

> TDD estricto: ROJO → VERDE (→ Refactor). Las reglas del monolito
> modular de `specs/modular-architecture/spec.md` aplican a cada
> unidad de UI/archivo.

## Aviso de reconstrucción

El árbol `feat/migrate-nextjs-tailwind4-pr1` contiene artefactos de
planificación más material sin rastrear contra `origin/develop`
(`09ef767`). **Nada fusionado.** Los `[x]` previos en Fase 1 + Fase
2a eran un artefacto de planificación, no trabajo entregado.
**Todas las tareas quedan pendientes de reconstrucción.**
Secuencial hacia `develop` (sin ramas apiladas, sin bases hijas)
según `AGENTS.md` §4. El árbol de respaldo es fuente de solo
lectura. El pronóstico por sub-PR, pruebas, harnesses y límites de
reversión vive en `apply-progress.md` §Estado de reconstrucción
(columna Archivos fuente por sub-PR) y §Límite de reversión por
sub-PR.

## Pronóstico de carga de revisión

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Low

> Orden: **1a.1 → 1a.2 → 1b.1 → 1b.2 → 1b.3a → 1b.3b → 2a → 2b →
> 2c → 2d → 2e → 3 → 4 → 5**. Cada PR → `develop` directamente.
> PR 1 eran 1554 LoC sin rastrear; ahora dividido en seis sub-PRs
> ≤ 339 LoC. Reversión = revertir el sub-PR problemático.

## Fase 1a.1: Emisor del build-profile (PR 1a.1 → develop)

- [ ] 1a.1.1 R — `tests/test_build_profile.py` (contrato de script): emisor exit 0 + esquema JSON válido para `web/dist/`.
- [ ] 1a.1.2 V — `scripts/emit_build_profile.mjs`: recorre build dir, emite `build-profile.json`; exit no-cero ante build ausente/vacío.
- [ ] 1a.1.3 Refactor — el mensaje de error nombra la ruta faltante.

## Fase 1a.2: Test de esquema del build-profile (PR 1a.2 → develop)

- [ ] 1a.2.1 R — `tests/test_build_profile.py` (resto): asserts de forma para `chunks`, `total_bytes`, `per_route_bytes`.
- [ ] 1a.2.2 V — segunda expansión del archivo de test (sin código de producción).
- [ ] 1a.2.3 Refactor — parametrizar las aserciones de esquema.

## Fase 1b.1: Pin de Chromium (PR 1b.1 → develop)

- [ ] 1b.1.1 R — `tests/test_evidence_baseline.py` (bloque chromium): el binario instalado coincide con el SHA256 fijado.
- [ ] 1b.1.2 V — `scripts/verify_chromium.py`: imprime el pin + diff vs el binario instalado; exit no-cero ante divergencia.
- [ ] 1b.1.3 Refactor — el mensaje de error nombra el hash esperado vs el real.

## Fase 1b.2: Línea base de evidencia (PR 1b.2 → develop)

- [ ] 1b.2.1 R — `tests/test_evidence_baseline.py` (resto): roster de módulos legacy, tamaño total del código fuente, esquema JSON de evidence-baseline.
- [ ] 1b.2.2 V — segunda expansión del archivo de test.
- [ ] 1b.2.3 Refactor — parametrizar las aserciones del roster legacy.

## Fase 1b.3a: Script de medición de hidratación (PR 1b.3a → develop)

- [ ] 1b.3a.1 R — `tests/test_hydration_timing.py` (subset de esquema): `measure_hydration.py` exit 3 ante violación de esquema.
- [ ] 1b.3a.2 V — `scripts/measure_hydration.py`: lee JSON de hidratación, emite resumen legible; exit no-cero ante claves ausentes.
- [ ] 1b.3a.3 Refactor — separar lectura+resumen en dos funciones puras.

## Fase 1b.3b: Test de cronometraje de hidratación (PR 1b.3b → develop)

- [ ] 1b.3b.1 R — `tests/test_hydration_timing.py` (resto): asserts de forma para `delta_server_to_tree_first_paint_ms` y `console_warnings`.
- [ ] 1b.3b.2 V — segunda expansión del archivo de test.
- [ ] 1b.3b.3 Refactor — eliminar los números baseline legacy (ya en `design.md` §"Línea base de evidencia de migración").

## Fase 2a: Andamio de capas (PR 2a → develop)

- [ ] 2a.1 R — `tests/test_module_layers.py`: 4 carpetas de capa + `index.ts` por capacidad.
- [ ] 2a.2 V — andamio 5 capacidades × 4 carpetas de capa + barrels; aliases de `tsconfig.json`.
- [ ] 2a.3 Refactor — `test_no_forbidden_layer_name_per_module` + tope de carpetas totales.

## Fase 2b: Configuración ESLint (PR 2b → develop)

- [ ] 2b.1 R — `tests/test_no_restricted_imports.py` (config-presence): `.eslintrc.cjs` existe; 20 patrones presentes.
- [ ] 2b.2 V — `.eslintrc.cjs` patrones barrel-only para 5 capacidades × 4 capas.
- [ ] 2b.3 R — test runtime de barrel-import (`barrel_import.js` exit 0).

## Fase 2c: Triangulación ESLint (PR 2c → develop)

- [ ] 2c.1 R — `tests/test_no_restricted_imports.py` (bloque triangulación runtime): cada par (capacidad, capa) rechazado en runtime.
- [ ] 2c.2 V — 20 fixtures `scripts/eslint-fixtures/deep_import_<capability>_<layer>.js`.

## Fase 2d: Dominio de taxonomía (PR 2d → develop)

- [ ] 2d.1 R — `tests/test_taxonomy_domain.py`: compila sin Next/React/FastAPI; forma de campos + superficie de invariantes.
- [ ] 2d.2 V — `src/modules/taxonomy/domain/taxon.ts` tipos planos + invariantes.

## Fase 2e: Guardia de pureza de dominio (PR 2e → develop)

- [ ] 2e.1 R — `tests/test_domain_purity.py`: cero coincidencias de framework en el dominio.
- [ ] 2e.2 Refactor — strip de comentarios JSDoc antes del regex; parametrizaciones de tokens prohibidos.

## Fase 3: Bootstrap de frontend (PR 3 → develop)

- [ ] 3.1 R — `tests/test_tailwind_4_parity.py`: cada `var(--token)` de `web/index.html`.
- [ ] 3.2 V — `src/modules/design-system/infrastructure/globals.css`: `@import "tailwindcss"` + `@theme` + `@layer base`.
- [ ] 3.3 R — `tests/test_make_api_build.py`: `Makefile::api` ejecuta build de Next y luego uvicorn.
- [ ] 3.4 V — `Makefile::api` ejecuta `npm install && npm run build:web && uvicorn`; `scripts/check-runtime.mjs` exige Node ≥20.9.0.
- [ ] 3.5 R — `tests/test_static_mount.py`: `GET /` devuelve HTML de Next; `GET /_next/static/<h>.js` 200.
- [ ] 3.6 V — `api/server.py:54` `WEB_DIR = Path("out")`; signature del mount preservada.
- [ ] 3.7 R/V — reubicar `web/search_urls.js` → `src/modules/research/infrastructure/search-engines.js`; `open()` del test AC-21 actualizado.
- [ ] 3.8 Refactor — grep `src/` por hex; asegurar ninguno fuera del módulo design-system.

## Fase 4: Estado del navegador (PR 4 → develop)

- [ ] 4.1 R — `tests/test_browser_state_keys.py`: greps `src/`; espera 4 getItem + 4 setItem.
- [ ] 4.2 V — `src/modules/browser-state/{store,keys,defaults}.ts`: 4+4 sitios dentro de `useEffect`.
- [ ] 4.3 R — `tests/test_hydration_console.py` (Playwright) falla hasta que lecturas estén gated por mounted.
- [ ] 4.4 V — `useSyncExternalStore` detrás de flag `mounted`; cero warnings de hidratación.

## Fase 5: Puertos de capacidades (PR 5 → develop)

- [ ] 5.1 R — `tests/test_taxonomy_infra.py`: mockea `fetchTaxon`/`fetchChildren`.
- [ ] 5.2 V — `src/modules/taxonomy/infrastructure/api.ts`; aplicación expone solo view-models.
- [ ] 5.3 V — `useTaxonTree()` + portar `web/{tree,detail,breadcrumb}.js` → `src/modules/taxonomy/presentation/{Tree,DetailPanel,Breadcrumb}.tsx`.
- [ ] 5.4 R — `tests/test_research_infra.py`: mockea `/api/taxon/{id}/files{,/serve}`.
- [ ] 5.5 V — `src/modules/research/infrastructure/api.ts`; tipos de dominio primero.
- [ ] 5.6 V — portar `web/{file_explorer,file_viewer,format,keymap}.js` → React; CDN fijado.
- [ ] 5.7 R — selectores Playwright + e2e actualizados.
- [ ] 5.8 V — contrato `data-*` preservado; perf ≤ 0%.
- [ ] 5.9 Refactor — borrar `web/*.{html,js,css}` + `tailwind.config.js`.

## Fuera de alcance (según AGENTS.md)

Sin `git push`, `git commit`, `gh pr create`, `git stash`; sin
árboles nuevos; sin ediciones a código fuente/test. Solo cambian
`tasks.md`, `apply-progress.md`, sus espejos en español, y Engram.