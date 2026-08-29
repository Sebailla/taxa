# Delta para modular-architecture

## Propósito

Restricción aprobada: la aplicación migrada DEBE seguir un
**monolito modular con arquitectura por capas**. Neutra respecto
al framework; toda otra capacidad DEBE mantenerse coherente.

## Reglas

1. **Monolito único** — sin servicio de frontend o backend por
   separado. Un proceso FastAPI; un origen HTTP
   `127.0.0.1:8765`; `extension/manifest.json::host_permissions`
   en `["http://localhost:8765/*"]`.
2. **Módulos por capability** — primer nivel nombrado tras
   capabilities (`research`, `taxonomy`, `design-system`,
   `browser-state`). Nombres técnicos (`controllers`, `services`,
   `repositories`, `utils`, `helpers`, `common`, `shared`,
   `misc`) NO DEBEN ser la partición de primer nivel.
3. **Cuatro capas por módulo** — **presentación**,
   **aplicación**, **dominio**, **infraestructura**, todas
   visibles por módulo.
4. **Dependencias hacia adentro** — presentación → aplicación →
   dominio; infraestructura → dominio. El dominio NO DEBE
   depender de presentación, aplicación, navegador, HTTP,
   framework ni infraestructura. La aplicación NO DEBE depender
   de presentación ni infraestructura directamente.
5. **Contratos públicos** — barrel export, `index.ts` o
   equivalente por módulo. Símbolos no exportados son privados.
   Imports cruzados profundos se rechazan en build mediante
   path-aliases o guarda de lint equivalente.
6. **Neutra respecto al framework** — reglas 1–5 rigen para cada
   enfoque candidato (Next.js estático bajo FastAPI, Next.js dev
   en otro puerto, híbrido por fases). Ninguna regla se relaja
   para encajar un framework elegido.
7. **Cumplimiento de la frontera §1** — la frontera Next.js ↔
   FastAPI elegida en `design.md::§1 Decisión` DEBE cumplir las
   reglas 1–5. Permanece basada en evidencia hasta que el diseño
   la resuelva. El diseño NO DEBE relajar ninguna regla.

## Requisitos AÑADIDOS

### Requisito: Monolito único

El sistema DEBE satisfacer la regla 1.

#### Escenario: Una sola unidad desplegable

- DADO que la migración aterriza
- CUANDO el orquestador inspecciona los artefactos desplegables
- ENTONCES existe exactamente una unidad (FastAPI sirviendo `/`
  y `/api/*`)
- Y no se requiere un segundo contenedor, grupo de procesos o
  servicio

### Requisito: Módulos por capability

El sistema DEBE satisfacer la regla 2.

#### Escenario: Los nombres se corresponden con capabilities

- DADO que la fase de diseño lista el árbol de fuentes migrado
- CUANDO una persona revisora asigna cada módulo a una línea
- ENTONCES cada nombre se lee como capability de negocio
- Y ningún nombre se lee como un vertedero técnico

### Requisito: Cuatro capas por módulo

El sistema DEBE satisfacer la regla 3.

#### Escenario: Cuatro capas presentes en cada módulo

- DADO que se inspecciona un módulo de capability
- CUANDO el orquestador enumera carpetas o archivos de capa
- ENTONCES presentación, aplicación, dominio e infraestructura
  están representadas
- Y ninguna capa se fusiona silenciosamente con otra

### Requisito: La dirección de dependencia es hacia adentro

El sistema DEBE satisfacer la regla 4.

#### Escenario: El dominio se mantiene libre de framework e I/O

- DADO que se inspecciona la capa de dominio
- CUANDO una persona revisora busca `react`, `next`, `fastapi`,
  `fetch`, `localStorage`, `document.`, `window.`, `process.` u
  objetos de petición HTTP
- ENTONCES no aparece ninguna coincidencia
- Y la capa de dominio compila y ejecuta sus tests sin arrancar
  Next.js, React, FastAPI ni ningún subsistema de I/O

#### Escenario: La aplicación no importa presentación

- DADO que se inspecciona la capa de aplicación
- CUANDO una persona revisora busca imports de módulos de
  presentación, componentes React o JSX
- ENTONCES no aparece ninguna coincidencia
- Y cualquier view-model es una estructura plana consumible por
  cualquier presentación

### Requisito: Fronteras de módulo y contratos públicos

El sistema DEBE satisfacer la regla 5.

#### Escenario: Los imports cruzados pasan por el contrato público

- DADO que el módulo A importa desde el módulo B
- CUANDO una persona revisora traza la ruta de import
- ENTONCES el import resuelve solo a través del contrato público
  de B
- Y la guarda de build rechaza cualquier import profundo en las
  carpetas privadas de B

### Requisito: La restricción aplica a cada enfoque

El sistema DEBE satisfacer la regla 6.

#### Escenario: La restricción se sostiene para cada enfoque candidato

- DADO que la propuesta enumera los Enfoques A, B y C
- CUANDO la fase de diseño evalúa cada uno
- ENTONCES las reglas 1–5 siguen siendo vinculantes
- Y el enfoque elegido se registra en `design.md::§1 Decisión`
  citando este spec

### Requisito: La frontera Next.js ↔ FastAPI debe cumplir

El sistema DEBE satisfacer la regla 7.

#### Escenario: El diseño cita el spec al cerrar la decisión

- DADO que la fase de diseño finaliza el enfoque Next.js ↔ FastAPI
- CUANDO la decisión aterriza en `design.md::§1 Decisión`
- ENTONCES la entrada cita este spec por ruta como autoridad
  arquitectónica
- Y si el diseño ve un conflicto con alguna regla, se eleva de
  vuelta a la propuesta antes de implementar