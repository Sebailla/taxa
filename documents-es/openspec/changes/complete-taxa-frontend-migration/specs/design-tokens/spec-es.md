# Especificación de Design Tokens

> Dominio: `design-tokens`. Dominio nuevo. Autorizado bajo
> `complete-taxa-frontend-migration`. La sede canónica es la
> carpeta del cambio; el archivo copia este fichero literalmente
> en `openspec/specs/design-tokens/spec.md` al activarse.

## Propósito

La identidad visual de Taxa se codifica como un bloque `@theme` de
Tailwind 4 más variables CSS, migrado **byte a byte igual** desde
el bloque `<style>` ad hoc inline de `web/index.html` y el
`tailwind.config.js` legacy. Los tokens alimentan tanto las
clases utility de Tailwind como las reglas de CSS plano (p. ej.
selectores ad hoc, `@keyframes`, `.animate-spin`, cascadas con
`color-mix()`). El orden de cascada debe coincidir con el build
legacy para que el diff visual contra el fixture chromium que
captura la harness G4 de Playwright esté vacío.

El contrato preservado contra el build legacy es **paridad de
tokens**: cada token `:root`, cada clase utility y cada regla ad
hoc resuelve a una declaración no vacía.

## Requisitos

### Requisito: Bloque `@theme` de Tailwind 4 en `globals.css`

El sistema DEBE declarar el bloque completo `@theme { ... }` de
Tailwind 4 dentro de `src/app/globals.css` (o el canónico
`src/modules/design-system/infrastructure/globals.css` según la
regla 3 del spec modular-architecture) bajo `@layer base`.

#### Escenario: Cada token `:root` legacy migrado

- DADO que el bloque `:root { … }` legacy en
  `web/index.html:24–` declara cada token (p. ej.
  `--primary: #1d7ea9`, `--accent: #176587`, `--surface: #ffffff`,
  `--elevated: #bbbbbb`, `--on-surface: #333333`,
  `--on-surface-variant: #555555`, `--outline: #bbbbbb`,
  `--outline-variant: #d9d9d9`,
  `--surface-container-low: #fafafa`,
  `--surface-container: #f5f5f5`,
  `--surface-container-high: #eeeeee`, la familia `--realm-*`, la
  paleta oscura de `data-theme`, etc.)
- CUANDO el worker de apply migra el bloque a `globals.css`
- ENTONCES cada token se declara con el **mismo** nombre y el
  **mismo** valor
- Y ningún token se renombra, elimina o fusiona
- Y tanto la paleta clara (`:root`) como la oscura
  (`[data-theme="dark"]`) están presentes

#### Escenario: Las clases utility resuelven

- DADO que el build legacy usa clases utility (p. ej.
  `bg-primary`, `text-on-surface`, `border-outline-variant`,
  `bg-surface-container-lowest`, `shadow-sm`, `rounded-r-md`,
  `bg-primary-fixed`, `text-on-primary-fixed`)
- CUANDO el worker de apply migra a `@theme` de Tailwind 4
- ENTONCES cada clase utility legacy resuelve a una declaración
  CSS no vacía
- Y el bloque `@theme` aliasa los nombres existentes para que
  `--color-primary` resuelva al valor legacy de `--primary`
- Y el mismo patrón de alias aplica a cada token legacy que las
  clases utility consumen

#### Escenario: Reglas ad hoc en `@layer base`

- DADO que el build legacy lleva reglas CSS ad hoc en el bloque
  `<style>` inline de `web/index.html` — incluyendo `@keyframes`,
  `.animate-spin`, selectores con `color-mix()`, declaraciones de
  `font-family`, la regla `body { overscroll-behavior: none; … }`,
  y el reset `main > :first-child { margin-top: 0 !important; }`
- CUANDO el worker de apply migra las reglas a `globals.css`
- ENTONCES las reglas viven bajo `@layer base`
- Y el orden de fuente coincide con el bloque legacy
- Y la cascada resuelve idénticamente (sin diff visual en el
  fixture chromium)

### Requisito: Las referencias `var(--token)` del CSS plano resuelven

El sistema DEBE mantener funcionando cada regla de CSS plano que
lee un token vía `var(--name)` sin renombrar ni derivar valores.

#### Escenario: Selectores ad hoc que consumen tokens

- DADO que el CSS ad hoc del build legacy usa
  `var(--primary)`, `var(--accent)`, `var(--bg-surface)`,
  `var(--realm-coelenterata)`, etc.
- CUANDO el worker de apply audita `globals.css`
- ENTONCES cada referencia `var(--name)` resuelve a una
  declaración no vacía
- Y ningún nombre de token se ha renombrado silenciosamente (p.
  ej. `--primary` no se ha renombrado a `--color-primary` en
  reglas de CSS plano)

#### Escenario: Alias de namespace de Tailwind 4

- DADO que Tailwind 4 deriva su propio namespace `--color-*` del
  bloque `@theme`
- CUANDO el worker de apply escribe el bloque `@theme`
- ENTONCES los nombres `--primary`, `--accent`, `--bg-surface`,
  `--realm-*` resuelven mediante un alias explícito para que
  tanto la generación de clases utility como las referencias
  `var(--name)` del CSS plano vean el mismo valor

### Requisito: Familias de fuente e icono preservadas

El sistema DEBE mantener las familias de fuente e icono legacy
sin cambios.

#### Escenario: `next/font` resuelve las fuentes legacy

- DADO que el build legacy envía Raleway (sans body),
  JetBrains Mono (monospace) y Material Symbols Outlined (set de
  iconos)
- CUANDO el worker de apply conecta `next/font`
- ENTONCES Raleway es la familia del body
- Y JetBrains Mono es la familia monoespaciada
- Y Material Symbols Outlined es la familia de iconos
- Y no se introduce un nuevo set de iconos
- Y los glyphs de icono que usa el build legacy (p. ej.
  `search`, `folder_open`, `folder`, `chevron_right`,
  `expand_more`, `close`, `settings`, `help`, `science`,
  `science_off`, `download`) conservan sus nombres legacy de
  glyph

### Requisito: Test de paridad de tokens

El sistema DEBE incluir un test focalizado que enumere cada
token `:root` y cada referencia `var(--token)` del build legacy
y exija que el nuevo build los resuelva a declaraciones no
vacías.

#### Escenario: Test de enumeración de tokens

- DADO que `tests/test_design_tokens.py` es el test focalizado
- CUANDO el worker de apply ejecuta el test contra el nuevo build
- ENTONCES cada token `:root` legacy se afirma presente en
  `globals.css` con una declaración no vacía
- Y cada referencia `var(--name)` del CSS ad hoc legacy se
  afirma que resuelve
- Y el test falla ruidosamente si cualquier token se renombra,
  elimina o queda con una declaración vacía

#### Escenario: Test de enumeración de clases utility

- DADO que el footprint de clases utility del build legacy es
  enumerable
- CUANDO el worker de apply ejecuta el test focalizado
- ENTONCES cada clase utility que el build legacy emite (a través
  de cada fichero de componente que el build legacy envía)
  resuelve a una declaración CSS no vacía en el nuevo build
- Y el test falla ruidosamente si Tailwind 4 descarta
  silenciosamente una clase utility que el build legacy emite

### Requisito: Paridad de modo oscuro

El sistema DEBE preservar la paleta de modo oscuro legacy y el
toggle `data-theme`.

#### Escenario: Paleta `[data-theme="dark"]`

- DADO que el build legacy redefine la paleta bajo
  `[data-theme="dark"]` dentro del bloque `<style>` inline
- CUANDO el worker de apply migra la regla a `globals.css`
- ENTONCES `[data-theme="dark"]` redefine cada token que la
  `:root` clara declara
- Y el toggle de tema en Settings estampa / quita `data-theme` en
  `<html>` mediante el store tipado
- Y ningún token se descarta, renombra o deriva en valor dentro de
  la paleta oscura

#### Escenario: Fallback de preferencia del SO

- DADO que el usuario todavía no ha elegido un tema
- CUANDO la aplicación arranca
- ENTONCES se consulta la media query `prefers-color-scheme` del SO
- Y se estampa `data-theme="dark"` si el SO prefiere oscuro
- Y `data-theme` **no** se estampa (default claro) en otro caso
- Y no se dispara ningún parpadeo antes de que se aplique el
  estampado (el estampado vive en el `<head>` para preceder al
  primer pintado)

## Notas

- La configuración CSS-first de Tailwind 4 reemplaza a
  `tailwind.config.js`; el fichero legacy se borra en la
  activación.
- `tailwindcss`, `@tailwindcss/forms`, `autoprefixer` y `postcss`
  del `package.json` legacy se eliminan; solo se añade la
  dependencia Tailwind 4 al nuevo `package.json`.
- El bloque `:root` ad hoc en `globals.css` DEBE ir **después**
  de la capa de utilities de Tailwind 4 para mantener la última
  palabra en el orden de cascada (coincidiendo con el orden
  legacy de `web/index.html`: `<link rel="stylesheet"
  href="dist/tailwind.css" />` primero, `<style>` segundo).