# Verificación canónica del PASS de G3 (PR #116)

## What

PR #116 (`fix(g3): preserve virtualenv Python paths`) cierra la
secuencia G3 sobre `origin/develop` junto con PR #109 + PR #111 +
PR #115: el verificador `scripts/verify_consumers.py` queda
plenamente operativo con runtime controlado (`--serve --venv
--fixture-web-root --repo-root`), aplicación fail-closed de forma
HTTP a través de `tools/g3-legacy-fixture/scripts/check_http_status.py`
y preservación de symlinks de virtualenv. Los **26 / 26**
consumidores del `cutover-manifest.json` pasan su `verification.command`
contra el fixture controlado, y se emite un
`CONSUMER-READINESS.json` válido.

## How

PR #116 sustituye dos `.resolve()` por `.expanduser()` en
`scripts/verify_consumers.py` para que el python del venv mantenga
su symlink. Un test nuevo
(`test_find_venv_python_preserves_symlink_path`) fija la invariante:
la ruta devuelta debe ser el symlink, no el destino resuelto. La
cláusula de cobertura HTTP-shape de PR #115 enruta automáticamente
las expectativas tipo `"200"` o `"200 for each"` al helper
`tools/g3-legacy-fixture/scripts/check_http_status.py` para validar
el código real y no sólo la salida del shell.

La verificación canónica ejecuta:

```
python scripts/verify_consumers.py \
  --manifest openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json \
  --out <build-root> \
  --serve \
  --venv <repo-root>/.venv/bin/python \
  --fixture-web-root <repo-root>/tools/g3-legacy-fixture/web \
  --repo-root <repo-root>
```

con `exit_code = 0` y `CONSUMER-READINESS.json` con
`activation_complete: true`, `unselected_count: 0`,
`failed_verifications[]` vacío.

## Where

- `scripts/verify_consumers.py` — verificador (PR #109) +
  augmentos controlados (PR #111) + aplicación HTTP fail-closed
  (PR #115) + preservación de symlinks de venv (PR #116).
- `tools/g3-legacy-fixture/scripts/check_http_status.py` — helper
  controlado que valida el código HTTP real.
- `tools/g3-legacy-fixture/web/` — fixture autocontenido (16 JS +
  index.html) servido por `python -m http.server` en puerto libre
  aislado.
- `tests/test_verify_consumers.py` — triangulación del verificador
  (incluye el test de symlink de PR #116 y los tests HTTP-shape de
  PR #115).
- `tests/test_g3_legacy_fixture.py` — cobertura del fixture.
- `openspec/changes/migrate-nextjs-tailwind4/cutover-manifest.json`
  — manifiesto canónico (sin cambios en este PR).
- `openspec/changes/migrate-nextjs-tailwind4/design.md::§3.3.3` y
  `documents-es/openspec/changes/migrate-nextjs-tailwind4/design-es.md::§3.3.3`
  — registro canónico del PASS.

## Why

G3 representa el contrato de que cada consumidor enumerado en §3.1
sigue servido por la ruta prevista después del corte. Sin G3 PASS,
una aprobación del verificador equivaldría a una suposición: podría
ocurrir que un comando salga `0` aunque el servidor devuelva 404,
porque `curl -w '%{http_code}'` siempre sale `0` cuando la conexión
se establece. PR #115 + PR #116 cierran ese agujero: ahora el
verificador compara el código HTTP real contra la expectativa y
preserva el symlink del venv para que pytest dispare el intérprete
correcto.

## How it works

1. El verificador parsea el manifiesto y valida el esquema.
2. Con `--serve --fixture-web-root` levanta `python -m http.server`
   sobre `<fixture-web-root>` en un puerto TCP libre elegido por el
   SO (nunca `8765`).
3. Reescribe cada `verification.command` para apuntar al puerto
   aislado en lugar de `127.0.0.1:8765`.
4. Resuelve el python del venv desde `--venv` o
   `<repo-root>/.venv/bin/python` preservando el symlink (PR #116).
5. Enruta expectativas HTTP-shape (`"200"`, `"200 for each"`) a
   `tools/g3-legacy-fixture/scripts/check_http_status.py` para
   validar el código real (PR #115). Expectativas no-HTTP mantienen
   la semántica de sólo-exit-del-shell.
6. Ejecuta cada `verification.command` con el shell.
7. Si **todos** los comandos salen `0`, escribe
   `<build-root>/CONSUMER-READINESS.json` atómicamente vía
   temp-file + rename, con `manifest_sha256`, `node_version ≥
   20.9.0`, `verified_at`, `exit_code = 0`,
   `consumers[].status = "ready"`, `unselected_count = 0`,
   `failed_verifications[]` vacío, `activation_complete = true`.
8. Cualquier fallo cierra el artefacto (fail-closed) y el verificador
   sale distinto de cero.

## Workflows

- **Verificación canónica post-merge**: tras fusionar PR #109 + PR #111 +
  PR #115 + PR #116 sobre `develop`, el comando documentado arriba
  ejecuta los 26 / 26 consumidores y emite
  `CONSUMER-READINESS.json` válido.
- **G3 Tier-1**: el PASS actual cubre la selección **Nivel-1 (legacy
  pre-cut)** contra el runtime del legado servido por el fixture
  controlado. No requiere G2/G4/G5/G6 PASS.
- **G3 Tier-2 (pendiente)**: la selección **Nivel-2 (atomic-cut)**
  contra el artefacto de build del Enfoque A / B / C elegido sigue
  acoada por PASS de G4 (paridad Playwright + Lighthouse) + G5 (línea
  base de hidratación reproducible) + G6 (éxito de
  `cutover-rehearsal.json`). El Enfoque A / B / C sigue sin
  seleccionar.
- **Corte**: G3 PASS para Nivel-1 **no** implica activación de
  FastAPI. PR3e sigue bloqueado hasta que Nivel-2 cierre vía PR3d/PR3e.
- **Espejos**: el design / design-es reflejan el cambio de disposición
  G3 a "APROBADO para Nivel-1; NO APROBADO para Nivel-2", preservando
  verbatim el lenguaje de G4 / G5 / G6 / G2-Tier-2 / Enfoque-A-B-C-sin-seleccionar.
