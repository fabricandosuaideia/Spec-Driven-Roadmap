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

Funciona em todo SO onde o Claude Code roda e é o **único caminho de instalação com atualização
embutida** — o caminho da skill simples, abaixo, não se atualiza sozinho, então subir de versão por
lá significa rodar o instalador de novo. Instale uma vez e o `/plugin update` mantém tudo em dia:

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

A skill em si é markdown mais um script auxiliar em Python 3 (só biblioteca padrão), então é
totalmente multiplataforma; só o instalador muda por SO. Esse script serve para exatamente uma
coisa — converter um projeto de roadmap único em roadmaps por seção — e precisa de um `python3`
funcionando no PATH. No Windows, o `python3` puro costuma ser o stub da Microsoft Store, que abre a
Store em vez de rodar qualquer coisa: instale o Python pelo python.org — depois disso o
launcher `py -3` dele também funciona.

### Meu roadmap está sadio?

Peça — *"confere meu roadmap"* — e a skill roda as próprias sanity checks sobre o que ela gerou,
inclusive um roadmap que cresceu ao longo de várias ondas. Ela reporta o que falhou, o que é aviso e
o que não conseguiu julgar; nada é editado.

Cobre dependências para frente, nomes repetidos, o orçamento de oito tasks, o acordo nos dois
sentidos entre as perguntas abertas de cada feature e o roll-up, uma linha de ledger por tema,
`uncovered: none`, o `.txt` de ordem de build batendo com o roadmap, os limiares de tamanho, e
unicidade de nome contra todo outro roadmap e todo diretório `.specs/features/` — inclusive uma
feature construída que nenhum roadmap nomeia mais. Uma falha é uma pergunta para você, não um
veredito.

A Phase 2 roda as mesmas checagens sempre que fecha um roadmap; isto aqui é para perguntar depois.

### Qual versão eu tenho?

A versão fica no campo `metadata.version` do frontmatter do próprio `SKILL.md` da skill.

Se você instalou **o plugin**, a resposta é `/plugin update` — o único caminho de instalação que se
atualiza sozinho.

Se você instalou **a skill simples** (`install.sh` ou `install.ps1`), compare sua cópia com a
publicada no `main`:

```bash
gh_version=$(curl -fsSL https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/SKILL.md | sed -n 's/^ *version: *//p' | head -1 | tr -d '"')
printf 'installed: %s\ngithub:    %s\n' \
  "$(for f in .claude/skills/spec-driven-roadmap/SKILL.md ~/.claude/skills/spec-driven-roadmap/SKILL.md; do [ -f "$f" ] && { sed -n 's/^ *version: *//p' "$f" | head -1 | tr -d '"'; break; }; done || echo 'not installed')" \
  "${gh_version:-unreachable}"
```

Ele imprime duas linhas — por exemplo, uma cópia parada em uma versão antiga:

```
installed: 3.1.0
github:    3.5.0
```

Esses números são ilustrativos. O que diz alguma coisa é a comparação entre as duas linhas, não os
valores em si.

O comando checa primeiro a instalação de **projeto** e cai para a **global** — a mesma precedência
que o Claude Code aplica quando as duas existem — e imprime `not installed` na primeira linha quando
não encontra nenhuma. Uma segunda linha com `unreachable` significa que o download falhou, não que
você está em dia — verifique a rede e rode de novo. No Windows, rode pelo Git Bash ou pelo WSL.
Quando as duas linhas divergirem, rode o instalador de novo com `--force` (`-Force` no
`install.ps1`).

A instalação de projeto fica em `.claude/skills/spec-driven-roadmap/` e a global em
`~/.claude/skills/`; as duas podem coexistir em versões diferentes, e a versão que vale é sempre a
da cópia que o Claude Code carregou.

O [`CHANGELOG.md`](CHANGELOG.md) é o registro do que mudou em cada versão.

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

Ao fim da execução, a skill entrega este prompt com o nome da feature e os caminhos já resolvidos —
cole-o em uma sessão nova para começar a feature um:

```
specify feature <name> — create it at `.specs/features/<name>/` using that exact directory name.
Spec source: docs/ROADMAP.md. Read docs/ROADMAP.md `## Cross-Cutting Decisions` before Discuss and
treat it as settled — do not re-decide what it answers.
```

Essa é a opção A, uma feature por vez. A opção B é um único prompt `/loop` que constrói o roadmap
inteiro sem supervisão. Ela é sempre oferecida; o que ela exige antes é um roadmap sem perguntas
em aberto, e a skill fecha essas perguntas com você antes de entregar o prompt — o guia explica o
que ela troca.

## Trabalhando na própria skill

[`CONTRIBUTING.md`](CONTRIBUTING.md) — preparação do ambiente, e os dois diretórios que um clone não
recebe. [`CLAUDE.md`](CLAUDE.md) — as regras de trabalho que um agente segue aqui.
[`benchmark/`](benchmark/) — uma fixture congelada com sete ambiguidades plantadas, um gabarito, e um
placar por versão.

## Como se encaixa com o tlc-spec-driven

As duas skills são donas de arquivos diferentes e nunca colidem:

- **Esta skill** é dona de `docs/` — o roadmap, a ordem de build, o status do backlog.
- **tlc-spec-driven** é dona de `.specs/` — specs, designs, tasks, relatórios de validação, decisões.

A única superfície compartilhada é uma escrita no `## Handoff` do `.specs/STATE.md`, no schema de
campos próprio daquela skill, apontando de volta para o roadmap. A conclusão de features é lida de
`.specs/features/<name>/validation.md`, nunca controlada manualmente — então as duas nunca discordam
sobre o que está pronto.
