# Verificador de readiness de consumidores G3 (PR #109)

## What

PR #109 incorpora el verificador G3 de readiness de consumidores y sus pruebas de contrato. Lee el manifiesto de cutover y falla cerrado mientras existan destinos sin seleccionar.

## How

El script valida esquema, campos obligatorios e IDs únicos. Sólo ejecuta verificaciones y publica `CONSUMER-READINESS.json` mediante escritura atómica cuando todos los consumidores están seleccionados y sus comandos terminan correctamente.

## Where

- `scripts/verify_consumers.py` — verificador fail-closed y publicación atómica.
- `tests/test_verify_consumers.py` — pruebas TDD con manifiestos sintéticos.
- `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json` — entrada canónica.

## Why

G3 no puede interpretar una ausencia de decisión como readiness. El fallo cerrado evita que un candidato sin reemplazos autorizados active un cutover incompleto.

## How it works

1. El verificador lee y valida el manifiesto.
2. Si algún consumidor permanece `unselected`, termina sin artefacto.
3. Con destinos seleccionados, ejecuta cada comando de verificación.
4. Sólo con todos los resultados verdes escribe el artifact de readiness atómicamente.

## Workflows

- **TDD estricto**: 18 pruebas enfocadas y 32 pruebas de verificadores G2/G3 en verde.
- **Cutover**: mantiene G3 bloqueado hasta seleccionar reemplazos sin activar FastAPI ni seleccionar A/B/C.
