# Dominio taxonómico puro (PR #84)

## What

PR #84 incorpora el primer contrato de dominio concreto dentro de `src/modules/`: los rangos taxonómicos, el registro `Taxon` inmutable y sus invariantes puros. El módulo puede compilarse y ejercitarse sin iniciar Next, React, FastAPI, el DOM ni servicios de E/S.

## How

El work unit siguió TDD estricto. Se creó primero `tests/test_taxonomy_domain.py` para fijar la ausencia inicial del archivo y el contrato observable; después se implementó `src/modules/taxonomy/domain/taxon.ts`. El test compila únicamente ese archivo con TypeScript 5.7 en modo `--strict`, objetivo ES2022 y librería ES2022, emite CommonJS temporal y ejecuta un arnés de Node que valida los helpers reales. La validación final fue `6 passed` en el test enfocado y `148 passed` junto con los contratos previos de capas e imports.

## Where

- `src/modules/taxonomy/domain/taxon.ts` — declara `Rank`, la interfaz `Taxon`, el orden canónico de rangos y los helpers puros `isValidRank`, `isValidTaxon` y `compareRanks`.
- `tests/test_taxonomy_domain.py` — comprueba el shape del contrato, la ausencia de dependencias prohibidas y el comportamiento compilado en runtime.
- `openspec/changes/migrate-nextjs-tailwind4/tasks.md` — define el work unit Phase 2d: tipos planos e invariantes de dominio taxonómico.

## Why

La migración necesita un núcleo de negocio independiente antes de conectar APIs o componentes. Al mantener los datos taxonómicos y sus validaciones fuera de la infraestructura, los siguientes PR pueden adaptar Catalogue of Life, WoRMS y la UI sin que las reglas del dominio dependan de un framework, una red o el navegador.

## How it works

`Rank` restringe el rango a los ocho niveles admitidos, desde `kingdom` hasta `subspecies`. `Taxon` expone cinco campos de solo lectura: identificador, nombre, rango, autoría y padre. `isValidRank` y `isValidTaxon` permiten validar datos desconocidos en el límite de una futura infraestructura; `compareRanks` ordena dos rangos de más amplio a más específico. Ninguno de estos helpers importa módulos ni realiza efectos secundarios.

## Workflows

- **TDD estricto**: RED por archivo ausente, GREEN con los seis tests enfocados y triangulación mediante casos positivos, inválidos y de orden para los helpers de runtime.
- **Compilación aislada**: el test ejecuta `tsc` sobre un único archivo con ES2022; esto prueba que el dominio no requiere presets o tipos de Next, React, FastAPI ni DOM.
- **Cadena de migración**: PR #84 sigue a los PR #78, #80 y #82; el siguiente slice, PR 2e, profundizará el guard de pureza del dominio.
- **CI y limpieza**: PR #84 se fusionó a `develop` en `8315c0b` con Smoke tests en verde. Esta entrada se publica antes de borrar el worktree de PR 2d, según `AGENTS.md`.
