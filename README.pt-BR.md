# Spec-Driven-Roadmap

🌐 **Disponível em:** [English](README.md) · [Português](README.pt-BR.md) · [Español](README.es.md)

Criador de Roadmap e Plano de Produto compatível com o TLC Spec-Driven Framework.

Uma skill do Claude Code que decide **o que construir e em que ordem**, e então repassa o trabalho.
Ela transforma o escopo de um sistema — um documento existente, uma entrevista quando você não tem
um, ou uma base de código existente — em um backlog de features ordenado por dependência, e semeia a
skill spec-driven seguinte para que ela possa começar a construir a feature um.

É uma **prequela** do ciclo de build. Ela nunca escreve specs, designs, tasks ou código.

📖 **Novo por aqui? Leia primeiro o guia de como funciona:**
[English](guide/HOW-IT-WORKS.md) · [Português](guide/HOW-IT-WORKS.pt-BR.md) · [Español](guide/HOW-IT-WORKS.es.md)

## Instalação

### Como plugin (recomendado)

Funciona em todo SO onde o Claude Code roda, e te dá `/plugin update`:

```
/plugin marketplace add fabricandosuaideia/Spec-Driven-Roadmap
/plugin install spec-driven-roadmap@fabricandosuaideia
```

### Como skill simples

```bash
curl -fsSL https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.sh | bash
```

Instala em `.claude/skills/spec-driven-roadmap/` no projeto atual.

Com flags — note o `-s --`, que é obrigatório ao usar pipe para o bash:

```bash
curl -fsSL .../install.sh | bash -s -- --global   # instala em ~/.claude/skills/
curl -fsSL .../install.sh | bash -s -- --force    # sobrescreve uma instalação existente
```

### Windows

`install.sh` precisa de bash, então funciona no Git Bash e no WSL. Para PowerShell nativo (5.1+, vem
com Windows 10 e posteriores) use `install.ps1` — não precisa de curl, tar, bash ou WSL:

```powershell
irm https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.ps1 | iex
```

A forma via pipe não aceita parâmetros. Para `-Global` ou `-Force`, baixe o arquivo antes:

```powershell
irm https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.ps1 -OutFile install.ps1
.\install.ps1 -Global -Force
```

A skill em si é markdown puro e totalmente multiplataforma; só o instalador muda por SO.

## Pré-requisito

O roadmap repassa o trabalho para uma skill spec-driven seguinte, que faz a construção de fato. A
suposição padrão é [`tlc-spec-driven`](https://github.com/tech-leads-club/agent-skills), acompanhada
de sua skill complementar [`not-your-babysitter`](https://github.com/tech-leads-club/agent-skills):

```bash
git init   # apenas se esta pasta ainda não tiver controle de versão — veja a nota abaixo
npx @tech-leads-club/agent-skills install --skill tlc-spec-driven -a claude-code
npx @tech-leads-club/agent-skills install --skill not-your-babysitter -a claude-code
```

> **Este instalador exige um repositório git — mas você provavelmente já tem um.** Se você está
> rodando isso dentro de um projeto que já está versionado (tem uma pasta `.git`, não importa como
> ela surgiu — `git init`, `git clone`, etc.), pule a linha `git init`; o requisito já está
> satisfeito. `git init` só é necessário como correção pontual para uma pasta nova, ainda não
> versionada.
>
> Fora de um repositório git, o instalador imprime `✅ Successfully installed` e sai com código 0
> sem escrever nada em `.claude/skills/` — sem erro, então a falha passa despercebida facilmente.
> Verifique com `ls .claude/skills/tlc-spec-driven` e `ls .claude/skills/not-your-babysitter` antes
> de seguir em frente. (Os dois instaladores acima não têm essa exigência — funcionam em qualquer
> diretório, com ou sem git.)

Sem uma skill seguinte instalada, o roadmap ainda é gerado — só a etapa de handoff é pulada, e ele
avisa isso.

## Uso

Três pontos de entrada, dependendo do que você já tem:

| Você tem | Diga | Isso produz |
|---|---|---|
| Um PRD, doc de arquitetura, ADRs, export de fluxograma | `generate a roadmap from docs/PRD.md` | o roadmap diretamente |
| Nada, e nenhuma ideia clara ainda | `plan product` / `I don't know what to build yet` | `docs/PROJECT.md` via entrevista, depois o roadmap |
| Uma base de código existente, sem doc de escopo | `map this codebase into a roadmap source` | `docs/CODEBASE-SUMMARY.md`, depois o roadmap |

A saída fica em `docs/` — um `ROADMAP.md` mais um `roadmap.txt` legível por máquina com a ordem de
build (ou um `ROADMAP-INDEX.md` com um roadmap por seção, se você escolher o modo multi-seção). A
posição no backlog fica em um bloco `## Status` que é atualizado a cada execução.

Depois, repasse para o ciclo de build:

```
specify feature <name> — spec source: docs/ROADMAP.md
```

## Como se encaixa com o tlc-spec-driven

As duas skills são donas de arquivos diferentes e nunca colidem:

- **Esta skill** é dona de `docs/` — o roadmap, a ordem de build, o status do backlog.
- **tlc-spec-driven** é dona de `.specs/` — specs, designs, tasks, relatórios de validação, decisões.

A única superfície compartilhada é uma escrita no `## Handoff` do `.specs/STATE.md`, no schema de
campos próprio daquela skill, apontando de volta para o roadmap. A conclusão de features é lida de
`.specs/features/<name>/validation.md`, nunca controlada manualmente — então as duas nunca discordam
sobre o que está pronto.
