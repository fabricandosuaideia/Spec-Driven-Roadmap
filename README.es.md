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

La skill en sí es markdown más un script auxiliar en Python 3 (solo biblioteca estándar), así que es
totalmente multiplataforma; solo el instalador cambia según el SO. Ese script sirve para exactamente
una cosa — convertir un proyecto de roadmap único en roadmaps por sección — y necesita un `python3`
funcionando en el PATH. En Windows, el `python3` a secas suele ser el stub de Microsoft Store, que
abre la Store en vez de ejecutar nada: instala Python desde python.org; después su lanzador
`py -3` también funciona.

### ¿Mi roadmap está sano?

Pide — *"revisa mi roadmap"* — y la skill ejecuta sus propias sanity checks sobre lo que generó,
incluso un roadmap que creció a lo largo de varias olas. Informa qué falló, qué es advertencia y qué
no pudo juzgar; no edita nada.

Cubre dependencias hacia adelante, nombres repetidos, el presupuesto de ocho tareas, el acuerdo en
ambos sentidos entre las preguntas abiertas de cada feature y el roll-up, una fila de ledger por
tema, `uncovered: none`, que el `.txt` de orden de construcción coincida con el roadmap, los umbrales
de tamaño, y la unicidad de nombre contra todo otro roadmap y todo directorio `.specs/features/` —
incluida una feature construida que ningún roadmap nombra ya. Un fallo es una pregunta para ti, no un
veredicto.

La Fase 2 ejecuta las mismas comprobaciones al cerrar un roadmap; esto es para preguntar después.

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
suposición por defecto es [`tlc-spec-driven`](https://github.com/tech-leads-club/agent-skills), junto
con su skill complementaria [`not-your-babysitter`](https://github.com/tech-leads-club/agent-skills):

```bash
git init   # solo si esta carpeta aún no tiene control de versiones — ver nota abajo
npx @tech-leads-club/agent-skills install --skill tlc-spec-driven -a claude-code
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
> desapercibido. Verifica con `ls .claude/skills/tlc-spec-driven` y
> `ls .claude/skills/not-your-babysitter` antes de continuar. (Los dos instaladores de arriba no
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
build (o un `ROADMAP-INDEX.md` con un roadmap por sección, si eliges el modo multi-sección). La
posición en el backlog vive en un bloque `## Status` que se actualiza en cada ejecución.

Al terminar la ejecución, la skill te entrega este prompt con el nombre de la funcionalidad y las
rutas ya resueltas — pégalo en una sesión nueva para empezar la funcionalidad uno:

```
specify feature <name> — create it at `.specs/features/<name>/` using that exact directory name.
Spec source: docs/ROADMAP.md. Read docs/ROADMAP.md `## Cross-Cutting Decisions` before Discuss and
treat it as settled — do not re-decide what it answers.
```

Esa es la opción A, una funcionalidad a la vez. La opción B es un único prompt `/loop` que construye
el roadmap entero sin supervisión. Siempre se ofrece; lo que exige antes es un roadmap sin preguntas
abiertas, y la skill las cierra contigo antes de entregarte el prompt — la guía explica qué cede a
cambio.

## Cómo encaja con tlc-spec-driven

Las dos skills son dueñas de archivos distintos y nunca chocan:

- **Esta skill** es dueña de `docs/` — el roadmap, el orden de build, el estado del backlog.
- **tlc-spec-driven** es dueña de `.specs/` — specs, diseños, tareas, reportes de validación, decisiones.

La única superficie compartida es una escritura en el `## Handoff` de `.specs/STATE.md`, en el
esquema de campos propio de esa skill, apuntando de vuelta al roadmap. La finalización de
funcionalidades se lee de `.specs/features/<name>/validation.md`, nunca se rastrea a mano — así que
las dos nunca discrepan sobre qué está terminado.
