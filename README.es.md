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

Funciona en cualquier SO donde corra Claude Code, y te da `/plugin update`:

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

La skill en sí es markdown puro y totalmente multiplataforma; solo el instalador cambia según el SO.

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

Luego, entrega al ciclo de build:

```
specify feature <name> — spec source: docs/ROADMAP.md
```

## Cómo encaja con tlc-spec-driven

Las dos skills son dueñas de archivos distintos y nunca chocan:

- **Esta skill** es dueña de `docs/` — el roadmap, el orden de build, el estado del backlog.
- **tlc-spec-driven** es dueña de `.specs/` — specs, diseños, tareas, reportes de validación, decisiones.

La única superficie compartida es una escritura en el `## Handoff` de `.specs/STATE.md`, en el
esquema de campos propio de esa skill, apuntando de vuelta al roadmap. La finalización de
funcionalidades se lee de `.specs/features/<name>/validation.md`, nunca se rastrea a mano — así que
las dos nunca discrepan sobre qué está terminado.
