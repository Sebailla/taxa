# Especificación de Hidratación del Estado del Navegador

> Dominio: `browser-state-hydration`. Dominio nuevo. Autorizado
> bajo `complete-taxa-frontend-migration`. La sede canónica es la
> carpeta del cambio; el archivo copia este fichero literalmente
> en `openspec/specs/browser-state-hydration/spec.md` al
> activarse.

## Propósito

El estado local del navegador (`theme`, `tree-source`,
`last-taxon-id`, `kebab-open-id`) se migra desde el singleton
legacy `web/state.js` a un **store tipado** con un sitio de
lectura + un sitio de escritura por clave. Las lecturas de
storage suceden dentro de `useEffect` detrás de una bandera
`mounted` para que el primer pintado tome como default el estado
vacío y la guardia de hidratación de React nunca se dispare. El
contrato preservado contra el build legacy es **mutación de
estado determinista y de sitio único** — cada preferencia
sobrevive a una recarga de página, cada clave tiene exactamente
un dueño en el árbol de fuentes y el store tipado emite eventos
tipados para que los suscriptores no tengan que parsear
strings crudos de `localStorage`.

## Requisitos

### Requisito: Store tipado con un sitio de lectura + un sitio de escritura por clave

El sistema DEBE definir un store tipado que posea cuatro claves
de `localStorage` y exponga exactamente un sitio de lectura y un
sitio de escritura por clave.

#### Escenario: Forma del store

- DADO que el worker de apply escribe
  `src/modules/browser-state/{store,keys,defaults}.ts`
- CUANDO el store se inicializa
- ENTONCES expone las cuatro claves de abajo con los tipos
  listados
- Y cada clave tiene exactamente una función `read` (tipada) y
  una función `write` (tipada) exportadas desde el barrel
  público

| Clave (lógica) | Clave `localStorage` | Tipo | Default |
| --- | --- | --- | --- |
| `theme` | `taxa.settings.theme` | `"light" \| "dark"` | Fallback a `prefers-color-scheme` del SO, `light` si no está disponible |
| `tree-source` | `taxa.tree.source` | `"col" \| "worms" \| "freshwater"` | `"col"` |
| `last-taxon-id` | `taxa.tree.lastTaxonId` | `number \| null` | `null` |
| `kebab-open-id` | `taxa.tree.kebabOpenId` | `number \| null` | `null` |

#### Escenario: Un sitio de lectura por clave

- DADO que el store tipado está en ámbito
- CUANDO el worker de apply greps `src/modules/browser-state/`
  buscando llamadas `localStorage.getItem(...)`
- ENTONCES existen exactamente cuatro sitios de llamada — uno
  por clave
- Y cada sitio lee la clave de `localStorage` correspondiente
- Y ningún otro módulo (`src/modules/taxonomy/**`,
  `src/modules/research/**`, `src/modules/app-shell/**`,
  `src/modules/design-system/**`) lee `localStorage`
  directamente

#### Escenario: Un sitio de escritura por clave

- DADO que el store tipado está en ámbito
- CUANDO el worker de apply greps `src/modules/browser-state/`
  buscando llamadas `localStorage.setItem(...)` y
  `localStorage.removeItem(...)`
- ENTONCES existen exactamente cuatro sitios de llamada — uno
  por clave
- Y cada sitio escribe la clave de `localStorage` correspondiente
- Y ningún otro módulo escribe `localStorage` directamente
- Y `removeItem` se invoca desde el mismo módulo que posee el
  sitio de escritura (p. ej. el control reset-tree-width en
  Settings delega en el store)

### Requisito: Guardia de hidratación contra mismatch servidor / cliente

El sistema DEBE diferir cada lectura de `localStorage` hasta
**después** del primer pintado, detrás de una bandera `mounted`,
para que la guardia de hidratación de React nunca se dispare.

#### Escenario: Primer pintado con default de estado vacío

- DADO que el árbol React se monta por primera vez
- CUANDO se dispara el render inicial
- ENTONCES la bandera `mounted` es `false`
- Y cada sitio `read` devuelve el default tipado (no el valor
  de `localStorage`)
- Y la estructura del árbol toma como default el estado vacío
- Y la URL todavía no refleja un `last-taxon-id`

#### Escenario: `useEffect` rehidrata y dispara un render posterior

- DADO que el primer pintado completó con el estado vacío
- CUANDO corre el `useEffect` del worker de apply
- ENTONCES cada uno de los cuatro sitios `read` se invoca
  exactamente una vez
- Y el store tipado rehidrata el slot de estado correspondiente
- Y un render posterior aplica el estado rehidratado
- Y la URL se actualiza al taxón del `last-taxon-id` si hay uno
  almacenado
- Y el tree-source activo, el tema y el kebab-open-id
  coinciden con los valores almacenados

#### Escenario: Sin advertencia de hidratación en la consola del navegador

- DADO que se carga el fixture chromium
- CUANDO el worker de apply inspecciona la consola del navegador
  tras el ciclo de primer pintado + rehidratación
- ENTONCES no se dispara ninguna advertencia de hydration
  mismatch de React
- Y no se dispara ninguna advertencia
  `Warning: Text content did not match`
- Y no se dispara ninguna advertencia
  `Warning: Expected server HTML to contain`

### Requisito: Suscriptores tipados

El sistema DEBE exponer una API de suscriptores tipada para que
los consumidores (`AppShell`, el árbol, el panel de detalle, la
vista de ajustes) puedan escuchar cambios sin re-leer
`localStorage`.

#### Escenario: `subscribe` devuelve un unsubscribe

- DADO que un consumidor se suscribe a una de las cuatro claves
- CUANDO el store tipado muta la clave
- ENTONCES el suscriptor del consumidor se dispara
  síncronamente con el nuevo valor tipado
- Y el consumidor puede des-suscribirse mediante el callback
  devuelto
- Y ningún consumidor re-lee `localStorage` directamente para
  enterarse del cambio

#### Escenario: Los suscriptores no se fugan entre montajes

- DADO que un componente consumidor se monta, se suscribe y
  luego se desmonta
- CUANDO el consumidor se desmonta
- ENTONCES el suscriptor se elimina de la lista de listeners del
  store
- Y ningún listener obsoleto se dispara después del desmontaje

### Requisito: Seguridad ante cuota / navegación privada

El sistema DEBE tragar excepciones de `localStorage` (modo
privado, cuota excedida) y caer al default tipado.

#### Escenario: `localStorage` lanza en lectura

- DADO que `localStorage.getItem` lanza (navegación privada)
- CUANDO se dispara un sitio `read`
- ENTONCES el store devuelve el default tipado
- Y no se propaga ninguna excepción no capturada
- Y la aplicación continúa renderizando con el estado vacío

#### Escenario: `localStorage` lanza en escritura

- DADO que `localStorage.setItem` lanza (cuota excedida, modo
  privado)
- CUANDO se dispara un sitio `write`
- ENTONCES el store traga la excepción
- Y el estado en memoria aún se actualiza (para que la UI
  refleje el cambio en la sesión actual)
- Y la siguiente recarga de página vuelve al default tipado (no
  ocurrió una escritura persistente)

### Requisito: Affordance de reset / clear

El sistema DEBE exponer una affordance tipada `reset` que
limpie cada clave a su default tipado y elimine las entradas
correspondientes de `localStorage`.

#### Escenario: Reset limpia cada clave

- DADO que el usuario dispara la affordance de reset desde la
  vista de ajustes
- CUANDO se dispara el `reset()` del store tipado
- ENTONCES cada una de las cuatro claves se establece a su
  default tipado
- Y cada entrada de `localStorage` se elimina
- Y los suscriptores se disparan síncronamente con los nuevos
  defaults
- Y la UI re-renderiza para reflejar el estado vacío

#### Escenario: Reset persiste entre recargas

- DADO que el usuario disparó `reset()` y luego recargó la página
- CUANDO el worker de apply inspecciona `localStorage`
- ENTONCES ninguna de las cuatro claves `taxa.*` está presente
- Y el estado rehidratado es el default tipado para cada slot

## Notas

- Las cuatro claves en este spec son la lista canónica. La clave
  legacy `taxa.fex.treeWidth` (usada por el splitter) está
  **fuera del alcance** de este dominio y queda en propiedad del
  módulo file explorer — la fase de apply no debe mover esa
  clave al store tipado bajo este spec.
- El barrel `src/modules/browser-state/index.ts` exporta solo las
  cuatro funciones `read`, las cuatro funciones `write`, la
  función `subscribe`, la función `reset`, los defaults tipados y
  el tipo listener tipado. **No** se exporta ningún getter /
  setter crudo de `localStorage`.
- La regla 4 del spec modular-architecture sigue aplicando: la
  capa de **dominio** de `browser-state` son tipos TypeScript
  planos (sin `localStorage`, sin `window`, sin `document`); la
  capa de **infraestructura** de `browser-state` posee las
  llamadas reales a `localStorage`; las capas de **presentación**
  / **aplicación** de `browser-state` consumen solo la API
  tipada.