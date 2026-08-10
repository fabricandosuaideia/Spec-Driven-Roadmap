# Roadmap — Pauta

size re-raised (as of 2026-08-09): single-section confirmed — a equipe é pequena e quer um único arquivo para ler; aceita que ele fique longo e vai dividir depois, se ficar inviável.

## Status

Ainda não semeado. O seed de handoff não foi executado nesta rodada, então este bloco ainda não tem
a lista de progresso — ele é escrito e atualizado por `references/handoff-seed.md`, Step 5.

## Cross-Cutting Decisions

Varridas uma vez, no nível do projeto, contra a rubrica de dimensões implícitas do
`tlc-spec-driven` v3.3.0 (`references/specify.md`, nove temas). As duas linhas
`deferred to feature` esperam por uma pergunta que a feature citada já carrega.

| Theme | Decisão |
|---|---|
| Input validation & bounds | Validação nas schemas Pydantic, na borda do FastAPI; um único envelope de erro `{"error": {"code", "message", "fields"}}`, com HTTP 422 para falha de validação; título até 120 caracteres, descrição até 2000, tempo estimado entre 1 e 480 minutos. Uma borda só e um formato de erro só impedem que cada feature invente o seu. |
| Failure / partial-failure states | Uma transação por requisição, com rollback total em erro; efeito externo (e-mail, webhook) é gravado como linha de outbox dentro da mesma transação e entregue fora dela. Nenhuma escrita de domínio é desfeita por uma entrega que falhou, e a falha de entrega não aparece para quem fez a requisição. |
| Idempotency / retry / duplicate handling | Todo endpoint de escrita expressa o estado final desejado, nunca uma alternância: o voto é `PUT`/`DELETE` sobre o par (pessoa, item), não um `POST /toggle`; convite e confirmação de e-mail são idempotentes por token; entregas do outbox são at-least-once e levam um id de entrega para o destinatário deduplicar. Repetir uma chamada nunca muda o resultado. |
| Auth boundaries & rate limits | Sessão por cookie na aplicação; dado de equipe só é alcançável por quem é membro dela (A2); a API pública de F1 autentica por token por equipe, somente leitura, com teto de 100 req/min por token — folgado para 40 pessoas em 6 equipes. deferred to feature `pauta-team-roles` — see its `open questions`, porque A5 não nomeia nenhum papel. |
| Concurrency / ordering | Last-write-wins nas edições, sem trava otimista — são 40 pessoas no piloto e o custo de conflito é baixo; contagem de votos sempre por agregação na leitura, nunca contador cacheado; a ordem da pauta é calculada na leitura. deferred to feature `pauta-item-voting` — see its `open questions`, porque C3 não define desempate. |
| Data lifecycle / expiry | Exclusão sempre lógica: nenhum registro sai do banco, o que preserva o histórico que D3 pesquisa. Pauta encerrada é retida indefinidamente no piloto; link de convite vale 7 dias e link de confirmação de e-mail vale 24 horas. |
| Observability | Log estruturado em JSON no stdout do container único, uma linha por requisição com método, rota, status, duração e id da pessoa. Corpo de requisição nunca é logado; endereço de e-mail e texto de decisão nunca aparecem em log. |
| External-dependency failure | As únicas dependências externas são o relay SMTP e as URLs de webhook dos assinantes. Ambas são chamadas pelo worker de outbox com timeout de 10s, 5 tentativas em backoff exponencial e dead-letter depois disso; nenhuma requisição de usuário falha porque um terceiro caiu. |
| State-transition integrity | Os estados da pauta são exatamente os quatro de B2, em uma direção só — `rascunho → aberta → em reunião → encerrada` — cada transição disparada manualmente por um membro da equipe, e `encerrada` é irreversível (B4). `arquivar` (A5) é um sinalizador à parte sobre uma pauta já encerrada, não um quinto estado. Item e voto só são aceitos em `aberta` (B3); decisão só em `em reunião` (D1). |
| Canal de aviso e transporte de e-mail (`project-specific`) | Os três avisos (E1, E2, E3) saem por e-mail, pelo mesmo relay SMTP que A1 já exige para a confirmação de cadastro; host e credenciais vêm de variáveis de ambiente, sem SDK de provedor compilado junto. Sem caixa de entrada no app e sem push no piloto. Nenhum tema da rubrica cobre a escolha de canal, e ela passa nos três testes do Step 7. |

### pauta-account-signup

- **objective** — Permitir cadastro com e-mail e senha e liberar o primeiro login somente depois da confirmação do e-mail.
- **scope-units covered** — A1
- **depends on** — —
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 7
- **implicit dimensions present** — persistence/state, external calls, auth, state transitions
- **open questions** —
  - Qual é a regra de senha exigida no cadastro — comprimento mínimo, classes de caracteres, lista de proibidas? A1 pede "e-mail e senha" e não define nenhuma regra. status: open
  - O link de confirmação pode ser reenviado, e o que a pessoa vê ao tentar entrar antes de confirmar — erro, ou tela pedindo reenvio? A1 exige a confirmação antes do primeiro login e não descreve nenhum dos dois casos. status: open
- **needs pre-written context.md** — yes

### pauta-team-membership

- **objective** — Modelar equipes e o vínculo de uma pessoa com uma ou mais delas, base de toda a visibilidade do produto.
- **scope-units covered** — A2
- **depends on** — `pauta-account-signup`
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 6
- **implicit dimensions present** — persistence/state, auth
- **open questions** —
  - Como uma equipe passa a existir: qualquer pessoa cria a sua, ou as 6 equipes do piloto são provisionadas por fora? A Seção A descreve pertencimento (A2) e convite (A3), e nenhuma unidade do PRD descreve a criação de uma equipe. status: open
- **needs pre-written context.md** — yes

### pauta-team-invites

- **objective** — Trazer alguém para uma equipe por link, mandando quem já tem conta direto para dentro e quem não tem para o cadastro.
- **scope-units covered** — A3
- **depends on** — `pauta-account-signup`, `pauta-team-membership`
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 6
- **implicit dimensions present** — persistence/state, auth, state transitions
- **open questions** —
  - Quem pode gerar um convite: qualquer membro, ou só quem tem papel para isso? A3 fala em "convite por link" sem dizer quem convida, e A5 define papéis sem citar convite. status: open
  - O link é de uso único ou serve para várias pessoas entrarem na mesma equipe? A3 não distingue os dois. status: open
- **needs pre-written context.md** — yes

### pauta-user-profile

- **objective** — Deixar cada pessoa editar nome de exibição, fuso horário e avatar.
- **scope-units covered** — A4
- **depends on** — `pauta-account-signup`
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 6
- **implicit dimensions present** — persistence/state
- **open questions** —
  - Onde o avatar fica guardado, e com que teto de tamanho e que formatos aceitos? A4 pede avatar editável, a restrição de container único não diz nada sobre arquivos, e nenhuma parte do PRD nomeia um destino de armazenamento. status: open
- **needs pre-written context.md** — yes

### pauta-agenda-lifecycle

- **objective** — Criar uma pauta com título, equipe e data/hora prevista, conduzi-la pelos quatro estados, congelá-la ao encerrar e listar as pautas da equipe.
- **scope-units covered** — B1, B2, B4, B5
- **depends on** — `pauta-team-membership`
- **external contract consumed** — none
- **size** — Large
- **task estimate** — 7
- **implicit dimensions present** — persistence/state, auth, state transitions
- **open questions** —
  - Pautas em `rascunho` e `em reunião` aparecem em qual dos dois grupos da listagem? B5 separa futuras de encerradas e B2 define quatro estados, então dois deles não têm grupo. status: open
- **needs pre-written context.md** — yes

### pauta-agenda-items

- **objective** — Deixar qualquer membro propor um item com título, descrição e tempo estimado, editá-lo e retirá-lo, aceitando escrita só enquanto a pauta está aberta.
- **scope-units covered** — C1, C5, C6, B3
- **depends on** — `pauta-agenda-lifecycle`
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 7
- **implicit dimensions present** — persistence/state, auth
- **open questions** —
  - Editar um item que já recebeu votos mantém os votos ou os zera? C5 libera a edição enquanto a pauta está aberta e C2 não fala de edição. status: open
  - Retirar um item (C6) descarta os votos já dados nele, e é a mesma operação que A5 concede a quem pode "remover itens dos outros"? O PRD descreve as duas ações em seções diferentes e não diz se são a mesma. status: open
- **needs pre-written context.md** — yes

### pauta-item-voting

- **objective** — Registrar um voto por pessoa por item, com o mesmo gesto retirando o voto, e ordenar a pauta por número de votos.
- **scope-units covered** — C2, C3
- **depends on** — `pauta-agenda-items`
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 6
- **implicit dimensions present** — persistence/state, auth, concurrency
- **open questions** —
  - Qual é o critério de desempate quando dois itens têm o mesmo número de votos — mais antigo primeiro, menor tempo estimado, ordem de proposta? C3 ordena por votos e não trata empate, que com 40 pessoas será comum. status: open
  - Quem votou em um item é visível para a equipe, ou o voto é anônimo? C2 define um voto por pessoa e não diz se a autoria aparece. status: open
- **needs pre-written context.md** — yes

### pauta-time-budget

- **objective** — Mostrar a soma dos tempos estimados ao lado da duração prevista da reunião e avisar quando a soma passa dela.
- **scope-units covered** — C4
- **depends on** — `pauta-agenda-items`, `pauta-item-voting`
- **external contract consumed** — none
- **size** — Small
- **task estimate** — 4
- **implicit dimensions present** — none
- **open questions** —
  - De onde vem a "duração prevista da reunião" com que C4 compara a soma? B1 registra título, equipe e data/hora prevista — nenhuma unidade do PRD registra duração, então o outro lado da comparação não tem fonte. status: open
- **needs pre-written context.md** — yes

### pauta-team-roles

- **objective** — Introduzir papéis dentro da equipe e aplicá-los às duas permissões que A5 nomeia: arquivar uma pauta e remover itens de outras pessoas.
- **scope-units covered** — A5
- **depends on** — `pauta-team-membership`, `pauta-agenda-lifecycle`, `pauta-agenda-items`
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 7
- **implicit dimensions present** — persistence/state, auth
- **open questions** —
  - Quais são os papéis dentro da equipe e quem atribui o papel de quem? A5 nomeia duas permissões e nenhum papel, e não diz quem é o primeiro a ter poder de atribuir. status: open
- **needs pre-written context.md** — yes

### pauta-meeting-decisions

- **objective** — Registrar, durante a reunião, uma decisão em texto livre e um responsável para cada item.
- **scope-units covered** — D1
- **depends on** — `pauta-agenda-items`
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 6
- **implicit dimensions present** — persistence/state, auth, state transitions
- **open questions** —
  - O responsável por uma decisão precisa ser membro da equipe, e um item pode receber mais de uma decisão? D1 pede "uma decisão em texto livre e um responsável" sem restringir o responsável nem a quantidade. status: open
- **needs pre-written context.md** — yes

### pauta-undiscussed-carryover

- **objective** — Marcar como "não discutido" o item que chegou ao encerramento sem decisão e levá-lo para a próxima pauta da equipe com um clique.
- **scope-units covered** — D2
- **depends on** — `pauta-meeting-decisions`
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 5
- **implicit dimensions present** — persistence/state, state transitions
- **open questions** —
  - Qual é "a próxima pauta da mesma equipe" quando existem várias em aberto, ou quando não existe nenhuma? D2 promete o clique e não define o destino. status: open
  - Levar o item copia ou move, e os votos vão junto? D2 não diz, e B4 congela a pauta de origem no mesmo instante em que a marcação acontece. status: open
- **needs pre-written context.md** — yes

### pauta-decision-search

- **objective** — Buscar decisões por texto dentro da equipe.
- **scope-units covered** — D3
- **depends on** — `pauta-meeting-decisions`
- **external contract consumed** — none
- **size** — Small
- **task estimate** — 4
- **implicit dimensions present** — auth
- **open questions** —
  - A busca cobre só o texto da decisão, ou também título e descrição do item que a originou? D3 diz "busca de decisões por texto" e não delimita o que entra no índice. status: open
- **needs pre-written context.md** — yes
- **superseded** — replaced by `pauta-decision-search-v2` in wave 2 planning; kept here as the
  record of what wave 1 promised. Not in the build order.

### pauta-notification-events

- **objective** — Disparar os dois avisos orientados a evento: item novo numa pauta de que a pessoa participa, e responsabilidade recebida numa decisão.
- **scope-units covered** — E1, E3
- **depends on** — `pauta-agenda-items`, `pauta-meeting-decisions`
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 6
- **implicit dimensions present** — persistence/state, external calls
- **open questions** —
  - "Uma pauta de que você participa" (E1) quer dizer qualquer pauta da equipe a que a pessoa pertence, ou algo mais estreito, como ter proposto ou votado nela? Nada no PRD define participação numa pauta. status: open
  - O aviso de E3 sai no instante em que a decisão é registrada ou no encerramento da pauta? E3 nomeia o destinatário e não o momento. status: open
- **needs pre-written context.md** — yes

### pauta-meeting-reminder

- **objective** — Enviar antes da reunião um lembrete com a pauta já ordenada por votos.
- **scope-units covered** — E2
- **depends on** — `pauta-item-voting`, `pauta-notification-events`
- **external contract consumed** — none
- **size** — Small
- **task estimate** — 4
- **implicit dimensions present** — persistence/state, external calls, concurrency
- **open questions** —
  - Com quanta antecedência o lembrete sai, e esse intervalo é fixo para o produto ou escolhido por pessoa ou por pauta? E2 diz apenas "antes da reunião". status: open
- **needs pre-written context.md** — yes

### pauta-notification-preferences

- **objective** — Deixar cada pessoa ligar e desligar cada tipo de aviso.
- **scope-units covered** — E4
- **depends on** — `pauta-notification-events`, `pauta-meeting-reminder`
- **external contract consumed** — none
- **size** — Small
- **task estimate** — 4
- **implicit dimensions present** — persistence/state
- **open questions** —
  - Cada tipo de aviso nasce ligado ou desligado para quem acabou de criar conta? E4 entrega o controle e não define o estado inicial. status: open
- **needs pre-written context.md** — yes

### pauta-public-read-api

- **objective** — Expor uma API REST autenticada de leitura das pautas e decisões de uma equipe, com documentação gerada a partir do código.
- **scope-units covered** — F1, F3
- **depends on** — `pauta-agenda-lifecycle`, `pauta-meeting-decisions`
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 6
- **implicit dimensions present** — auth
- **open questions** —
  - A página de documentação de F3 fica aberta, ou exige a mesma credencial que F1? F3 pede a documentação e não diz quem pode abri-la. status: open
- **needs pre-written context.md** — yes

### pauta-closure-webhook

- **objective** — Disparar um webhook para os assinantes da equipe quando uma pauta é encerrada.
- **scope-units covered** — F2
- **depends on** — `pauta-agenda-lifecycle`
- **external contract consumed** — none
- **size** — Medium
- **task estimate** — 5
- **implicit dimensions present** — external calls, concurrency
- **open questions** —
  - Quem cadastra a URL de destino, o que vai no corpo do disparo e como o destinatário confere que o disparo veio daqui? F2 define só o gatilho — "quando uma pauta é encerrada". status: open
- **needs pre-written context.md** — yes

## Open Questions

- `pauta-account-signup` — Qual é a regra de senha exigida no cadastro — comprimento mínimo, classes de caracteres, lista de proibidas? A1 pede "e-mail e senha" e não define nenhuma regra. status: open
- `pauta-account-signup` — O link de confirmação pode ser reenviado, e o que a pessoa vê ao tentar entrar antes de confirmar — erro, ou tela pedindo reenvio? A1 exige a confirmação antes do primeiro login e não descreve nenhum dos dois casos. status: open
- `pauta-team-membership` — Como uma equipe passa a existir: qualquer pessoa cria a sua, ou as 6 equipes do piloto são provisionadas por fora? A Seção A descreve pertencimento (A2) e convite (A3), e nenhuma unidade do PRD descreve a criação de uma equipe. status: open
- `pauta-team-invites` — Quem pode gerar um convite: qualquer membro, ou só quem tem papel para isso? A3 fala em "convite por link" sem dizer quem convida, e A5 define papéis sem citar convite. status: open
- `pauta-team-invites` — O link é de uso único ou serve para várias pessoas entrarem na mesma equipe? A3 não distingue os dois. status: open
- `pauta-user-profile` — Onde o avatar fica guardado, e com que teto de tamanho e que formatos aceitos? A4 pede avatar editável, a restrição de container único não diz nada sobre arquivos, e nenhuma parte do PRD nomeia um destino de armazenamento. status: open
- `pauta-agenda-lifecycle` — Pautas em `rascunho` e `em reunião` aparecem em qual dos dois grupos da listagem? B5 separa futuras de encerradas e B2 define quatro estados, então dois deles não têm grupo. status: open
- `pauta-agenda-items` — Editar um item que já recebeu votos mantém os votos ou os zera? C5 libera a edição enquanto a pauta está aberta e C2 não fala de edição. status: open
- `pauta-agenda-items` — Retirar um item (C6) descarta os votos já dados nele, e é a mesma operação que A5 concede a quem pode "remover itens dos outros"? O PRD descreve as duas ações em seções diferentes e não diz se são a mesma. status: open
- `pauta-item-voting` — Qual é o critério de desempate quando dois itens têm o mesmo número de votos — mais antigo primeiro, menor tempo estimado, ordem de proposta? C3 ordena por votos e não trata empate, que com 40 pessoas será comum. status: open
- `pauta-item-voting` — Quem votou em um item é visível para a equipe, ou o voto é anônimo? C2 define um voto por pessoa e não diz se a autoria aparece. status: open
- `pauta-time-budget` — De onde vem a "duração prevista da reunião" com que C4 compara a soma? B1 registra título, equipe e data/hora prevista — nenhuma unidade do PRD registra duração, então o outro lado da comparação não tem fonte. status: open
- `pauta-team-roles` — Quais são os papéis dentro da equipe e quem atribui o papel de quem? A5 nomeia duas permissões e nenhum papel, e não diz quem é o primeiro a ter poder de atribuir. status: open
- `pauta-meeting-decisions` — O responsável por uma decisão precisa ser membro da equipe, e um item pode receber mais de uma decisão? D1 pede "uma decisão em texto livre e um responsável" sem restringir o responsável nem a quantidade. status: open
- `pauta-undiscussed-carryover` — Qual é "a próxima pauta da mesma equipe" quando existem várias em aberto, ou quando não existe nenhuma? D2 promete o clique e não define o destino. status: open
- `pauta-undiscussed-carryover` — Levar o item copia ou move, e os votos vão junto? D2 não diz, e B4 congela a pauta de origem no mesmo instante em que a marcação acontece. status: open
- `pauta-decision-search` — A busca cobre só o texto da decisão, ou também título e descrição do item que a originou? D3 diz "busca de decisões por texto" e não delimita o que entra no índice. status: open
- `pauta-notification-events` — "Uma pauta de que você participa" (E1) quer dizer qualquer pauta da equipe a que a pessoa pertence, ou algo mais estreito, como ter proposto ou votado nela? Nada no PRD define participação numa pauta. status: open
- `pauta-notification-events` — O aviso de E3 sai no instante em que a decisão é registrada ou no encerramento da pauta? E3 nomeia o destinatário e não o momento. status: open
- `pauta-meeting-reminder` — Com quanta antecedência o lembrete sai, e esse intervalo é fixo para o produto ou escolhido por pessoa ou por pauta? E2 diz apenas "antes da reunião". status: open
- `pauta-notification-preferences` — Cada tipo de aviso nasce ligado ou desligado para quem acabou de criar conta? E4 entrega o controle e não define o estado inicial. status: open
- `pauta-public-read-api` — A página de documentação de F3 fica aberta, ou exige a mesma credencial que F1? F3 pede a documentação e não diz quem pode abri-la. status: open
- `pauta-closure-webhook` — Quem cadastra a URL de destino, o que vai no corpo do disparo e como o destinatário confere que o disparo veio daqui? F2 define só o gatilho — "quando uma pauta é encerrada". status: open

## Expected Gray Areas

- `pauta-account-signup` — Auth boundaries & rate limits — o algoritmo de hash da senha sai do padrão documentado da biblioteca de segurança do próprio stack; não é escolha de produto.
- `pauta-user-profile` — project-specific — gravar instante em UTC e renderizar no fuso de cada pessoa é o padrão documentado das bibliotecas de data/hora do stack.
- `pauta-decision-search` — project-specific — que mecanismo indexa o texto é o recurso nativo já documentado do banco relacional fixado em `docs/PRD.md`, que roda no mesmo container único; nada aqui é decisão de negócio.
- `pauta-public-read-api` — project-specific — a referência OpenAPI já vem gerada pelo framework fixado em `docs/PRD.md`, que é o padrão documentado dele; não é escolha de produto.

## Coverage

| Scope-unit | Disposition |
|---|---|
| A1 | `pauta-account-signup` |
| A2 | `pauta-team-membership` |
| A3 | `pauta-team-invites` |
| A4 | `pauta-user-profile` |
| A5 | `pauta-team-roles` |
| B1 | `pauta-agenda-lifecycle` |
| B2 | `pauta-agenda-lifecycle` |
| B3 | `pauta-agenda-items` |
| B4 | `pauta-agenda-lifecycle` |
| B5 | `pauta-agenda-lifecycle` |
| C1 | `pauta-agenda-items` |
| C2 | `pauta-item-voting` |
| C3 | `pauta-item-voting` |
| C4 | `pauta-time-budget` |
| C5 | `pauta-agenda-items` |
| C6 | `pauta-agenda-items` |
| D1 | `pauta-meeting-decisions` |
| D2 | `pauta-undiscussed-carryover` |
| D3 | `pauta-decision-search` |
| E1 | `pauta-notification-events` |
| E2 | `pauta-meeting-reminder` |
| E3 | `pauta-notification-events` |
| E4 | `pauta-notification-preferences` |
| F1 | `pauta-public-read-api` |
| F2 | `pauta-closure-webhook` |
| F3 | `pauta-public-read-api` |

uncovered: none (0 deferred, 0 pre-existing, listed above)

## Execution Order

O PRD não declara incrementos, então não há linha de fronteira aqui. O grafo é quase uma fila:
contas → equipes → pautas → itens → votos → decisões, com uma bifurcação no fim, onde avisos (E) e
API pública (F) dependem do mesmo tronco e não um do outro.

```
pauta-account-signup
pauta-team-membership
pauta-team-invites
pauta-user-profile
pauta-agenda-lifecycle
pauta-agenda-items
pauta-item-voting
pauta-time-budget
pauta-team-roles
pauta-meeting-decisions
pauta-undiscussed-carryover
pauta-decision-search
pauta-notification-events
pauta-meeting-reminder
pauta-notification-preferences
pauta-public-read-api
pauta-closure-webhook
```
