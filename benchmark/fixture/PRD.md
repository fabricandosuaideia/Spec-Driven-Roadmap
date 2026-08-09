# Pauta — PRD v1

Ferramenta para equipes remotas prepararem reuniões de forma assíncrona. Em vez de a pauta nascer
no início da reunião, ela é construída antes: qualquer pessoa propõe um item, a equipe vota no que
importa, e a reunião começa por ordem de prioridade. Depois, as decisões ficam registradas ligadas
ao item que as originou.

**Stack:** backend em Python (FastAPI), frontend em React, banco relacional. Monorepo.

---

## Seção A — Contas e equipes

- **A1** — Cadastro por e-mail e senha. Confirmação de e-mail antes do primeiro login.
- **A2** — Uma pessoa pertence a uma ou mais equipes. Toda pauta pertence a exatamente uma equipe.
- **A3** — Convite para equipe por link. Quem já tem conta entra direto; quem não tem passa por A1.
- **A4** — Perfil editável: nome de exibição, fuso horário, avatar.
- **A5** — Papéis dentro da equipe: quem pode arquivar uma pauta e remover itens dos outros.

## Seção B — Pautas

- **B1** — Criar pauta com título, equipe e data/hora prevista da reunião.
- **B2** — Estados da pauta: rascunho, aberta para contribuição, em reunião, encerrada.
- **B3** — Só pauta *aberta* aceita item novo ou voto.
- **B4** — Encerrar uma pauta congela tudo: nada mais é editado, e ela vira leitura.
- **B5** — Listagem de pautas da equipe, separando as futuras das encerradas.

## Seção C — Itens e votação

- **C1** — Qualquer membro da equipe propõe um item: título, descrição, tempo estimado em minutos.
- **C2** — Um voto por pessoa por item. Votar de novo remove o voto.
- **C3** — A ordem da pauta é por número de votos, decrescente.
- **C4** — O tempo total da pauta é a soma dos tempos estimados, mostrado ao lado da duração prevista
  da reunião — quando passa, a interface avisa.
- **C5** — Item pode ser editado por quem o propôs enquanto a pauta estiver aberta.
- **C6** — Autor pode retirar o próprio item.

## Seção D — Decisões

- **D1** — Durante a reunião, cada item recebe uma decisão em texto livre e um responsável.
- **D2** — Item sem decisão ao encerrar a pauta é marcado "não discutido" e pode ser levado para a
  próxima pauta da mesma equipe com um clique.
- **D3** — Busca de decisões por texto, dentro da equipe.

## Seção E — Notificações

- **E1** — Aviso quando alguém propõe um item numa pauta de que você participa.
- **E2** — Lembrete antes da reunião com a pauta já ordenada.
- **E3** — Aviso a quem ficou responsável por uma decisão.
- **E4** — Cada pessoa liga e desliga cada tipo de aviso.

## Seção F — API pública

- **F1** — API REST autenticada para ler pautas e decisões de uma equipe.
- **F2** — Webhook disparado quando uma pauta é encerrada.
- **F3** — Documentação da API gerada a partir do código.

---

## Fora de escopo por agora

- Integração com Google Calendar / Outlook.
- Videoconferência embutida.
- Aplicativo móvel nativo.
- Pautas privadas dentro de uma equipe (toda pauta é visível para a equipe inteira).

## Restrições

- Precisa rodar em um único container para o piloto interno.
- O piloto tem 40 pessoas em 6 equipes.
