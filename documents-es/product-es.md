# Producto

<!-- impeccable:product-schema 1 -->

## Plataforma

web

## Usuarios

Investigadores taxonómicos y gestores de colecciones que necesitan explorar registros taxonómicos, evidencia de respaldo y archivos científicos asociados.

## Propósito del producto

Taxa permite explorar información taxonómica y su evidencia científica en un único flujo de trabajo. El éxito consiste en que las personas usuarias puedan pasar de un taxón a búsquedas y materiales relevantes sin perder el contexto.

## Posicionamiento

Taxa conecta taxonomía, búsqueda orientada a evidencia y archivos científicos en una experiencia de exploración coherente, en lugar de tratarlos como herramientas desconectadas.

## Contexto operativo

Las personas usuarias trabajan en un navegador con jerarquías taxonómicas, enlaces de búsqueda y material de archivos. La sonda de exportación estática desechable es un fixture interno de evidencia y es inalcanzable desde producción.

## Capacidades y restricciones

- El producto sirve tanto a flujos de investigación como de gestión de colecciones.
- El runtime de producción activo sigue siendo la experiencia actual servida por FastAPI hasta una futura decisión de frontera revisada.
- La exportación estática no queda seleccionada por la sonda de evidencia desechable.
- La sonda debe permanecer aislada de consumidores de producción, rutas de API y estado persistido de usuario.

## Evidencia disponible

- Flujos existentes de jerarquía taxonómica, motores de búsqueda y exploración de archivos en el repositorio.
- Un diseño Stitch para la sonda de evidencia: proyecto `11813286795400731874`, pantalla `ec543a4cec974c2e82085a5e0406334a`.
- No existe una afirmación de evidencia terminada de exportación estática, paridad o Lighthouse.

## Principios del producto

- Preservar el contexto científico durante la exploración taxonómica.
- Hacer descubribles la evidencia y el material asociado sin inventar afirmaciones.
- Mantener reversibles los cambios de arquitectura hasta validarlos con evidencia comparable.
- Separar los diagnósticos desechables del comportamiento de producción.

## Accesibilidad e inclusión

WCAG 2.2 AA es el objetivo durable de accesibilidad para las superficies web.
