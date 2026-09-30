# Spec-Driven-Roadmap

🌐 **Disponible en:** [English](README.md) · [Português](README.pt-BR.md) · [Español](README.es.md)

Creador de Roadmap y Plan de Producto compatible con el TLC Spec-Driven Framework.

Una skill de Claude Code que decide **qué construir y en qué orden**, y luego entrega el trabajo.
Convierte el alcance de un sistema — un documento existente, una entrevista cuando no tienes uno, o
una base de código existente — en un backlog de funcionalidades ordenado por dependencias, y prepara
la skill spec-driven siguiente para que pueda empezar a construir la funcionalidad uno.

Es una **precuela** del ciclo de build. Nunca escribe specs, diseños, tareas ni código.

📖 **¿Nuevo aquí? Lee primero la guía de cómo funciona:**
[English](guide/HOW-IT-WORKS.md) · [Português](guide/HOW-IT-WORKS.pt-BR.md) · [Español](guide/HOW-IT-WORKS.es.md)

## Instalación

### Como plugin (recomendado)

Funciona en cualquier SO donde corra Claude Code y es la **única vía de instalación con
actualización incorporada** — la vía de la skill simple, abajo, no se actualiza sola, así que subir
de versión ahí significa volver a ejecutar el instalador. Instala una vez y `/plugin update` la
mantiene al día:

```
/plugin marketplace add fabricandosuaideia/Spec-Driven-Roadmap
/plugin install spec-driven-roadmap@fabricandosuaideia
```

### Como skill simple

```bash
curl -fsSL https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.sh | bash
```

Se instala en `.claude/skills/spec-driven-roadmap/` dentro del proyecto actual.

Con flags — nota el `-s --`, obligatorio cuando se usa pipe hacia bash:

```bash
curl -fsSL .../install.sh | bash -s -- --global   # instala en ~/.claude/skills/
curl -fsSL .../install.sh | bash -s -- --force    # sobrescribe una instalación existente
```

### Windows

`install.sh` necesita bash, así que funciona en Git Bash y WSL. Para PowerShell nativo (5.1+, viene
con Windows 10 y posteriores) usa `install.ps1` — no necesita curl, tar, bash ni WSL:

```powershell
irm https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.ps1 | iex
```

La forma con pipe no acepta parámetros. Para `-Global` o `-Force`, descarga el archivo primero:

```powershell
irm https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.ps1 -OutFile install.ps1
.\install.ps1 -Global -Force
```

La skill en sí es markdown más ocho scripts auxiliares en Python 3 (solo biblioteca estándar), así que
es totalmente multiplataforma; solo el instalador cambia según el SO. Convierten un proyecto de
roadmap único en roadmaps por sección, revisan un roadmap, miden cuánto cuestan las ejecuciones de
agentes, imprimen solo el tramo del roadmap que necesita quien construye una feature, mantienen
pequeño el bloque de estado del roadmap, escriben las definiciones de sub-agente que dispara un loop, planifican una ejecución de la cadena y
cronometran el gate completo del proyecto; cada uno necesita un `python3` funcionando en el PATH. En Claude
Code la skill también trae un script de Workflow que construye un roadmap con un agente nuevo por rol
— constructor, probador, verificador, revisor, fusionador — y solo corre cuando lo pides. En Windows, el `python3` a secas suele ser el stub de Microsoft Store, que
abre la Store en vez de ejecutar nada: instala Python desde python.org; después su lanzador
`py -3` también funciona.

### ¿Mi roadmap está sano?

Pide — *"revisa mi roadmap"* — y la skill ejecuta sus propias sanity checks sobre lo que generó,
incluso un roadmap que creció a lo largo de varias olas. Informa qué falló, qué es advertencia y qué
no pudo juzgar; no edita nada.

Cubre dependencias hacia adelante, nombres repetidos, el presupuesto de ocho tareas, el acuerdo en
ambos sentidos entre las preguntas abiertas de cada feature y el roll-up, una fila de ledger por
tema, `uncovered: none`, que el nivel de riesgo de cada feature esté en su piso o por encima, que el `.txt` de orden de construcción coincida con el roadmap, los umbrales
de tamaño, y la unicidad de nombre contra todo otro roadmap y todo directorio `.specs/features/` —
incluida una feature construida que ningún roadmap nombra ya. Un fallo es una pregunta para ti, no un
veredicto.

La Fase 2 ejecuta las mismas comprobaciones al cerrar un roadmap; esto es para preguntar después.

### ¿Adónde fue mi cuota?

Pide — *"mide el costo de mis agentes"* — y la skill lee los transcritos de Claude Code de este
proyecto y muestra adónde fueron los tokens: por rol, por reintento, y cuánto de cada conversación es
contexto que se acumula turno tras turno. No edita nada ni ejecuta nada más. Guarda una línea base
antes de cambiar cómo corren los agentes, y compara después: un ahorro que nadie midió es una
suposición.

### ¿Qué versión tengo?

La versión vive en el campo `metadata.version` del frontmatter del propio `SKILL.md` de la skill.

Si instalaste **el plugin**, la respuesta es `/plugin update` — la única vía de instalación que se
actualiza sola.

Si instalaste **la skill simple** (`install.sh` o `install.ps1`), compara tu copia con la publicada
en `main`:

```bash
gh_version=$(curl -fsSL https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/SKILL.md | sed -n 's/^ *version: *//p' | head -1 | tr -d '"')
printf 'installed: %s\ngithub:    %s\n' \
  "$(for f in .claude/skills/spec-driven-roadmap/SKILL.md ~/.claude/skills/spec-driven-roadmap/SKILL.md; do [ -f "$f" ] && { sed -n 's/^ *version: *//p' "$f" | head -1 | tr -d '"'; break; }; done || echo 'not installed')" \
  "${gh_version:-unreachable}"
```

Imprime dos líneas — por ejemplo, una copia que quedó en una versión antigua:

```
installed: 3.1.0
github:    3.5.0
```

Esos números son ilustrativos. Lo que dice algo es la comparación entre las dos líneas, no los
valores en sí.

El comando revisa primero la instalación de **proyecto** y cae a la **global** — la misma precedencia
que aplica Claude Code cuando ambas existen — e imprime `not installed` en la primera línea cuando no
encuentra ninguna. Una segunda línea con `unreachable` significa que la descarga falló, no que estés
al día — revisa la red y vuelve a ejecutarlo. En Windows, ejecútalo desde Git Bash o WSL. Cuando las
dos líneas difieran, vuelve a ejecutar el instalador con `--force` (`-Force` en `install.ps1`).

La instalación de proyecto vive en `.claude/skills/spec-driven-roadmap/` y la global en
`~/.claude/skills/`; las dos pueden coexistir en versiones distintas, y la versión que cuenta es
siempre la de la copia que Claude Code cargó.

El [`CHANGELOG.md`](CHANGELOG.md) es el registro de qué cambió en cada versión.

## Prerrequisito

El roadmap entrega el trabajo a una skill spec-driven siguiente, que hace la construcción real. La
suposición por defecto es [`tlc-spec-lean`](https://github.com/tech-leads-club/agent-skills), la skill
spec-driven actual de Tech Leads Club; [`tlc-spec-driven`](https://github.com/tech-leads-club/agent-skills)
también está totalmente soportada, y un proyecto que ya la usa sigue con ella. Dos complementarias
valen la pena a su lado: [`tlc-discover`](https://github.com/tech-leads-club/agent-skills), que asume la
entrevista cuando aún no tienes un documento de alcance, y
[`not-your-babysitter`](https://github.com/tech-leads-club/agent-skills):

```bash
git init   # solo si esta carpeta aún no tiene control de versiones — ver nota abajo
npx @tech-leads-club/agent-skills install --skill tlc-spec-lean -a claude-code
npx @tech-leads-club/agent-skills install --skill tlc-discover -a claude-code
npx @tech-leads-club/agent-skills install --skill not-your-babysitter -a claude-code
```

> **Este instalador requiere un repositorio git — pero probablemente ya tienes uno.** Si estás
> ejecutando esto dentro de un proyecto que ya está versionado (tiene una carpeta `.git`, sin
> importar cómo llegó ahí — `git init`, `git clone`, etc.), omite la línea `git init`; el requisito
> ya está satisfecho. `git init` solo es necesario como arreglo puntual para una carpeta nueva, aún
> no versionada.
>
> Fuera de un repositorio git, el instalador imprime `✅ Successfully installed` y termina con
> código 0 sin escribir nada en `.claude/skills/` — sin error, así que el vacío pasa fácilmente
> desapercibido. Verifica con `ls .claude/skills/tlc-spec-lean` y
> `ls .claude/skills/tlc-discover` antes de continuar. (Los dos instaladores de arriba no
> tienen este requisito — funcionan en cualquier directorio, con o sin git.)

Sin una skill siguiente instalada, el roadmap igual se genera — solo se omite el paso de entrega, y
te lo indica.

## Uso

Tres puntos de entrada, según lo que ya tengas:

| Tienes | Di | Esto produce |
|---|---|---|
| Un PRD, doc de arquitectura, ADRs, export de flowchart | `generate a roadmap from docs/PRD.md` | el roadmap directamente |
| Nada, y ninguna idea clara todavía | `plan product` / `I don't know what to build yet` | `docs/PROJECT.md` vía entrevista, luego el roadmap |
| Una base de código existente, sin doc de alcance | `map this codebase into a roadmap source` | `docs/CODEBASE-SUMMARY.md`, luego el roadmap |

La salida queda en `docs/` — un `ROADMAP.md` más un `roadmap.txt` legible por máquina con el orden de
build (o un `ROADMAP-INDEX.md` con un roadmap por sección, si eliges el modo multi-sección). Cada
funcionalidad lleva un nivel de riesgo — A, B o C, derivado de su tamaño y de lo que toca — que fija
cuánta verificación y cuántos intentos recibe. La posición en el backlog vive en un bloque `## Status`
que la skill reescribe en cada seed y mantiene pequeño: lo que las ejecuciones anteriores escribieron
ahí pasa, textual, a `docs/roadmap-history.md`. El handoff que escribe en `.specs/STATE.md` se mantiene
pequeño igual — el viejo, y las copias viejas que las ejecuciones dejaron a su lado, van a ese mismo archivo.

Al terminar la ejecución, la skill te pregunta cómo quieres construir y te entrega un prompt con los
nombres y rutas ya resueltos. Pégalo en una sesión nueva.

- **A — una funcionalidad a la vez.** Con `tlc-spec-lean` dice:

  ```
  specify feature <name> — create it at `.specs/features/<name>/` using that exact directory name.
  Plan source: run `python3 .claude/skills/spec-driven-roadmap/scripts/feature-brief.py <name>` — it prints the
  entry from docs/ROADMAP.md, its risk tier and what that tier sets (follow it), the questions naming it and docs/ROADMAP.md `## Cross-Cutting Decisions`,
  which are settled before planning: do not re-decide what they answer. Do not open docs/ROADMAP.md whole;
  if the script cannot run, read only its `### <name>` entry and the lines naming <name>.
  ```

  El constructor lee solo la porción del roadmap de su funcionalidad, nunca el archivo entero: cada
  turno de un agente vuelve a leer lo que ya leyó.
- **B — un `/loop` sobre un roadmap**, sin supervisión. La sesión del loop solo coordina: cada
  funcionalidad la construye un sub-agente nuevo y la verifica otro, y la skill escribe
  `.claude/agents/roadmap-*.md` para que cada rol corra con su propio esfuerzo. Toda pregunta abierta
  de ese roadmap se cierra contigo antes, porque después nadie estará ahí para responder.
- **C — una ejecución en pipeline, solo Claude Code.** Un script de Workflow que la skill incluye
  construye el roadmap con un agente nuevo por rol — constructor, un probador que ejecuta tu gate una
  vez, el verificador, un revisor para el nivel de riesgo A, un integrador, y tu barrera del lote
  (`barrierGate`) si dejas la suite entera para ella — y devuelve una línea por funcionalidad.
  Confirmas los comandos de gate una sola vez; un gate más largo que los 10 minutos de un comando se
  ejecuta desacoplado y se espera; `bench-gate.py` puede medir su tiempo por ti.

La [guía](guide/HOW-IT-WORKS.es.md) explica qué cede cada opción a cambio.

**Modo gestor — el backlog entero, sin nadie mirando.** En un proyecto multi-sección, en Claude Code,
puedes pedir el *"manager mode"* (modo gestor): un Workflow recorre cada sección pendiente, en el
orden de construcción, descompone cada una justo antes de construirla — **decidiendo él mismo las
preguntas abiertas y marcando cada decisión como `Decided by the manager`** para que la revises — y
la construye con el pipeline de la opción C. Solo se ejecuta con tu delegación por escrito
(`manager.delegation` en `docs/process/pipeline.json`), se detiene antes de las secciones que
reserves (`stopAt`), ante una barrera en rojo, y nunca construye sobre una sección que no terminó.
Fuera del modo gestor, la skill nunca decide por ti. Dos niveles, como permisos más estrechos o más
amplios: `decide` se detiene cuando algo se rompe y te espera; `unblock` también hace el triaje de una
barrera en rojo por script y la repara, con un verificador independiente antes de cualquier merge.
Experimental.

## Actualizar un proyecto que ya usa la skill

Los proyectos nuevos no necesitan nada de esto. Un proyecto que planificó una versión anterior recibe
el comportamiento nuevo en una sola ejecución:

1. Instala la nueva versión en ese proyecto — vuelve a ejecutar el instalador, o `/plugin update` si es un plugin.
2. En ese proyecto, pide *"upgrade this project"* (o escribe `/spec-driven-roadmap upgrade this project`).

Entonces la skill guarda una línea base de costos a partir de las transcripciones del propio proyecto
(`docs/process/cost-baseline.json`), revisa el roadmap con el linter, vuelve a ejecutar su seed — que
mueve el `## Status` viejo y el handoff viejo, copias incluidas, a `docs/roadmap-history.md` — ofrece reemplazar las
líneas puente antiguas en tu `CLAUDE.md` (solo si dices que sí) y pregunta cómo quieres construir.
Nunca regenera el roadmap ni renombra una funcionalidad. Puedes pedirle a Claude Code ambos pasos en
una frase: *"reinstall spec-driven-roadmap in this project, then upgrade this project"*. Cuando ya
haya algunas funcionalidades construidas, pide otra vez *"measure my agent cost"*: la comparación con
esa línea base es la única prueba de que la actualización ahorró algo.

Dos cosas a tener en cuenta. Los tipos de sub-agente de `.claude/agents/` se cargan al iniciar una
sesión en el proyecto, así que abre una sesión nueva después de que la opción B los escriba. Y un
`CLAUDE_CODE_EFFORT_LEVEL` definido en tu entorno anula el esfuerzo que fija cada uno de ellos.

## Trabajar en la propia skill

[`CONTRIBUTING.md`](CONTRIBUTING.md) — preparación del entorno, y los dos directorios que un clon no
recibe. [`CLAUDE.md`](CLAUDE.md) — las reglas de trabajo que un agente sigue aquí.
[`benchmark/`](benchmark/) — un fixture congelado con siete ambigüedades plantadas, una clave de
respuestas, y un marcador por versión.

## Cómo encaja con las skills TLC

Las dos son dueñas de archivos distintos y nunca chocan:

- **Esta skill** es dueña de `docs/` — los roadmaps, el orden de build, el estado del backlog, su
  historial (`docs/roadmap-history.md`) y la configuración del pipeline (`docs/process/pipeline.json`,
  opción C). Con la opción B y sub-agentes también escribe `.claude/agents/roadmap-*.md`.
- **La skill posterior** — `tlc-spec-lean` por defecto, `tlc-spec-driven` también soportada — es dueña
  de `.specs/`: planes o specs, checks o tareas, reportes de verificación, decisiones.

La única escritura dentro de `.specs/` es el `## Handoff` de `.specs/STATE.md`, en el esquema de
campos propio de esa skill, apuntando de vuelta al roadmap. La finalización de funcionalidades se lee
del reporte de cada una (`verification.md` para `tlc-spec-lean`, `validation.md` para
`tlc-spec-driven`) y del gate de finalización de esa skill, nunca se rastrea a mano — así que las dos
nunca discrepan sobre qué está terminado.
