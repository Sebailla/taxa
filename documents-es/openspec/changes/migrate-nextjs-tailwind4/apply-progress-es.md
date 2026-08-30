# Progreso de apply: migrate-nextjs-tailwind4

> Artefacto de persistencia en modo híbrido. Refleja el progreso de
> apply estructurado en Engram (`topic_key` =
> `sdd/migrate-nextjs-tailwind4/apply-progress`).
>
> **Aviso de reconciliación (2026-08-29)**: este cambio tiene
> **6 / 14 sub-PRs entregados a `origin/develop`** según el historial
> de commits (1a.1, 1b.1, 2a, 2b, 2c, 2d — ver provenencia por fila
> abajo); **5 / 14 sub-PRs son inciertos** porque la provenencia
> del slice nombrado no se puede determinar a partir de los límites
> de los commits (1a.2, 1b.2, 1b.3a, 1b.3b, 2e); **3 / 14 sub-PRs
> quedan pendientes de reconstrucción** (PR 3, PR 4, PR 5). El
> framing previo de "7 / 35 tareas completas" era un artefacto de
> planificación y queda reemplazado.

---

## Estado de reconstrucción (reemplaza los lotes de apply previos)

| Sub-PR | Alcance | Presupuesto LoC | Archivos fuente | Estado |
|--------|---------|-----------------|-----------------|--------|
| PR 1a.1 | Emisor del build-profile | 296 | `scripts/emit_build_profile.mjs` + bloque de contrato de script de `tests/test_build_profile.py` | entregado — origin/develop #75 (`646f00d`) envía `scripts/emit_build_profile.mjs` + `tests/test_build_profile.py` completo (321 LoC) |
| PR 1a.2 | Test de esquema del build-profile | 241 | resto de `tests/test_build_profile.py` | incierto — #75 añadió `tests/test_build_profile.py` completo; el límite del slice nombrado con 1a.1 (bloque de contrato de script vs resto de esquema) no es determinable a partir del historial de commits |
| PR 1b.1 | Pin de chromium | 247 | `scripts/verify_chromium.py` + bloque chromium de `tests/test_evidence_baseline.py` | entregado — origin/develop #76 (`97776de`) envía `tests/test_evidence_baseline.py` completo (829 LoC); `scripts/verify_chromium.py` precede al slice (#3c16dad, feat(security)) |
| PR 1b.2 | Línea base de evidencia | 250 | resto de `tests/test_evidence_baseline.py` | incierto — #76 añadió `tests/test_evidence_baseline.py` completo; el límite del slice nombrado con 1b.1 (bloque chromium vs resto de evidencia) no es determinable |
| PR 1b.3a | Script de medición de hidratación | 339 | `scripts/measure_hydration.py` + subset de esquema de `tests/test_hydration_timing.py` | incierto — #77 (`9d2e8a4`) envía `scripts/measure_hydration.py` (189 LoC) + `tests/test_hydration_timing.py` completo (331 LoC); el límite del slice nombrado con 1b.3b (script + subset de esquema vs resto) no es determinable |
| PR 1b.3b | Test de cronometraje de hidratación | 181 | resto de `tests/test_hydration_timing.py` | incierto — #77 añadió `tests/test_hydration_timing.py` completo; el límite del slice nombrado con 1b.3a no es determinable |
| PR 2a | Andamio de capas | 409* | `tsconfig.json` + 5 barrels + 20 `.gitkeep` + `tests/test_module_layers.py` | entregado — origin/develop #78 (`3e596db`); `size:exception` aceptada (409 líneas código+test, +9 / +2,3 % sobre el presupuesto de 400 líneas) |
| PR 2b | Configuración ESLint (literal + alias) | 388 | `.eslintrc.cjs` + `scripts/eslint-fixtures/{barrel_import,deep_import,deep_import_research}.js` + `tests/test_no_restricted_imports.py` | entregado — origin/develop #80 (`00560db`); bajo presupuesto (-12 / -3,0 %) |
| PR 2c | Triangulación ESLint | 239 | 20 fixtures + bloque de triangulación runtime de `tests/test_no_restricted_imports.py` | entregado — origin/develop #82 (`0bd294a`); bajo presupuesto (-161 / -40,25 %) |
| PR 2d | Dominio de taxonomía | 350 | `src/modules/taxonomy/domain/taxon.ts` + `tests/test_taxonomy_domain.py` | entregado — origin/develop #84 (`8315c0b`); 347 líneas código+test |
| PR 2e | Guardia de pureza de dominio | 176 | `tests/test_domain_purity.py` | incierto — #86 (`53a33be`) envía `tests/test_domain_purity.py` (320 LoC) pero excede el presupuesto de 176 LoC del plan; provenencia del slice nombrado incierta (desajuste entre presupuesto del plan y tamaño entregado) |
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

**Total entregado en `develop`**: 6 / 14 sub-PRs (1a.1, 1b.1, 2a, 2b,
2c, 2d — según el historial de commits de origin/develop).
**Total incierto (provenencia del slice nombrado)**: 5 / 14 sub-PRs
(1a.2, 1b.2, 1b.3a, 1b.3b, 2e — contenido de archivo presente en
`origin/develop`, límite del slice nombrado no determinable a partir
del historial de commits).
**Total pendiente de reconstrucción**: 3 / 14 sub-PRs (PR 3, PR 4, PR 5).

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

**6 / 14 sub-PRs entregados a `develop`** según el historial de
commits (1a.1, 1b.1, 2a, 2b, 2c, 2d); **5 sub-PRs son inciertos**
(provenencia del slice nombrado no determinable: 1a.2, 1b.2,
1b.3a, 1b.3b, 2e); **3 sub-PRs quedan pendientes de reconstrucción**
(PR 3, PR 4, PR 5). Los registros de staged previos de PR 2a / 2b /
2c abajo se conservan como contexto histórico — esas unidades ya
fueron entregadas a `develop` mediante los PRs #78 (#3e596db),
#80 (#00560db) y #82 (#0bd294a). La unidad de trabajo PR 2a fue
staged en el árbol `taxa-worktrees/migrate-nextjs-tailwind4-2a`
(andamio + test + tsconfig + evidencia OpenSpec + espejos en español);
el test enfocado `tests/test_module_layers.py` pasa 40 / 40 (RED →
GREEN → TRIANGULATE capturado). Con **409** líneas de código+test frente
al presupuesto de revisión de **400** líneas por PR, PR 2a lleva una
**`size:exception` aceptada**: el 2026-08-29 el mantenedor autorizó
explícitamente el exceso de +9 líneas (+2,3 %), por lo que la decisión
de entrega quedó cerrada (aceptada el 2026-08-29) y PR 2a ha sido
entregado a `develop` bajo la etiqueta `size:exception`.

La unidad de trabajo PR 2b fue staged en el árbol
`taxa-worktrees/migrate-nextjs-tailwind4-2b` (entregada mediante
PR #80 / #00560db) (config ESLint + 3
fixtures + test enfocado + registros de progreso OpenSpec + espejo en
español); el test enfocado `tests/test_no_restricted_imports.py` pasa
32 / 32 (RED → GREEN → TRIANGULATE → REFACTOR capturado; se confirmó
la invocación runtime de ESLint sobre las 40 combinaciones
`(capability × layer × form)`). Con **388** líneas de código+test
frente al presupuesto de revisión de **400** líneas por PR, PR 2b se
envió **bajo presupuesto** (-12 líneas, -3,0 % de holgura). La
superficie expandida frente al pronóstico original de 227 líneas es la
expansión explícita de aplicación de forma alias autorizada por el
mantenedor (`@taxa/<cap>/<layer>/*` además de
`src/modules/<cap>/<layer>/*`) más los tests de triangulación de forma
alias correspondientes; no se requiere `size:exception`.

La unidad de trabajo PR 2c fue staged en el árbol
`taxa-worktrees/migrate-nextjs-tailwind4-2c` (entregada mediante
PR #82 / #0bd294a) (20 fixtures literales
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
**400** líneas por PR, PR 2c se envió **bajo presupuesto** (-161
líneas, -40,25 % de holgura). Desglose: 20 fixtures
(`scripts/eslint-fixtures/deep_import_<cap>_<layer>.js`) a 5 LoC
cada uno = **100** + delta de `tests/test_no_restricted_imports.py`
de **139** (`wc -l` sobre el archivo staged = 448 frente a la base
PR 2b de 309) = **239** (`wc -l` sobre los archivos staged). No se
requiere `size:exception`.

Los sub-PRs restantes (PR 3, PR 4, PR 5) quedan pendientes de
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
    - **2026-08-29** — Pasada de reconciliación del ledger (esta
      entrada). Según la tarea del padre, el ledger de
      `apply-progress.md` se reconcilia contra el historial de
      commits de `origin/develop`. **6 / 14 sub-PRs marcados como
      entregados** (1a.1 → #75 / `646f00d`; 1b.1 → #76 / `97776de`;
      2a → #78 / `3e596db`; 2b → #80 / `00560db`; 2c → #82 /
      `0bd294a`; 2d → #84 / `8315c0b`). **5 / 14 sub-PRs marcados
      como inciertos** (1a.2, 1b.2, 1b.3a, 1b.3b, 2e) porque el
      límite del slice nombrado dentro del archivo de test
      fusionado no es determinable a partir del límite del commit
      (los commits relevantes añadieron el archivo de test
      completo, no dividido). **Estado de PR 3, PR 4, PR 5
      preservado exactamente como origin** (pendientes de
      reconstrucción, aún no escritos). Totales actualizados; el
      framing de "staged en árbol de trabajo" de PR 2a / 2b / 2c
      convertido a tiempo pasado porque esas unidades ya han sido
      entregadas. La provenencia del slice nombrado de PR 2e es
      además incierta porque el tamaño entregado (320 LoC) excede
      el presupuesto de 176 LoC del plan. Las notas de
      `size:exception` de PR 2a (409 / +9 / +2,3 %) y expansión de
      forma alias de PR 2b se conservan verbatim. Sin cambios de
      código o test en esta pasada; no se realiza commit / push.
      Espejo en inglés actualizado en paralelo.
    - **2026-08-30** — Pasada de reconciliación de docs-only G2 / G5
      (esta entrada). Según la tarea del padre, los artefactos de
      planificación canónicos (`proposal.md`, `design.md`,
      `apply-progress.md`) y sus espejos fieles en español
      (`proposal-es.md`, `design-es.md`, `apply-progress-es.md`) se
      reconcilian contra el estado actual. **No se crean fuente,
      tests, scripts, tasks, ficheros de producto, ficheros de
      evidencia, ni el workspace `tools/g2-candidate/`.**
      Autorizaciones de la tarea del padre: (1) el workspace
      candidato aislado sin activación en `tools/g2-candidate/` queda
      **autorizado pero no creado** en esta pasada — no debe cablear
      FastAPI, `web/`, CI, `package.json` raíz, `Makefile`, ni
      `extension/manifest.json`, y no selecciona el Enfoque A / B / C
      ni exportación estática; (2) la disposición de la auditoría
      del legado queda **irreproducible y no aceptada para G5**.
      Deltas concretos: (a) `design.md::§3.3.2.1` registra el
      contrato G2 (raíz candidata `tools/g2-candidate/`, comando de
      build `<candidate-root>/node_modules/.bin/next build`, raíz de
      salida `<candidate-root>/out/`, clases de activo, esquema y
      ubicación de `BUILD-INVENTORY.json`, requisito de Node `>= 20.9.0`,
      semántica de fallo sin fallback silencioso al legado, y
      precondiciones del verificador strict-TDD G2); (b)
      `design.md::§3.3.5` registra la disposición G5 como
      **irreproducible**, enumera los ficheros de evidencia revisados
      solo por nombre (`web/dist/evidence-baseline.json`,
      `tests/test_evidence_baseline.py`,
      `tools/static-export-probe/scripts/capture.mjs`,
      `tools/static-export-probe/evidence/*.json`), lista el
      inventario de pruebas faltantes (comando de captura, log,
      entorno, número de iteraciones, Playwright crudo, Lighthouse
      crudo, fila de delta, coincidencia con CLI/esquema), y fija el
      camino de cierre. Pie de estado actualizado: G2 queda
`bloqueado — contrato definido; verificador no implementado`;
          G5 queda `bloqueada — línea base no reproducible; comparación
          no intentada`; la activación de PR3e sigue bloqueada hasta que
          G1–G6 cierren. Espejos en español actualizados en paralelo.
          No se realiza commit ni push en esta pasada.
        - **2026-08-30** — Pasada de correcciones del contrato G2 (tres
          decisiones explícitas del mantenedor aplicadas a
          `design.md::§3.3.2.1`; esta entrada). Según la tarea del padre,
          el contrato G2 canónico se corrige para registrar tres
          decisiones explícitas del mantenedor mientras **sigue
          `bloqueado — contrato definido; verificador no implementado`**
          (ningún verificador G2 se escribe en esta pasada, ninguna
          puerta aprueba, no se tocan fuente / tests / scripts /
          workspace candidato / package-lock / ficheros de evidencia).
          (1) **Excepción de tamaño (fichero generado, condicional)** —
          una `size:exception` se aplica **solo** a
          `tools/g2-candidate/package-lock.json`, y **solo después**
          de que `npm ci` salga 0 contra el
          `tools/g2-candidate/package.json` local del candidato. La
          excepción es condicional y nula si `npm ci` falla (no se
          commitea ningún `package-lock.json`). **Ningún otro fichero
          generado bajo `tools/g2-candidate/` queda exceptuado** del
          presupuesto de revisión por PR — todo otro artefacto generado
          (salida de build, manifiestos, logs, artefactos de captura,
          otros lockfiles) cuenta bajo el tope de líneas autoradas.
          Registrado en `design.md::§3.3.2.1` como nueva fila de tabla
          `Excepción de tamaño (fichero generado, condicional)`.
          (2) **Staging post-build de manifiestos (atómico)** — el
          verificador G2 DEBE copiar atómicamente los manifiestos
          requeridos de Next desde `<candidate-root>/.next/` a
          `<candidate-root>/out/.next/` (concretamente
          `<candidate-root>/.next/build-manifest.json` →
          `<candidate-root>/out/.next/build-manifest.json` y
          `<candidate-root>/.next/app-build-manifest.json` →
          `<candidate-root>/out/.next/app-build-manifest.json`) antes de
          la validación del inventario. La copia es todo-o-nada:
          cualquier fallo individual de copia aborta el paso de
          staging, retira cualquier staging parcial, **no** deja
          ningún `BUILD-INVENTORY.json` válido en disco, y propaga
          una salida no-cero. Manifiestos fuente ausentes también son
          un fallo de staging. Registrado en `design.md::§3.3.2.1` como
          nueva fila `Staging post-build de manifiestos (atómico)`,
          y las filas `Semántica de fallo` y `Esquema y ubicación del
          inventario` se actualizan para enumerar la rama de fallo de
          staging.
          (3) **Clasificación de entradas HTML** — `index.html` es la
          **única** entrada HTML de ruta-de-aplicación normal.
          `404.html` y `500.html` son exenciones de página de error
          explícitamente permitidas: si Next.js las emite, el
          verificador las registra bajo la clase de activo
          **separada** `error_pages` — **no** se promueven a entradas
          de ruta-de-aplicación, **no** se listan bajo `assets[]` para
          la clase `application_route_html`, y su ausencia **nunca**
          es un fallo de clases faltantes para el contrato de
          ruta-de-aplicación. Registrado en `design.md::§3.3.2.1`
          dividiendo la fila original `Clases de activos requeridas`
          en una nueva fila `Clases de activos requeridas
          (ruta-de-aplicación)` más una nueva fila `Exenciones de
          página de error (clasificadas aparte)`, y actualizando la
          fila `Frontera de verificación` para asertar la
          clasificación.
          Las filas `Frontera de verificación` y `Esquema y ubicación
          del inventario` se actualizan para que el verificador
          strict-TDD G2 posterior deba asertar las tres correcciones
          como precondiciones. El pie de estado en `design.md` (y su
          espejo en español) se actualiza para enumerar las tres
          correcciones; el lenguaje de bloqueo G2 / G5 / PR3e se
          conserva verbatim. Ninguna frontera seleccionada, ninguna
          puerta aprobada, sin manifest de cutover, ningún verificador
          G2 escrito, no se tocan fuente / tests / scripts / workspace
          candidato / package-lock / ficheros de evidencia. Espejos
          en español actualizados en paralelo. No se realiza commit
          ni push en esta pasada.
        - **2026-08-30** — Pasada de corrección del contrato de salida G2
          (una decisión explícita del mantenedor aplicada a
          `design.md::§3.3.2.1`; esta entrada). Según la tarea del padre,
          el contrato G2 canónico se corrige para reflejar la disposición
          de salida verificada del **build limpio de Next.js 16.3.3 /
          Turbopack** (CSS bajo `out/_next/static/chunks/**`, chunks JS
          planos bajo `out/_next/static/chunks/**` sin subdirectorio
          `chunks/app/`, y `build-manifest.json` en staging / requerido
          mientras que `app-build-manifest.json` es opcional y nunca un
          fallo de clase faltante). G2 **sigue `bloqueado — contrato
          definido; verificador no implementado`**, no `aprobado` (ningún
          verificador G2 se escribe en esta pasada, ninguna puerta
          aprueba, no se tocan fuente / tests / scripts / workspace
          candidato / package-lock / ficheros de evidencia / artefacto de
          build candidato de Next 16; las realidades de la salida del
          build son hallazgos de implementación, no suposiciones).
          (4) **Corrección del contrato de salida de Next.js 16 /
          Turbopack** — registrada en `design.md::§3.3.2.1` contra la
          disposición de salida del build limpio `next build` verificada:
          - (4.a) **Clase CSS** — la clase CSS de ruta-de-aplicación
            requerida es **uno-o-más ficheros `*.css` no vacíos en
            cualquier punto bajo
            `<candidate-root>/out/_next/static/chunks/**`** (los bundles
            CSS están co-ubicados con los chunks JS), **no** bajo
            `out/_next/static/css/` (no se requiere ni se aserta ningún
            directorio CSS separado).
          - (4.b) **Clase JS** — la clase JS de ruta-de-aplicación
            requerida es **uno-o-más ficheros `*.js` no vacíos en
            cualquier punto bajo
            `<candidate-root>/out/_next/static/chunks/**`**; el contrato
            lleva **sin requisito del subdirectorio `chunks/app/`**
            (Next.js 16 / Turbopack emite chunks JS planos).
          - (4.c) **Semántica del staging de manifiestos** — solo
            `<candidate-root>/.next/build-manifest.json` →
            `<candidate-root>/out/.next/build-manifest.json` es
            **requerido** (su ausencia de la salida del build es un fallo
            de clase faltante);
            `<candidate-root>/.next/app-build-manifest.json` →
            `<candidate-root>/out/.next/app-build-manifest.json` es
            **opcional y nunca un fallo de clase faltante** — el
            verificador intenta la copia solo cuando el manifiesto fuente
            existe, registra `staged` / `not_emitted` en `assets[]`, y
            nunca falla por su ausencia (el build limpio verificado de
            Next 16.3.3 / Turbopack emite solo `build-manifest.json`).
          Registrado en `design.md::§3.3.2.1` actualizando las filas
          `Clases de activos requeridas (ruta-de-aplicación)`, `Staging
          post-build de manifiestos (atómico)`, `Esquema y ubicación del
          inventario`, `Semántica de fallo`, y `Frontera de verificación
          (precondiciones del verificador strict-TDD G2)`; la fila
          `Frontera de verificación` además aserta que el verificador
          strict-TDD G2 NO DEBE requerir un directorio
          `_next/static/css/` ni un subdirectorio
          `_next/static/chunks/app/`. La fila `Semántica de fallo` añade
          la rama (b′) para ausencia opcional de `app-build-manifest.json`
          (`not_emitted` **nunca** es un fallo) y aprieta la rama (b) a
          solo `build-manifest.json` requerido. El pie de estado en
          `design.md` (y su espejo en español) se actualiza para enumerar
          las **cuatro** correcciones; el lenguaje de bloqueo G2 / G5 /
          PR3e se conserva verbatim. Espejos en español actualizados en
          paralelo. Ninguna frontera seleccionada, ninguna puerta
          aprobada, sin manifest de cutover, ningún verificador G2
          escrito, no se tocan fuente / tests / scripts / workspace
          candidato / package-lock / ficheros de evidencia / artefacto
              de build candidato de Next 16. No se realiza commit ni push en
              esta pasada.
        - **2026-08-30** — Pasada de registro del PASS de G2 (esta entrada).
          Según la tarea del padre, la evidencia verificada independientemente
          del run limpio G2 capturada en el árbol de trabajo dedicado
          `taxa-worktrees/migrate-nextjs-g2-evidence-capture` (sobre
          `develop` en `a74289b`; la entrada de aprendizaje de PR106 ya
          fusionada en esta base **sin cambio de contrato**) se registra
          aquí y en el pie de estado de `design.md`; **no se tocan,
          comitean, ni pushean fuente, tests, scripts, tasks, ficheros
          de producto, ficheros de evidencia, workspace candidato, ni
          `package-lock.json` en esta pasada.** G2 **pasa** contra el
          contrato canónico definido en `design.md::§3.3.2.1` (se
          honran las **cuatro** correcciones explícitas del mantenedor).
          Resumen de evidencia:
          - **Timestamp del run** — build iniciado
            `2026-08-30T18:10:59.430633+00:00`, build finalizado
            `2026-08-30T18:11:02.803400+00:00` (limpio, ~3,4 s).
          - **Versión de Node** — `v26.8.1` (requisito duro ≥ `20.9.0`).
          - **Ubicación del artefacto** —
            `taxa-worktrees/migrate-nextjs-g2-evidence-capture/tools/g2-candidate/out/BUILD-INVENTORY.json`
            (y `out/.next/build-manifest.json` para el manifiesto en
            staging). El workspace capturado **no** se comitea; solo se
            referencian aquí la ruta y el contenido del inventario.
          - **Comando de build** (registrado en el campo
            `build_command` del inventario) —
            `<candidate-root>/node_modules/.bin/next build` con
            `cwd = <candidate-root>`; exit `0`.
          - **Clases presentes en el inventario** (sin
            `missing_classes`): `application_route_html` ×1
            (`out/index.html`), `js_class` ×1 (un `*.js` no vacío bajo
            `out/_next/static/chunks/**`), `css_class` ×1 (un `*.css`
            no vacío bajo `out/_next/static/chunks/**`),
            `staged_manifest` ×2 (`build-manifest.json` requerido
            `staged`, `app-build-manifest.json` opcional `not_emitted`
            — la ausencia **nunca** es un fallo según el contrato de
            **cuatro** correcciones), `error_pages` ×1 (`out/404.html`
            clasificado por separado, **no** promovido a
            `application_route_html`).
          - **Build-manifest en staging** —
            `<candidate-root>/out/.next/build-manifest.json`,
            **607 bytes**, sha256
            `f52f7edd901e373a2a24a4ecf8ba61c96ad227093c6440dc4a3a6ca58a92f2a3`
            (`staged`).
          - **App-build-manifest opcional** — `not_emitted` (registrado,
            **no** es un fallo de clase faltante).
          - **Tests** — el test enfocado `tests/test_verify_build.py`
            pasa **14 / 14** (12 funciones + 2 expansiones
            parametrizadas sobre `(omit, label)`); el test enfocado
            `tests/test_g2_candidate.py` pasa **34 / 34** (17 funciones
            + expansiones parametrizadas sobre `(path)` y `(needle)`).
          - **Log de build** — `<candidate-root>/build.log` capturado
            (presente la advertencia de múltiples lockfiles y **no es
            bloqueante** según el contrato canónico — la salida del
            verificador se propagó limpia a `0`).
          - **Nota de riesgo** — la tarea breve del padre listó el
            prefijo sha256 del build-manifest en staging como
            `7ad2277db4ab4e80...`; el sha256 **real** capturado es
            `f52f7edd901e373a2a24a4ecf8ba61c96ad227093c6440dc4a3a6ca58a92f2a3`
            (el conteo de bytes coincide en 607). El prefijo de la
            breve parece ser un error de transcripción; la evidencia
            capturada arriba es lo que está en disco y se registra
            verbatim. Ninguna semántica de la puerta G2 depende del
            prefijo del hash más allá de las aserciones de
            bytes-contados + estabilidad de sha256; la aserción del
            contrato canónico se cumple con el sha256 registrado.
          - **Verdad preservada** — G2 **pasa** (build limpio del
            candidato + inventario reproducible, todas las aserciones
            del contrato satisfechas); **G3, G4, G5, G6 siguen
            bloqueadas** (G5 irreproducible según la auditoría §3.3.5;
            los verificadores G3 / G4 / G6 aún no se escriben); **la
            exportación estática sigue sin seleccionarse** (no se elige
            ningún Enfoque A / B / C); **sin activación de FastAPI**
            (el workspace candidato sigue como raíz de build
            autocontenida sin activación según la autorización
            canónica en `design.md::§3.3.2.1` fila 1). El pie `status:`
            en `design.md` (y su espejo en español) se actualiza para
            enumerar este registro de PASS de G2 preservando verbatim
            el lenguaje de bloqueo G3 / G4 / G5 / G6 / exportación
            estática / FastAPI y el contrato G2 de **cuatro**
            correcciones. El cuerpo del contrato G2 en
            `design.md::§3.3.2.1` **no** se modifica en esta pasada.
            Espejos en español actualizados en paralelo. No se realiza
            commit, push, ni apertura de PR en esta pasada.