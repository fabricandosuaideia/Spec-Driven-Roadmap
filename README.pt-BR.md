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

### Como skill simples — macOS, Linux, WSL, Git Bash

> **No Windows, num terminal PowerShell, não use este bloco — vá para [Windows](#windows-powershell).**
> Com o WSL instalado, `bash` no PowerShell é o *lançador do WSL*: o pipe roda dentro do Linux e o
> terminal vira WSL. (E no Windows PowerShell 5.1, `curl` é um alias que rejeita `-fsSL`.)

```bash
curl -fsSL https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.sh | bash
```

Instala em `.claude/skills/spec-driven-roadmap/` no projeto atual.

Com flags — note o `-s --`, que é obrigatório ao usar pipe para o bash:

```bash
curl -fsSL .../install.sh | bash -s -- --global   # instala em ~/.claude/skills/
curl -fsSL .../install.sh | bash -s -- --force    # sobrescreve uma instalação existente
```

### Windows (PowerShell)

`install.sh` precisa de bash. Para PowerShell nativo (5.1+, vem com Windows 10 e posteriores) use
`install.ps1` — não precisa de curl, tar, bash ou WSL, e continua no terminal em que você está:

```powershell
irm https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.ps1 | iex
```

A forma via pipe não aceita parâmetros. Para `-Global` ou `-Force`, baixe o arquivo antes:

```powershell
irm https://raw.githubusercontent.com/fabricandosuaideia/Spec-Driven-Roadmap/main/install.ps1 -OutFile install.ps1
.\install.ps1 -Global -Force
```

A skill em si é markdown mais oito scripts auxiliares em Python 3 (só biblioteca padrão), então é
totalmente multiplataforma; só o instalador muda por SO. Eles convertem um projeto de roadmap único
em roadmaps por seção, conferem um roadmap, medem quanto as execuções de agentes custam, imprimem só
o trecho do roadmap que o construtor de uma feature precisa, mantêm pequeno o bloco de status do
roadmap, escrevem as definições de sub-agente que um loop dispara, planejam uma execução da esteira e cronometram o gate completo do projeto;
cada um precisa de um `python3` funcionando no PATH. No Claude Code a skill também traz um script de
Workflow que constrói um roadmap com um agente novo por papel — construtor, provador, verificador,
revisor, mesclador — e ele só roda quando você pede. No Windows, o `python3` puro costuma ser o stub da Microsoft Store, que abre a
Store em vez de rodar qualquer coisa: instale o Python pelo python.org — depois disso o
launcher `py -3` dele também funciona.

### Meu roadmap está sadio?

Peça — *"confere meu roadmap"* — e a skill roda as próprias sanity checks sobre o que ela gerou,
inclusive um roadmap que cresceu ao longo de várias ondas. Ela reporta o que falhou, o que é aviso e
o que não conseguiu julgar; nada é editado.

Cobre dependências para frente, nomes repetidos, o orçamento de oito tasks, o acordo nos dois
sentidos entre as perguntas abertas de cada feature e o roll-up, uma linha de ledger por tema,
`uncovered: none`, o nível de risco de cada feature no piso dela ou acima, o `.txt` de ordem de build batendo com o roadmap, os limiares de tamanho, e
unicidade de nome contra todo outro roadmap e todo diretório `.specs/features/` — inclusive uma
feature construída que nenhum roadmap nomeia mais. Uma falha é uma pergunta para você, não um
veredito.

A Phase 2 roda as mesmas checagens sempre que fecha um roadmap; isto aqui é para perguntar depois.

### Para onde foi minha cota?

Peça — *"mede o custo dos meus agentes"* — e a skill lê os transcritos do Claude Code deste projeto e
mostra para onde os tokens foram: por papel, por nova tentativa, e quanto de cada conversa é contexto
se acumulando turno após turno. Não edita nada e não roda mais nada. Salve uma linha de base antes de
mudar como os agentes rodam, e compare depois: economia que ninguém mediu é chute.

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
suposição padrão é [`tlc-spec-lean`](https://github.com/tech-leads-club/agent-skills), a skill
spec-driven atual do Tech Leads Club; a [`tlc-spec-driven`](https://github.com/tech-leads-club/agent-skills)
também é totalmente suportada, e um projeto que já a usa continua com ela. Duas complementares valem a
pena ao lado: a [`tlc-discover`](https://github.com/tech-leads-club/agent-skills), que assume a
entrevista quando você ainda não tem um documento de escopo, e a
[`not-your-babysitter`](https://github.com/tech-leads-club/agent-skills):

```bash
git init   # apenas se esta pasta ainda não tiver controle de versão — veja a nota abaixo
npx @tech-leads-club/agent-skills install --skill tlc-spec-lean -a claude-code
npx @tech-leads-club/agent-skills install --skill tlc-discover -a claude-code
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
> Verifique com `ls .claude/skills/tlc-spec-lean` e `ls .claude/skills/tlc-discover` antes
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
build (ou um `ROADMAP-INDEX.md` com um roadmap por seção, se você escolher o modo multi-seção). Toda feature
carrega um nível de risco — A, B ou C, derivado do tamanho dela e do que ela toca — que define quanta
verificação e quantas tentativas ela recebe. A posição no backlog fica em um bloco `## Status` que a
skill reescreve a cada seed e mantém pequeno: o que execuções anteriores escreveram nele vai, literal,
para `docs/roadmap-history.md`. O handoff que ela escreve em `.specs/STATE.md` fica pequeno do mesmo
jeito — o antigo, e as cópias antigas que execuções deixaram ao lado dele, vão para esse mesmo arquivo.

Ao fim da execução, a skill pergunta como você quer construir e entrega um prompt com os nomes e os
caminhos já resolvidos. Cole-o em uma sessão nova.

- **A — uma feature por vez.** Com o `tlc-spec-lean`, ele fica assim:

  ```
  specify feature <name> — create it at `.specs/features/<name>/` using that exact directory name.
  Plan source: run `python3 .claude/skills/spec-driven-roadmap/scripts/feature-brief.py <name>` — it prints the
  entry from docs/ROADMAP.md, its risk tier and what that tier sets (follow it), the questions naming it and docs/ROADMAP.md `## Cross-Cutting Decisions`,
  which are settled before planning: do not re-decide what they answer. Do not open docs/ROADMAP.md whole;
  if the script cannot run, read only its `### <name>` entry and the lines naming <name>.
  ```

  O construtor lê só a fatia do roadmap que é da sua feature, nunca o arquivo inteiro: a cada turno, um
  agente relê tudo o que já leu.
- **B — um `/loop` sobre um roadmap**, sem supervisão. A sessão do loop só coordena: cada feature é
  construída por um sub-agente novo e verificada por outro, e a skill escreve
  `.claude/agents/roadmap-*.md` para que cada papel rode com o próprio esforço. Toda pergunta aberta
  desse roadmap é fechada com você antes, porque depois não haverá ninguém para responder.
- **C — uma execução da esteira, só no Claude Code.** Um script de Workflow que a skill traz constrói o
  roadmap com um agente novo por papel — construtor, um provador que roda o seu gate uma vez, o
  verificador, um revisor para o nível de risco A, um mesclador, e a sua barreira do lote
  (`barrierGate`) se você deixa a suíte inteira para ela — e devolve uma linha por feature. Você
  confirma os comandos de gate uma vez; um gate mais longo que os 10 minutos de um comando roda
  desanexado e é esperado; o `bench-gate.py` pode cronometrá-lo para você.

O [guia](guide/HOW-IT-WORKS.pt-BR.md) explica o que cada opção troca.

**Modo gestor — o backlog inteiro, sem ninguém olhando.** Num projeto multi-seção, no Claude Code,
você pode pedir o *"manager mode"* (modo gestor): um Workflow percorre toda seção que falta, na ordem
de construção, decompõe cada uma logo antes de construí-la — **decidindo ele mesmo as perguntas
abertas e marcando cada decisão como `Decided by the manager`** para você revisar — e a constrói com
a esteira da opção C. Ele só roda com a sua delegação por escrito (`manager.delegation` em
`docs/process/pipeline.json`), para antes das seções que você reservar (`stopAt`), numa barreira
vermelha, e nunca constrói sobre uma seção que não terminou. Fora do modo gestor, a skill nunca
decide por você. Dois níveis, como permissões mais estreitas ou mais amplas: `decide` para quando algo
quebra e espera você; `unblock` também faz a triagem de uma barreira vermelha por script e a conserta,
com um conferente independente antes de qualquer merge. Experimental.

## Atualizando um projeto que já usa a skill

Projetos novos não precisam de nada aqui. Um projeto que uma versão anterior planejou recebe o
comportamento novo em uma execução:

1. Instale a versão nova nesse projeto — rode o instalador de novo, ou `/plugin update` no caso de plugin.
2. Nesse projeto, peça *"atualiza este projeto"* (ou digite `/spec-driven-roadmap upgrade this project`).

A skill então salva uma linha de base de custo a partir dos transcritos do próprio projeto
(`docs/process/cost-baseline.json`), confere o roadmap, roda de novo o seed dela — que move o `## Status`
antigo e o handoff antigo, cópias incluídas, para `docs/roadmap-history.md` —, oferece trocar as linhas de ponte antigas
no seu `CLAUDE.md` (só com o seu sim) e pergunta como você quer construir. Ela nunca regenera o
roadmap nem renomeia uma feature. Você pode pedir os dois passos ao Claude Code em uma frase: *"reinstala
o spec-driven-roadmap neste projeto e depois atualiza este projeto"*. Depois que algumas features
estiverem construídas, peça de novo *"mede o custo dos meus agentes"*: a comparação com essa linha de
base é a única prova de que a atualização economizou alguma coisa.

Duas coisas para saber. Os tipos de sub-agente em `.claude/agents/` são carregados quando uma sessão
começa no projeto, então abra uma sessão nova depois que a opção B os escrever. E um
`CLAUDE_CODE_EFFORT_LEVEL` definido no seu ambiente sobrepõe o esforço que cada um deles define.

## Trabalhando na própria skill

[`CONTRIBUTING.md`](CONTRIBUTING.md) — preparação do ambiente, e os dois diretórios que um clone não
recebe. [`CLAUDE.md`](CLAUDE.md) — as regras de trabalho que um agente segue aqui.
[`benchmark/`](benchmark/) — uma fixture congelada com sete ambiguidades plantadas, um gabarito, e um
placar por versão.

## Como se encaixa com as skills TLC

As duas são donas de arquivos diferentes e nunca colidem:

- **Esta skill** é dona de `docs/` — os roadmaps, a ordem de build, o status do backlog, o histórico dele
  (`docs/roadmap-history.md`) e a configuração da esteira (`docs/process/pipeline.json`, opção C). Com
  a opção B e sub-agentes, ela também escreve `.claude/agents/roadmap-*.md`.
- **A skill seguinte** — `tlc-spec-lean` por padrão, `tlc-spec-driven` também suportada — é dona de
  `.specs/`: planos ou specs, checks ou tasks, relatórios de verificação, decisões.

A única escrita em `.specs/` é o `## Handoff` do `.specs/STATE.md`, no schema de campos próprio daquela
skill, apontando de volta para o roadmap. A conclusão de features é lida do relatório de cada feature
(`verification.md` para o `tlc-spec-lean`, `validation.md` para o `tlc-spec-driven`) e do gate de
conclusão da própria skill, nunca controlada manualmente — então as duas nunca discordam sobre o que
está pronto.
