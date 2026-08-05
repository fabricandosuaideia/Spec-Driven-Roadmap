# Como o Spec-Driven Roadmap Funciona

*Um guia em linguagem simples, para humanos. Se você quer as regras exatas que a skill segue, leia
[`SKILL.md`](../SKILL.md) — esta página é a versão amigável.*

Outros idiomas: [English](HOW-IT-WORKS.md) · [Español](HOW-IT-WORKS.es.md)

## Em uma frase

Essa skill descobre **o que construir e em que ordem** — ela nunca escreve código, specs ou
testes. Pense nela como a etapa que acontece *antes* de você entregar uma feature para a sua skill
de build (`tlc-spec-driven`, por padrão): ela transforma o que você já tem — um documento, uma
ideia, ou um código existente — em um backlog ordenado, e depois sai de cena.

## Como acionar

Duas formas, ambas funcionam igual:

**1. Simplesmente fale com o Claude em texto livre.** Sem sintaxe especial. Qualquer uma destas
frases aciona a skill:

- "generate a roadmap from docs/PRD.md"
- "plan product"
- "I don't know what to build yet, help me figure it out"
- "map this codebase into a roadmap source"
- "decompose this architecture into features"

**2. Use o comando de barra**, se preferir ser explícito:

- Instalada como skill simples (método `curl`/`install.ps1`): `/spec-driven-roadmap`
- Instalada como plugin (`/plugin install`): `/spec-driven-roadmap:spec-driven-roadmap`

De qualquer forma, uma vez iniciada, é só conversa — você responde às perguntas dela e ela faz o
resto.

## As três formas de começar (escolha pelo que você já tem)

Você nunca precisa preparar um arquivo com antecedência. Diga o que é verdade para o seu caso, ou
simplesmente comece a falar que ela pergunta.

### A — "Eu já tenho um documento"

Você tem um PRD, um documento de arquitetura, um conjunto de ADRs, ou um flowchart exportado. Diga
algo como *"generate a roadmap from docs/PRD.md"*. A skill lê o documento, faz algumas perguntas de
confirmação (qual skill de build você usa, se você quer um roadmap único ou vários), e decompõe.

### B — "Eu não tenho nada escrito, e nem sei bem o que construir"

Diga *"plan product"* ou *"I don't know what to build yet"*. A skill te entrevista — uma pergunta
por vez, nunca uma lista inteira de uma vez:

1. O que você está construindo?
2. Para quem é, e que problema resolve?
3. Qual é a menor versão que já é útil?
4. O que fica explicitamente fora de escopo por agora?
5. Alguma restrição rígida? *(opcional)*
6. Que stack técnica, se você já souber? *(opcional)*

Ela escreve suas respostas em `docs/PROJECT.md` para você — você nunca escreve esse arquivo à mão —
e então decompõe, igual ao caminho A.

### C — "Eu tenho código, mas nada que descreva o que ele faz"

Diga *"map this codebase into a roadmap source"*. A skill verifica se a sua skill de build (ou a
skill `codenavi`) já tem um mapeamento do código que ela pode reaproveitar; se não tiver, ela faz
uma varredura leve — só o suficiente para saber o que já existe e o que provavelmente está
faltando, não uma auditoria profunda de arquitetura. Ela escreve `docs/CODEBASE-SUMMARY.md`,
pergunta o que você realmente quer adicionar em seguida, e decompõe a partir daí.

## Mais uma pergunta que ela sempre faz, independente do caminho

**Um roadmap só, ou vários?** Para um projeto pequeno a médio, uma lista única
(`docs/ROADMAP.md`) é mais simples. Para um sistema grande com fronteiras internas reais, dividir
em vários roadmaps (`docs/ROADMAP-INDEX.md` + um arquivo por seção) permite pensar sobre — ou
construir — cada parte de forma um pouco independente. A skill apresenta o trade-off e pergunta;
você não precisa decidir isso antes de começar.

## O que você recebe, em disco

| Arquivo | Quando |
|---|---|
| `docs/ROADMAP.md` + `docs/roadmap.txt` | Sempre (modo roadmap único) |
| `docs/ROADMAP-INDEX.md` + um `ROADMAP-<slug>.md`/`roadmap-<slug>.txt` por seção | Se você escolheu vários roadmaps |
| `docs/PROJECT.md` | Só se você passou pela entrevista (caminho B) |
| `docs/CODEBASE-SUMMARY.md` | Só se ela mapeou seu código (caminho C) |
| `.specs/STATE.md` (uma linha atualizada) | Só se sua skill de build estiver confirmada/instalada — esse é o handoff |

O próprio arquivo de roadmap contém, por feature: um objetivo, do que ela depende, uma estimativa
honesta de tasks (≤8 — se uma feature precisar de mais, ela é dividida), quais dimensões
"delicadas" estão presentes (auth, persistência, chamadas externas, etc.), e qualquer pergunta em
aberto que ela não conseguiu responder por você. Fecha com uma tabela de cobertura provando que
nada ficou de fora.

## Um exemplo real

Dado um PRD de dois parágrafos para um rastreador de tarefas compartilhado bem simples, sem
detalhes de autenticação especificados, uma execução produziu isto (resumido):

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

Repare que ela não chutou como funciona a associação de time — o PRD nunca disse, então ela marcou
como pergunta em aberto e **recusou entregar a primeira feature** até isso ser respondido. É assim
por design: ela nunca decide algo ambíguo no seu lugar.

## As perguntas que ela faz antes de terminar

Antes de fechar o roadmap, ela roda uma varredura curta de **decisões que valem para o projeto
inteiro** — aquelas que, sem isso, seriam redecididas de forma diferente dentro de cada feature:
delete lógico ou físico, modelo de auth, o que acontece numa falha parcial, política de retry e
idempotência, o que nunca pode ir para o log. Ela só pergunta sobre os temas que o seu roadmap
realmente toca, e cada um vem com um default recomendado que você aceita numa palavra. As respostas
vão para um bloco `## Cross-Cutting Decisions`, e toda feature passa a ser construída contra ele.

Ela deliberadamente **não** pergunta sobre tudo. Decisões que vivem dentro de uma feature só —
layout, formato de resposta, texto de erro — ficam para a sua skill de build, que pergunta depois
com o código na frente e responde melhor por isso. Essas ficam listadas num bloco
`## Expected Gray Areas`, para você ver o que vem pela frente sem precisar decidir agora.

## O que acontece depois

Quando o roadmap está pronto e sua skill de build está instalada, a skill confirma que o trabalho de
planejamento terminou e pergunta **como você quer construir**. Duas opções:

**A — uma feature por vez.** Você recebe o comando só da próxima feature, roda, e volta quando ela
passar:

```
specify feature `tt-create-task` — spec source: docs/ROADMAP.md
```

**B — o roadmap inteiro em um loop.** Você recebe um prompt que começa com `/loop` (o comando de loop
do seu próprio CLI — Claude Code, Cursor e OpenCode têm um) e que só termina quando todas as features
do backlog estiverem verificadas. Como um loop roda sem supervisão e não tem a quem perguntar, essa
opção exige um roadmap com **zero perguntas em aberto** — então a skill primeiro lê o roadmap inteiro
atrás de lacunas, te entrevista até toda pergunta em aberto ser respondida, grava as respostas de
volta, e então relê os arquivos do disco para confirmar que não sobrou nada em aberto. Só aí ela te
entrega o prompt.

⚠️ **Nos dois casos, rode esse prompt em uma nova sessão de chat, com contexto limpo** — não na
sessão que gerou o roadmap. A própria skill vai te avisar disso. A skill de build relê tudo o que
precisa de `.specs/STATE.md` e dos arquivos do roadmap no disco; reaproveitar a sessão de
planejamento só arrisca ela trabalhar pela conversa lembrada em vez dos arquivos escritos, e começa a
construção com o orçamento de contexto já gasto.

Esse prompt é a última coisa que essa skill faz. Dali em diante, todo o ciclo de build — spec,
design, tasks, implementação, verificação — pertence inteiramente à sua skill de build
(`tlc-spec-driven`, por padrão). Mesmo no modo loop, quem conduz aquela skill é o seu CLI; essa aqui
já parou. Ela não intervém de novo até você pedir para gerar ou atualizar um roadmap.

## O que ela deliberadamente *não* faz

- Nunca escreve `spec.md`, `design.md`, `tasks.md`, ou código de aplicação.
- Nunca avança pelas features sozinha — sem avanço automático. Ela até *escreve* um prompt `/loop`
  para você, mas quem roda é o seu CLI, na sua sessão, depois que essa skill já parou.
- Nunca chuta uma ambiguidade — ela pergunta, ou registra como pergunta em aberto e bloqueia o
  handoff até isso ser resolvido.
- Nunca re-deriva o que outra skill já mapeou — se sua skill de build (ou a `codenavi`) já
  documentou o código, ela reaproveita em vez de escanear de novo.

## Perguntas frequentes

**Preciso criar algum arquivo antes de usar?**
Não. Nem o roadmap — é isso que ela produz. Se você já tem um documento, é opcional mas ajuda; se
não tiver, ela te entrevista.

**O roadmap é o único arquivo obrigatório?**
É o único que a cadeia inteira realmente precisa para começar a andar — e nem isso é
estritamente exigido pela sua skill de build (ela consegue especificar uma feature a partir de uma
conversa simples, sem nenhum arquivo prévio). O valor do roadmap é decidir *o quê* e *em que ordem*
com antecedência, em vez de improvisar feature por feature.

**Como sei se é essa skill ou a minha skill de build que está ativa?**
Pelo que está acontecendo: se está decidindo o que construir e em que ordem, é essa skill. No
momento em que você vê `spec.md`, `design.md`, `tasks.md`, ou código de verdade sendo escrito, é a
sua skill de build — essa já se afastou.

**E se eu já tiver um roadmap e só quiser acrescentar mais coisa?**
Diga isso — "add this new section to the roadmap" ou algo parecido. Ela reaproveita o que já existe
em vez de recomeçar, e nunca renomeia ou reordena features que já foram construídas.
