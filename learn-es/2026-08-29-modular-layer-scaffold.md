# Andamiaje modular por capas (PR #78)

## What

PR #78 introdujo el andamiaje del monolito modular por capas bajo `src/modules/`: cinco módulos de capability, cada uno con cuatro capas (`presentation`, `application`, `domain`, `infrastructure`) y un barrel público `index.ts`, junto con los alias estrictos en `tsconfig.json` que bloquean los imports cruzados hacia las carpetas internas. La validación queda concentrada en un único test enfocado, `tests/test_module_layers.py`, que fija el layout mediante 40 aserciones parametrizadas y mantiene el PR dentro del work unit Phase 2a de `tasks.md`.

## How

El work unit aplica TDD estricto según `tasks.md` §Phase 2a. Primero se añadieron los tests del layout en `tests/test_module_layers.py` con tuplas `CAPABILITIES` y `LAYERS` parametrizadas; después se materializó el scaffold — las carpetas de capa con `.gitkeep` y los cinco barrels — y se incorporaron los path-aliases `@taxa/<capability>` y `@taxa/<capability>/*` en `tsconfig.json`. Cada barrel es deliberadamente un `export {};` para que `tsc --noEmit` lo acepte como módulo TypeScript válido; los exports reales aterrizan por capability en los PR 3–5. Las reglas arquitectónicas se formalizan en `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md` (reglas 1–7) y el contrato del PR 2a vive en `design.md` §"PR 2a Scope Boundary" y §"Layer Architecture Decisions". El `.gitignore` se amplía con la excepción explícita `!src/modules/research/` para evitar que el patrón `Research/` (case-insensitive en macOS) descarte el módulo `research/`.

## Where

- `src/modules/{taxonomy,research,design-system,browser-state,app-shell}/index.ts` — barrel público por módulo; en este PR todos contienen `export {};` como placeholder válido.
- `src/modules/<capability>/{presentation,application,domain,infrastructure}/.gitkeep` — placeholder por capa, 20 archivos en total.
- `tsconfig.json` — modo `strict` activado y `paths` con los alias `@taxa/<capability>` y `@taxa/<capability>/*` para los cinco módulos.
- `tests/test_module_layers.py` — 9 funciones de test que producen 40 aserciones parametrizadas: raíz de módulos, capability por nombre, capa por capability, barrel `.ts` por módulo, suffix `.ts` del barrel, ausencia de carpetas técnicas de primer nivel, alineación con `CAPABILITIES`, conteo total fijado a cinco e hijos permitidos dentro de cada módulo.
- `.gitignore` — añade la negación `!src/modules/research/` junto a las negaciones ya existentes `!openspec/changes/*/specs/research/`, `!openspec/changes/archive/*/specs/research/` y `!openspec/specs/research/` para resolver la colisión case-insensitive en macOS con el ignore `Research/`.
- `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md` y su espejo `documents-es/openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec-es.md` — delta normativo (reglas 1–7) en inglés y espejo en español.
- `openspec/changes/migrate-nextjs-tailwind4/{proposal,design,tasks,apply-progress}.md` y sus espejos `documents-es/.../{proposal,design,tasks,apply-progress}-es.md` — propuesta, diseño (incluye §"PR 2a Scope Boundary" y §"Layer Architecture Decisions"), tareas con marcadores TDD estrictos y registro de reconstrucción por sub-PR.

## Why

La migración del frontend vanilla a Next.js 16 + React 19 + Tailwind 4 exige una partición del árbol de código que separe capabilities de negocio y mantenga el dominio libre de framework. El monolito modular por capas fija esa partición antes de mover código real, de modo que ningún PR futuro pueda relajar las reglas 1–7 sin pasar por una revisión de spec. Los alias estrictos y el barrel por módulo dan al ESLint (PR 2b, `no-restricted-imports`) y a la triangulación de runtime (PR 2c) una base estable sobre la cual rechazar imports profundos hacia `presentation`, `application`, `domain` o `infrastructure`. La excepción de ignore para `src/modules/research/` resuelve una colisión real en macOS entre la carpeta de capability y la carpeta `Research/` que el endpoint `POST /api/taxon/{id}/materialize` materializa bajo demanda.

## How it works

En el árbol del repo, cada capability vive en `src/modules/<nombre>/` y expone únicamente su `index.ts`. Cualquier consumidor entre módulos importa desde `import … from '@taxa/<capability>'` (alias declarado en `tsconfig.json`) o desde la ruta directa al barrel, nunca desde las carpetas de capa. `tests/test_module_layers.py` recorre los 5 capabilities × 4 layers y verifica que cada carpeta exista, que cada barrel sea un archivo `.ts`, que no aparezcan carpetas técnicas de primer nivel (`utils`, `shared`, `controllers`, `services`, `repositories`, `components`, `hooks`, `lib`, `common`, `helpers`, `misc`) y que el conteo total de módulos sea exactamente cinco. La regla 4 del spec mantiene `domain/` compilable y testeable de forma aislada — sin React, Next, FastAPI ni I/O — mientras la regla 5 garantiza que el barrel y los alias son los únicos puntos de entrada cross-module. En macOS, la negación explícita `!src/modules/research/` en `.gitignore` impide que el patrón `Research/` (case-insensitive) descarte el módulo `research/`, y las negaciones paralelas `!openspec/.../specs/research/` conservan los deltas de spec en OpenSpec.

## Workflows

- **TDD estricto**: la fase 2a de `tasks.md` exige RED → GREEN → Refactor. El test del layout entra en el primer paso (RED = fixtures que resuelven a paths inexistentes) y la materialización del scaffold más los alias cierra el GREEN; la tercera tarea del work unit refina los asserts negativos (`test_no_forbidden_layer_name_per_module` y el cap de conteo).
- **Cadena de PR hacia `develop`**: PR 2a es el séptimo sub-PR de la cadena `1a.1 → 1a.2 → 1b.1 → 1b.2 → 1b.3a → 1b.3b → 2a → 2b → 2c → 2d → 2e → 3 → 4 → 5`. PR 2b añade `.eslintrc.cjs` con `no-restricted-imports` para reforzar barrel-only en build, y PR 2c triangula cada par (capability, layer) en runtime.
- **Excepción de tamaño aceptada**: el conteo medido en `apply-progress.md` es `tsconfig.json` 45 + 5 barrels 115 + 20 `.gitkeep` 0 + `tests/test_module_layers.py` 249 = 409 líneas de código y test, lo que supera en 9 líneas (+2,3 %) el presupuesto de revisión por PR de 400. El maintainer aceptó el `size:exception` el 2026-08-29; PR 2a se publica con esa etiqueta y sin re-slicing.
- **CI Smoke y merge**: PR #78 fusionado a `develop` en el commit `3e596db` (sobre `eaa8176`) con CI Smoke en verde antes de la limpieza del worktree. Esta entrada `/learn-es` se crea antes de borrar el worktree, según §2 de `AGENTS.md`.
- **Espejo bilingüe de OpenSpec**: cada artefacto del change (`proposal`, `design`, `tasks`, `apply-progress`, `specs/modular-architecture/spec`) se mantiene en `openspec/...` en inglés y en `documents-es/openspec/...` como espejo en español, con sufijo `-es.md` en el nombre de archivo.
