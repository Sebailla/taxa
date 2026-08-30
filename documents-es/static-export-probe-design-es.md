# Diseño: Sonda de Exportación Estática — Caparazón de Diagnóstico Desechable

## Alcance de este artefacto

Este es el **compañero de solo-diseño** para la pantalla de sonda de
exportación estática ya generada en Stitch para el proyecto
`11813286795400731874`, pantalla `ec543a4cec974c2e82085a5e0406334a`.
Captura el caparazón de diagnóstico desechable aprobado, fija los
identificadores de Stitch, define los criterios de auditoría y
prohíbe explícitamente el enlace con producción o la reutilización
como UI de producto. Es un artefacto de documentación, no de código:
entrega cero código fuente, cero tests, cero configuración, cero
cableado de build, y cero cambios bajo `web/`, `api/`, `Makefile`,
`package.json`, `extension/manifest.json`, `tests/`, `etl/`, `src/`,
`openspec/` o `documents-es/`. No pre-selecciona la Aproximación A /
B / C en `design.md` §1 — §1 queda **Abierta / Basada-en-evidencia**.

---

## Autoridad

La sonda se rige por los cinco innegociables de
`openspec/changes/migrate-nextjs-tailwind4/proposal-es.md::Sonda de
Exportación Estática Desechable (Solo Evidencia)` (commit
`866a55d`, PR #91):

| # | Innegociable | Cómo lo honra este diseño |
|---|---|---|
| 1 | **Inalcanzable desde producción** | La salida no la sirve FastAPI, no se vincula a `127.0.0.1:8765` y no es alcanzable desde ningún artefacto desplegado (sin cambios en `host_permissions` de la extensión, sin integración con `make api`, sin artefacto de release). |
| 2 | **Sin cambios en consumidores** | El montaje `StaticFiles` en `api/server.py:1847`, los consumidores del contrato AC-21 y las rutas de activación de UI (`state` singleton, claves de `localStorage`) quedan intactos. La sonda no produce superficie visible para consumidores. |
| 3 | **Solo evidencia** | Registra tamaño de `next build`, perfil de hidratación y muestras opcionales de paridad con Playwright. No modifica `design.md` §1 ni pre-selecciona la Aproximación A. |
| 4 | **Descarte / rollback explícito** | La sonda vive en una rama de corta vida (`docs/static-export-probe-design`); `git branch -D` más la eliminación del worktree restablece el estado previo sin residuos en fuente, tests o configuración. |
| 5 | **No puede seleccionar exportación estática por sí sola** | Seleccionar la Aproximación A requiere una modificación de seguimiento a la propuesta (o un cambio sucesor), revisada contra la evidencia registrada; esta propuesta no es el punto de selección. |

Citas arquitectónicas: `proposal-es.md::Sonda de Exportación
Estática Desechable`, `design-es.md::§1 Decisión de frontera de
responsabilidad del servidor (Next.js ↔ FastAPI)`,
`specs/modular-architecture/spec-es.md::regla 7`. No se identifica
ningún conflicto con las reglas 1–6 del spec a nivel de diseño; la
sonda añade superficie cero.

---

## Identificadores de la sonda (fijados)

| Campo | Valor |
|---|---|
| ID de proyecto Stitch | `11813286795400731874` |
| ID de pantalla Stitch | `ec543a4cec974c2e82085a5e0406334a` |

Si cualquiera deriva, la sonda debe regenerarse contra el nuevo par
y este artefacto enmendarse; el par anterior se retira y el log de
auditoría registra el intercambio. Los dos IDs DEBEN aparecer
juntos en cualquier artefacto regenerado.

---

## Caparazón de diagnóstico desechable aprobado

La pantalla es un caparazón **estático** y no interactivo. Existe
solo para comunicar su propia existencia y procedencia; no lleva UI
de producto, ni marca, ni navegación, ni controles, ni datos, ni
persistencia.

### Contrato visual

| Región | Permitido | Prohibido |
|---|---|---|
| Fondo de página | Blanco sólido (`#FFFFFF`) — el único color de fondo. | Gradientes, imágenes, superficies tintadas de marca, modo oscuro, trucos con `color-mix()`. |
| Contenedor | Una única tarjeta **centrada** con borde visible de 1 px, padding generoso y ancho máximo apto para lectura (sin valor fijo en píxeles; responsivo dentro de la tarjeta). | Tarjetas anidadas, marcos decorativos, sombras que imiten chrome de producto, transiciones animadas. |
| H1 | Exactamente un `<h1>` que describe la naturaleza diagnóstica (p. ej. *"Static-export probe (diagnostic only)"* o equivalente neutro). | Subtítulos (`<h2>`–`<h6>`), copia de marketing, nombre del proyecto, banner de versión. |
| Explicación | Un párrafo corto (1–3 frases) que declara que la pantalla es diagnóstico desechable, no es parte del producto y no recolecta datos. | Voz de marca, lenguaje de persona, llamadas a la acción, enlaces a superficies de producto. |
| Filas de estado | Exactamente **tres** filas, cada una con etiqueta neutra corta + valor (p. ej. *Rol: diagnostic*, *Alcance: solo evidencia*, *Producción: inalcanzable*). Solo copia estática. | Más o menos filas, valores dinámicos, barras de progreso, minigráficos, charts. |

### Alto contraste, semántica, foco

- **Alto contraste**: texto del cuerpo ≥ 4,5:1 y borde de la tarjeta ≥ 3:1 contra blanco (WCAG 2.1 AA).
- **Semántica**: un `<main>` envuelve la tarjeta; el H1 es el único encabezado; las tres filas son una `<ul>` de tres `<li>`; sin `<section>` / `<article>` / `<nav>` / `<header>` / `<footer>` que imiten chrome de producto.
- **Foco**: sin controles interactivos, así que el orden de tabulación es trivial; el H1 es el primer nodo de texto focalizable para tecnología asistiva; la explicación y la lista leen en orden de fuente. Sin skip-links, sin focus traps, sin `:focus-visible` que imite affordances de producto.
- **Idioma**: `<html lang="...">` coincide con el idioma de la explicación; sin modismos ni tono de marketing.

---

## Contrato de implementación (autorización estrecha)

Esta modificación autoriza una superficie de implementación delimitada **solo dentro** de `tools/static-export-probe/`. Nada fuera de ese directorio gana fuente, test, configuración, cableado de build o artefacto nuevo. Los cinco innegociables arriba siguen vigentes; esta sección los acota, amplía o restringe solo donde se indica explícitamente.

### Superficies autorizadas (solo locales a la sonda)

| # | Superficie | Ubicación | Restricción |
|---|---|---|---|
| 1 | `package.json` de la sonda con dependencias de Next 16 y React 19 | `tools/static-export-probe/package.json` | Limitado a la sonda; sin hoisting de workspace; sin scripts que salgan de `tools/static-export-probe/`. |
| 2 | Configuración Next de la sonda (p. ej. `next.config.*`) | `tools/static-export-probe/next.config.*` | Solo exportación estática; sin `experimental` que toque estado compartido. |
| 3 | App de la sonda que implementa el caparazón diagnóstico aprobado | `tools/static-export-probe/app/**` | Cumple el contrato visual arriba; sin cableado de producto; sin import de consumidor. |
| 4 | Script de captura que ejecuta `next build` y timing de Playwright | `tools/static-export-probe/scripts/capture.*` | Lee solo la salida de la sonda; escribe artefactos solo bajo `tools/static-export-probe/evidence/`. |

Cualquier archivo fuera de `tools/static-export-probe/` que requiera configuración o cableado debe añadirse a **Rutas de escritura prohibidas** abajo, no asumirse permitido.

### Semántica de fallo de captura

El script de captura DEBE salir con estado distinto de cero y emitir **ningún artefacto válido** cuando se cumpla cualquiera de estas condiciones:

- `next build` no puede completar: instalación de dependencias falla, deriva del lockfile, error de build, o cualquier salida de build distinta de cero.
- El timing de Playwright no está disponible: el navegador no arranca, la medición de carga/hidratación excede el tiempo, falta la traza, o la captura de timing no devuelve muestras.

Una captura fallida NO DEBE emitir un artefacto marcador de posición. Específicamente: ningún `0`, `null`, `"unknown"`, `{}` o valor proxy puede sustituir a una medición real. La única salida en caso de fallo es una salida distinta de cero y un log de error legible; cualquier resumen parcial JSON/Markdown es inválido y debe borrarse antes de salir el script.

### Rutas de escritura prohibidas

Además de todas las superficies prohibidas en **Fuera de alcance** abajo, las siguientes rutas están explícitamente prohibidas para cualquier escritura por la implementación de la sonda, el script de captura o el cableado de build:

- `web/`, `api/`, `Makefile`, `package.json` raíz del repo, `extension/manifest.json`, `tests/`, `etl/`, `src/`, `openspec/`, `documents-es/`, y cualquier ruta fuera de `tools/static-export-probe/` para fuente, test, configuración, lockfile o salida de build.
- `tools/static-export-probe/evidence/` puede recibir salida de captura **solo** cuando la captura tenga éxito (ver *Semántica de fallo de captura*).

### Estrategia de instalación determinista

El `package.json` de la sonda DEBE ir acompañado de un lockfile versionado (`package-lock.json`, `pnpm-lock.yaml`, o equivalente) bajo `tools/static-export-probe/`. El script de captura DEBE instalar con el comando determinista correspondiente a ese lockfile (`npm ci`, `pnpm install --frozen-lockfile`, o equivalente). `npm install` / `pnpm install` sin lockfile está prohibido y DEBE provocar que el script de captura salga distinto de cero antes de cualquier build o medición.

### Umbral de división de PR

Un PR que envíe la implementación autorizada DEBE dividirse en piezas más pequeñas si su diff combinado (fuentes de la sonda, configuraciones, scripts, lockfile y cualquier modificación de diseño posterior) supera las 400 líneas añadidas. Dividir es precondición de revisión, no limpieza posterior.

---

## Criterios de auditoría (inventario negativo + lista)

Corra esta lista contra el HTML/JSON regenerado de la sonda. Cada
casilla DEBE marcarse; cualquier casilla sin marcar es un defecto y
obliga a regenerar. La lista es el contrato de migración para
cualquier intercambio futuro del par proyecto/pantalla.

**Procedencia Stitch**

- [ ] ID de proyecto Stitch presente e igual a `11813286795400731874`
- [ ] ID de pantalla Stitch presente e igual a `ec543a4cec974c2e82085a5e0406334a`
- [ ] Los dos IDs aparecen juntos (mismo documento / mismo nodo JSON)

**Estructura del caparazón**

- [ ] Fondo blanco sólido (`#FFFFFF`); sin gradientes, imágenes ni superficies tintadas
- [ ] Exactamente una tarjeta centrada con borde visible
- [ ] Exactamente un `<h1>`, sin `<h2>`–`<h6>`
- [ ] Párrafo de explicación presente, neutro, nombra el rol diagnóstico
- [ ] Exactamente tres filas de estado en un único `<ul>` de tres `<li>`; solo copia estática

**Sin marca / nav / controles / datos / persistencia**

- [ ] Sin marca: sin logo, wordmark, eslogan, nombre de producto ni tokens `--primary` / `--realm-*`
- [ ] Sin navegación: sin cabecera, lateral, breadcrumb, tabs ni enlaces de pie
- [ ] Sin controles: sin botones, inputs, selects, toggles, sliders, diálogos ni menús
- [ ] Sin datos: sin taxonomía, motores de búsqueda, números de build-profile, mediciones de hidratación ni variables de entorno
- [ ] Sin persistencia: sin `localStorage` / `sessionStorage` / cookies / IndexedDB; sin analytics ni telemetría

**Sin cableado de producto**

- [ ] Sin imports desde `web/app.js`, `web/api.js`, `web/state.js` ni cualquier ruta bajo `src/modules/`
- [ ] Sin llamadas a `/api/*`; sin selectores de content-script que coincidan con la extensión

**Aislamiento de producción**

- [ ] El HTML de la sonda **no** lo sirve FastAPI; **no** se vincula a `127.0.0.1:8765`; **no** es alcanzable desde `http://localhost:8765/*` (verificado por ausencia del montaje `StaticFiles` en `api/server.py:1847` y de `extension/manifest.json::host_permissions`)
- [ ] `git branch -D docs/static-export-probe-design` más eliminación del worktree deja `origin/develop` byte-idéntico (sin residuos en fuente, tests, configuración, `openspec/` o `documents-es/`)

**Accesibilidad**

- [ ] Contraste de texto ≥ 4,5:1 contra blanco; contraste de borde ≥ 3:1
- [ ] `<html lang="...">` coincide con el idioma de la explicación
- [ ] Sin `<section>` / `<article>` / `<nav>` / `<header>` / `<footer>` imitando chrome de producto

---

## Fuera de alcance

Cualquier código fuente de aplicación, test o archivo de
configuración; cualquier cambio en `web/`, `api/`, `Makefile`,
`package.json`, `extension/manifest.json`, `tests/`, `etl/`, `src/`,
`openspec/` o `documents-es/`; cualquier cableado en FastAPI, la
extensión de Chrome, la suite de smoke o el artefacto de release;
cualquier pre-selección de la Aproximación A / B / C
(`design.md::§1` se queda **Abierta / Basada-en-evidencia**);
cualquier capa de persistencia, telemetría, analytics o script de
terceros; cualquier iteración futura del caparazón (una pantalla,
un diseño, una pasada de auditoría).

---

## Límite de rollback

Esta unidad añade solo dos archivos sin commit:

```text
tools/static-export-probe/DESIGN.md
documents-es/static-export-probe-design-es.md
```

Ambos viven en la rama `docs/static-export-probe-design`. Revertir
significa borrar ambos archivos del worktree, luego `git branch -D
docs/static-export-probe-design` más eliminación del worktree.
Ningún archivo bajo `src/`, `web/`, `api/`, `tests/`, `etl/`,
`openspec/`, `documents-es/` (excepto el espejo nuevo), `Makefile`,
`package.json` o `extension/manifest.json` resulta tocado;
`origin/develop` se restablece byte-idéntico.

---

## Conjunto de referencias

| § de este diseño | Cita |
|---|---|
| Cinco innegociables | `openspec/changes/migrate-nextjs-tailwind4/proposal-es.md::Sonda de Exportación Estática Desechable (Solo Evidencia)` |
| Estado de §1 | `openspec/changes/migrate-nextjs-tailwind4/design-es.md::§1 Decisión de frontera de responsabilidad del servidor (Next.js ↔ FastAPI)` |
| Reglas arquitectónicas | `openspec/changes/migrate-nextjs-tailwind4/specs/modular-architecture/spec-es.md::regla 7` |
| Identificadores de la sonda | Proyecto Stitch `11813286795400731874`, pantalla `ec543a4cec974c2e82085a5e0406334a` |
| Guarda de enlace con producción | Montaje `StaticFiles` en `api/server.py:1847`, `extension/manifest.json::host_permissions` |
| Guarda de consumidores | AC-21 `tests/test_smoke.py::test_search_engine_contract` (sin cambios) |
| Espejo (inglés) | `tools/static-export-probe/DESIGN.md` |

---

`status: complete (unidad de solo-diseño; sin fuente/tests/config añadidos; enlace con producción prohibido por diseño; decisión §1 sigue basada-en-evidencia)`
