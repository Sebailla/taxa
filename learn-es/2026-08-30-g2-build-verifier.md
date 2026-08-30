# Verificador de inventario de build G2 (PR #105)

## What

PR #105 incorpora `scripts/verify_build.py` y su suite de contrato para validar el build del candidato G2. El verificador sólo produce `BUILD-INVENTORY.json` cuando el build, manifests y clases de activos cumplen el contrato.

## How

La implementación siguió TDD estricto con fixtures sintéticos y ejecutables falsos de Node y Next. El script verifica Node antes del build, ejecuta el binario local del candidato, registra la salida, hace staging atómico de manifests y publica el inventario con `os.replace`.

## Where

- `scripts/verify_build.py` — CLI de verificación y publicación atómica del inventario.
- `tests/test_verify_build.py` — pruebas sintéticas de errores, staging, clases de activos e inventario.
- `tools/g2-candidate/` — candidato previamente incorporado, usado como contrato de paths.

## Why

La evidencia G2 debe detectar builds inválidos sin copiar ni servir el frontend legado. Un artefacto parcial o un fallback silencioso convertirían un fallo técnico en una falsa señal de readiness.

## How it works

1. El script comprueba `node --version` antes de iniciar el build.
2. Ejecuta `next build` dentro del candidato y captura `build.log`.
3. Exige `build-manifest.json`, registra opcionalmente `app-build-manifest.json` y clasifica HTML, JS, CSS, fuentes y páginas de error según Next 16.
4. Si cualquier condición falla, borra staging e inventarios parciales y retorna estado no cero.
5. Si todas pasan, calcula hashes SHA-256 y publica `out/BUILD-INVENTORY.json` de forma atómica.

## Workflows

- **TDD estricto**: RED inicial, GREEN con 14 pruebas enfocadas y triangulación con 159 pruebas relevantes.
- **G2**: habilita la verificación de foundation build sin montar el candidato en FastAPI ni seleccionar A/B/C.
- **Fallos seguros**: build, versión de Node, manifests y clases de activos fallan sin fallback hacia `web/`.
