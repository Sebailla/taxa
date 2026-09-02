# Propuesta: complete-taxa-frontend-migration

> **Fase**: semilla sdd-init. Sucesora de `migrate-nextjs-tailwind4`.
> La migración total del frontend de Taxa está autorizada por el
> usuario; este cambio es su hogar OpenSpec/SDD. **Esta semilla no
> escribe código de aplicación.** Las fases spec / design / tasks
> elaboran a partir de aquí.

## TL;DR

- **Objetivo**: completar la migración total del frontend de Taxa que
  `migrate-nextjs-tailwind4` planificó pero no terminó. Un único
  frontend en producción, sin pre-corte paralelo, bajo el mismo origen
  FastAPI en `127.0.0.1:8765`.
- **El backend es innegociable**: FastAPI + SQLite (WAL) permanecen
  como el único backend/origen. Las formas de los payloads de
  `/api/*` se mantienen byte-idénticas. La extensión de Chrome conserva
  `host_permissions: ["http://localhost:8765/*"]`.
- **Stack objetivo**: Next.js 16 (App Router) + React 19 + Tailwind 4 —
  el mismo stack que planificó el predecesor. Sin cambio de framework
  en este cambio.
- **Aproximación por defecto**: Aproximación A — `next build` →
  `out/` servido por el montaje `StaticFiles` de FastAPI (origen
  único preservado). La fase spec puede anular A en favor de B o C
  solo con justificación anclada en evidencia citando los números G2
  / G5 ya producidos.
- **Reutilización de evidencia**: G1 (origen único) está registrada.
  Los artefactos G2 (perfil de build), G3 (manifiesto de
  consumidores), G4 (línea base chromium), G5 (sonda de hidratación),
  G6 (dry-run de consumidores) del predecesor se importan como
  **historial**, no se rederivan. La `proposal.md` / `spec.md` /
  `design.md` / `tasks.md` / `apply-progress.md` /
  `cutover-manifest.json` / `specs/modular-architecture/spec.md` del
  predecesor son entradas de solo lectura.

## Estado del sucesor

| Campo | Valor |
| --- | --- |
| Predecesor | `migrate-nextjs-tailwind4` |
| Relación | Sucesor: este cambio hereda el objetivo; el predecesor queda congelado como historial de planificación. |
| ¿Editable en este cambio? | **No.** Los archivos bajo `openspec/changes/migrate-nextjs-tailwind4/` NO DEBEN modificarse. |
| Referenciado como | Base de evidencia para la decisión de Aproximación A/B/C y para las puertas de evidencia G1–G6. |
| Estado de la evidencia al intake | G1 PASS registrado; estado de G2 / G3 / G4 / G5 / G6 trasladado literalmente desde `migrate-nextjs-tailwind4/apply-progress.md`. |

El sucesor no rederiva la línea base chromium, el emisor del perfil
de build, la sonda de hidratación ni el verificador dry-run de
consumidores. Esos artefactos ya viven bajo el predecesor y son leídos
por las fases spec / design de este cambio como historial de
planificación.

## Contrato del backend (innegociable)

Cualquier cambio propuesto que viole una fila de esta tabla queda
fuera del alcance y debe plantearse en un cambio aparte.

| Superficie | Restricción | Fuente |
| --- | --- | --- |
| Origen | Solo `http://127.0.0.1:8765` | G1 (origen único) |
| Puerto | Solo 8765; sin segundo puerto de servidor de desarrollo | G1 |
| Formas de `/api/*` | Byte-idénticas al FastAPI actual | Regla de equivalencia funcional |
| `host_permissions` de la extensión | `["http://localhost:8765/*"]` sin cambios | Regla de continuidad |
| Modo SQLite | WAL; conexiones API de solo lectura | Convención del repo (`openspec/sdd-init.md`) |
| Pipeline ETL | Sin cambios en este cambio | Fuera del alcance del predecesor |
| Flujo de materialización, defensa SSRF en `save-url` | Sin cambios en este cambio | Fuera del alcance del predecesor |

## Alcance

### Dentro del alcance

- Migración total del frontend a Next.js 16 + React 19 + Tailwind 4,
  reemplazando la aplicación vanilla-JS en disco de `web/` bajo la
  Aproximación A (por defecto).
- Un único frontend en producción. El build legacy de pre-corte
  paralelo se retira al activar — sin estado de doble build en la fase
  apply de este cambio.
- Origen FastAPI preservado en `127.0.0.1:8765`. Se permiten
  ediciones mínimas de `api/server.py` solo para reorientar `WEB_DIR`
  y cualquier middleware estrictamente necesario para montar la nueva
  salida del frontend. Los handlers de ruta no se reescriben.
- Test de contrato de motores de búsqueda AC-21 preservado
  (`web/search_urls.js` puede moverse bajo `src/data/`; forma byte a
  byte preservada salvo revisión explícita de la fase spec).
- Estado local del navegador (`theme`, `tree-source`, `last-taxon-id`,
  `kebab-open-id`) migrado de forma determinista a un store tipado
  con un sitio de lectura + un sitio de escritura por clave.
- Restricciones de arquitectura modular desde
  `specs/modular-architecture/spec.md` del predecesor se aplican sin
  cambios.

### Fuera del alcance

- Reescritura del backend: handlers de ruta de `api/server.py`,
  lógica SQLite/WAL, flujo de materialización, defensa SSRF en
  `save-url`.
- Pipeline ETL: `etl/parse_textree`, `load_coldp`, `load_worms`,
  `load_freshwater`, migraciones.
- Trabajo de paridad de la extensión de Chrome — un cambio aparte
  rastrea cualquier adaptación de la extensión consciente de React.
- Trabajo de SEO / metadata / sitemap / robots.
- Nuevas rutas (Settings, About, Help) más allá de lo que la UI
  legacy expone hoy.
- Herramientas de cobertura (`coverage.available: false` es el estado
  actual).
- Rediseño visual (impeccable / seguimiento de Stitch, no es
  bloqueante).
- Editar o "completar" el directorio de cambios del predecesor. El
  predecesor está **congelado**, no finalizado.
- Reejecutar las sondas G2 / G4 / G5 / G6 del predecesor — sus
  salidas se importan tal cual.

## Aproximación

El predecesor difirió la decisión de Aproximación A / B / C a la fase
design. Este cambio sucesor adopta el **default bloqueado por
evidencia**: **Aproximación A — Exportación estática bajo FastAPI**.
`next build` produce `out/`; el montaje `StaticFiles` existente de
FastAPI lo sirve; sin SSR / route handlers / server components;
origen único preservado.

**El default es A**, no B ni C, porque:

- G1 (origen único) ya está registrada. La Aproximación A cumple G1
  trivialmente; B la rompe (dos puertos); C la preserva mediante
  despliegue por fases pero añade superficie de revisión.
- El manifest de la extensión de Chrome permanece sin cambios bajo A.
- El cambio de `WEB_DIR` es la ruta de edición mínima (montaje
  `StaticFiles` en `api/server.py:1815` reorientado a `out/`).
- Las fases spec / design pueden anular A en favor de B o C solo
  citando los números del perfil de build G2 y los números de
  hidratación G5 desde el `apply-progress.md` del predecesor. La
  anulación se documenta en `design.md::§1` de este cambio.

## Capacidades

### Nuevas capacidades

- `frontend-runtime`: aplicación de pantalla única Next.js App
  Router, exportada estáticamente a `out/`, servida por el montaje
  `StaticFiles` existente de FastAPI en `127.0.0.1:8765`.
- `design-tokens`: bloque `@theme` de Tailwind 4 + variables CSS
  preservados literalmente desde el bloque `<style>` ad hoc de
  `web/index.html` y `tailwind.config.js`.
- `browser-state-hydration`: store tipado con claves explícitas de
  rehidratación desde `localStorage` (`theme`, `tree-source`,
  `last-taxon-id`, `kebab-open-id`), un sitio de lectura + un sitio
  de escritura por clave.

### Capacidades modificadas

- `research`: los consumidores API migran a llamadas `fetch` desde
  componentes React / server components. Sin cambios en la forma de
  request/response; el test de contrato AC-21 sigue leyendo
  `web/search_urls.js` salvo que la fase sdd-spec revise AC-21
  explícitamente.
- `frontend-bootstrap`: `web/index.html` deja de ser el entry; el
  entry es `out/index.html` (o el equivalente servido desde
  `.next/static`) servido por FastAPI.

### Capacidades sin cambios (importadas del predecesor)

- `modular-architecture`: `specs/modular-architecture/spec.md` del
  predecesor se aplica sin cambios. No se escribe una segunda copia.

## Áreas afectadas

| Área | Impacto | Nota |
| --- | --- | --- |
| `web/index.html` | Eliminado | Reemplazado por `out/index.html` (exportación estática de Next.js). |
| `web/*.js` (18 módulos, ~6.345 LoC) | Eliminado | Reescrito como componentes React bajo `src/components/`. |
| `web/index.css` | Modificado | Pasa a ser `src/app/globals.css`; el bloque `@theme` reemplaza a `tailwind.config.js`. |
| `tailwind.config.js` | Eliminado | Configuración CSS-first de Tailwind 4 en `globals.css`. |
| `package.json` | Modificado | Sube a `next@^16`, `react@^19`, `react-dom@^19`, `tailwindcss ^4.x`; añade toolchain TS; `engines.node: ">=20.9.0"`. |
| `api/server.py` (solo punto de montaje) | Modificado | `WEB_DIR` reorientado a `out/`; handlers de ruta intactos. |
| `Makefile` | Modificado | `make api` primero construye Next.js y luego ejecuta uvicorn; superficie de `make smoke` sin cambios. |
| `tests/test_smoke.py::test_search_engine_contract` | Posiblemente modificado | Si `web/search_urls.js` se mueve bajo `src/data/`, la ruta `open()` del test se actualiza; forma byte a byte preservada. |
| `tests/test_e2e_file_explorer.py`, `tests/test_web_toggle.py` | Modificado | Selectores DOM actualizados al nuevo árbol de componentes; contrato de atributos `data-*` preservado. |
| `extension/manifest.json` | Sin cambios | `host_permissions` permanece en `["http://localhost:8765/*"]`. |
| `openspec/changes/migrate-nextjs-tailwind4/**` | **Sin cambios** | Congelado como historial de planificación. Este cambio no lo edita. |
| `documents-es/openspec/changes/complete-taxa-frontend-migration/**` | Nuevo (espejo) | Espejo en español de los artefactos de este cambio, según la convención bilingüe de AGENTS.md. |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
| --- | --- | --- |
| El default de Aproximación A es anulado por spec/design sin evidencia nueva. | Media | La anulación DEBE citar los números G2 (perfil de build) + G5 (hidratación) desde el `apply-progress.md` del predecesor; la anulación se registra en `design.md::§1` de este cambio. |
| El cambio de namespace de tokens en Tailwind 4 (`--color-primary` vs `--primary`) rompe las referencias `var(--token)` del CSS plano. | Media | Alias de nombres en `@theme` para que los tokens `--primary`, `--bg-surface`, `--realm-*` resuelvan sin cambios; test de paridad enumera cada referencia `var(--token)` y exige una declaración no vacía. |
| Reordenamiento en cascada de `color-mix()` en el bloque `<style>` inline de 80 KB provoca deriva visual. | Media | Migrar las reglas ad hoc a `globals.css` dentro de `@layer base` para que el orden de fuente coincida; regresión visual con Playwright sobre el fixture existente de `tests/test_web_toggle.py`. |
| El test de contrato AC-21 de motores de búsqueda falla porque `web/search_urls.js` cambió de ubicación. | Media | Mantener el literal bajo `src/data/search-engines.js` con la misma forma; el test lee `open()` desde la nueva ruta. La fase spec decide si se modifica AC-21. |
| Desajuste de hidratación por lecturas de `localStorage` en servidor vs cliente. | Media | El render inicial usa una bandera `mounted`; las lecturas suceden dentro de `useEffect`; la estructura del árbol asume estado vacío en el primer pintado. |
| La exportación estática pierde rutas dinámicas / image optimization que pueda requerir trabajo futuro. | Baja | Aceptable para v1; migrar al servidor de dev completo de Next.js (Aproximación B) es el coste del siguiente cambio si se necesita. |
| El bundle de dependencias Next.js + React introduce regresión en el pintado inicial (presupuesto de rendimiento). | Baja | Perfil de `next build` capturado antes/después; muestra de Playwright + Lighthouse sobre el fixture chromium existente; ≤ 0% de regresión como criterio de éxito. |
| El contrato de puerto único se rompe si cambian accidentalmente los `host_permissions` de la extensión. | Baja | Regla dura en Makefile + verificación CI de humo: `make api` solo escucha 8765; sin segundo origen añadido; `manifest.json` sin cambios en este cambio. |
| Los artefactos del predecesor derivan durante la fase apply de este cambio (alguien edita `migrate-nextjs-tailwind4/`). | Baja | Regla de CI / branch protection: los PRs de este cambio NO DEBEN modificar `openspec/changes/migrate-nextjs-tailwind4/**`; el hook de lint rechaza. |

## Plan de rollback

1. **Reversión a nivel de PR**: `git revert <migration-sha>` restaura
   el `web/` vanilla + `tailwind.config.js` + pipeline de build de
   Tailwind 3.4. `package-lock.json` conserva el estado previo de
   dependencias; `npm ci` reproduce el lock. `make api` regenera
   `web/dist/tailwind.css` desde la fuente revertida.
2. **Efectos colaterales**: el test de contrato AC-21 vuelve a su
   lectura previa `open("web/search_urls.js")`; los tests de backend
   quedan intactos.
3. **Sin migración de datos requerida**: no se envía ningún cambio de
   esquema de BD en este cambio.
4. **Continuidad de la extensión**: la extensión habla con
   `http://localhost:8765` antes, durante y después del rollback — no
   se requiere actualizar `manifest.json` para revertir.
5. **Predecesor congelado**: revertir este cambio NO toca
   `openspec/changes/migrate-nextjs-tailwind4/**`. El predecesor
   permanece como historial de planificación.
6. **Verificación tras el rollback**: `make smoke` vuelve a la línea
   base previa a la migración (63 passed, 8 skipped sobre el mismo
   conjunto de fixtures, más las ejecuciones existentes de
   Playwright).

## Dependencias

- `next@^16` (App Router; admite React `^19.0.0`).
- `react@^19`, `react-dom@^19`.
- `tailwindcss` ^4.x.
- `typescript` `>=5.1.0`, `@types/react@^19`,
  `@types/react-dom@^19`, `@types/node` (toolchain TS).
- `next/font` para Raleway, JetBrains Mono, Material Symbols Outlined
  (sin nuevo set de iconos).
- Motor de runtime: Node.js `>=20.9.0` (requisito duro de Next.js
  16).

## Forma de entrega

- **Estrategia de entrega**: `ask-on-risk` (preexistente).
- **Estrategia de cadena**: `deferred` (según preflight; cambiar a
  `auto-chain` si sdd-tasks demuestra que el conteo de rebanadas
  excede el presupuesto de revisión de 400 líneas).
- **Presupuesto de revisión**: 400 líneas por PR.
- **Carga de trabajo**: el `tasks.md` del predecesor enumera 35 tareas
  en 14+ sub-PRs. Este cambio las re-rebana bajo la Aproximación A y
  la estrategia de cadena diferida; ningún sub-PR excede el
  presupuesto de 400 líneas.
- **Regla de rama**: cada sub-PR apunta a `develop`; los nombres de
  rama coinciden con `^(feat|fix|chore|...)/[a-z0-9._-]+$`.

## Criterios de éxito

- [ ] Paridad funcional: cada flujo de usuario (navegar, buscar,
      materializar, previsualizar, abrir carpeta, guardar URL, ver
      archivos en todos los formatos soportados) se comporta de forma
      idéntica al build legacy.
- [ ] Rendimiento: sin regresión en el pintado inicial ni en la
      latencia de interacción sobre la muestra existente de Playwright
      + Lighthouse (Δ ≤ 0%).
- [ ] Origen local único: `make api` solo escucha 8765; sin segundo
      puerto de servidor de desarrollo; `host_permissions` de la
      extensión sin cambios.
- [ ] Los tests pytest del backend siguen verdes (línea base 63
      passed, 8 skipped).
- [ ] El suite de Playwright actualizado sigue verde contra el nuevo
      árbol de componentes; contrato de atributos `data-*` preservado.
- [ ] Test de contrato AC-21 de motores de búsqueda pasa (la ubicación
      del archivo puede moverse; forma byte a byte sin cambios salvo
      revisión de la fase spec).
- [ ] El estado y las preferencias locales del navegador migran de
      forma determinista (`theme`, `tree-source`, `last-taxon-id`,
      `kebab-open-id`) con un sitio de lectura + un sitio de
      escritura por clave.
- [ ] Paridad de Tailwind 4: cada clase utilitaria y cada token
      `:root` resuelve a una declaración no vacía.
- [ ] Accesibilidad: cada rol ARIA, etiqueta y handler de teclado del
      build legacy se preserva; el escaneo axe no presenta nuevas
      violaciones.
- [ ] Predecesor congelado: `openspec/changes/migrate-nextjs-tailwind4/**`
      es byte-idéntico antes y después de la fase apply de este
      cambio.
- [ ] Rollback: `git revert` del PR de migración restaura el build
      legacy con humo + Playwright en verde.

## Siguiente paso

La fase spec (sdd-spec) lee esta propuesta más la `design.md`,
`apply-progress.md` y `cutover-manifest.json` del predecesor, y
después confirma la Aproximación A o elige B / C con justificación
anclada en evidencia. La salida de spec aterriza en
`openspec/changes/complete-taxa-frontend-migration/spec.md`. La fase
design registra entonces la aproximación elegida en
`openspec/changes/complete-taxa-frontend-migration/design.md::§1`
(final, no diferida).
