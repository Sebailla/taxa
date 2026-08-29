# Progreso de apply: migrate-nextjs-tailwind4

> Artefacto de persistencia en modo híbrido. Refleja el progreso de
> apply estructurado en Engram (`topic_key` =
> `sdd/migrate-nextjs-tailwind4/apply-progress`).
>
> **Aviso de reconstrucción**: este cambio **no tiene trabajo
> entregado** en `origin/develop` aún. El árbol de trabajo actual
> (`taxa-worktrees/migrate-nextjs-tailwind4-pr1`) contiene artefactos
> de planificación más archivos de implementación sin rastrear. La
> versión previa de este archivo reportaba "7 / 35 tareas completas"
> para PR 1 + PR 2a; ese conteo era un artefacto de planificación, no
> trabajo entregado. Las 35 tareas quedan pendientes de reconstrucción
> según el `tasks.md` actualizado §Aviso de reconstrucción.

---

## Estado de reconstrucción (reemplaza los lotes de apply previos)

| Sub-PR | Alcance | Presupuesto LoC | Archivos fuente | Estado |
|--------|---------|-----------------|-----------------|--------|
| PR 1a.1 | Emisor del build-profile | 296 | `scripts/emit_build_profile.mjs` + bloque de contrato de script de `tests/test_build_profile.py` | reconstrucción pendiente |
| PR 1a.2 | Test de esquema del build-profile | 241 | resto de `tests/test_build_profile.py` | reconstrucción pendiente |
| PR 1b.1 | Pin de chromium | 247 | `scripts/verify_chromium.py` + bloque chromium de `tests/test_evidence_baseline.py` | reconstrucción pendiente |
| PR 1b.2 | Línea base de evidencia | 250 | resto de `tests/test_evidence_baseline.py` | reconstrucción pendiente |
| PR 1b.3a | Script de medición de hidratación | 339 | `scripts/measure_hydration.py` + subset de esquema de `tests/test_hydration_timing.py` | reconstrucción pendiente |
| PR 1b.3b | Test de cronometraje de hidratación | 181 | resto de `tests/test_hydration_timing.py` | reconstrucción pendiente |
| PR 2a | Andamio de capas | 409* | `tsconfig.json` + 5 barrels + 20 `.gitkeep` + `tests/test_module_layers.py` | `size:exception` **aceptada** por el mantenedor (2026-08-29); unidad de trabajo en `taxa-worktrees/migrate-nextjs-tailwind4-2a` habilitada para commit + push a `develop` tal como está staged |
| PR 2b | Configuración ESLint (literal + alias) | 388 | `.eslintrc.cjs` + `scripts/eslint-fixtures/{barrel_import,deep_import,deep_import_research}.js` + `tests/test_no_restricted_imports.py` | **staged** en árbol `taxa-worktrees/migrate-nextjs-tailwind4-2b`; habilitado para commit + push a `develop` tal como está staged |
| PR 2c | Triangulación ESLint | 239 | 20 fixtures + bloque de triangulación runtime de `tests/test_no_restricted_imports.py` | **staged** en árbol `taxa-worktrees/migrate-nextjs-tailwind4-2c`; habilitado para commit + push a `develop` tal como está staged |
| PR 2d | Dominio de taxonomía | 350 | `src/modules/taxonomy/domain/taxon.ts` + `tests/test_taxonomy_domain.py` | reconstrucción pendiente |
| PR 2e | Guardia de pureza de dominio | 176 | `tests/test_domain_purity.py` | reconstrucción pendiente |
| PR 3 | Bootstrap de frontend (Tailwind 4, Makefile, static mount, search_urls) | TBD | aún no escrito | reconstrucción pendiente |
| PR 4 | browser-state | TBD | aún no escrito | reconstrucción pendiente |
| PR 5 | Puertos de capacidades + borrado de `web/*` legacy | TBD | aún no escrito | reconstrucción pendiente |

\* **Corrección de conteo de líneas de PR 2a y `size:exception`
aceptada**: la columna Presupuesto LoC arriba muestra la cifra medida
real (**409** líneas de código+test), no la estimación preliminar previa
(**377**). Desglose: `tsconfig.json` 45 + 5 barrels
(`src/modules/<capability>/index.ts`) 115 + 20 placeholders `.gitkeep`
de capa 0 + `tests/test_module_layers.py` 249 = **409** (`wc -l` sobre
los archivos staged). Esto **excede el presupuesto de revisión de 400
líneas por PR** en **9 líneas (+2,3 %)**. El **2026-08-29** se le
presentaron al mantenedor las tres opciones del contrato de delegación
del worker — aceptar-con-flag (`size:exception`, commitear como está
staged), re-rebanar (dividir el test o un barrel en un PR 2a'), o
recortar (reducir el test enfocado) — y **eligió explícitamente
aceptar-con-flag**. El exceso de +9 líneas (+2,3 %) es por lo tanto una
**`size:exception` autorizada**, no una decisión abierta: PR 2a se envía
tal como está staged, con 409 líneas de código+test frente al
presupuesto de 400 líneas, y el PR lleva la etiqueta `size:exception`.
No se requiere más re-rebanado ni recorte. Este registro documenta
únicamente la decisión; no modifica código ni tests y no realiza commit
ni push.

\*\* **Tamaño medido de PR 2b y expansión de forma alias**: la fila de
PR 2b arriba muestra la cifra medida real (**388** líneas de código+test),
no el pronóstico original (**227**). Desglose: `.eslintrc.cjs` 66 +
`scripts/eslint-fixtures/barrel_import.js` 4 +
`scripts/eslint-fixtures/deep_import.js` 4 +
`scripts/eslint-fixtures/deep_import_research.js` 5 +
`tests/test_no_restricted_imports.py` 309 = **388** (`wc -l` sobre los
archivos staged). Esto **cabe en el presupuesto de revisión de 400
líneas por PR** con **-12 líneas (-3,0 %)** de holgura tras la pasada
de recorte. El crecimiento desde el pronóstico original de 227 líneas
proviene enteramente de la expansión explícita de aplicación de la
forma alias autorizada por el mantenedor: la regla literal
`src/modules/<cap>/<layer>/*` sola (el pronóstico original) envía
~32 LoC de patrones dentro de `.eslintrc.cjs`, pero la forma alias
`@taxa/<cap>/<layer>/*` añade otros ~32 LoC de patrones más ~50 LoC
de tests de triangulación de forma alias en el archivo de tests,
más ~30 LoC para el helper `_load_eslint_patterns` que carga vía
Node y permite al test afirmar sobre la config *resuelta* (en vez de
escanear el texto fuente, lo cual habría roto el refactor del array
de patrones programático). PR 2b se envía bajo el presupuesto de 400
líneas sin `size:exception`; la cobertura expandida del alias es
parte del contrato de diseño, no un exceso.

**Total entregado en `develop`**: 0 / 14 sub-PRs.
**Total pendiente de reconstrucción**: 11 sub-PRs.
**Total staged en árbol de trabajo, autorizado para commit**: 3 sub-PRs
(PR 2a, `size:exception` aceptada; PR 2b, bajo presupuesto; PR 2c, bajo presupuesto).

### Orden de reconstrucción (determinista, secuencial hacia `develop`)

```
1a.1 → 1a.2 → 1b.1 → 1b.2 → 1b.3a → 1b.3b → 2a → 2b → 2c → 2d → 2e → 3 → 4 → 5
```

La base de cada sub-PR = `origin/develop` tras el merge del previo.
Sin ramas apiladas. Sin bases hijas. Cada PR apunta a `develop`
directamente según `AGENTS.md` §4.

### Política de árboles de trabajo

- **Árbol de respaldo** en `taxa-worktrees/migrate-nextjs-tailwind4-pr1`:
  fuente de referencia de solo lectura para los archivos de cada
  sub-PR. **No** editar, rebasear, ni fusionar desde él tras
  registrarse este plan.
- **Árboles de reconstrucción** lanzados por el worker de apply
  para cada sub-PR: creados bajo el home del usuario como hermanos
  del respaldo según guía CodeGraph. Cada árbol recibe su propio
  índice `.codegraph/`; aplica la regla de ubicación consciente de
  CodeGraph.

### Manifiesto de reconstrucción (por sub-PR)

Para cada sub-PR, el worker de apply DEBE:

1. Crear un árbol de trabajo nuevo desde `origin/develop` con nombre
   `taxa-worktrees/migrate-nextjs-tailwind4-pr<N>`.
2. Copiar solo los archivos listados para ese sub-PR en
   `tasks.md` §Aviso de reconstrucción (lista de archivos por
   sub-PR) desde el árbol de
   respaldo al árbol nuevo usando `cp -p`. Sin ediciones al copiar.
3. Ejecutar el comando de prueba enfocado (ver las filas por
   sub-PR en `tasks.md` §§Fase 1a.1–5). DEBE pasar antes de
   cualquier commit.
4. Ejecutar el harness de ejecución (ver misma tabla). DEBE exit 0 /
   devolver la salida esperada.
5. Conventional Commit con asunto en inglés (sin trailer de IA).
   Cuerpo del PR en español según `AGENTS.md` §Hard Rules:
   `## Resumen`, `## Cambios`, `## Validación`, `## Lo que NO cambió`.
6. Abrir el PR contra `develop` usando la skill `branch-pr`.
7. Con CI verde: marcar las tareas de ese sub-PR con `[x]` en
   `tasks.md` y `tasks-es.md`; anteponer un registro de lote por
   sub-PR aquí y en `apply-progress.md`.
8. Continuar al siguiente sub-PR repitiendo desde el paso 1 con un
   árbol nuevo sobre el `develop` ya fusionado.

### Límite de reversión por sub-PR

Cada reversión de sub-PR elimina **solo** sus propios archivos (ver
`tasks.md` §§Fase 1a.1–5 (lista de archivos por sub-PR) y la
correspondiente nota de `Límite de reversión` en este
`apply-progress.md`. Ningún sub-PR toca `web/*`, `package.json`,
`api/server.py`, `Makefile`, `extension/manifest.json`, ni los
artefactos de captura de PR 1.

---

## Contexto histórico — PR 2 (rechazado, reparticionado)

La narrativa de abajo documenta la unidad PR 2 original (~1369 LoC)
rechazada por exceder el presupuesto de revisión de 400 líneas por
PR. El trabajo se conserva aquí como referencia; la propiedad de los
artefactos se repartió en el `tasks.md` replanificado
§§Fase 2a–2e (PR 2 → PR 2a–2e).

PR 2 cerró las tareas 2.1–2.7. La tarea 1.5 quedó diferida a la
fase de diseño. La ruta elegida por el usuario fue la repartición
encadenada (2a–2e) sobre `size:exception`.

PR 1 (la línea base solo de evidencia) se envió originalmente como
una sola unidad de ~1554 LoC. Tras el mismo rechazo de 400 líneas
sobre PR 2, PR 1 también se reparticiona en esta pasada en seis
sub-PRs (1a.1, 1a.2, 1b.1, 1b.2, 1b.3a, 1b.3b).

Las dos reparticiones juntas producen **14 sub-PRs** apuntando a
`develop` secuencialmente, cada uno ≤ 400 líneas autorales.

## Carga / Límite de PR (post-reconstrucción)

- Modo: **PRs encadenados apilados-a-main** (sub-PRs secuenciales de Fase 1 + Fase 2).
- Total de sub-PRs tras la reconstrucción: **14** (1a.1, 1a.2, 1b.1, 1b.2, 1b.3a, 1b.3b, 2a, 2b, 2c, 2d, 2e, 3, 4, 5 — notar que 3, 4, 5 son PR único según plan original).
- Cada sub-PR ≤ 339 LoC autorales, **excepto**:
  - **PR 2a con 409 líneas de código+test**, que se envía bajo la
    `size:exception` aceptada por el mantenedor (+9 líneas, +2,3 %
    sobre el presupuesto de revisión de 400 líneas).
  - **PR 2b con 388 líneas de código+test**, que se envía **bajo el
    presupuesto de revisión de 400 líneas** (-12 líneas, -3,0 % de
    holgura). La superficie expandida de PR 2b (frente al pronóstico
    original de 227 líneas) es la expansión explícita de aplicación de
    forma alias autorizada por el mantenedor
    (`@taxa/<cap>/<layer>/*` además de `src/modules/<cap>/<layer>/*`)
    más los tests de triangulación de forma alias correspondientes.
- Base de cada sub-PR = `origin/develop` tras el merge del sub-PR previo.
  Sin ramas apiladas. Sin bases hijas.

## Riesgos

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| La secuencia de reconstrucción se interrumpe; un merge parcial de sub-PRs de la Fase 1 deja el proyecto en estado inconsistente. | Media | El test enfocado de cada sub-PR pasa de forma independiente de los sub-PRs posteriores. Un PR atascado bloquea solo a su sucesor, no a toda la cadena. |
| El árbol de respaldo se edita por accidente durante la reconstrucción; los archivos fuente se desvían del plan. | Alta | El árbol de respaldo se marca como de solo lectura a nivel de sistema de archivos; todo el trabajo de reconstrucción ocurre en árboles nuevos ramificados de `develop`. |
| Las listas de archivos de PR 3, 4, 5 aún no están detalladas; una pasada futura de planificación debe actualizar `tasks.md` §§Fase 3–5 con listas de archivos por sub-PR explícitas. | Media | Las Fases 3, 4, 5 se mantienen bajo `aún no escrito` en esta pasada; se le indica al worker de apply pausar antes de PR 3 y actualizar las listas por sub-PR. |
| Seis nuevos PRs (1a.x, 1b.x) más cinco existentes (2a–2e) inflan el conteo total de PRs que los mantenedores revisan. | Baja | Cada PR ≤ 400 líneas; el foco de revisión se mantiene acotado; la estrategia de cadena es `stacked-to-main` por elección previa del usuario. |

## Estado

**0 / 35 tareas entregadas en `develop`.** La unidad de trabajo
PR 2a está staged en el árbol `taxa-worktrees/migrate-nextjs-tailwind4-2a`
(andamio + test + tsconfig + evidencia OpenSpec + espejos en español);
el test enfocado `tests/test_module_layers.py` pasa 40 / 40 (RED →
GREEN → TRIANGULATE capturado). Con **409** líneas de código+test frente
al presupuesto de revisión de **400** líneas por PR, PR 2a lleva una
**`size:exception` aceptada**: el 2026-08-29 el mantenedor autorizó
explícitamente el exceso de +9 líneas (+2,3 %), por lo que la decisión
de entrega queda cerrada y PR 2a queda habilitado para commit + push a
`develop` tal como está staged bajo la etiqueta `size:exception`.

La unidad de trabajo PR 2b está staged en el árbol
`taxa-worktrees/migrate-nextjs-tailwind4-2b` (config ESLint + 3
fixtures + test enfocado + registros de progreso OpenSpec + espejo en
español); el test enfocado `tests/test_no_restricted_imports.py` pasa
32 / 32 (RED → GREEN → TRIANGULATE → REFACTOR capturado; se confirmó
la invocación runtime de ESLint sobre las 40 combinaciones
`(capability × layer × form)`). Con **388** líneas de código+test
frente al presupuesto de revisión de **400** líneas por PR, PR 2b se
envía **bajo presupuesto** (-12 líneas, -3,0 % de holgura). La
superficie expandida frente al pronóstico original de 227 líneas es la
expansión explícita de aplicación de forma alias autorizada por el
mantenedor (`@taxa/<cap>/<layer>/*` además de
`src/modules/<cap>/<layer>/*`) más los tests de triangulación de forma
alias correspondientes; no se requiere `size:exception`.

La unidad de trabajo PR 2c está staged en el árbol
`taxa-worktrees/migrate-nextjs-tailwind4-2c` (20 fixtures literales
+ bloque de triangulación runtime de
`tests/test_no_restricted_imports.py` + registros de progreso
OpenSpec + espejo en español); el test enfocado
`tests/test_no_restricted_imports.py` pasa 102 / 102 (32 PR 2b + 70
PR 2c; RED → GREEN → TRIANGULATE → REFACTOR capturado). La
invocación runtime de ESLint demuestra que las **40 formas de deep
import** se rechazan: 20 fixtures literales
(`src/modules/<cap>/<layer>/deep`) + 20 entradas dinámicas de alias
(`@taxa/<cap>/<layer>/deep` en `tmp_path`), parametrizadas sobre la
matriz completa `CAPABILITIES × LAYERS`. Los barrels públicos se
mantienen permitidos bajo ambas formas (10 casos barrel-allow). Con
**239** líneas de código+test frente al presupuesto de revisión de
**400** líneas por PR, PR 2c se envía **bajo presupuesto** (-161
líneas, -40,25 % de holgura). Desglose: 20 fixtures
(`scripts/eslint-fixtures/deep_import_<cap>_<layer>.js`) a 5 LoC
cada uno = **100** + delta de `tests/test_no_restricted_imports.py`
de **139** (`wc -l` sobre el archivo staged = 448 frente a la base
PR 2b de 309) = **239** (`wc -l` sobre los archivos staged). No se
requiere `size:exception`.

Los sub-PRs restantes (1a.x, 1b.x, 2d–2e, 3, 4, 5) quedan pendientes de
reconstrucción según `tasks.md` §Aviso de reconstrucción.

---

## Registro de cambios

- **2026-08-28** — Artefacto compañero inicial creado.
- **2026-08-28** — Los lotes de PR 1 + PR 2a se reportaron como
  completos; ese estado era un artefacto de planificación y queda
  reemplazado por esta pasada de reconstrucción.
- **2026-08-28** — Pasada de reconstrucción: PR 1 dividido en seis
  sub-PRs (1a.1, 1a.2, 1b.1, 1b.2, 1b.3a, 1b.3b); PR 2 dividido en
  cinco sub-PRs (2a–2e); PR 3, 4, 5 se mantienen como PRs únicos
  según plan original. Los 14 sub-PRs apuntan a `develop`
  directamente (sin ramas apiladas, sin bases hijas). Árbol de
  respaldo bloqueado como referencia de solo lectura. Espejo en
  español actualizado en paralelo.
- **2026-08-29** — Unidad de trabajo PR 2a staged en el árbol
  dedicado `taxa-worktrees/migrate-nextjs-tailwind4-2a`. Archivos
  añadidos: `tsconfig.json` (modo estricto + 5 alias de ruta por
  capability), `src/modules/{taxonomy,research,design-system,browser-state,app-shell}/index.ts`
  (5 barrels vacíos), `src/modules/{capability}/{presentation,application,domain,infrastructure}/.gitkeep`
  (20 placeholders de capa), `tests/test_module_layers.py` (40
  aserciones enfocadas). Evidencia OpenSpec migrada y versionada:
  `openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks}.md` +
  `specs/modular-architecture/spec.md`; espejos en español bajo
  `documents-es/openspec/changes/migrate-nextjs-tailwind4/{proposal,tasks}-es.md`
  + `specs/modular-architecture/spec-es.md`. Los sub-PRs siguientes
  continúan bajo el mismo plan de reconstrucción.
- **2026-08-29** — `size:exception` de PR 2a **aceptada**. El tamaño
  medido es de **409** líneas de código+test (`tsconfig.json` 45 + 5
  barrels 115 + 20 placeholders `.gitkeep` de capa 0 +
  `tests/test_module_layers.py` 249) frente al presupuesto de revisión
  de **400** líneas por PR — un exceso de **+9 líneas (+2,3 %)**. El
  mantenedor autorizó explícitamente esa excepción en lugar de
  re-rebanar o recortar, por lo que PR 2a se envía tal como está staged
  con la etiqueta `size:exception` y la decisión de entrega deja de
  estar pendiente. Este registro no modifica código ni tests y no
  realiza commit ni push. Espejo en inglés actualizado en paralelo.
- **2026-08-29** — Unidad de trabajo PR 2b staged en el árbol dedicado
  `taxa-worktrees/migrate-nextjs-tailwind4-2b`. Archivos añadidos:
  `.eslintrc.cjs` (66 LoC, forma CommonJS legacy; patrones de
  `no-restricted-imports` derivados de una matriz
  `CAPABILITIES × LAYERS` y emiten AMBAS formas de ruta — literal
  `src/modules/<cap>/<layer>/*` Y alias `@taxa/<cap>/<layer>/*` —
  según la decisión explícita del mantenedor para evitar bypass por
  forma alias);
  `scripts/eslint-fixtures/{barrel_import,deep_import,deep_import_research}.js`
  (3 fixtures, 13 LoC en total);
  `tests/test_no_restricted_imports.py` (309 LoC, 32 aserciones
  enfocadas incluyendo 2 tests de triangulación de forma alias usando
  `tmp_path` de pytest para no commitear fixtures adicionales). El
  test enfocado pasa 32 / 32 contra `.eslintrc.cjs` (RED → GREEN →
  TRIANGULATE → REFACTOR capturado). La invocación runtime de ESLint
  verificó que las 40 combinaciones `(capability × layer × form)` se
  rechazan y los 10 paths de barrel (5 caps × 2 formas) se permiten.
  Tamaño medido **388** líneas de código+test frente al presupuesto
  de revisión de **400** líneas por PR — bajo presupuesto por
  **-12 líneas (-3,0 %)** tras la pasada de recorte. La superficie
      expandida frente al pronóstico original de 227 líneas es la
      expansión explícita de aplicación de forma alias autorizada por el
      mantenedor; no se requiere `size:exception`. Este registro no
      modifica código ni tests y no realiza commit ni push. Espejo en
      inglés actualizado en paralelo.
    - **2026-08-29** — Unidad de trabajo PR 2c staged en el árbol dedicado
      `taxa-worktrees/migrate-nextjs-tailwind4-2c`. Archivos añadidos:
      `scripts/eslint-fixtures/deep_import_<cap>_<layer>.js` (20
      fixtures literales commiteados, 5 LoC cada uno = 100 LoC en total,
      cubriendo cada par `(capability × layer)` sobre la matriz de 5
      capacidades × 4 capas); el archivo existente
      `tests/test_no_restricted_imports.py` se extendió con un bloque
      parametrizado de triangulación runtime (delta de +139 LoC llevando
      el archivo de 309 a 448 LoC, +70 aserciones enfocadas: 20 de
      existencia de fixture, 20 de runtime forma literal, 20 de runtime
      forma alias vía `tmp_path`, 10 de barrel permitido cubriendo
      ambas formas de barrel literal y alias). El test enfocado pasa
      102 / 102 (32 PR 2b + 70 PR 2c) contra `.eslintrc.cjs` (RED →
      GREEN → TRIANGULATE → REFACTOR capturado). La invocación runtime
      de ESLint demuestra que las **40 formas de deep import** se
      rechazan: 20 fixtures literales
      (`src/modules/<cap>/<layer>/deep`) más 20 entradas dinámicas de
      alias (`@taxa/<cap>/<layer>/deep` escritas en `tmp_path` por
      test). Los barrels públicos se mantienen permitidos bajo ambas
      formas. Tamaño medido **239** líneas de código+test (20 fixtures
      100 + delta del archivo de test 139) frente al presupuesto de
      revisión de **400** líneas por PR — bajo presupuesto por **-161
      líneas (-40,25 %)** de holgura. No se requiere `size:exception`.
      Este registro no modifica código ni tests y no realiza commit ni
      push. Espejo en inglés actualizado en paralelo.