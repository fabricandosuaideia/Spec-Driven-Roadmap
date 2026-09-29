# Cómo Funciona Spec-Driven Roadmap

*Una guía en lenguaje simple, para humanos. Si quieres las reglas exactas que sigue la skill, lee
[`SKILL.md`](../SKILL.md) para el mapa y [`references/`](../references/) para los procedimientos en
sí — cuando esos dos no coinciden, manda el archivo de referencia. Esta página es la versión
amigable.*

*¿No sabes qué versión tienes instalada? Mira
[**¿Qué versión tengo?**](../README.es.md#qué-versión-tengo) en el README.*

Otros idiomas: [English](HOW-IT-WORKS.md) · [Português](HOW-IT-WORKS.pt-BR.md)

## En una frase

Esta skill descubre **qué construir y en qué orden** — nunca escribe código, specs ni tests.
Piénsala como el paso que ocurre *antes* de entregar una feature a tu skill de build
(`tlc-spec-lean` por defecto, `tlc-spec-driven` también soportada): convierte lo que ya tengas — un documento, una idea, o un código
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
- "revisa mi roadmap" *(una lectura — mira [Preguntar si tu roadmap está sano](#preguntar-si-tu-roadmap-está-sano))*

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

**Se detiene apenas tu visión, tus usuarios y los límites del MVP están lo bastante claros como para
descomponer desde ahí** — así que no toda ejecución hace las seis preguntas, y se salta cualquiera
que ya hayas respondido antes en la conversación. Respuestas breves están bien; a este documento se
le permite ser delgado. Ella escribe tus respuestas en `docs/PROJECT.md` por ti — nunca escribes ese
archivo a mano — y luego lo descompone, igual que el camino A.

**Si `tlc-discover` está instalada, ella hace esta entrevista en su lugar** — va más a fondo, y termina
con un veredicto sobre si conviene construir siquiera. Un diseño que confirmó pasa a ser la fuente,
exactamente como en A; uno que rechazaste detiene la ejecución, porque no hay nada que descomponer;
un borrador nunca se descompone.

### C — "Tengo código, pero nada que describa qué hace"

Di *"map this codebase into a roadmap source"*. La skill verifica si tu skill de build (o la skill
`codenavi`) ya tiene un mapeo del código que pueda reutilizar; si no, hace un escaneo ligero — lo
suficiente para saber qué ya existe y qué probablemente falta, no una auditoría profunda de
arquitectura.

Después, en este orden: te pregunta directamente qué quieres agregar o cambiar — un backlog nunca se
infiere de observaciones sobre deuda técnica, así que esa respuesta es su única fuente —, pone dos
listas **en el chat** para que las corrijas (**Capabilities Already Built** y
**Gaps / Likely Next Work**), y solo cuando las confirmas escribe `docs/CODEBASE-SUMMARY.md`.
Corregir esas listas vale el minuto que toma: todo lo que quede mal archivado como ya construido
queda excluido del roadmap de forma permanente, y la tabla de cobertura no puede detectarlo — esa
unidad nunca llegó a enumerarse.

## Una pregunta más que hace, sin importar el camino

**¿Un solo roadmap, o varios?** Para un proyecto pequeño a mediano, una lista única
(`docs/ROADMAP.md`) es más simple. Para un sistema grande con fronteras internas reales, dividir en
varios roadmaps (`docs/ROADMAP-INDEX.md` + un archivo por sección) permite razonar sobre — o
construir — cada parte de forma algo independiente. La skill presenta el trade-off y pregunta; no
necesitas decidir esto antes de empezar. Hay una excepción: si el proyecto ya tiene un
`docs/ROADMAP-INDEX.md` o un `docs/ROADMAP.md`, el modo ya quedó fijado antes y la ejecución
continúa en él — en ese caso no se repite al inicio de la ejecución. Vuelve solo si pides cambiar el
formato (las preguntas frecuentes, abajo, cubren ese caso), o si el roadmap crece lo bastante como
para que la skill la plantee de nuevo; en cualquier caso la respuesta es tuya, y "seguir como está"
es una respuesta válida. Si existen *ambos* archivos, eso es una contradicción — la ejecución se
detiene y te pregunta cuál es el autoritativo.

## Qué obtienes, en disco

| Archivo | Cuándo |
|---|---|
| `docs/ROADMAP.md` + `docs/roadmap.txt` | Siempre (modo roadmap único) |
| `docs/ROADMAP-INDEX.md` + un par `ROADMAP-<slug>.md`/`roadmap-<slug>.txt` por sección descompuesta | Si elegiste varios roadmaps |
| `docs/PROJECT.md` | Solo si pasaste por la entrevista (camino B) |
| `docs/CODEBASE-SUMMARY.md` | Solo si mapeó tu código (camino C) |
| `.specs/STATE.md` (cuerpo de `## Handoff` reescrito) | Solo si hay algo que sembrar *y* una skill de build confirmada cuyo esquema sea legible — cuatro casos que se saltan, abajo |
| `docs/roadmap-history.md` | Siempre que la siembra reescribe el bloque de Status o el handoff: el viejo va aquí, textual, junto con las copias viejas del handoff que las ejecuciones dejaron en `.specs/STATE.md`. Un registro para personas; a ningún agente se le apunta hacia él |
| `.claude/agents/roadmap-*.md` | Solo si eliges la opción B y tu sesión puede lanzar sub-agentes |
| `docs/process/pipeline.json` | Solo si eliges la opción C (el pipeline), con el comando de gate que confirmaste |
| `docs/process/cost-baseline.json` | Solo cuando actualizas un proyecto, o le pides guardar una línea base de costos |

El propio archivo de roadmap contiene, por feature: un objetivo, de qué depende, una estimación
honesta de tareas (≤8 — si una feature necesita más, se divide), qué dimensiones "delicadas" están
presentes (auth, persistencia, llamadas externas, etc.), un **nivel de riesgo** — A, B o C, derivado de
su tamaño y de esas dimensiones, que fija cuánta verificación y cuántos intentos recibe después — y
cualquier pregunta abierta que no pudo responder por ti. Cierra con una tabla de cobertura que prueba que nada quedó fuera.

**La descomposición es perezosa.** En modo multi-sección solo la sección que pediste recibe su par
`.md`/`.txt`; las demás quedan en el índice como `NOT YET DECOMPOSED`, y la skill simplemente reporta
la siguiente acción — *"decompose section `<slug>`"*. Es deliberado: una sección descompuesta semanas
antes de construirse queda desactualizada. Agregar una sección al índice tampoco dispara un handoff,
porque una sección sin `.txt` no tiene orden de construcción de donde elegir un objetivo. Y si
corres el proyecto en olas, cada ola puede ser su propia sección — la skill pregunta por cuál
camino ir cuando llega el alcance nuevo.

**Cuatro cosas hacen que esa última escritura no ocurra**, y la skill registra cuál de ellas en la
línea `Handoff` de su propio bloque de Status: ninguna skill downstream instalada; una confirmada
pero con su esquema de handoff ilegible; trabajo real en curso; o nada que sembrar porque toda
feature descompuesta ya está lista.

**`docs/` es fijo, no configurable.** Y los archivos `.txt` son de lectura por máquina: solo nombres
de features, uno por línea, sin comentarios y sin marcadores de estado. La siembra cuenta esas líneas
para calcular el progreso, así que cualquier otra cosa ahí inflaría el total y nunca coincidiría con
una feature. El orden de construcción legible para humanos — con marcadores de incremento y todo —
vive en el `.md` del roadmap, a su lado.

## Un ejemplo ilustrativo

Dado un PRD de dos párrafos para un rastreador de tareas compartido muy simple, sin detalles de
autenticación especificados, una ejecución ilustrativa produce algo con esta forma (resumido):

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

Nota que no adivinó cómo funciona la pertenencia a equipos — el PRD nunca lo dijo, así que en su
lugar la registró como pregunta abierta. Así es por diseño: nunca decide algo ambiguo en tu lugar.

**El handoff se escribe de todas formas** — siempre que hubiera uno que escribir (ver más abajo). Esa
pregunta se copia al campo `Blockers` del Handoff, el campo `Next step` apunta a responderla en vez
de a especificar la feature, y la ejecución reporta esto como **sembrado pero bloqueado**, nunca como
"no sembrado". Lo único que se retiene es el comando de arranque para copiar y pegar, para que no
recibas uno que arrancaría una feature que no puede arrancar limpiamente.

## Las preguntas que hace antes de terminar

Antes de cerrar el roadmap, corre un barrido corto de **decisiones que valen para todo el proyecto**
— las que, sin esto, se volverían a decidir de forma distinta dentro de cada feature: borrado lógico
o físico, modelo de auth, qué pasa ante una falla parcial, política de retry e idempotencia, qué
nunca debe ir al log. Solo pregunta por los temas que tu roadmap realmente toca, y cada uno viene con
un default recomendado que puedes aceptar en una palabra. El resultado va a un bloque
llamado `## Cross-Cutting Decisions`, y toda feature se construye contra él.

**Espera un registro exhaustivo, no una lista de respuestas.** Ese bloque lleva exactamente una fila
por cada tema de la rúbrica — ninguno ausente, ninguno dos veces — y una fila se lee de una de cuatro
formas: la decisión más una línea de razonamiento; `N/A because <reason> (as of <roadmap>)` cuando
nada de lo descompuesto hasta ahora lo toca; `not decided`, apuntando a la pregunta abierta en que se
convirtió; o `deferred to feature <name>` cuando la pregunta recibió su propia feature en el orden de
construcción. Así que las filas `N/A` son el bloque funcionando, no algo que falta — la completitud
es todo su valor: tu skill de build lo lee antes de cada discusión de zona gris, así que "no está
listado aquí" tiene que significar "este proyecto no tiene ese tema" y nunca "se nos olvidó".

Un tema sin responder cae en dos lugares — la fila `not decided`, más una pregunta abierta que lleva
una línea `affects:` nombrando lo que la respuesta alcanzaría. Ese par retiene el comando de arranque
de las features que realmente alcanza; responderla las libera.

Deliberadamente **no** pregunta por todo. Las decisiones que viven dentro de una sola feature —
layout, formato de respuesta, texto de error — quedan para tu skill de build, que las pregunta
después con el código delante y las responde mejor por eso. Esas quedan listadas en un bloque
llamado `## Expected Gray Areas`, para que veas lo que viene sin tener que decidirlo ahora.

## Qué pasa después

**La pregunta "cómo quieres construirlo" solo aparece cuando de verdad se sembró algo y tu skill de
build está confirmada.** Si no, la ejecución termina con el reporte y el motivo. Seis finales se
detienen antes de la pregunta: solo corrió la Fase 1, así que hay una sección indexada pero no
descompuesta; el nombre de un roadmap se desvió de un directorio que ya está en disco; hay trabajo
real en curso; toda feature descompuesta ya está lista; no hay ninguna skill de build instalada; o sí
la hay, pero no se pudo leer su esquema de handoff. En los seis casos el roadmap queda terminado y
usable tal como está — lo que falta es el handoff, no el plan.

**Si no hay ninguna skill de build instalada, genera el roadmap de todos modos.** Las Fases 1 y 2
escriben solo en `docs/`, así que obtienes todo, y **no se crea absolutamente nada bajo `.specs/`** —
ni siquiera un `STATE.md` vacío, porque una forma adivinada es peor que un archivo ausente: la
reanudación de tu skill de build lo trataría como una foto vieja que hay que reconciliar. El motivo
queda registrado de forma duradera en la línea `Handoff` del bloque de Status, para que una ejecución
posterior pueda distinguir "nunca se sembró" de "se sembró y luego se sobrescribió". Instala la
skill, pide la siembra otra vez, y la cadena se completa **sin volver a correr la Fase 2**.

Cuando hay un objetivo y una skill confirmada, dice que el trabajo de planificación terminó y
pregunta **cómo quieres construirlo**. Dos opciones — tres en Claude Code:

**A — una feature a la vez.** Recibes el comando solo de la siguiente feature, lo ejecutas, y vuelves
cuando pase:

```
specify feature tt-create-task — create it at `.specs/features/tt-create-task/` using that exact
directory name. Plan source: run `python3 .claude/skills/spec-driven-roadmap/scripts/feature-brief.py
tt-create-task` — it prints the entry from docs/ROADMAP.md, its risk tier and what that tier sets
(follow it), the questions naming it and docs/ROADMAP.md `## Cross-Cutting Decisions`, which are
settled before planning: do not re-decide what they answer. Do not open docs/ROADMAP.md whole.
```

Esa es la forma de `tlc-spec-lean`; con `tlc-spec-driven` dice *spec* y *Discuss* en su lugar. El
constructor lee solo la porción del roadmap de su propia feature — en dos proyectos reales, una
mediana de alrededor de una décima parte de los archivos que abriría de otro modo — porque cada turno
de un agente vuelve a leer todo lo que ya leyó.

**B — un roadmap completo en un loop.** Recibes un prompt que empieza con `/loop` (el comando de loop
de tu propio CLI — Claude Code, Cursor y OpenCode tienen uno) y que no se detiene hasta que todas las
features de ese roadmap estén verificadas. Como un loop corre sin supervisión y no tiene a quién
preguntar, esta opción exige un roadmap con **cero preguntas abiertas** — así que la skill primero lee
el roadmap completo buscando huecos, te entrevista hasta que toda pregunta abierta quede respondida,
escribe las respuestas de vuelta, y luego relee los archivos desde el disco para confirmar que no
quedó nada abierto. Solo entonces te entrega el prompt. Esas respuestas se quedan en el archivo para
siempre, como el registro de qué se decidió y por qué — vale la pena tenerlas, y son también la
mayor razón de que un roadmap crezca de una ola a la siguiente.

**La sesión del loop solo coordina.** Si la sesión donde lo ejecutas puede lanzar sub-agentes (la
skill lo pregunta), cada feature la construye un sub-agente nuevo y luego la verifica otro — nunca un
hijo del propio constructor — y en la conversación del loop queda solo una línea por feature. Importa
porque una conversación vuelve a leer todo lo que contiene en cada turno: en una construcción
multi-agente real, releer contexto fue cerca de tres cuartas partes del costo. La skill escribe las
definiciones de sub-agente en `.claude/agents/` para que cada rol corra con su propio esfuerzo; el
modelo sigue siendo tuyo de elegir. Sin sub-agentes, toda la construcción ocurre en la única
conversación, y la skill te dice claramente que entonces la opción A, en una sesión nueva por
feature, es el camino más barato.

**Lo que la opción B sacrifica no es "que no queden preguntas".** El loop no elimina las zonas grises
que la skill dejó deliberadamente para tu skill de build — decide cada una con el default y **la deja
escrita**, con su justificación, en el spec de esa feature (`tlc-spec-driven`, bajo Assumptions & Open
Questions) o en su plan (`tlc-spec-lean`, bajo `## Assumptions`); revisar esas secciones después es el paso esperado, no trabajo
extra. El conteo del bloque `## Expected Gray Areas` de ese roadmap dimensiona ese trade-off por
adelantado, y es un **piso, no un techo** — solo contiene lo que encontró el barrido de
planificación, mientras que la discusión propia de cada feature genera más encima. Tampoco es un
truco: enrutar una zona gris declinada hacia el spec o el plan con el default del agente y su
justificación es el fallback documentado por cada skill.

**Dos cosas que el loop no hace, y un lugar donde se detiene.** Nunca edita, debilita, omite ni
borra una prueba para llegar a un `PASS`, y nunca registra una feature como hecha con la suite en
rojo — el `PASS` verificado es la única evidencia que produce la ejecución, y una prueba amañada para
producirlo destruye la evidencia en vez del defecto. También aprueba sus propios specs, diseños y
listas de tareas, porque no hay nadie allí para hacerlo; cada uno queda anotado como auto-aprobado en
el spec de esa feature, para que puedas encontrarlos después. Y si la misma feature sale de la
verificación sin un `PASS` dos veces, la ejecución se detiene y te avisa en vez de intentarlo otra
vez o seguir adelante — una feature que no puede pasar es lo único que el loop no resuelve solo.

**Un loop cubre un roadmap.** Si dividiste el producto en roadmaps por sección, el loop construye la
sección en la que estás — no el producto entero. Es deliberado: lo que una sección le entrega a otra
sigue siendo provisional hasta que esa sección se construya de verdad, así que el límite entre dos
secciones es donde el plan se encuentra con lo que se entregó. Es un checkpoint que vale la pena
mantener con un humano presente. Cuando la sección termina, vuelves, la skill re-siembra, y la
siguiente sección recibe su propio loop.

**C — una ejecución en pipeline, solo Claude Code.** El mismo roadmap único, construido por un script
de Workflow que la skill incluye: por feature un constructor, un probador nuevo que ejecuta tu gate
completo una vez y escribe un recibo, el verificador de tu skill de build — que reutiliza ese recibo
en vez de volver a ejecutar la suite —, un revisor para las features de nivel de riesgo A, y un
integrador que ejecuta el gate sobre el árbol exacto antes de hacer el merge. Los intentos tienen un
tope según el nivel, y al tercero se le pide nombrar el invariante que sus predecesores seguían
pasando por alto antes de escribir código. La skill te pide una sola vez el gate que toda feature debe
pasar — tu gate entero, o, si tu proyecto deja la suite entera para una barrera del lote, el gate por
feature más esa barrera (`barrierGate`), que entonces se ejecuta en la rama principal integrada y
detiene todo merge siguiente cuando queda en rojo —, porque cada PASS que registra el pipeline se
apoya en él, y puede medir el tiempo de ese comando por ti. Un gate más largo que los 10 minutos de un
comando se ejecuta desacoplado y se espera. Misma precondición que B: cero preguntas abiertas.

**Modo gestor — no es una cuarta opción, es una forma de trabajar.** A, B y C construyen un roadmap
cada una y se detienen, porque la costura entre dos secciones es donde una persona vuelve a planificar.
Cuando nadie va a estar ahí — un build que se deja corriendo día y noche —, pide el *"manager mode"*
en un proyecto multi-sección, en Claude Code. Escribes, una vez, lo que delegas (`manager.delegation`)
y qué secciones todavía te necesitan (`stopAt`). Entonces un Workflow — un script, no una
conversación, así que no pierde su misión en un contexto largo — toma cada sección pendiente en el
orden de construcción, la descompone justo antes de construirla, responde él mismo las preguntas
abiertas (la opción conservadora, marcada `Decided by the manager`) y la construye con el pipeline de
la opción C. Se detiene antes de una sección reservada o ante una barrera en rojo, y omite lo que
depende de una sección que no terminó. Después, las decisiones son tuyas para revisar: cada una queda
marcada en los roadmaps y listada en el registro de la ejecución.

⚠️ **En cualquier caso, ejecuta ese prompt en una sesión de chat nueva, con contexto limpio** — no en la
sesión que generó el roadmap. La propia skill te lo va a advertir. En una sesión nueva **el prompt
mismo es el canal**: tu skill de build vuelve a derivar lo que necesita de las rutas de ese prompt y
de los archivos del roadmap en disco. `.specs/STATE.md` se lee en un `resume work` posterior — para
eso sirve el Handoff, no para un arranque nuevo — y por eso el prompt debe pegarse íntegro, con el
nombre exacto de directorio y todo. Reutilizar la sesión de planificación solo arriesga que el agente
trabaje desde la conversación recordada en vez de los archivos escritos, y arranca la construcción
con el presupuesto de contexto ya gastado.

Ese prompt es lo último que hace esta skill. De ahí en adelante, todo el ciclo de build — spec,
diseño, tareas, implementación, verificación — pertenece por completo a tu skill de build
(`tlc-spec-lean` por defecto). Incluso en modo loop, quien conduce esa skill es tu CLI; esta ya se
detuvo. No vuelve a intervenir hasta que le pidas generar o actualizar un roadmap.

## Cómo sabe qué ya está construido

Nunca se fía de la palabra de nadie, y que un archivo exista no prueba nada. Para cada nombre del
orden de construcción lee el reporte de esa feature — `verification.md` para `tlc-spec-lean`,
`validation.md` para `tlc-spec-driven` —, ejecutando el script de gate de tu
skill de build si esa skill realmente trae uno **en disco** (un gate que no encuentra nada que comprobar nunca se lee como un pase) — mira el disco, no la documentación,
porque el conjunto de scripts de una skill cambia entre releases y una instalación se queda atrás — y
si no, leyendo el reporte exactamente con las mismas reglas. Un **PASS sin ninguna cita de evidencia
`path.ext:NN` cuenta como no hecho**, igual que una plantilla `[PASS | FAIL]` sin rellenar. Las
features que son solo pregunta son la única excepción: como no producen código, se dan por saldadas
cuando su pregunta queda respondida — o, con `tlc-spec-driven`, cuando existe un `context.md` para ellas. Y cuando hay
trabajo real en curso — algo completado o en progreso en el Handoff, o la feature nombrada en el
Handoff tiene un `spec.md` en disco y ningún PASS de verdad — **no reescribe `.specs/STATE.md` en
absoluto**: refresca su propio bloque de Status, nombra la feature en curso, y ahí se detiene. Nada
de eso se dispara si la feature que el Handoff nombra ya tiene un PASS de verdad — terminada y luego
pausada no es trabajo en curso.

## Qué aparece en el archivo y podría sorprenderte

- **Una feature que no construye nada.** Cuando una pregunta sin resolver condiciona varias features
  posteriores, puede recibir una pequeña feature propia cuyo único trabajo es conseguir esa
  respuesta. Lleva la línea literal `discharge: no code — answered open question or context.md`,
  textual, porque tres consumidores distintos dependen de ella: el test de "hecho" de la siembra, su
  elección de objetivo, y la lista de omisiones del prompt de loop.
- **Un bloque de Status arriba de tu roadmap** (o del índice, en modo multi-sección): conteos, el
  orden de construcción restante, la siguiente feature, y si el handoff se escribió — o por qué no.
  Se regenera en cada siembra, así que nunca lo edites a mano; lo que hubiera antes pasa a
  `docs/roadmap-history.md`. Una ejecución de loop agrega una línea `**Last run**:` y deja su relato
  completo en ese historial, nunca en el bloque — cada agente apuntado al bloque pagaría por ello.
- **Inglés dentro de un roadmap que no está en inglés.** La prosa sale en el idioma en que estás
  trabajando, pero los nombres de features, prefijos, slugs, nombres de archivo y **todo encabezado
  generado** siguen en inglés: son claves de lectura por máquina, componentes de ruta y nombres de
  directorio, y traducir uno rompe el handoff, los directorios `.specs/features/<name>/`, o una
  búsqueda entre archivos.

## Preguntar si tu roadmap está sano

Puedes pedirlo por sí solo, sin generar nada — *"revisa mi roadmap"*, *"¿mi roadmap está sano?"*. No
se escribe nada: la skill lee lo que produjo y te cuenta qué encontró.

Es la misma lista que la Fase 2 ejecuta al cerrar un roadmap, así que esto es para preguntar
**después** — meses más tarde, tras varias olas, cuando quieres saber si el archivo todavía se
sostiene. Comprueba que ninguna feature dependa de otra listada después de ella, que ningún nombre se
use dos veces, que ninguna feature pase el presupuesto de ocho tareas, que toda pregunta abierta de
una feature aparezca también en el roll-up *y al revés*, que la tabla de cobertura cierre sin nada
descubierto, que el `.txt` de orden de construcción siga coincidiendo con el roadmap, y que ningún
nombre de feature choque con otro roadmap o con un directorio bajo `.specs/`. También señala lo
inverso: una feature que ya construiste y que ningún roadmap nombra ya, que es como se ve un cambio
de nombre después del hecho.

Dos cosas que vale saber. **Un fallo es una pregunta, no un veredicto** — el roadmap es tuyo, y la
salida existe para leerse antes de cambiar nada. Y dice cuándo *no pudo* juzgar algo en vez de
adivinar, porque una falsa alarma sobre un backlog real cuesta más que una omisión.

Lo que no puede comprobar es la parte que necesita a una persona: si una pregunta abierta está
formulada lo bastante bien como para responderse, si una feature es de verdad un corte vertical, y si
una disposición de la tabla de cobertura es honesta. Eso sigue siendo lectura.

## Medir lo que cuestan los agentes, y actualizar un proyecto

Pide *"measure my agent cost"* y la skill lee las transcripciones de Claude Code de tu propio proyecto
y muestra adónde fueron los tokens: por rol, por reintento, por el modelo y el esfuerzo con que corrió
cada rol, y cuánto de cada conversación fue contexto acumulándose turno tras turno. No edita nada.
Guarda una línea base antes de cambiar cómo corren los agentes y compara después; un ahorro que nadie
midió es una suposición.

Un proyecto que planificó una versión anterior recibe el comportamiento nuevo pidiendo *"upgrade this
project"* tras instalar allí la nueva versión: guarda esa línea base, revisa el roadmap con el linter,
vuelve a ejecutar la siembra — que vacía el bloque de Status viejo y el handoff viejo hacia `docs/roadmap-history.md` —,
ofrece reemplazar las líneas puente antiguas en tu `CLAUDE.md` y pregunta cómo quieres construir.
Nunca regenera el roadmap.

## Lo que deliberadamente *no* hace

- Nunca escribe `spec.md`, `design.md`, `tasks.md`, ni código de aplicación.
- Nunca avanza por las features sola — sin avance automático. Sí puede *escribirte* un prompt
  `/loop`, pero ejecutarlo es tarea de tu CLI, en tu sesión, después de que esta skill ya se detuvo.
- Nunca adivina una ambigüedad — pregunta, o la registra como pregunta abierta. Esa pregunta retiene
  el comando de arranque de la **feature objetivo**, no el backlog: la pregunta propia de una feature
  bloquea esa feature, y una de alcance de proyecto bloquea solo cuando su línea `affects:` dice
  `all` o nombra al objetivo. Bloquear más ancho congelaría todo el backlog detrás de una sola
  pregunta de proyecto.
- Nunca vuelve a derivar lo que otra skill ya mapeó — si tu skill de build o `codenavi` ya documentó
  el código, lo reutiliza en vez de escanear de nuevo. Que tu skill de build tenga ese paso **depende
  de la versión** (`tlc-spec-driven` v2 lo tenía, v3.x no), así que detecta qué hay realmente
  instalado en vez de dar por supuesta una ruta.

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
Dilo — "add this new section to the roadmap" o algo similar; nunca regenera lo que ya está. Existen
dos formas de aterrizar el alcance nuevo, y la skill te plantea la elección en el momento en que ese
alcance llega.

**Extiende el roadmap que ya tienes** — lo indicado para una adición pequeña y continua. Los nombres
de features **y su orden relativo se congelan en el momento en que existe un directorio
`.specs/features/<name>/`** — no al pasar una verificación, así que un spec a medio escribir o una
ejecución fallida también congelan su feature. El alcance nuevo se agrega después de ese bloque
congelado; una feature obsoleta se marca como superseded en su lugar, nunca se borra, nunca se
renombra.

**Dale a la ola nueva su propia sección** — lo indicado cuando el trabajo nuevo es un lote distinto
y no unos pocos ítems más. El proyecto se convierte a multi-sección: lo que ya tienes pasa a ser el
roadmap de una sección, la ola nueva pasa a ser la siguiente, y un índice las ordena. El
procedimiento exacto es `Converting a single-section project to multi-section`, en
`references/index-phase.md`. La conversión la hace un pequeño script de Python 3 que viene con la
skill, así que una máquina sin `python3` no puede ejecutarla.

Por qué importa la elección: un roadmap solo te cuesta lo que se carga. Los constructores ya no lo
cargan — leen la porción de su feature mediante `feature-brief.py` —, pero cada ejecución de
planificación y cada siembra sigue leyendo el roadmap con el que trabaja, así que uno que crece ola
tras ola se arrastra a través de todas ellas. Una sección terminada nunca se vuelve a cargar entera:
el progreso se cuenta desde su `.txt` y desde el reporte de cada feature, mientras que las lecturas
puntuales en su cuerpo — el test de `discharge:`, el roll-up de `## Open Questions` — siguen
ocurriendo. En
números: cada feature cuesta unos 200-250 tokens del roadmap, así que la skill avisa cerca de 2.000
— diciendo cuántas features caben aún antes de dividir — y vuelve a plantear la pregunta de
uno-o-varios pasados unos 3.000, unas 12-15 features. Convertir renombra **archivos, no features**,
así que nada de lo ya construido se ve afectado — con una salvedad: el puntero de handoff en
`.specs/STATE.md` nombra archivos por ruta, así que queda obsoleto y la skill vuelve a ejecutar su
siembra para repararlo. Si una feature está a medio construir cuando conviertes, esa reparación
tiene que esperar a que pase, y la skill te lo dice.
