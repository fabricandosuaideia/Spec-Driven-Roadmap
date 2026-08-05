# Cómo Funciona Spec-Driven Roadmap

*Una guía en lenguaje simple, para humanos. Si quieres las reglas exactas que sigue la skill, lee
[`SKILL.md`](../SKILL.md) — esta página es la versión amigable.*

Otros idiomas: [English](HOW-IT-WORKS.md) · [Português](HOW-IT-WORKS.pt-BR.md)

## En una frase

Esta skill descubre **qué construir y en qué orden** — nunca escribe código, specs ni tests.
Piénsala como el paso que ocurre *antes* de entregar una feature a tu skill de build
(`tlc-spec-driven` por defecto): convierte lo que ya tengas — un documento, una idea, o un código
existente — en un backlog ordenado, y luego se hace a un lado.

## Cómo activarla

Dos formas, ambas funcionan igual:

**1. Simplemente habla con Claude en texto libre.** Sin sintaxis especial. Cualquiera de estas
frases la activa:

- "generate a roadmap from docs/PRD.md"
- "plan product"
- "I don't know what to build yet, help me figure it out"
- "map this codebase into a roadmap source"
- "decompose this architecture into features"

**2. Usa el comando de barra**, si prefieres ser explícito:

- Instalada como skill simple (método `curl`/`install.ps1`): `/spec-driven-roadmap`
- Instalada como plugin (`/plugin install`): `/spec-driven-roadmap:spec-driven-roadmap`

De cualquier forma, una vez iniciada, es solo conversación — respondes sus preguntas y ella hace el
resto.

## Las tres formas de empezar (elige según lo que ya tengas)

Nunca necesitas preparar un archivo de antemano. Di lo que sea cierto para tu caso, o simplemente
empieza a hablar y ella preguntará.

### A — "Ya tengo un documento"

Tienes un PRD, un documento de arquitectura, un conjunto de ADRs, o un flowchart exportado. Di algo
como *"generate a roadmap from docs/PRD.md"*. La skill lo lee, hace un par de preguntas de
confirmación (qué skill de build usas, si quieres un roadmap único o varios), y lo descompone.

### B — "No tengo nada escrito, y ni siquiera sé bien qué construir"

Di *"plan product"* o *"I don't know what to build yet"*. La skill te entrevista — una pregunta a
la vez, nunca una lista entera de golpe:

1. ¿Qué estás construyendo?
2. ¿Para quién es, y qué problema resuelve?
3. ¿Cuál es la versión más pequeña que ya es útil?
4. ¿Qué queda explícitamente fuera de alcance por ahora?
5. ¿Alguna restricción rígida? *(opcional)*
6. ¿Qué stack técnico, si ya lo sabes? *(opcional)*

Ella escribe tus respuestas en `docs/PROJECT.md` por ti — nunca escribes ese archivo a mano — y
luego lo descompone, igual que el camino A.

### C — "Tengo código, pero nada que describa qué hace"

Di *"map this codebase into a roadmap source"*. La skill verifica si tu skill de build (o la skill
`codenavi`) ya tiene un mapeo del código que pueda reutilizar; si no, hace un escaneo ligero — lo
suficiente para saber qué ya existe y qué probablemente falta, no una auditoría profunda de
arquitectura. Escribe `docs/CODEBASE-SUMMARY.md`, pregunta qué quieres agregar a continuación, y
descompone desde ahí.

## Una pregunta más que siempre hace, sin importar el camino

**¿Un solo roadmap, o varios?** Para un proyecto pequeño a mediano, una lista única
(`docs/ROADMAP.md`) es más simple. Para un sistema grande con fronteras internas reales, dividir en
varios roadmaps (`docs/ROADMAP-INDEX.md` + un archivo por sección) permite razonar sobre — o
construir — cada parte de forma algo independiente. La skill presenta el trade-off y pregunta; no
necesitas decidir esto antes de empezar.

## Qué obtienes, en disco

| Archivo | Cuándo |
|---|---|
| `docs/ROADMAP.md` + `docs/roadmap.txt` | Siempre (modo roadmap único) |
| `docs/ROADMAP-INDEX.md` + un `ROADMAP-<slug>.md`/`roadmap-<slug>.txt` por sección | Si elegiste varios roadmaps |
| `docs/PROJECT.md` | Solo si pasaste por la entrevista (camino B) |
| `docs/CODEBASE-SUMMARY.md` | Solo si mapeó tu código (camino C) |
| `.specs/STATE.md` (una línea actualizada) | Solo si tu skill de build está confirmada/instalada — este es el handoff |

El propio archivo de roadmap contiene, por feature: un objetivo, de qué depende, una estimación
honesta de tareas (≤8 — si una feature necesita más, se divide), qué dimensiones "delicadas" están
presentes (auth, persistencia, llamadas externas, etc.), y cualquier pregunta abierta que no pudo
responder por ti. Cierra con una tabla de cobertura que prueba que nada quedó fuera.

## Un ejemplo real

Dado un PRD de dos párrafos para un rastreador de tareas compartido muy simple, sin detalles de
autenticación especificados, una ejecución produjo esto (resumido):

```markdown
# TinyTasks — Roadmap

### tt-create-task
- Objective: Let a team member create a task with a title and an assignee.
- Depends on: —
- Task estimate: 5
- Open questions:
  - How are teams and users (task assignees) identified for v1 — is there a
    pre-existing auth/team system, or does one need to be built here? — status: open

### tt-complete-task
- Depends on: tt-create-task
...

## Coverage
| Scope-unit | Disposition |
|---|---|
| S1 | tt-create-task |
| S2 | tt-complete-task |
| S3 | tt-list-open-tasks |
`uncovered: none (0 deferred, 0 pre-existing, listed above)`
```

Nota que no adivinó cómo funciona la pertenencia a equipos — el PRD nunca lo dijo, así que lo marcó
como pregunta abierta y **se negó a entregar la primera feature** hasta que eso se responda. Así es
por diseño: nunca decide algo ambiguo en tu lugar.

## Qué pasa después

Cuando el roadmap está listo y tu skill de build está instalada, la skill confirma que el trabajo de
planificación terminó y pregunta **cómo quieres construirlo**. Dos opciones:

**A — una feature a la vez.** Recibes el comando solo de la siguiente feature, lo ejecutas, y vuelves
cuando pase:

```
specify feature `tt-create-task` — spec source: docs/ROADMAP.md
```

**B — todo el roadmap en un loop.** Recibes un prompt que empieza con `/loop` (el comando de loop de
tu propio CLI — Claude Code, Cursor y OpenCode tienen uno) y que no se detiene hasta que todas las
features del backlog estén verificadas. Como un loop corre sin supervisión y no tiene a quién
preguntar, esta opción exige un roadmap con **cero preguntas abiertas** — así que la skill primero lee
el roadmap completo buscando huecos, te entrevista hasta que toda pregunta abierta quede respondida,
escribe las respuestas de vuelta, y luego relee los archivos desde el disco para confirmar que no
quedó nada abierto. Solo entonces te entrega el prompt.

⚠️ **En ambos casos, ejecuta ese prompt en una sesión de chat nueva, con contexto limpio** — no en la
sesión que generó el roadmap. La propia skill te lo va a advertir. La skill de build relee todo lo que
necesita de `.specs/STATE.md` y de los archivos del roadmap en disco; reutilizar la sesión de
planificación solo arriesga que trabaje desde la conversación recordada en vez de los archivos
escritos, y arranca la construcción con el presupuesto de contexto ya gastado.

Ese prompt es lo último que hace esta skill. De ahí en adelante, todo el ciclo de build — spec,
diseño, tareas, implementación, verificación — pertenece por completo a tu skill de build
(`tlc-spec-driven` por defecto). Incluso en modo loop, quien conduce esa skill es tu CLI; esta ya se
detuvo. No vuelve a intervenir hasta que le pidas generar o actualizar un roadmap.

## Lo que deliberadamente *no* hace

- Nunca escribe `spec.md`, `design.md`, `tasks.md`, ni código de aplicación.
- Nunca avanza por las features sola — sin avance automático. Sí puede *escribirte* un prompt
  `/loop`, pero ejecutarlo es tarea de tu CLI, en tu sesión, después de que esta skill ya se detuvo.
- Nunca adivina una ambigüedad — pregunta, o la registra como pregunta abierta y bloquea el handoff
  hasta que se resuelva.
- Nunca vuelve a derivar lo que otra skill ya mapeó — si tu skill de build (o `codenavi`) ya
  documentó el código, lo reutiliza en vez de escanear de nuevo.

## Preguntas frecuentes

**¿Necesito crear algún archivo antes de usarla?**
No. Ni siquiera el roadmap — eso es lo que ella produce. Si ya tienes un documento, es opcional
pero ayuda; si no, te entrevista.

**¿El roadmap es el único archivo obligatorio?**
Es el único que toda la cadena realmente necesita para empezar a moverse — y ni siquiera eso lo
exige estrictamente tu skill de build (puede especificar una feature a partir de una conversación
simple, sin ningún archivo previo). El valor del roadmap es decidir *qué* y *en qué orden* de
antemano, en vez de improvisar feature por feature.

**¿Cómo sé si es esta skill o mi skill de build la que está activa?**
Por lo que está pasando: si está decidiendo qué construir y en qué orden, es esta skill. En el
momento en que ves `spec.md`, `design.md`, `tasks.md`, o código real siendo escrito, es tu skill de
build — esta ya se hizo a un lado.

**¿Y si ya tengo un roadmap y solo quiero agregar más?**
Dilo — "add this new section to the roadmap" o algo similar. Reutiliza lo que ya existe en vez de
empezar de cero, y nunca renombra ni reordena features que ya fueron construidas.
