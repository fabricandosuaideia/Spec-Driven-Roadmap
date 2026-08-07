# Como o Spec-Driven Roadmap Funciona

*Um guia em linguagem simples, para humanos. Se você quer as regras exatas que a skill segue, leia
[`SKILL.md`](../SKILL.md) para o mapa geral e [`references/`](../references/) para os procedimentos
em si — quando os dois discordam, quem vale é o arquivo de reference. Esta página é a versão
amigável.*

*Não sabe qual versão você tem instalada? Veja
[**Qual versão eu tenho?**](../README.pt-BR.md#qual-versão-eu-tenho) no README.*

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

**Ela para assim que sua visão, seus usuários e os limites do MVP estiverem claros o suficiente para
decompor** — ou seja, nem toda execução faz as seis perguntas, e ela pula o que você já respondeu
antes na conversa. Respostas curtas servem; esse documento pode ser enxuto. Ela escreve suas
respostas em `docs/PROJECT.md` para você — você nunca escreve esse arquivo à mão — e então decompõe,
igual ao caminho A.

### C — "Eu tenho código, mas nada que descreva o que ele faz"

Diga *"map this codebase into a roadmap source"*. A skill verifica se a sua skill de build (ou a
skill `codenavi`) já tem um mapeamento do código que ela pode reaproveitar; se não tiver, ela faz
uma varredura leve — só o suficiente para saber o que já existe e o que provavelmente está
faltando, não uma auditoria profunda de arquitetura.

Depois disso, nesta ordem: ela pergunta diretamente a você o que quer adicionar ou mudar — backlog
nunca é inferido de observações sobre dívida técnica, então essa resposta é a única fonte que ela
tem —, coloca duas listas **no chat** para você corrigir (**Capabilities Already Built** e **Gaps /
Likely Next Work**) e só escreve `docs/CODEBASE-SUMMARY.md` depois que você confirmar. Vale o minuto
gasto conferindo essas listas: qualquer coisa arquivada por engano como já construída fica de fora
do roadmap para sempre, e a tabela de cobertura não pega isso — aquela unidade nunca chegou a ser
enumerada.

## Mais uma pergunta que ela faz, independente do caminho

**Um roadmap só, ou vários?** Para um projeto pequeno a médio, uma lista única
(`docs/ROADMAP.md`) é mais simples. Para um sistema grande com fronteiras internas reais, dividir
em vários roadmaps (`docs/ROADMAP-INDEX.md` + um arquivo por seção) permite pensar sobre — ou
construir — cada parte de forma um pouco independente. A skill apresenta o trade-off e pergunta;
você não precisa decidir isso antes de começar. Há uma exceção: se o projeto já tem um
`docs/ROADMAP-INDEX.md` ou um `docs/ROADMAP.md`, o modo já foi definido antes e a execução continua
nele — nesse caso ela não pergunta de novo. Se os *dois* arquivos existirem, isso é uma contradição
— a execução para e pergunta qual deles é o autoritativo.

## O que você recebe, em disco

| Arquivo | Quando |
|---|---|
| `docs/ROADMAP.md` + `docs/roadmap.txt` | Sempre (modo roadmap único) |
| `docs/ROADMAP-INDEX.md` + um par `ROADMAP-<slug>.md`/`roadmap-<slug>.txt` por seção decomposta | Se você escolheu vários roadmaps |
| `docs/PROJECT.md` | Só se você passou pela entrevista (caminho B) |
| `docs/CODEBASE-SUMMARY.md` | Só se ela mapeou seu código (caminho C) |
| `.specs/STATE.md` (corpo do `## Handoff` reescrito) | Só quando há algo para semear *e* uma skill de build confirmada cujo schema seja legível — quatro exceções, abaixo |

O próprio arquivo de roadmap contém, por feature: um objetivo, do que ela depende, uma estimativa
honesta de tasks (≤8 — se uma feature precisar de mais, ela é dividida), quais dimensões
"delicadas" estão presentes (auth, persistência, chamadas externas, etc.), e qualquer pergunta em
aberto que ela não conseguiu responder por você. Fecha com uma tabela de cobertura provando que
nada ficou de fora.

**A decomposição é preguiçosa.** No modo multi-seção, só a seção que você pediu ganha o par
`.md`/`.txt`; as outras ficam no índice como `NOT YET DECOMPOSED`, e a skill apenas reporta a
próxima ação — *"decompose section `<slug>`"*. Isso é de propósito: uma seção decomposta semanas
antes de ser construída envelhece. Acrescentar uma seção ao índice também nunca dispara um handoff,
porque uma seção sem `.txt` não tem ordem de build de onde escolher um alvo.

**Quatro situações pulam essa última escrita**, e a skill registra qual delas foi na linha `Handoff`
do bloco de status dela própria: nenhuma skill de build instalada; uma confirmada, mas com o schema
de handoff ilegível; trabalho de verdade em andamento; ou nada sobrando para semear, porque toda
feature decomposta já está pronta.

**`docs/` é fixo, não é configurável.** E os arquivos `.txt` são feitos para máquina ler: só nomes
de feature, um por linha, sem comentários e sem marcadores de status. O seed conta essas linhas para
calcular o progresso, então qualquer outra coisa ali inflaria o total e nunca casaria com uma
feature. A ordem de build legível para humanos — com marcadores de incremento e tudo — mora no `.md`
do roadmap ao lado.

## Um exemplo ilustrativo

Dado um PRD de dois parágrafos para um rastreador de tarefas compartilhado bem simples, sem
detalhes de autenticação especificados, uma execução ilustrativa produz algo com esta cara
(resumido):

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

Repare que ela não chutou como funciona a associação de time — o PRD nunca disse, então ela
registrou como pergunta em aberto. É assim por design: ela nunca decide algo ambíguo no seu lugar.

**O handoff continua sendo escrito** — sempre que houver algum para escrever (veja abaixo). Essa
pergunta é copiada para o campo `Blockers` do Handoff, o campo `Next step` passa a apontar para
respondê-la em vez de apontar para especificar a feature, e a execução reporta isso como **semeado,
porém bloqueado**, nunca como "não semeado". O que fica retido é só o comando de início pronto para
copiar e colar, para você não sair daqui com um comando que começaria uma feature que não tem como
começar limpa.

## As perguntas que ela faz antes de terminar

Antes de fechar o roadmap, ela roda uma varredura curta de **decisões que valem para o projeto
inteiro** — aquelas que, sem isso, seriam redecididas de forma diferente dentro de cada feature:
delete lógico ou físico, modelo de auth, o que acontece numa falha parcial, política de retry e
idempotência, o que nunca pode ir para o log. Ela só pergunta sobre os temas que o seu roadmap
realmente toca, e cada um vem com um default recomendado que você aceita numa palavra. O resultado
vai para um bloco `## Cross-Cutting Decisions`, e toda feature passa a ser construída contra ele.

**Espere um livro-razão, não uma lista de respostas.** Esse bloco carrega exatamente uma linha por
tema da rubrica — nenhum ausente, nenhum repetido — e cada linha se lê de uma entre quatro formas: a
decisão mais uma linha de justificativa; `N/A because <reason> (as of <roadmap>)`, quando nada do
que foi decomposto até aqui encosta nesse tema; `not decided`, apontando para a pergunta em aberto
em que ele virou; ou `deferred to feature <name>`, quando a pergunta ganhou uma feature própria na
ordem de build. Ou seja, linhas `N/A` são o bloco funcionando, não algo faltando — a completude é o
valor inteiro dele: sua skill de build lê esse bloco antes de cada discussão de área cinzenta, então
"não está listado aqui" precisa significar "este projeto não tem esse tema", e nunca "a gente
esqueceu".

Um tema sem resposta cai em dois lugares — a linha `not decided`, mais uma pergunta em aberto com
uma linha `affects:` nomeando o que a resposta alcançaria. Esse par segura o comando de início das
features que ele de fato alcança; responder libera essas features.

Ela deliberadamente **não** pergunta sobre tudo. Decisões que vivem dentro de uma feature só —
layout, formato de resposta, texto de erro — ficam para a sua skill de build, que pergunta depois
com o código na frente e responde melhor por isso. Essas ficam listadas num bloco
`## Expected Gray Areas`, para você ver o que vem pela frente sem precisar decidir agora.

## O que acontece depois

**A pergunta "como você quer construir" só aparece quando alguma coisa foi de fato semeada e a sua
skill de build está confirmada.** Fora isso, a execução termina no relatório, com o motivo. Seis
finais param antes da pergunta: só a Fase 1 rodou, então a seção está indexada mas não decomposta;
um nome de roadmap divergiu de um diretório que já existe no disco; há trabalho de verdade em
andamento; toda feature decomposta já está pronta; nenhuma skill de build está instalada; ou tem
uma, mas o schema de handoff dela não pôde ser lido. Nos seis casos o roadmap está terminado e
utilizável do jeito que está — o que falta é o handoff, não o plano.

**Se nenhuma skill de build estiver instalada, ela gera o roadmap mesmo assim.** As fases 1 e 2
escrevem só em `docs/`, então você recebe a coisa inteira, e **nada é criado dentro de `.specs/`** —
nem um `STATE.md` vazio, porque um arquivo de formato chutado é pior que arquivo nenhum: o resume da
sua skill de build trataria aquilo como um retrato desatualizado a reconciliar. O motivo fica
registrado de forma durável na linha `Handoff` do bloco de status, para uma execução futura
conseguir diferenciar "nunca foi semeado" de "foi semeado e depois sobrescrito". Instale a skill,
peça o seed de novo, e a cadeia se completa **sem reexecutar a Fase 2**.

Quando existe um alvo e uma skill confirmada, ela avisa que o trabalho de planejamento terminou e
pergunta **como você quer construir**. Duas opções:

**A — uma feature por vez.** Você recebe o comando só da próxima feature, roda, e volta quando ela
passar:

```
specify feature tt-create-task — create it at `.specs/features/tt-create-task/` using that exact
directory name. Spec source: docs/ROADMAP.md. Read docs/ROADMAP.md `## Cross-Cutting Decisions`
before Discuss and treat it as settled — do not re-decide what it answers.
```

**B — um roadmap inteiro em um loop.** Você recebe um prompt que começa com `/loop` (o comando de
loop do seu próprio CLI — Claude Code, Cursor e OpenCode têm um) e que só termina quando todas as
features daquele roadmap estiverem verificadas. Como um loop roda sem supervisão e não tem a quem
perguntar, essa opção exige um roadmap com **zero perguntas em aberto** — então a skill primeiro lê
o roadmap inteiro atrás de lacunas, te entrevista até toda pergunta em aberto ser respondida, grava
as respostas de volta, e então relê os arquivos do disco para confirmar que não sobrou nada em
aberto. Só aí ela te entrega o prompt.

**O que a opção B troca não é "não sobrou pergunta".** O loop não elimina as áreas cinzentas que a
skill deliberadamente deixou para a sua skill de build — ele decide cada uma pelo default e **deixa
registrado**, com a justificativa, no `.specs/features/<name>/spec.md` daquela feature, na seção de
premissas e perguntas em aberto; revisar essas seções depois é a etapa esperada, não trabalho extra.
A contagem no bloco `## Expected Gray Areas` daquele roadmap já dimensiona a troca de antemão, e ela
é um **piso, não um teto** — ali está só o que a varredura do planejamento levantou, enquanto a
discussão de cada feature gera mais em cima disso. E isso não é gambiarra: mandar uma área cinzenta
recusada para a spec com o default e a justificativa do agente é o fallback documentado da própria
`tlc-spec-driven`.

**Um loop cobre um roadmap.** Se você dividiu o produto em roadmaps por seção, o loop constrói a
seção em que você está — não o produto inteiro. Isso é de propósito: o que uma seção entrega para
outra fica provisório até aquela seção ser realmente construída, então a fronteira entre duas seções
é onde o plano encontra o que foi entregue. É um checkpoint que vale manter com um humano presente.
Quando a seção termina, você volta, a skill re-semeia, e a próxima seção ganha o loop dela.

⚠️ **Nos dois casos, rode esse prompt em uma nova sessão de chat, com contexto limpo** — não na
sessão que gerou o roadmap. A própria skill vai te avisar disso. Numa sessão nova, **o canal é o
próprio prompt**: sua skill de build re-deriva o que precisa a partir dos caminhos que estão nele e
dos arquivos de roadmap no disco. O `.specs/STATE.md` é lido depois, num `resume work` — é para isso
que o Handoff serve, não para um começo do zero —, e é por isso que o prompt precisa ser colado
inteiro, com o nome exato do diretório e tudo. Reaproveitar a sessão de planejamento só arrisca o
agente trabalhar pela conversa lembrada em vez dos arquivos escritos, e começa a construção com o
orçamento de contexto já gasto.

Esse prompt é a última coisa que essa skill faz. Dali em diante, todo o ciclo de build — spec,
design, tasks, implementação, verificação — pertence inteiramente à sua skill de build
(`tlc-spec-driven`, por padrão). Mesmo no modo loop, quem conduz aquela skill é o seu CLI; essa aqui
já parou. Ela não intervém de novo até você pedir para gerar ou atualizar um roadmap.

## Como ela sabe o que já foi construído

Ela nunca aceita a palavra de ninguém, e a existência de um arquivo não prova nada. Para cada nome
da ordem de build ela lê o `.specs/features/<name>/validation.md`, rodando o script de gate da sua
skill de build se aquela skill realmente entregar um **no disco** — ela olha o disco, não a
documentação, porque o conjunto de scripts de uma skill muda entre releases e a instalação fica para
trás — e, se não houver script, lê o relatório exatamente pelas mesmas regras. Um **PASS sem citação
de evidência no formato `path.ext:NN` conta como não feito**, e um template `[PASS | FAIL]` não
preenchido também. Features que só respondem uma pergunta são a única exceção: como não produzem
código, elas se quitam quando a pergunta é respondida — ou quando existe um `context.md` para elas.
E quando há trabalho de verdade em andamento — algo concluído ou em progresso no Handoff, ou a
feature nomeada no Handoff tem `spec.md` no disco e não tem um PASS de verdade — ela **não reescreve
o `.specs/STATE.md` de jeito nenhum**: atualiza só o bloco de status dela, nomeia a feature em
andamento, e para por aí.

## O que aparece no arquivo e pode te surpreender

- **Uma feature que não constrói nada.** Quando uma pergunta não resolvida trava várias features
  seguintes, ela pode ganhar uma feature pequena só dela, cujo único trabalho é conseguir aquela
  resposta. Essa feature carrega a linha literal
  `discharge: no code — answered open question or context.md`, ipsis litteris, porque três
  consumidores diferentes dependem dela: o teste de "está feito" do seed, a escolha de alvo dele, e
  a lista de skip do prompt de loop.
- **Um bloco de status no topo do seu roadmap** (ou do índice, no modo multi-seção): contagens, a
  ordem de build restante, a próxima feature, e se o handoff foi escrito — ou por que não. Ele é
  regerado a cada seed, então nunca edite à mão.
- **Inglês dentro de um roadmap que não está em inglês.** A prosa sai no idioma em que você está
  trabalhando, mas nomes de feature, prefixos, slugs, nomes de arquivo e **todo heading gerado**
  continuam em inglês: são chaves lidas por máquina, componentes de caminho e nomes de diretório, e
  traduzir um deles quebra o handoff, os diretórios `.specs/features/<name>/`, ou alguma busca entre
  arquivos.

## O que ela deliberadamente *não* faz

- Nunca escreve `spec.md`, `design.md`, `tasks.md`, ou código de aplicação.
- Nunca avança pelas features sozinha — sem avanço automático. Ela até *escreve* um prompt `/loop`
  para você, mas quem roda é o seu CLI, na sua sessão, depois que essa skill já parou.
- Nunca chuta uma ambiguidade — ela pergunta, ou registra como pergunta em aberto. Essa pergunta
  segura o comando de início da **feature-alvo**, não o backlog: uma pergunta da própria feature
  bloqueia aquela feature, e uma pergunta de projeto inteiro só bloqueia quando a linha `affects:`
  dela diz `all` ou nomeia o alvo. Bloquear mais largo que isso congelaria o backlog inteiro atrás
  de uma única pergunta de projeto.
- Nunca re-deriva o que outra skill já mapeou — se sua skill de build ou a `codenavi` já documentou
  o código, ela reaproveita em vez de escanear de novo. Se a sua skill de build tem ou não essa
  etapa **depende da versão** (a `tlc-spec-driven` v2 tinha, a v3.x não tem), então ela detecta o
  que está realmente instalado em vez de supor um caminho.

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
Diga isso — "add this new section to the roadmap" ou algo parecido. Ela estende o que já existe em
vez de regerar tudo. Nomes de feature **e a ordem relativa entre elas congelam no instante em que
existe um diretório `.specs/features/<name>/`** — na existência do diretório, não numa verificação
aprovada, então uma spec pela metade ou uma execução que falhou congelam a feature delas também. Uma
feature que se mostrou obsoleta é marcada como superseded no lugar, com uma nota; nunca apagada,
nunca renomeada. Escopo novo entra depois do bloco congelado.
