# Integridad de captura G4 (PR #128)

## What

PR #128 endurece la captura G4 para que la evidencia corresponda al corpus versionado y para conservar la evidencia anterior cuando falle su publicación final.

## How

El launcher ASGI G4 sirve el `index.html` del fixture antes del mount estático de producción. El productor Node vuelve a consultar el destino y valida status HTTP, SHA-256 de bytes crudos y marcador DOM antes de ejecutar Lighthouse o escribir evidencia. La publicación atómica usa un directorio hermano de respaldo y restaura la salida previa si falla el rename final.

## Where

- `tools/g4-capture/scripts/g4_asgi.py` — ruta G4 que sirve el corpus fijado.
- `tools/g4-capture/scripts/capture.mjs` — verificación del destino y publicación atómica recuperable.
- `tests/test_capture_parity.py` — pruebas de aislamiento, integridad, rollback y limpieza de estado.

## Why

La captura podía registrar el hash del manifiesto mientras auditaba contenido mutable de `web/`. Además, un fallo durante el reemplazo de evidencia podía eliminar una salida válida previa. Ambos escenarios debilitaban la trazabilidad y la recuperación de la captura.

## How it works

1. El launcher G4 responde `/index.html` con el archivo del corpus versionado.
2. La captura consulta esa URL y compara status, hash y marcador con el manifiesto.
3. Si alguna comprobación falla, no ejecuta Lighthouse ni publica archivos.
4. Si la captura es válida, escribe la nueva evidencia en staging.
5. Al publicar, conserva la salida anterior como respaldo y la restaura ante un fallo final.

## Workflows

- **CI**: la suite completa terminó con 494 pruebas aprobadas y 30 omitidas.
- **Smoke tests**: la secuencia G4 y smoke conserva el estado de `api.server` entre módulos.
- **Evidencia de captura**: el manifiesto, el destino auditado y la evidencia publicada quedan alineados de forma verificable.
