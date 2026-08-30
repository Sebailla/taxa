# Probe de evidencia para exportación estática (PR #96)

## What

PR #96 incorpora un probe aislado para medir una exportación estática de Next.js 16 con React 19. No se conecta al producto ni selecciona aún una alternativa de integración con FastAPI.

## How

El probe vive íntegramente en `tools/static-export-probe/`. Usa dependencias exactas, `npm ci`, una configuración `output: "export"` y un identificador de build determinista derivado de las versiones fijadas. El script de captura construye el fixture, lo sirve sólo en loopback con puerto efímero, toma muestras reales de hidratación mediante Playwright y publica evidencia JSON de forma atómica al final.

## Where

- `tools/static-export-probe/package.json` — versiones exactas de Next 16.3.3 y React 19.2.8.
- `tools/static-export-probe/next.config.mjs` — exportación estática e identificador de build determinista.
- `tools/static-export-probe/app/` — shell diagnóstico inaccesible desde producción.
- `tools/static-export-probe/scripts/capture.mjs` — captura, validación y guardia de escrituras.

## Why

La migración necesita evidencia reproducible antes de decidir si la UI se sirve de forma estática. El probe evita que una medición experimental afecte rutas de FastAPI, la extensión, pruebas existentes o artefactos de producción.

## How it works

1. La captura valida el lockfile y ejecuta `npm ci`.
2. Construye la exportación y comprueba las versiones resueltas y el build ID.
3. Sirve `out/` en `127.0.0.1` con puerto aleatorio y rechaza el puerto 8765.
4. Playwright espera el marcador de hidratación y reúne tres muestras de recarga.
5. Un snapshot SHA-256 del repositorio rechaza escrituras fuera de los directorios generados del probe.
6. Sólo si todas las validaciones pasan, publica el JSON de evidencia de manera atómica.

## Workflows

- **Evidencia de migración**: mantiene la decisión Next.js ↔ FastAPI basada en mediciones, no en supuestos.
- **CI y revisión**: PR #96 se fusionó a `develop` en `ae74d8b` con Smoke tests en verde.
- **Aislamiento**: los fallos de dependencia, build, navegador, timing o escrituras prohibidas terminan con estado no cero y sin evidencia válida.
