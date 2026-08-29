# Guard de pureza del dominio (PR #86)

## What

PR #86 convierte la Regla 4 de la arquitectura modular en una prueba ejecutable para el dominio taxonómico. El guard detecta dependencias de framework, red, navegador y proceso en archivos TypeScript directos de `src/modules/taxonomy/domain/`.

## How

El work unit siguió TDD: el helper de stripping comenzó como stub (RED) y luego se implementó antes de ejecutar el guard (GREEN). `tests/test_domain_purity.py` reemplaza comentarios de línea, bloque y JSDoc por espacios, preservando los saltos de línea para que los diagnósticos apunten al archivo original. Casos controlados prueban que los tokens prohibidos dentro de comentarios no generan falsos positivos y que los tokens en código sí fallan.

## Where

- `tests/test_domain_purity.py` — guard parametrizado para los archivos `.ts` directos del dominio taxonómico.
- `src/modules/taxonomy/domain/taxon.ts` — primer consumidor protegido por el guard.
- `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec.md` — Regla 4 que define la pureza del dominio.

## Why

Los tipos y reglas del dominio deben seguir siendo utilizables sin iniciar Next, React, FastAPI, DOM, red o almacenamiento. Un guard automatizado convierte esa restricción arquitectónica en una señal de CI temprana, antes de que una dependencia accidental se propague hacia la UI o infraestructura.

## How it works

La prueba obtiene los archivos `.ts` directos del directorio de dominio, excluye placeholders y limpia los comentarios antes de buscar tokens prohibidos. Cubre paquetes de framework, `fetch(`, APIs de navegador y `process.`. Los imports cross-module `@taxa/*` quedan fuera: pertenecen a la Regla 5 de límites de módulos, no a la Regla 4 de pureza.

## Workflows

- **TDD estricto**: RED por helper de stripping incompleto; GREEN con 26 casos enfocados, incluidos casos de comentarios y diagnósticos por línea.
- **Arquitectura modular**: PR #86 sigue al dominio taxonómico de PR #84 y evita que sus futuras extensiones incorporen dependencias prohibidas.
- **CI y limpieza**: PR #86 se fusionó a `develop` en `53a33be` con Smoke tests en verde. Esta entrada se publica antes de eliminar el worktree del PR, según `AGENTS.md`.
