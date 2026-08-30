# Workspace candidato aislado para G2 (PR #103)

## What

PR #103 incorpora `tools/g2-candidate/`, un workspace Next.js 16 aislado para producir y validar un build candidato G2. No se monta en FastAPI ni selecciona todavía una estrategia de entrega.

## How

El workspace fija Next 16.3.3 y React 19.2.8, exige Node 20.9.0 o superior y usa `output: "export"`. La suite `tests/test_g2_candidate.py` aplica TDD sobre dependencias, configuración, aislamiento y lockfile; `npm ci` valida el lockfile local antes de admitir su excepción de tamaño.

## Where

- `tools/g2-candidate/package.json` — dependencias exactas y script de build aislado.
- `tools/g2-candidate/next.config.mjs` — exportación estática no activada.
- `tools/g2-candidate/app/` — ruta mínima y CSS para producir clases de activos G2.
- `tests/test_g2_candidate.py` — contrato del workspace candidato.

## Why

G2 necesita un output reproducible que pueda inventariarse sin modificar FastAPI, `web/`, CI, el Makefile, la extensión ni paquetes raíz. Separar el candidato evita convertir una evidencia de build en una decisión de cutover.

## How it works

1. `npm ci` instala sólo las dependencias locales del candidato.
2. `next build` genera `out/` dentro del mismo workspace.
3. Los tests verifican versiones, Node mínimo, knobs de Next y ausencia de wiring de producto.
4. El futuro verificador G2 inspeccionará ese output y emitirá `BUILD-INVENTORY.json`; no se agrega en este PR.

## Workflows

- **TDD estricto**: 34 pruebas enfocadas pasaron antes de publicar el workspace.
- **Presupuesto de revisión**: las 396 líneas no generadas quedaron bajo el límite; el `package-lock.json` fue la única excepción aprobada tras `npm ci` exitoso.
- **Migración**: el workspace habilita el siguiente slice del verificador G2, sin cerrar G2 ni activar PR3e.
